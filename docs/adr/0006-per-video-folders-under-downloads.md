# 0006. Per-video folders under Downloads/, anchored to main.py

Status: Accepted (2026-10-13)

## Context
Output went to per-type `Data/`, `Audio/` and `Video/` folders, relative to the working directory. The data is meant to be reused in other projects.

## Decision
Everything for a video goes in `Downloads/<title> [<id>]/`, next to `main.py`. A re-run overwrites everything, re-downloading media. The JSON's `epoch` field records the fetch time, so no date goes into names.

Rejected: one flat shared folder (long names, and a video's files are grouped only by sort order) and per-type folders (one video spread over four places).

## Consequences
The video ID keeps folder names unique. Running the script from another directory still writes to the project's `Downloads/`.
