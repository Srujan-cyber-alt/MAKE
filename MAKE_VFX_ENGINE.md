# MAKE VFX ENGINE

Advanced VFX System for MAKE AI Video.

## Effects

- Fire
- Smoke
- Fog
- Rain
- Snow
- Dust
- Sparks
- Explosions
- Lightning
- Magic
- Energy
- Particles
- Muzzle flash
- Atmosphere
- Lens effects
- Glow
- Volumetric light
- Environmental effects

## Layered Compositing

Every effect has:
- Timing
- Position
- Scale
- Intensity
- Blend mode
- Tracking
- Depth relationship

## Natural Language Examples

| Command | Action |
|---------|--------|
| "Add rain." | Rain overlay with tracking |
| "Make it foggy." | Atmospheric fog |
| "Add sparks." | Particle system |
| "Lightning strike." | Lightning effect with timing |
| "Glowing neon edges." | Edge glow VFX |

## API

VFX parameters are embedded in generation requests via:
- `POST /api/v1/phase12/video-to-video`
- `POST /api/v1/phase12/command`

## Requirements

- Backend: `VFXEngine`
- Frontend: VFX panel + layer timeline
