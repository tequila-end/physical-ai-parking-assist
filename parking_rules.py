"""Parking task decisions, independent of AI providers and ROS.

Run `python parking_rules.py` for fixtures only: no AI call or robot motion.
"""

import json
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ParkingSlot:
    name: str
    max_height_m: float
    occupied: bool
    distance_from_entrance: float
    destination_xy: tuple[float, float]


# Fictional layout. Destination coordinates must be matched to the simulator.
DEMO_SLOTS = (
    ParkingSlot("A", 1.55, False, 2.0, (0.0, 1.5)),
    ParkingSlot("B", 2.10, False, 4.0, (2.0, 1.5)),
    ParkingSlot("C", 2.30, True, 6.0, (4.0, 1.5)),
)


def decide_parking(request: dict, slots=DEMO_SLOTS) -> dict:
    """Validate interpreted conditions, then select an available slot.

    This is a classroom simulation rule, not a real vehicle safety controller.
    Only 'ready' permits a later motion controller to receive a destination.
    """
    if not isinstance(request, dict):
        return {"status": "invalid", "reason": "request must be an object"}
    expected = {"vehicle_height_m", "preference", "needs_clarification"}
    if set(request) != expected:
        return {"status": "invalid", "reason": "unexpected or missing fields"}
    if type(request["needs_clarification"]) is not bool:
        return {"status": "invalid", "reason": "needs_clarification must be boolean"}
    if request["needs_clarification"] or request["vehicle_height_m"] is None:
        return {"status": "clarify", "reason": "車高など、指示の不明点を確認してください。"}
    height = request["vehicle_height_m"]
    if type(height) not in (int, float) or not math.isfinite(height) or height <= 0:
        return {"status": "invalid", "reason": "vehicle height must be a positive finite number"}
    if request["preference"] not in ("near_entrance", "any"):
        return {"status": "invalid", "reason": "unsupported preference"}

    compatible = [slot for slot in slots if height <= slot.max_height_m]
    if not compatible:
        return {"status": "blocked", "reason": "車高に適合する区画がありません。"}
    available = [slot for slot in compatible if not slot.occupied]
    if not available:
        return {"status": "blocked", "reason": "車高に適合する区画は満車です。"}
    if request["preference"] == "near_entrance":
        selected = min(available, key=lambda slot: (slot.distance_from_entrance, slot.name))
    else:
        # Keep entrance-adjacent spaces available for users who request them.
        selected = max(available, key=lambda slot: (slot.distance_from_entrance, slot.name))
    return {
        "status": "ready",
        "slot": selected.name,
        "destination_xy": selected.destination_xy,
        "reason": f"区画{selected.name}は空車で、車高{height:.2f}mに対応しています。",
    }


def make_request(height, preference="near_entrance", needs_clarification=False):
    return {
        "vehicle_height_m": height,
        "preference": preference,
        "needs_clarification": needs_clarification,
    }


def main():
    print("FIXTURE DEMO: no AI inference, no ROS, no robot motion")
    examples = (
        ("車高1.50m、入口近く", make_request(1.50)),
        ("車高2.00m、入口近く", make_request(2.00)),
        ("車高2.20m、対応区画は満車", make_request(2.20)),
        ("背の高い車（具体的な車高不明）", make_request(None, needs_clarification=True)),
    )
    for label, request in examples:
        print(label)
        print(json.dumps(decide_parking(request), ensure_ascii=False))


if __name__ == "__main__":
    main()
