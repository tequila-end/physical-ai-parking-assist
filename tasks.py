"""Connect inferred preference to deterministic parking constraints."""

from intent_ai import IntentClassifier
from parking_rules import DEMO_SLOTS, decide_parking, make_request


SCENARIOS = [
    {'title': '01 入口に近い区画へ', 'text': '入口の近いところをお願いします', 'height': 1.50, 'expected': 'A',
     'explanation': 'AIが「入口近く」と分類。車高と空車を確認し、区画Aへ移動します。'},
    {'title': '02 同じ車高でも要望で行き先変更', 'text': '空いていればどこでも大丈夫です', 'height': 1.50, 'expected': 'B',
     'explanation': 'AIが「指定なし」と分類。近い区画を残す運用ルールで、区画Bへ移動します。'},
    {'title': '03 車高制限を優先', 'text': '入口の近いところをお願いします', 'height': 2.00, 'expected': 'B',
     'explanation': '近くを希望しても車高制限を優先。区画Aを除外し、区画Bへ移動します。'},
    {'title': '04 対応区画が満車なら発進しない', 'text': '入口の近いところをお願いします', 'height': 2.20, 'expected': 'blocked',
     'explanation': '高さに対応できる区画Cは満車。移動命令を出さず、理由を表示します。'},
]


def prepare_task(text, height, slots=DEMO_SLOTS, classifier=None):
    inference = (classifier or IntentClassifier()).predict(text)
    request = make_request(height, inference['label'] or 'any', needs_clarification=not inference['accepted'])
    decision = decide_parking(request, slots)
    return inference, decision
