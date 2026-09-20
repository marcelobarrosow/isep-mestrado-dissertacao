import unittest

from quality import is_response_acceptable, response_quality_issues


OK = (
    "I hear how proud you are of this step, and also how scared you feel "
    "that others might judge you. Those two feelings can sit together. "
    "It makes sense to want support while you settle into the new role."
)


class TestQuality(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(response_quality_issues(""), ["empty"])
        self.assertEqual(response_quality_issues("   "), ["empty"])

    def test_acceptable_instruct_reply(self):
        self.assertEqual(response_quality_issues(OK, epoch_id="E3"), [])
        self.assertTrue(is_response_acceptable(OK, epoch_id="E3"))

    def test_e1_allows_shorter_finished_sentence(self):
        short = "I am proud of you."
        self.assertEqual(response_quality_issues(short, epoch_id="E1"), [])
        self.assertIn("too_short", response_quality_issues(short, epoch_id="E3"))

    def test_incomplete_ending(self):
        text = "I hear that you are proud but still worried about"
        flags = response_quality_issues(text, epoch_id="E3")
        self.assertIn("incomplete_ending", flags)
        self.assertIn("too_short", flags)

    def test_garbage_repetition(self):
        text = "sorry sorry sorry sorry sorry sorry sorry sorry sorry sorry sorry sorry."
        self.assertIn("garbage", response_quality_issues(text, epoch_id="E3"))


if __name__ == "__main__":
    unittest.main()
