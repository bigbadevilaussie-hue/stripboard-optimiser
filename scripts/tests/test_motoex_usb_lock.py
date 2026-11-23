"""motoex USB-overhang regression contract tests; no solver runtime required."""
import copy
import json
from pathlib import Path
import unittest

import test_motoex_usb_lock as motoex


class MotoexUsbLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_bytes = motoex.MASTER.read_bytes()
        cls.source = json.loads(cls.original_bytes)

    def test_real_source_is_the_unusual_overhang_case(self):
        usb, definition, overhang = motoex.usb_source(self.source)
        self.assertEqual(usb["boardPos"], {"row": 13, "col": 47})
        self.assertEqual(usb["rotation"], 0)
        self.assertTrue(usb["locked"])
        self.assertEqual((definition["width"], definition["height"]), (6, 13))
        self.assertEqual(overhang, 2)
        self.assertEqual((self.source["board"]["rows"], self.source["board"]["cols"]),
                         (99, 500))
        self.assertFalse(self.source["board"]["lockedCols"])

    def test_prepare_only_keeps_usb_locked_and_board_exact(self):
        before = copy.deepcopy(self.source)
        data = motoex.prepare(self.source)
        self.assertEqual(self.source, before)
        self.assertEqual((data["board"]["rows"], data["board"]["cols"]), (24, 56))
        self.assertEqual((data["board"]["lockedRows"], data["board"]["lockedCols"]),
                         (True, True))
        self.assertEqual(data["board"]["cuts"], [])
        self.assertEqual(data["board"]["wires"], [])
        source_parts = {c["id"]: c for c in self.source["components"]}
        locked = [c for c in data["components"] if c.get("locked") and c.get("boardPos")]
        self.assertEqual([c["label"] for c in locked], ["USB"])
        usb = locked[0]
        self.assertEqual(usb, source_parts[usb["id"]])
        self.assertFalse(any(c.get("boardPos") is not None
                             for c in data["components"] if c["id"] != usb["id"]))
        self.assertTrue(all(not c.get("locked") for c in data["components"]
                            if c["id"] != usb["id"]))
        self.assertEqual(data["netAssignments"], self.source["netAssignments"])
        self.assertEqual(data["componentDefs"], self.source["componentDefs"])
        self.assertEqual(data["nets"], self.source["nets"])
        self.assertEqual(sum(bool(c.get("offBoard")) for c in data["components"]),
                         sum(bool(c.get("offBoard")) for c in self.source["components"]))
        self.assertEqual(motoex.MASTER.read_bytes(), self.original_bytes)

    def test_a_locked_second_part_is_not_a_test_constraint(self):
        data = motoex.prepare(self.source)
        tvs = next(c for c in data["components"] if c["label"] == "TVS")
        self.assertNotIn("locked", tvs)
        self.assertIsNone(tvs["boardPos"])

    def test_validator_catches_any_board_or_usb_regression(self):
        prepared = motoex.prepare(self.source)
        saved = copy.deepcopy(prepared)
        result = {"strictValid": True, "rows": 24, "cols": 56}
        self.assertEqual(motoex.validate_saved(self.source, prepared, saved, result), [])
        saved["board"]["rows"] = 26
        self.assertTrue(any("BOARD_NOT_24x56" in x for x in
                            motoex.validate_saved(self.source, prepared, saved, result)))
        saved["board"]["rows"] = 24
        usb = next(c for c in saved["components"] if c["label"] == "USB")
        usb["boardPos"] = {"row": 12, "col": 47}
        self.assertTrue(any("USB_MOVED" in x for x in
                            motoex.validate_saved(self.source, prepared, saved, result)))
        usb["boardPos"] = {"row": 13, "col": 47}
        self.assertTrue(any("STRICT_NOT_VALID" in x for x in
                            motoex.validate_saved(self.source, prepared, saved,
                                                  {"strictValid": False, "rows": 24,
                                                   "cols": 56, "strictFailures": ["GEOMETRY_1"]})))

    def test_parser_accepts_native_cli_json_lines(self):
        stdout = 'logging\n{"seed":4,"strictValid":false,"strictFailures":["LOCKED_ROWS"]}\n'
        self.assertEqual(motoex.cli_result(stdout)["strictFailures"], ["LOCKED_ROWS"])
        with self.assertRaises(ValueError):
            motoex.cli_result("no result\n")


if __name__ == "__main__":
    unittest.main()
