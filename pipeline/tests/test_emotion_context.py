import unittest

from emotion_analyzer import EmotionAnalyzer, TAU


class TestEmotionContext(unittest.TestCase):
    def setUp(self):
        self.analyzer = EmotionAnalyzer.__new__(EmotionAnalyzer)

    def test_ambivalent_when_both_valences_meet_tau(self):
        scores = {"joy": 0.40, "fear": 0.40, "neutral": 0.90}
        ctx = self.analyzer.build_context(scores, tau=TAU)
        self.assertTrue(ctx.ambivalent)
        self.assertEqual(ctx.dominant_positive_emotion, "joy")
        self.assertEqual(ctx.dominant_negative_emotion, "fear")
        self.assertEqual(ctx.ambivalence_index, 0.40)

    def test_not_ambivalent_below_tau(self):
        scores = {"joy": 0.40, "fear": 0.05}
        ctx = self.analyzer.build_context(scores, tau=TAU)
        self.assertFalse(ctx.ambivalent)
        self.assertEqual(ctx.dominant_positive_emotion, "joy")
        self.assertIsNone(ctx.dominant_negative_emotion)
        self.assertEqual(ctx.ambivalence_index, 0.0)

    def test_index_is_min_of_dominant_scores(self):
        scores = {"pride": 0.80, "sadness": 0.12}
        ctx = self.analyzer.build_context(scores, tau=TAU)
        self.assertTrue(ctx.ambivalent)
        self.assertEqual(ctx.ambivalence_index, 0.12)

    def test_neutral_does_not_enter_rule(self):
        scores = {"neutral": 0.99, "joy": 0.20, "anger": 0.20}
        ctx = self.analyzer.build_context(scores, tau=TAU)
        self.assertTrue(ctx.ambivalent)
        self.assertEqual(ctx.dominant_positive_emotion, "joy")
        self.assertEqual(ctx.dominant_negative_emotion, "anger")


if __name__ == "__main__":
    unittest.main()
