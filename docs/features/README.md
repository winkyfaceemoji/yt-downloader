# Features

Per-feature deep dives describing the current state: architecture, data shapes and
invariants. For setup and running, see the [project README](../../README.md); for why
things are the way they are, see [DECISIONS.md](../DECISIONS.md).

| Feature | Doc | Source |
|---|---|---|
| English transcripts (JSON segments + readable `.txt`) | [transcripts.md](transcripts.md) | `transcript.py`, `main.py` (`save_metadata_and_transcript`) |
| Output layout (`Downloads/` folders, file names, audio format and tags) | [output-layout.md](output-layout.md) | `main.py` |
