"""Compatibility Blender script; prefer asset_pipeline/adapters/blender/snapshot.py."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "asset_pipeline/adapters/blender/snapshot.py"), run_name="__main__")
