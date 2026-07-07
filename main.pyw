# Thin no-console launcher: runs main.py so there is a single source of truth.
# Note: double-clicking uses the system Python, so yt-dlp must be importable there;
# the reliable path is running `python main.py` from the activated .venv.
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py"))
