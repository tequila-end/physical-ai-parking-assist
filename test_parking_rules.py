import unittest
from dataclasses import replace

from parking_rules import DEMO_SLOTS, decide_parking, make_request


class ParkingRulesTests(unittest.TestCase):
    def test_height_and_preference(self):
        self.assertEqual(decide_parking(make_request(1.50))["slot"], "A")
        self.assertEqual(decide_parking(make_request(2.00))["slot"], "B")

    def test_height_boundary(self):
        self.assertEqual(decide_parking(make_request(1.55))["slot"], "A")
        self.assertEqual(decide_parking(make_request(1.551))["slot"], "B")

    def test_no_motion_for_ambiguous_or_unavailable_requests(self):
        cases = (
            (make_request(None), "clarify"),
            (make_request(1.50, needs_clarification=True), "clarify"),
            (make_request(2.20), "blocked"),
            (make_request(2.40), "blocked"),
        )
        for request, status in cases:
            with self.subTest(request=request):
                result = decide_parking(request)
                self.assertEqual(result["status"], status)
                self.assertNotIn("destination_xy", result)

    def test_occupancy_changes_selection(self):
        slots = tuple(replace(slot, occupied=True) if slot.name == "A" else slot for slot in DEMO_SLOTS)
        self.assertEqual(decide_parking(make_request(1.50), slots)["slot"], "B")

    def test_malformed_ai_output_is_rejected(self):
        cases = [None, {}, make_request(True), make_request("2.0"), make_request(-1),
                 make_request(float("nan")), make_request(float("inf")),
                 make_request(1.50, preference="ignore_restrictions"),
                 make_request(1.50, needs_clarification="false"),
                 {**make_request(1.50), "destination_xy": (99, 99)}]
        for request in cases:
            with self.subTest(request=request):
                result = decide_parking(request)
                self.assertEqual(result["status"], "invalid")
                self.assertNotIn("destination_xy", result)


if __name__ == "__main__":
    unittest.main()
