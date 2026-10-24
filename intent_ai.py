"""Local learned text classifier: character n-grams + multinomial Naive Bayes.

No keyword-to-label rules, pretrained LLM, cloud service, or ML dependency.
The score is an uncalibrated model score, not a guarantee of correctness.
"""

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LABEL_NAMES = {'near_entrance': '入口近くを希望', 'any': '場所の指定なし'}


def features(text):
    normalized = unicodedata.normalize('NFKC', text).lower()
    normalized = re.sub(r'[\W\d_]+', '', normalized)
    return Counter([normalized[i:i + n] for n in (1, 2) for i in range(len(normalized) - n + 1)])


class IntentClassifier:
    def __init__(self, path=None):
        data = json.loads(Path(path or ROOT / 'data' / 'training.json').read_text(encoding='utf-8'))
        self.counts = {}
        self.document_counts = {}
        for label, examples in data.items():
            counts = Counter()
            for example in examples:
                counts.update(features(example))
            self.counts[label] = counts
            self.document_counts[label] = len(examples)
        self.vocabulary = set().union(*(counts.keys() for counts in self.counts.values()))
        self.totals = {label: sum(counts.values()) for label, counts in self.counts.items()}

    def predict(self, text):
        if not isinstance(text, str) or len(text) > 200:
            return {'accepted': False, 'label': None, 'score': 0.0, 'reason': '200文字以内の要望を入力してください。'}
        tokens = features(text)
        known = {token: count for token, count in tokens.items() if token in self.vocabulary}
        known_bigrams = sum(1 for token in known if len(token) == 2)
        coverage = sum(known.values()) / max(1, sum(tokens.values()))
        scores = {}
        documents = sum(self.document_counts.values())
        for label, counts in self.counts.items():
            score = math.log(self.document_counts[label] / documents)
            denominator = self.totals[label] + len(self.vocabulary)
            score += sum(count * math.log((counts[token] + 1) / denominator) for token, count in known.items())
            scores[label] = score
        best = max(scores, key=scores.get)
        probability = 1 / sum(math.exp(score - scores[best]) for score in scores.values())
        accepted = bool(known_bigrams >= 2 and coverage >= .45 and probability >= .80)
        return {'accepted': accepted, 'label': best if accepted else None,
                'score': round(probability, 4), 'known_bigram_count': known_bigrams,
                'coverage': round(coverage, 4),
                'reason': LABEL_NAMES[best] if accepted else '要望を判断できません。入口近くを希望するか、場所の指定がないかを入力してください。'}

    def evaluate(self):
        cases = json.loads((ROOT / 'data' / 'evaluation.json').read_text(encoding='utf-8'))
        predictions = []
        for case in cases:
            result = self.predict(case['text'])
            predictions.append({**case, 'prediction': result, 'correct': result['label'] == case['label']})
        correct = sum(item['correct'] for item in predictions)
        return {'method': 'character unigram/bigram multinomial Naive Bayes, Laplace smoothing',
                'training_examples': sum(self.document_counts.values()), 'evaluation_examples': len(cases),
                'correct': correct, 'accuracy': correct / len(cases),
                'note': 'Small manually authored holdout set; not evidence of unrestricted Japanese language understanding.',
                'predictions': predictions}


if __name__ == '__main__':
    print(json.dumps(IntentClassifier().evaluate(), ensure_ascii=False, indent=2))
