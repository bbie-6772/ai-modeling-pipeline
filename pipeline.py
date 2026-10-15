"""Compatibility entry point. New runs use python -m asset_pipeline."""
from asset_pipeline.legacy import bundle_digest, digest, local_file, main, validate

if __name__ == "__main__":
    raise SystemExit(main())
