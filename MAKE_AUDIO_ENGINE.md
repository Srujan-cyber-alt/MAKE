# MAKE AUDIO ENGINE

Audio + Voice Superengine for MAKE AI Video.

## Capabilities

- Text-to-speech abstraction
- Voice selection
- Dialogue
- Voice cloning architecture where legally/technically supported
- Lip-sync architecture
- Music
- SFX
- Ambience
- Foley
- Ducking
- Normalization
- Mixing
- Mastering
- Captions
- Subtitles
- Multilingual output

## Natural Language Examples

| Command | Action |
|---------|--------|
| "Add cinematic music." | Background music generation |
| "Make dialogue remain clear." | Audio ducking |
| "Add Foley for footsteps." | Foley sound design |
| "Generate voiceover." | TTS generation |
| "Add captions." | Caption generation |

## API

Audio parameters are embedded in generation requests via:
- `POST /api/v1/phase12/make-auto`
- `POST /api/v1/phase12/command`

## Requirements

- Backend: `AudioSystem`, `CaptionSystem`
- Frontend: Audio timeline + mixer
