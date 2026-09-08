# MAKE AUDIO — HUMAN EVALUATION PACK

## Overview

This pack defines scenarios for human evaluation of MAKE Audio outputs.

All evaluations must be conducted on CPU-generated reference outputs unless otherwise noted.

---

## 1. Voice Realism

**Scenario:** Listen to 10 voice samples generated from text prompts.

**Criteria:**
- Does the voice sound natural?
- Is there appropriate prosody?
- Are pitch variations realistic?
- Are breath sounds natural?

**Rating:** 1-5 (1 = completely artificial, 5 = indistinguishable from human)

---

## 2. Voice Consistency

**Scenario:** Generate 5 samples from the same voice ID with different text.

**Criteria:**
- Does the voice maintain consistent timbre?
- Are pitch characteristics stable?
- Is speaking rate consistent?

**Rating:** 1-5

---

## 3. Emotional Performance

**Scenario:** Generate the same text with 5 different emotion labels.

**Emotions:** happy, sad, angry, calm, excited

**Criteria:**
- Does the emotion come through in the audio?
- Is the emotional transition natural?
- Does intensity control work?

**Rating:** 1-5 per emotion

---

## 4. Dialogue Naturalness

**Scenario:** Generate a 2-speaker dialogue script (10 exchanges).

**Criteria:**
- Do speakers sound distinct?
- Is turn-taking natural?
- Are pauses appropriate?
- Does conversational flow feel real?

**Rating:** 1-5

---

## 5. Spatial Realism

**Scenario:** Place 3 sound sources at different positions in a stereo field.

**Criteria:**
- Can you localize each source?
- Does movement sound natural?
- Is the stereo image stable?

**Rating:** 1-5

---

## 6. Room Realism

**Scenario:** Apply 3 different room acoustics presets to the same voice.

**Rooms:** small room, large hall, outdoor

**Criteria:**
- Does the room character come through?
- Are reverb tails realistic?
- Does the voice sit naturally in the space?

**Rating:** 1-5 per room

---

## 7. Foley Synchronization

**Scenario:** Generate foley events synced to a 10-second video clip.

**Events:** footsteps, door, impact

**Criteria:**
- Are events timed to the action?
- Do sounds match the visual action?
- Is the overall effect cohesive?

**Rating:** 1-5

---

## 8. Ambience Quality

**Scenario:** Generate 30-second soundscapes for 3 environments.

**Environments:** forest, city, interior

**Criteria:**
- Does the environment feel immersive?
- Are layers well-balanced?
- Is there appropriate variation?

**Rating:** 1-5 per environment

---

## 9. Music Quality

**Scenario:** Generate 30-second music pieces in 3 genres.

**Genres:** ambient, electronic, orchestral

**Criteria:**
- Is the musical structure coherent?
- Are instruments distinguishable?
- Does the piece have dynamics?

**Rating:** 1-5 per genre

---

## 10. Editing Quality

**Scenario:** Replace a 2-second segment in a 10-second audio clip.

**Criteria:**
- Is the splice seamless?
- Does the replacement match the original context?
- Are there audible artifacts?

**Rating:** 1-5

---

## 11. Repair Quality

**Scenario:** Add noise to a clean audio clip, then repair it.

**Criteria:**
- Is noise removed effectively?
- Is the original signal preserved?
- Are there repair artifacts?

**Rating:** 1-5

---

## 12. Cinematic Mix Quality

**Scenario:** Mix dialogue, music, and ambience for a 30-second scene.

**Criteria:**
- Is dialogue intelligible?
- Does music duck appropriately?
- Are ambience and effects balanced?
- Is the overall mix cohesive?

**Rating:** 1-5

---

## Scoring Template

| Scenario | Rater 1 | Rater 2 | Rater 3 | Average |
|----------|---------|---------|---------|---------|
| Voice Realism | | | | |
| Voice Consistency | | | | |
| Emotional Performance | | | | |
| Dialogue Naturalness | | | | |
| Spatial Realism | | | | |
| Room Realism | | | | |
| Foley Synchronization | | | | |
| Ambience Quality | | | | |
| Music Quality | | | | |
| Editing Quality | | | | |
| Repair Quality | | | | |
| Cinematic Mix Quality | | | | |

**Minimum passing average:** 3.0/5.0
