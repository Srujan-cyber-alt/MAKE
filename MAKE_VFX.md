# MAKE VFX

## Overview

VFX compositor applies visual effects layers to video using FFmpeg filter chains.

## Supported VFX Layers

- Fire
- Smoke
- Rain
- Snow
- Fog
- Sparks
- Lightning
- Glow
- Explosion
- Energy
- Atmospheric
- Debris
- Cinematic particles

## Blend Modes

- Normal
- Overlay
- Screen
- Multiply
- Add
- Soft light

## Usage

VFX layers are specified in transformation operations:

```json
{
  "type": "vfx_apply",
  "vfx_layers": [
    {
      "layer_type": "fire",
      "blend_mode": "screen",
      "opacity": 0.9,
      "intensity": 1.0,
      "duration_seconds": 3.0
    }
  ]
}
```

## Implementation

VFXCompositor generates FFmpeg filter chains for each layer and composites them onto the base video. All arguments are security-validated to prevent injection.

## Limitations

- VFX layers are procedural FFmpeg filters, not generative AI
- For AI-generated VFX, providers with VFX_GENERATION capability should be used
- Complex multi-layer compositions may require significant processing time
