# Heartbeat Tasks

This file is checked every 30 minutes by Finclaw.
Add tasks below that you want Finclaw to work on periodically.

If this file has no active tasks (only headers and comments), the heartbeat will be skipped.

## Active Tasks

- Check WATCHLIST.md for any stocks that haven't had a price update today. For those, call stock_quote and record the latest price with watchlist add_note. Alert the user if any stock has moved >2% since the last check.
- Scan stock_news for any watched stocks where there's major news (earnings, guidance, M&A, regulatory, leadership change). If found, form an updated opinion and notify the user.

## Completed

<!-- Move completed tasks here or delete them -->

