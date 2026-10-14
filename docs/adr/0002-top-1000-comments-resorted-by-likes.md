# 0002. Top 1000 comments via YouTube's "top" sort, re-sorted by likes

Status: Accepted (2026-07-07)

## Context
YouTube offers only "top" and "newest" comment sorts, not "most liked". The true 1000 most-liked would mean fetching every comment: slow, with many more "Incomplete data received" retries on big videos.

## Decision
Fetch at most 1000 comments with `comment_sort=top` and `max_comments=1000`, then re-sort the saved comments by `like_count`, most-liked first.

Rejected: fetching every comment for an exact ranking.

## Consequences
Fast, but it may miss a highly-liked comment that YouTube's "top" sort didn't surface. yt-dlp sets `comment_count` to the number fetched, so `data.json` doesn't keep the video's real total.
