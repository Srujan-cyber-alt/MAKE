# MAKE MODEL ROUTER

Model Orchestration 4.0 for MAKE AI Video.

## Routing Considerations

- Capability
- Task
- Image/video conditioning
- References
- Duration
- Resolution
- Aspect ratio
- Quality
- Latency
- Cost
- Provider health
- GPU availability
- Queue length
- Previous success rate

## Modes

| Mode | Priority |
|------|----------|
| AUTO | Balanced |
| FAST | Speed |
| QUALITY | Best output |
| CINEMATIC | Premium quality |
| CHEAP | Cost optimized |
| EXPERIMENTAL | Cutting edge |

## API

Model routing is handled internally by:
- `SmartModelRouterV3`
- `CapabilityRegistry`

Users never see provider complexity in normal mode.

## Requirements

- Backend: `SmartModelRouterV3`, `CapabilityRegistry`, `GenerativeModelAbstraction`
- Frontend: Advanced mode toggle (optional)
