"""
MAKE-native Phoneme / Prosody Engine.

Provides:
- Text normalization (lowercasing, punctuation, number/abbreviation expansion)
- Sentence segmentation
- Grapheme-to-phoneme (rule-based + fallback dictionary)
- Phoneme duration prediction (stress, context, coarticulation)
- Pitch contour generation (intonation, emotional pitch, phrase contour)
- Prosody model (combine durations, pitch, pauses, breaths)
- ActingStyle (continuous performance controls)

All deterministic when seeded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import re
import numpy as np


# ARPAbet phoneme inventory
VOWELS = [
    "AA", "AE", "AH", "AO", "AW", "AY",
    "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW",
]

CONSONANTS = [
    "B", "CH", "D", "DH", "F", "G", "HH", "JH", "K", "L", "M", "N",
    "NG", "P", "R", "S", "SH", "T", "TH", "V", "W", "Y", "Z", "ZH",
]

STRESS_MARKERS = {"0", "1", "2"}

DEFAULT_PHONEME_DURATION_MS = 60.0
STRESSED_VOWEL_SCALE = 1.5
UNSTRESSED_VOWEL_SCALE = 0.8
CONSONANT_SCALE = 0.5
PAUSE_PERIOD_MS = 300.0
PAUSE_COMMA_MS = 150.0
PAUSE_PHRASE_MS = 100.0


class ActingStyle(Enum):
    NEUTRAL = "neutral"
    WHISPER = "whisper"
    SHOUT = "shout"
    HESITANT = "hesitant"
    SARCASTIC = "sarcastic"
    URGENT = "urgent"
    CONFIDENT = "confident"
    FEARFUL = "fearful"
    EXHAUSTED = "exhausted"
    EXCITED = "excited"
    CALM = "calm"
    INTIMATE = "intimate"
    DRAMATIC = "dramatic"


@dataclass
class Phoneme:
    symbol: str
    start_ms: float = 0.0
    duration_ms: float = DEFAULT_PHONEME_DURATION_MS
    is_vowel: bool = True
    is_stressed: bool = False
    voicing: float = 1.0
    amplitude: float = 1.0
    fundamental_freq: float = 120.0

    @property
    def end_ms(self) -> float:
        return self.start_ms + self.duration_ms


@dataclass
class Word:
    text: str
    phonemes: List[Phoneme] = field(default_factory=list)
    start_ms: float = 0.0
    end_ms: float = 0.0
    stress: float = 0.0


@dataclass
class Sentence:
    text: str
    words: List[Word] = field(default_factory=list)
    start_ms: float = 0.0
    end_ms: float = 0.0
    is_question: bool = False


class TextNormalizer:
    ABBREVIATIONS = {
        "mr": "mister",
        "mrs": "misses",
        "dr": "doctor",
        "prof": "professor",
        "st": "saint",
        "vs": "versus",
        "etc": "et cetera",
    }
    NUMBER_MAP = {
        "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
        "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
    }

    @staticmethod
    def normalize(text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"([,.])", r" \1 ", text)
        text = re.sub(r"([!?])", r" \1 ", text)
        for abbr, expanded in TextNormalizer.ABBREVIATIONS.items():
            text = re.sub(rf"\b{abbr}\b", expanded, text)
        text = re.sub(r"\b(\d+)\b", lambda m: TextNormalizer._expand_number(m.group(1)), text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _expand_number(num_str: str) -> str:
        if len(num_str) <= 3:
            parts = []
            for ch in num_str:
                parts.append(TextNormalizer.NUMBER_MAP.get(ch, ch))
            return " ".join(parts)
        return num_str


class SentenceSegmenter:
    @staticmethod
    def segment(text: str) -> List[Tuple[str, bool]]:
        sentences = []
        parts = re.split(r"([.!?])", text)
        current = ""
        for part in parts:
            if part in ".!?" and len(part) == 1:
                current += part
                is_question = part == "?"
                sentences.append((current.strip(), is_question))
                current = ""
            else:
                current += " " + part if current else part
        if current.strip():
            sentences.append((current.strip(), False))
        return sentences


class GraphemeToPhoneme:
    DICT = {
        "hello": ["HH", "AH0", "L", "OW1"],
        "world": ["W", "ER1", "L", "D"],
        "the": ["DH", "AH0"],
        "quick": ["K", "W", "IH1", "K"],
        "brown": ["B", "R", "AW1", "N"],
        "fox": ["F", "AA1", "K", "S"],
        "jumps": ["J", "H", "AH0", "M", "P", "S"],
        "over": ["OW1", "V", "ER0"],
        "lazy": ["L", "EY1", "Z", "IY0"],
        "dog": ["D", "AO1", "G"],
        "cat": ["K", "AE1", "T"],
        "run": ["R", "AH1", "N"],
        "test": ["T", "EH1", "S", "T"],
        "make": ["M", "E1", "Y", "K"],
        "audio": ["EY1", "D", "IY1", "OW0"],
        "hello": ["HH", "AH0", "L", "OW1"],
        "there": ["DH", "EH1", "R"],
        "how": ["HH", "AW1"],
        "are": ["AA1", "R"],
        "you": ["Y", "UW1"],
        "today": ["T", "AH0", "D", "EY1"],
        "good": ["G", "UH1", "D"],
        "morning": ["M", "AO1", "R", "N", "IH0", "NG"],
        "evening": ["IY1", "V", "N", "IH0", "NG"],
        "yes": ["Y", "EH1", "S"],
        "no": ["N", "OW1"],
        "please": ["P", "L", "IY1", "Z"],
        "thank": ["TH", "AE1", "NG", "K"],
        "you": ["Y", "UW1"],
        "sorry": ["S", "AA1", "R", "IY0"],
        "wait": ["W", "E1", "Y", "T"],
        "stop": ["S", "T", "AA1", "P"],
        "go": ["G", "OW1"],
        "come": ["K", "AH1", "M"],
        "here": ["HH", "IY1", "R"],
        "please": ["P", "L", "IY1", "Z"],
        "what": ["W", "AH1", "T"],
        "want": ["W", "AA1", "N", "T"],
        "need": ["N", "IY1", "D"],
        "can": ["K", "AE1", "N"],
        "will": ["W", "IH1", "L"],
        "would": ["W", "UH1", "D"],
        "could": ["K", "UW1", "D"],
        "should": ["SH", "UH1", "D"],
        "hello": ["HH", "AH0", "L", "OW1"],
        "hi": ["HH", "AY1"],
        "bye": ["B", "AY1"],
    }

    VOWEL_PHONEMES = set(VOWELS) | {v + s for v in VOWELS for s in STRESS_MARKERS}

    @classmethod
    def convert(cls, word: str) -> List[str]:
        word_lower = word.lower().strip(".,!?")
        if word_lower in cls.DICT:
            return list(cls.DICT[word_lower])
        return cls._fallback_g2p(word_lower)

    @classmethod
    def _fallback_g2p(cls, word: str) -> List[str]:
        if not word:
            return []
        result = []
        i = 0
        while i < len(word):
            matched = False
            if word[i] == "c" and i + 1 < len(word) and word[i + 1] in "ie":
                result.append("S")
                i += 2
                matched = True
            elif word[i] == "c" and i + 1 < len(word) and word[i + 1] == "k":
                result.append("K")
                i += 2
                matched = True
            elif word[i:i + 2] == "ch":
                result.append("CH")
                i += 2
                matched = True
            elif word[i:i + 2] == "sh":
                result.append("SH")
                i += 2
                matched = True
            elif word[i:i + 2] == "th":
                result.append("TH")
                i += 2
                matched = True
            elif word[i:i + 3] == "ing":
                result.extend(["IH0", "NG"])
                i += 3
                matched = True
            elif word[i:i + 2] == "ed" and i + 2 == len(word):
                result.append("T")
                i += 2
                matched = True
            elif word[i:i + 2] == "ly":
                result.append("L")
                i += 2
                matched = True
            elif word[i] in "aeiou":
                result.append(word[i].upper() + "0")
                i += 1
                matched = True
            elif word[i] in "bcdfghjklmnpqrstvwxyz":
                result.append(word[i].upper())
                i += 1
                matched = True
            else:
                i += 1
        return result

    @classmethod
    def is_vowel(cls, phoneme: str) -> bool:
        base = phoneme.rstrip("012")
        return base in VOWELS


class PitchContour:
    QUESTION_RISE = 1.3
    STATEMENT_FALL = 0.85
    WHISPER_PITCH = 0.8
    SHOUT_PITCH = 1.2
    HESITANT_WOBBLE = 0.15
    SARCASTIC_DIP = 0.7
    URGENT_BASE = 1.1
    FEARFUL_TREMOLO = 0.2

    @staticmethod
    def generate(
        num_phonemes: int,
        base_freq: float = 120.0,
        is_question: bool = False,
        acting: Optional[ActingStyle] = None,
        acting_intensity: float = 1.0,
    ) -> np.ndarray:
        t = np.linspace(0, 1, num_phonemes)
        freqs = np.ones(num_phonemes) * base_freq
        if is_question:
            freqs = np.linspace(base_freq, base_freq * PitchContour.QUESTION_RISE, num_phonemes)
        else:
            freqs = np.linspace(base_freq, base_freq * PitchContour.STATEMENT_FALL, num_phonemes)
        if acting == ActingStyle.WHISPER:
            freqs *= PitchContour.WHISPER_PITCH
        elif acting == ActingStyle.SHOUT:
            freqs *= PitchContour.SHOUT_PITCH
        elif acting == ActingStyle.URGENT:
            freqs *= PitchContour.URGENT_BASE
        elif acting == ActingStyle.HESITANT:
            wobble = acting_intensity * PitchContour.HESITANT_WOBBLE * np.sin(t * np.pi * 8)
            freqs = freqs * (1.0 + wobble)
        elif acting == ActingStyle.SARCASTIC:
            mid = num_phonemes // 2
            freqs[:mid] *= (1.0 + acting_intensity * 0.3)
            freqs[mid:] *= PitchContour.SARCASTIC_DIP
        elif acting == ActingStyle.FEARFUL:
            tremolo = np.sin(t * np.pi * 20) * acting_intensity * PitchContour.FEARFUL_TREMOLO
            freqs = freqs * (1.0 + tremolo)
        elif acting == ActingStyle.EXHAUSTED:
            freqs *= (1.0 - acting_intensity * 0.2)
            freqs[-int(num_phonemes * 0.3):] *= 0.85
        elif acting == ActingStyle.EXCITED:
            freqs *= (1.0 + acting_intensity * 0.3)
            t_local = np.linspace(0, 2 * np.pi, num_phonemes)
            freqs += np.sin(t_local) * acting_intensity * 5.0
        elif acting == ActingStyle.CALM:
            freqs *= 0.95
        elif acting == ActingStyle.INTIMATE:
            freqs *= 0.9
        elif acting == ActingStyle.DRAMATIC:
            freqs *= 1.15
            t_local = np.linspace(0, np.pi, num_phonemes)
            freqs += np.sin(t_local) * acting_intensity * 15.0
        return freqs


class PhonemeDuration:
    @staticmethod
    def predict(
        phoneme: str,
        is_stressed: bool = False,
        position: int = 0,
        total: int = 1,
        is_vowel: bool = True,
        context: Optional[str] = None,
        acting: Optional[ActingStyle] = None,
    ) -> float:
        base = DEFAULT_PHONEME_DURATION_MS
        if is_vowel:
            if is_stressed:
                base *= STRESSED_VOWEL_SCALE
            else:
                base *= UNSTRESSED_VOWEL_SCALE
        else:
            base *= CONSONANT_SCALE
        if position == 0:
            base *= 1.2
        elif position == total - 1:
            base *= 1.1
        if context == "before_pause":
            base *= 1.3
        if acting == ActingStyle.WHISPER:
            base *= 0.9
        elif acting == ActingStyle.SHOUT:
            base *= 0.85
        elif acting == ActingStyle.HESITANT:
            if is_stressed:
                base *= 1.4
        elif acting == ActingStyle.URGENT:
            base *= 0.8
        elif acting == ActingStyle.CALM:
            base *= 1.1
        elif acting == ActingStyle.EXCITED:
            base *= 0.9
        elif acting == ActingStyle.INTIMATE:
            base *= 1.2
        elif acting == ActingStyle.EXHAUSTED:
            base *= 1.3
        return base


class ProsodyModel:
    @staticmethod
    def build_prosody(
        phonemes: List[str],
        stress_pattern: List[int],
        is_question: bool = False,
        acting: Optional[ActingStyle] = None,
        acting_intensity: float = 1.0,
        speaking_rate: float = 1.0,
        add_breath: bool = True,
        base_amplitude: float = 0.6,
    ) -> List[Phoneme]:
        result: List[Phoneme] = []
        current_pos = 0.0
        total = len(phonemes)
        for i, ph in enumerate(phonemes):
            is_v = GraphemeToPhoneme.is_vowel(ph)
            is_stressed = stress_pattern[i] > 0 if i < len(stress_pattern) else False
            duration = PhonemeDuration.predict(
                ph, is_stressed, i, total, is_vowel=is_v,
                context="before_pause" if i == total - 1 else None,
                acting=acting,
            ) / speaking_rate
            freq = 120.0
            result.append(Phoneme(
                symbol=ph,
                start_ms=current_pos,
                duration_ms=duration,
                is_vowel=is_v,
                is_stressed=is_stressed,
                voicing=1.0,
                amplitude=base_amplitude,
                fundamental_freq=freq,
            ))
            current_pos += duration
        if total > 0:
            num_phones = len(result)
            if num_phones > 0:
                freqs = PitchContour.generate(
                    num_phones, base_freq=120.0,
                    is_question=is_question,
                    acting=acting, acting_intensity=acting_intensity,
                )
                for idx, ph in enumerate(result):
                    ph.fundamental_freq = float(freqs[idx])
                    if acting == ActingStyle.WHISPER:
                        ph.amplitude *= 0.4
                        ph.voicing = 0.3
                    elif acting == ActingStyle.SHOUT:
                        ph.amplitude = min(1.0, ph.amplitude * 2.0)
                    elif acting == ActingStyle.INTIMATE:
                        ph.amplitude *= 0.5
                    elif acting == ActingStyle.DRAMATIC:
                        ph.amplitude = min(1.0, ph.amplitude * 1.5)
        if add_breath and total > 0:
            breath = Phoneme(
                symbol="Breath",
                start_ms=current_pos,
                duration_ms=50.0,
                is_vowel=False,
                voicing=0.0,
                amplitude=0.3,
                fundamental_freq=0.0,
            )
            result.append(breath)
        return result

    @staticmethod
    def add_pause_after(sentence_end: bool, pause_ms: float = 0.0) -> float:
        if sentence_end:
            return PAUSE_PERIOD_MS
        return pause_ms

    @staticmethod
    def add_comma_pause() -> float:
        return PAUSE_COMMA_MS


class Phonemizer:
    @staticmethod
    def phonemize(text: str) -> List[Sentence]:
        normalized = TextNormalizer.normalize(text)
        segments = SentenceSegmenter.segment(normalized)
        sentences: List[Sentence] = []
        current_time = 0.0
        for seg_text, is_question in segments:
            words: List[Word] = []
            word_texts = seg_text.split()
            for w in word_texts:
                phones = GraphemeToPhoneme.convert(w)
                if not phones:
                    continue
                stress = []
                word_obj = Word(text=w, phonemes=[], stress=0.0)
                for p in phones:
                    clean_p = p.rstrip("012")
                    stress_marker = p[-1] if p[-1] in STRESS_MARKERS else "0"
                    stress_val = int(stress_marker)
                    stress.append(stress_val)
                    is_v = GraphemeToPhoneme.is_vowel(p)
                    word_obj.phonemes.append(Phoneme(
                        symbol=p,
                        start_ms=0.0,
                        is_vowel=is_v,
                        is_stressed=stress_val > 0,
                    ))
                words.append(word_obj)
            sentence = Sentence(text=seg_text, words=words, start_ms=current_time, is_question=is_question)
            for w in words:
                w.start_ms = current_time
                for ph in w.phonemes:
                    if w.stress == 0.0:
                        w.stress = max(w.stress, ph.is_stressed and 1.0 or 0.0)
                w.end_ms = current_time + sum(p.duration_ms for p in w.phonemes) if w.phonemes else current_time
                current_time = w.end_ms
            sentence.end_ms = current_time
            sentences.append(sentence)
            current_time += PAUSE_PERIOD_MS
        return sentences


def seed_from_text(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def generate_waveform(
    sentence: Sentence,
    sample_rate: int = 16000,
    acting: Optional[ActingStyle] = None,
    acting_intensity: float = 1.0,
    speaking_rate: float = 1.0,
    add_breath: bool = True,
) -> np.ndarray:
    """Generate a synthetic waveform from a phonemized sentence."""
    all_phonemes: List[Phoneme] = []
    current_offset = 0.0
    for word in sentence.words:
        word_phones = ProsodyModel.build_prosody(
            [p.symbol for p in word.phonemes],
            [p.is_stressed and 1 or 0 for p in word.phonemes],
            is_question=sentence.is_question,
            acting=acting,
            acting_intensity=acting_intensity,
            speaking_rate=speaking_rate,
            add_breath=False,
        )
        for ph in word_phones:
            ph.start_ms = current_offset
            current_offset += ph.duration_ms
            all_phonemes.append(ph)
    if add_breath:
        breath = Phoneme(
            symbol="Breath", start_ms=current_offset, duration_ms=50.0,
            is_vowel=False, voicing=0.0, amplitude=0.3,
        )
        all_phonemes.append(breath)
    total_ms = sum(p.duration_ms for p in all_phonemes)
    total_samples = int(total_ms * sample_rate / 1000.0)
    audio = np.zeros(total_samples, dtype=np.float32)
    pos = 0
    for ph in all_phonemes:
        n = int(ph.duration_ms * sample_rate / 1000.0)
        if n == 0:
            continue
        if ph.symbol == "Breath":
            envelope = np.linspace(0.3, 0.0, n)
            noise = np.random.RandomState(seed_from_text(ph.symbol + str(ph.start_ms))).randn(n)
            audio[pos:pos + n] = envelope * 0.05 * noise
        elif not ph.is_vowel:
            noise = np.random.RandomState(seed_from_text(ph.symbol + str(ph.start_ms))).randn(n)
            audio[pos:pos + n] = ph.amplitude * 0.3 * noise
        else:
            freq = ph.fundamental_freq
            t = np.arange(n) / sample_rate
            if acting == ActingStyle.WHISPER:
                noise = np.random.RandomState(seed_from_text("whisper" + ph.symbol)).randn(n)
                audio[pos:pos + n] = ph.amplitude * (0.4 * np.sin(2 * np.pi * freq * t) + 0.6 * noise * 0.1)
            else:
                audio[pos:pos + n] = ph.amplitude * np.sin(2 * np.pi * freq * t)
        pos += n
    if pos > 0:
        audio = np.clip(audio[:pos], -0.99, 0.99)
    return audio[:pos] if pos > 0 else np.zeros(1, dtype=np.float32)
