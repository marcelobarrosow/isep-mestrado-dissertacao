"""GoEmotions classifier and operational ambivalence derivation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


GOEMOTIONS_MODEL = "SamLowe/roberta-base-go_emotions"
TAU = 0.10

POSITIVE_EMOTIONS = {
    "admiration", "amusement", "approval", "caring", "desire",
    "excitement", "gratitude", "joy", "love", "optimism",
    "pride", "relief",
}

NEGATIVE_EMOTIONS = {
    "anger", "annoyance", "disappointment", "disapproval",
    "disgust", "embarrassment", "fear", "grief",
    "nervousness", "remorse", "sadness",
}
# Neutral is excluded. Classifier scores for labels outside these sets
# may appear in raw_emotions; they do not enter the ambivalence rule or A.


@dataclass
class EmotionalContext:
    ambivalent: bool
    dominant_positive_emotion: Optional[str]
    dominant_negative_emotion: Optional[str]
    ambivalence_index: float


class EmotionAnalyzer:
    """GoEmotions classifier; runs on CPU."""

    def __init__(self, model_id: str = GOEMOTIONS_MODEL):
        from transformers import pipeline

        self.model_id = model_id
        self._clf = pipeline(
            task="text-classification",
            model=model_id,
            top_k=None,
            device=-1,
        )

    def classify(self, text: str) -> Dict[str, float]:
        result = self._clf(text)[0]
        return {item["label"]: float(item["score"]) for item in result}

    @staticmethod
    def dominant(emotions: Dict[str, float], group: set[str]) -> tuple[Optional[str], float]:
        candidates = {e: s for e, s in emotions.items() if e in group}
        if not candidates:
            return None, 0.0
        name = max(candidates, key=candidates.get)
        return name, candidates[name]

    def build_context(self, emotions: Dict[str, float], tau: float = TAU) -> EmotionalContext:
        pos_name, pos_score = self.dominant(emotions, POSITIVE_EMOTIONS)
        neg_name, neg_score = self.dominant(emotions, NEGATIVE_EMOTIONS)
        ambivalent = pos_score >= tau and neg_score >= tau
        return EmotionalContext(
            ambivalent=ambivalent,
            dominant_positive_emotion=pos_name if pos_score >= tau else None,
            dominant_negative_emotion=neg_name if neg_score >= tau else None,
            ambivalence_index=min(pos_score, neg_score) if ambivalent else 0.0,
        )

    def analyze(self, text: str, tau: float = TAU) -> Dict[str, Any]:
        emotions = self.classify(text)
        context = self.build_context(emotions, tau=tau)
        return {
            "emotion_model": self.model_id,
            "emotional_context": context,
            "raw_emotions": emotions,
        }
