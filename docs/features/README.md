# Features

Per-feature deep dives describing the current state: architecture, data shapes and
invariants. For setup and running, see the [project README](../../README.md); for why
things are the way they are, see [DECISIONS.md](../DECISIONS.md).

| Feature | Doc | Source |
|---|---|---|
| Capturing a video end to end (`capture()`, its seams and steps) | [capture.md](capture.md) | `capture.py`, `helpers.py`, `main.py` |
| English transcripts (JSON segments + readable `.txt`) | [transcripts.md](transcripts.md) | `transcript.py` |
| Output layout (`Downloads/` folders, file names, audio format and tags) | [output-layout.md](output-layout.md) | `video_folder.py`, `capture.py` |
