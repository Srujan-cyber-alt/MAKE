# MAKE Image Engine — Dataset

## Dataset Engine

MAKE Image includes a provenance-tracked dataset acquisition system for legally usable training data.

## License Policy

Only permissive licenses are accepted:
- CC0
- CC-BY
- CC-BY-4.0
- Public Domain
- Pixabay License
- Pexels License
- Coverr License
- Videvo License

Forbidden licenses:
- All Rights Reserved
- Copyright
- CC-BY-NC
- CC-BY-NC-4.0
- CC-BY-SA
- Unknown

## Features

- License validation
- SHA-256 hashing
- Deduplication
- Quality filtering
- Resolution filtering
- Provenance tracking
- Train/validation/test splits
- Manifest generation

## Current Dataset

| Item | Value |
|------|-------|
| Source | picsum.photos |
| License | Picsum License |
| Samples | 50 |
| Resolution | 256x256 to 512x512 |
| Manifest | dataset/manifest.json |
| Split | Not yet split |

## Script

```bash
python3 scripts/image_download_dataset.py --output-dir ./dataset --max-samples 100 --min-resolution 256
```

## Blocker

Production training requires millions of licensed images. Current dataset is 50 samples for pipeline validation only.
