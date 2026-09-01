# MAKE MEDIA PIPELINE

## Asset Upload

1. User uploads file via `/api/v1/assets/upload`
2. Storage service saves to `projects/{project_id}/{uuid}_{filename}`
3. Asset record created with `status=READY`
4. Media inspection extracts: duration, width, height, fps, codec, audio

## Asset Intelligence

Every asset receives:
- Object detection
- Segmentation
- Tracking
- Scene detection
- OCR
- Audio analysis
- Visual embeddings
- Identity embeddings
- Product embeddings
- Style embeddings

Stored in Redis with 7-day TTL.

## Semantic Search

Natural language queries like:
- "Show me all shots with the red sneaker."
- "Find the woman from the previous campaign."
- "Use the same location as scene 2."

Resolved via `AssetIntelligence.semantic_search()`.

## Generated Asset Registration

After generation:
1. Video downloaded to `/tmp/makeai_downloads/{job_id}.mp4`
2. FFprobe validates media info
3. File uploaded to storage
4. Asset record created with `asset_type=GENERATED`
5. Provenance metadata includes: provider, model, prompt, shot/scene/plan IDs

## Verification

- Asset upload tested
- Asset registration tested
- Media inspection tested
- Capability registry tested
