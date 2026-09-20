#!/usr/bin/env python3
"""CLI smoke-test for GoEmotions via EmotionAnalyzer."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emotion_analyzer import EmotionAnalyzer

text = " ".join(sys.argv[1:])
analyzer = EmotionAnalyzer()
emotions = analyzer.classify(text)
print(json.dumps(
    {label: round(score, 4) for label, score in emotions.items()},
    indent=2,
))
