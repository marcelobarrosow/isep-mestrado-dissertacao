import unittest

from emotion_analyzer import EmotionalContext
from prompts import build_contextual_prompt, build_direct_prompt


USER = (
    "I am so proud and happy about this promotion, but I am "
    "also scared and anxious that everyone will soon see that I "
    "do not deserve it."
)

CTX = EmotionalContext(
    ambivalent=True,
    dominant_positive_emotion="joy",
    dominant_negative_emotion="fear",
    ambivalence_index=0.40,
)

CTX_NONE = EmotionalContext(
    ambivalent=False,
    dominant_positive_emotion=None,
    dominant_negative_emotion=None,
    ambivalence_index=0.0,
)


class TestPrompts(unittest.TestCase):
    def test_direct_causal(self):
        prompt = build_direct_prompt(USER, arch="causal_dialogue")
        self.assertTrue(prompt.startswith("User: "))
        self.assertTrue(prompt.endswith("Assistant:"))
        self.assertNotIn("ambivalent", prompt)

    def test_direct_seq2seq_is_bare_text(self):
        self.assertEqual(build_direct_prompt(USER, arch="seq2seq"), USER)

    def test_direct_chat_has_length_instruction(self):
        prompt = build_direct_prompt(USER, arch="chat")
        self.assertIn("conversational assistant", prompt)
        self.assertIn("2 to 4 complete sentences", prompt)
        self.assertNotIn("emotional ambivalence", prompt)

    def test_contextual_causal_injects_pair(self):
        prompt = build_contextual_prompt(USER, CTX, arch="causal_dialogue")
        self.assertIn("(The user seems ambivalent: joy and fear.)", prompt)

    def test_contextual_seq2seq_suffix(self):
        prompt = build_contextual_prompt(USER, CTX, arch="seq2seq")
        self.assertTrue(prompt.endswith("[emotional ambivalence: joy and fear]"))

    def test_contextual_chat_metadata_block(self):
        prompt = build_contextual_prompt(USER, CTX, arch="chat")
        self.assertIn("dominant positive emotion is joy", prompt)
        self.assertIn("dominant negative emotion is fear", prompt)
        self.assertIn("Do not mention the emotional analysis", prompt)

    def test_contextual_chat_without_ambivalence(self):
        prompt = build_contextual_prompt(USER, CTX_NONE, arch="chat")
        self.assertIn("No clear emotional ambivalence was detected.", prompt)


if __name__ == "__main__":
    unittest.main()
