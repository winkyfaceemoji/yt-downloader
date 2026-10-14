"""Small pure helpers used by the capture module."""


def sort_comments(comments):
    """Most-liked first; a missing like_count counts as 0."""
    return sorted(comments or [], key=lambda c: int(c.get('like_count') or 0), reverse=True)


def parse_choice(answer):
    """'a' / 'v' / 'b' (or the full words, any case/spacing) -> (want_audio, want_video)."""
    answer = answer.strip().lower()
    return answer in ('a', 'audio', 'b', 'both'), answer in ('v', 'video', 'b', 'both')


def is_playlist(result):
    """True for an unprocessed yt-dlp result that is a playlist rather than one video."""
    return result.get('_type') in ('playlist', 'multi_video')


def parse_yes(answer):
    """'y' / 'yes' in any case or spacing -> True; anything else -> False."""
    return answer.strip().lower() in ('y', 'yes')
