// ------------------------------------------------------------------
// Avatar color class — deterministic from user id
// ------------------------------------------------------------------
function avatarClass(userId) {
    return 'av-' + (userId % 5);
}

// Build a default avatar element — Twitter-style person silhouette
function buildDefaultAvatar(size) {
    size = size || 42;
    var div = document.createElement('div');
    div.className = 'avatar-circle avatar-default';
    div.style.width = size + 'px';
    div.style.height = size + 'px';
    div.setAttribute('aria-hidden', 'true');
    div.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor" style="width:60%;height:60%"><path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/></svg>';
    return div;
}

function buildAvatar(user, size) {
    size = size || 42;
    if (user.avatar_url) {
        var img = document.createElement('img');
        img.src = user.avatar_url;
        img.className = 'avatar-img';
        img.style.width = size + 'px';
        img.style.height = size + 'px';
        img.setAttribute('aria-hidden', 'true');
        img.alt = '';
        return img;
    }
    // No avatar_url → Twitter-style default silhouette
    return buildDefaultAvatar(size);
}

// ------------------------------------------------------------------
// Relative timestamp
// ------------------------------------------------------------------
function timeAgo(dateStr) {
    if (!dateStr) return '';
    // SQLite returns "2026-03-16 15:00:00" — we need "2026-03-16T15:00:00Z"
    // Using 'T' between date and time is required for reliable cross-browser parsing.
    var normalized = dateStr.endsWith('Z') ? dateStr : dateStr.replace(' ', 'T') + 'Z';
    var date = new Date(normalized);
    if (isNaN(date.getTime())) return dateStr; // fallback if unparseable

    var now = new Date();
    var diffMs = now - date;
    var diffSec = Math.floor(diffMs / 1000);

    if (diffSec < 0)  return 'たった今'; // future timestamp (clock skew or seed data)
    if (diffSec < 10) return 'たった今';
    if (diffSec < 60) return diffSec + '秒';

    var diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return diffMin + '分';

    var diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return diffHr + '時間';

    var diffDay = Math.floor(diffHr / 24);
    if (diffDay < 7) return diffDay + '日';

    // Older than a week: show "3月15日" style
    return date.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' });
}

// ------------------------------------------------------------------
// Format large counts (e.g. 12345 → "1.2万", 1500 → "1.5K")
// ------------------------------------------------------------------
function formatCount(n) {
    if (n >= 10000) return (n / 10000).toFixed(1) + '万';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
}

// ------------------------------------------------------------------
// Image zoom modal
// ------------------------------------------------------------------
function showImageModal(url) {
    document.getElementById('image-modal-img').src = url;
    document.getElementById('image-modal').style.display = 'flex';
}
