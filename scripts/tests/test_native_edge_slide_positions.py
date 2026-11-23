"""Native rigid edge slide geometry: board keeps physical dimensions."""
import copy
import unittest

from native_edge_slide_positions import anchors_for_component, edge_slide_anchors


def defn(w, h):
    return {
        "id": "fixture", "width": w, "height": h,
        "pins": [{"id": "1", "offsetRow": 0, "offsetCol": 0},
                 {"id": "2", "offsetRow": 0, "offsetCol": w - 1}],
        "bodyCells": [{"row": r, "col": c} for r in range(h) for c in range(w)],
    }


def part(row, col, **kwargs):
    return {
        "id": "P", "label": "USB", "defId": "fixture",
        "boardPos": {"row": row, "col": col},
        "rotation": 0, "locked": True, "edge": True, "slide": True,
        **kwargs,
    }


class NativeEdgeGeometryTests(unittest.TestCase):
    def setUp(self):
        self.board = {"rows": 24, "cols": 56, "lockedRows": True, "lockedCols": True}

    def test_bottom_overhang_13_high_on_24_board_still_has_51_columns(self):
        p = part(13, 47)
        before = copy.deepcopy(p)
        a = anchors_for_component(p, defn(6, 13), self.board)
        self.assertEqual(a.side, "bottom")
        self.assertEqual(a.positions[0], (13, 47))
        self.assertEqual(len(a.positions), 51)
        self.assertEqual({c for _, c in a.positions}, set(range(51)))
        self.assertTrue(all(r == 13 for r, _ in a.positions))
        self.assertEqual(p, before)

    def test_top_body_overhang_preserves_perpendicular(self):
        p = part(-2, 4)
        # Electrical pins would fall outside board; use pins at body row 3.
        d = defn(3, 5)
        for pin in d["pins"]:
            pin["offsetRow"] = 3
        a = anchors_for_component(p, d, self.board)
        self.assertEqual(a.side, "top")
        self.assertEqual(len(a.positions), 54)
        self.assertTrue(all(r == -2 for r, _ in a.positions))

    def test_left_and_right_preserve_perpendicular(self):
        d = defn(4, 2)
        for pin in d["pins"]:
            pin["offsetCol"] = 3
        a = anchors_for_component(part(6, -2), d, self.board)
        self.assertEqual(a.side, "left")
        self.assertEqual(len(a.positions), 23)
        self.assertTrue(all(c == -2 for _, c in a.positions))
        d = defn(4, 2)
        for pin in d["pins"]:
            pin["offsetCol"] = 0
        a = anchors_for_component(part(6, 54), d, self.board)
        self.assertEqual(a.side, "right")
        self.assertEqual(len(a.positions), 23)
        self.assertTrue(all(c == 54 for _, c in a.positions))

    def test_offboard_pins_rejected_even_if_edge_body_allowed(self):
        with self.assertRaisesRegex(ValueError, "electrical pin off board"):
            anchors_for_component(part(13, 47), defn(6, 13) | {
                "pins": [{"id": "x", "offsetRow": 12, "offsetCol": 0}]
            }, self.board)

    def test_slide_requirements_fail_closed(self):
        for p in (part(13, 47, edge=False), part(13, 47, slide=False),
                  part(13, 47, locked=False), part(13, 47, boardPos=None)):
            with self.assertRaises(ValueError):
                anchors_for_component(p, defn(6, 13), self.board)
        with self.assertRaises(ValueError):
            anchors_for_component(part(13, 47), defn(6, 13),
                                  {**self.board, "lockedRows": False})

    def test_multiple_sliders_and_unresolved_defs(self):
        project = {
            "board": self.board, "componentDefs": [defn(6, 13)],
            "components": [part(13, 47)]
        }
        anchors = edge_slide_anchors(project)
        self.assertEqual(len(anchors), 1)
        self.assertEqual(len(anchors[0].positions), 51)
        project["components"].append({**part(13, 47), "id": "OFF", "offBoard": True})
        self.assertEqual(len(edge_slide_anchors(project)), 1)
        project["components"].append({**part(13, 47), "id": "MISSING", "defId": "not-known"})
        with self.assertRaisesRegex(ValueError, "unresolved footprint"):
            edge_slide_anchors(project)


if __name__ == "__main__":
    unittest.main()
