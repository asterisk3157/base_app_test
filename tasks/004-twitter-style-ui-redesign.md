---
id: 004
title: "Twitter-style UI redesign"
assignee: frontend-agent
status: done
priority: high
depends_on: 002
created: 2026-03-16
---

## Description

Complete UI overhaul to Twitter-style layout: Left sidebar (logo, nav items: Home, Explore, Profile placeholder), Center timeline (tweet compose box at top with avatar + textarea + Tweet button, scrollable tweet feed below), Right sidebar (trending placeholder, bot accounts panel with 'Generate Bot Tweet' button). Each tweet card shows: avatar circle, display name (bold), handle (@gray), timestamp, content text, like button with count. Dark theme option. Mobile responsive (sidebar collapses). Keep the intentional innerHTML XSS vulnerability for tweet content rendering. Use CSS grid for the 3-column layout.

## Acceptance criteria

- [ ] Implementation complete
- [ ] No regressions introduced
- [ ] Code follows project conventions

## Result

Implemented a complete Twitter-style dark-theme UI in `templates/index.html`.

- CSS Grid 3-column layout: left sidebar (250px), center timeline (1fr), right sidebar (300px).
- Left sidebar: bird SVG logo, Home/Explore/Profile nav items with icons, Tweet button.
- Center timeline: sticky header, compose box with "Y" avatar circle, 280-char textarea with live counter (warn at 260+, disable at 280), Tweet submit button.
- Tweet cards: avatar circle (color-coded by user id mod 5), display name, handle, relative timestamp, content, like button with heart SVG and count, BOT badge for bot users.
- Right sidebar: Bot Tweets panel with avatar list of bot accounts, Generate Bot Tweet button, Trending placeholder section.
- Responsive: collapses sidebar labels at 1024px, hides both sidebars at 768px (375px mobile shows only timeline).
- Slide-in animation (0.35s) on new tweet cards; hover effects on all interactive elements.
