import json
import unittest

from intent_ai import ROOT, IntentClassifier
from parking_rules import decide_parking, make_request
from tasks import prepare_task


class IntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai = IntentClassifier()

    def test_holdout_is_not_training_data(self):
        training = json.loads((ROOT/'data'/'training.json').read_text(encoding='utf-8'))
        evaluation = json.loads((ROOT/'data'/'evaluation.json').read_text(encoding='utf-8'))
        texts = {text for examples in training.values() for text in examples}
        self.assertFalse(texts.intersection(case['text'] for case in evaluation))
        self.assertEqual(self.ai.evaluate()['correct'],len(evaluation))

    def test_same_height_different_intent_changes_destination(self):
        _, near = prepare_task('入口の近いところをお願いします',1.5,classifier=self.ai)
        _, any_slot = prepare_task('空いていればどこでも大丈夫です',1.5,classifier=self.ai)
        self.assertEqual((near['slot'],any_slot['slot']),('A','B'))

    def test_unrelated_and_empty_input_does_not_issue_motion(self):
        for text in ('', 'xyzqv', 'あいうえお', '明日の天気を教えて', 'a'*201):
            with self.subTest(text=text):
                _, result = prepare_task(text,1.5,classifier=self.ai)
                self.assertEqual(result['status'],'clarify')
                self.assertNotIn('destination_xy',result)

    def test_model_retrains_deterministically(self):
        self.assertEqual(self.ai.predict('入口の近く'),IntentClassifier().predict('入口の近く'))


if __name__ == '__main__':
    unittest.main()
