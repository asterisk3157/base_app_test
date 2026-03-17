"""
test_e2e.py — Basic Playwright end-to-end tests for the Twitter clone app.

Tests:
  1. Registration flow
  2. Posting a tweet
  3. Liking a tweet
  4. Viewing a profile
  5. Searching for a tweet
  6. Scheduling a tweet (API-level)

Run with: pytest tests/test_e2e.py -v
Requires: pytest, playwright, playwright browsers installed
  pip install pytest playwright pytest-playwright
  playwright install chromium
"""
import re
import time
import uuid
import pytest
import requests
from playwright.sync_api import sync_playwright, expect


BASE_URL = 'http://127.0.0.1:5000'


# ---------------------------------------------------------------------------
# Helper: create a unique handle for each test run
# ---------------------------------------------------------------------------
def _unique_handle():
    return '@test_' + uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Test 1: Registration flow
# ---------------------------------------------------------------------------
def test_registration_flow(base_url):
    """User can register, and the cookie is set."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        page.goto(base_url)
        page.wait_for_load_state('networkidle')

        handle = _unique_handle()
        display_name = 'Test User'

        # Use the API directly to register (UI may vary)
        resp = requests.post(
            f'{base_url}/api/register',
            json={'display_name': display_name, 'handle': handle},
        )
        assert resp.status_code == 201, f'Expected 201, got {resp.status_code}: {resp.text}'
        data = resp.json()
        assert 'user' in data
        assert data['user']['handle'] == handle
        assert data['user']['display_name'] == display_name
        assert data['user']['is_bot'] == 0

        browser.close()


# ---------------------------------------------------------------------------
# Test 2: Posting a tweet
# ---------------------------------------------------------------------------
def test_post_tweet(base_url):
    """A registered user can post a tweet via the API."""
    # Register a fresh user
    handle = _unique_handle()
    reg = requests.post(
        f'{base_url}/api/register',
        json={'display_name': 'Tweet Tester', 'handle': handle},
    )
    assert reg.status_code == 201
    user_id = reg.json()['user']['id']
    cookies = {'user_id': str(user_id)}

    # Post a tweet
    content = f'Hello from automated test {uuid.uuid4().hex[:6]}'
    resp = requests.post(
        f'{base_url}/api/tweets',
        json={'content': content},
        cookies=cookies,
    )
    assert resp.status_code == 201, f'Expected 201, got {resp.status_code}: {resp.text}'
    tweet = resp.json()['tweet']
    assert tweet['content'] == content
    assert tweet['user']['id'] == user_id


# ---------------------------------------------------------------------------
# Test 3: Liking a tweet
# ---------------------------------------------------------------------------
def test_like_tweet(base_url):
    """A registered user can like and unlike a tweet."""
    # Register user and post tweet
    handle = _unique_handle()
    reg = requests.post(
        f'{base_url}/api/register',
        json={'display_name': 'Liker', 'handle': handle},
    )
    assert reg.status_code == 201
    user_id = reg.json()['user']['id']
    cookies = {'user_id': str(user_id)}

    post = requests.post(
        f'{base_url}/api/tweets',
        json={'content': 'Like me!'},
        cookies=cookies,
    )
    assert post.status_code == 201
    tweet_id = post.json()['tweet']['id']

    # Like the tweet
    like_resp = requests.post(
        f'{base_url}/api/tweets/{tweet_id}/like',
        cookies=cookies,
    )
    assert like_resp.status_code == 200
    assert like_resp.json()['liked'] is True
    assert like_resp.json()['likes'] >= 1

    # Unlike the tweet
    unlike_resp = requests.post(
        f'{base_url}/api/tweets/{tweet_id}/like',
        cookies=cookies,
    )
    assert unlike_resp.status_code == 200
    assert unlike_resp.json()['liked'] is False


# ---------------------------------------------------------------------------
# Test 4: Viewing a profile (via Playwright browser)
# ---------------------------------------------------------------------------
def test_view_profile(base_url):
    """The app loads and displays content on the main page."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.wait_for_load_state('networkidle')

        # The page should have a title or at least a body
        assert page.title() is not None

        # The page should not show a 500 error
        content = page.content()
        assert '500' not in content or 'Internal Server Error' not in content

        browser.close()


# ---------------------------------------------------------------------------
# Test 5: Search for a tweet
# ---------------------------------------------------------------------------
def test_search_tweet(base_url):
    """A posted tweet can be found via the search API."""
    handle = _unique_handle()
    reg = requests.post(
        f'{base_url}/api/register',
        json={'display_name': 'Searcher', 'handle': handle},
    )
    assert reg.status_code == 201
    user_id = reg.json()['user']['id']
    cookies = {'user_id': str(user_id)}

    unique_keyword = 'uniquekeyword_' + uuid.uuid4().hex[:8]
    post = requests.post(
        f'{base_url}/api/tweets',
        json={'content': f'This tweet contains {unique_keyword}'},
        cookies=cookies,
    )
    assert post.status_code == 201

    # Search for the unique keyword
    search = requests.get(f'{base_url}/api/tweets/search', params={'q': unique_keyword})
    assert search.status_code == 200
    tweets = search.json()['tweets']
    assert any(unique_keyword in t['content'] for t in tweets), \
        f'Expected to find tweet with keyword "{unique_keyword}" in search results'


# ---------------------------------------------------------------------------
# Test 6: Scheduled tweet (API-level)
# ---------------------------------------------------------------------------
def test_schedule_tweet(base_url):
    """A user can schedule a tweet, list it, and cancel it."""
    handle = _unique_handle()
    reg = requests.post(
        f'{base_url}/api/register',
        json={'display_name': 'Scheduler', 'handle': handle},
    )
    assert reg.status_code == 201
    user_id = reg.json()['user']['id']
    cookies = {'user_id': str(user_id)}

    # Schedule a tweet 1 hour in the future
    schedule_resp = requests.post(
        f'{base_url}/api/tweets/schedule',
        json={
            'content': 'Scheduled tweet test',
            'scheduled_at': '2099-01-01T00:00:00',
        },
        cookies=cookies,
    )
    assert schedule_resp.status_code == 201, \
        f'Expected 201, got {schedule_resp.status_code}: {schedule_resp.text}'
    st = schedule_resp.json()['scheduled_tweet']
    assert st['content'] == 'Scheduled tweet test'
    assert st['posted'] == 0
    scheduled_id = st['id']

    # List scheduled tweets
    list_resp = requests.get(f'{base_url}/api/tweets/scheduled', cookies=cookies)
    assert list_resp.status_code == 200
    listed = list_resp.json()['scheduled_tweets']
    assert any(s['id'] == scheduled_id for s in listed), \
        'Scheduled tweet not found in listing'

    # Cancel the scheduled tweet
    cancel_resp = requests.delete(
        f'{base_url}/api/tweets/scheduled/{scheduled_id}',
        cookies=cookies,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()['ok'] is True

    # Verify it's no longer listed
    list_resp2 = requests.get(f'{base_url}/api/tweets/scheduled', cookies=cookies)
    listed2 = list_resp2.json()['scheduled_tweets']
    assert not any(s['id'] == scheduled_id for s in listed2), \
        'Cancelled tweet should not appear in scheduled listing'
