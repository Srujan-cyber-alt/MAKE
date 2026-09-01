# MAKE CAMERA ENGINE

Camera Control Superengine for MAKE AI Video.

## Movements

- Dolly
- Push in
- Pull out
- Orbit
- Pan
- Tilt
- Crane
- Truck
- Tracking
- Handheld
- Steadicam
- Drone
- FPV
- Whip pan
- Rack focus
- Zoom
- Dolly zoom

## Professional Controls

- Focal length
- Aperture
- Depth of field
- Shutter look
- Camera height
- Camera distance
- Camera angle
- Framing
- Composition
- Movement speed

## Natural Language Examples

| Command | Action |
|---------|--------|
| "Slowly push into the product." | Dolly in, slow speed |
| "Orbit around the woman while keeping her centered." | Orbit, subject tracking |
| "Give it a 24mm cinematic wide shot." | 24mm lens, wide composition |
| "Handheld documentary feel." | Handheld movement, organic motion |

## API

Camera parameters are embedded in generation requests via:
- `POST /api/v1/phase12/image-to-video`
- `POST /api/v1/phase12/video-to-video`
- `POST /api/v1/phase12/command`

## Requirements

- Backend: `CameraControlEngine`, `KeyframeSystemV2`
- Frontend: Camera controls panel + preview
