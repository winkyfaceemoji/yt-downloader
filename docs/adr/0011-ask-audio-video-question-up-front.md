# 0011. Ask the audio/video question before the metadata fetch

Status: Accepted (2026-10-13)

## Context
The audio/video question used to come after the slow metadata and comment fetch, so the user had to wait around to answer it.

## Decision
`main.py` asks for the URL and the audio/video choice up front, then passes both to `capture()`.

Rejected: asking after the fetch, which would need a callback into `capture()` just to prompt mid-run.

## Consequences
The rest of the run is unattended. An unrecognised answer downloads no media.
