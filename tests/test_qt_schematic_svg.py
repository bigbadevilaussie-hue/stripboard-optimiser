"""Qt schematic text contrast regressions; do not touch board renderer SVG."""
import unittest

from render.qt_schematic_svg import schematic_svg_for_qt


class SchematicQtContrastTests(unittest.TestCase):
    def test_dark_label_survives_while_white_halo_is_disabled(self):
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<line x1="1" x2="10" stroke="#fff" stroke-width="3"/>'
            '<text fill="#111" stroke="#fff" stroke-width="3" '
            'stroke-linejoin="round" paint-order="stroke" font-size="12">'
            '<tspan>USB</tspan></text>'
            '</svg>'
        )
        out = schematic_svg_for_qt(source)
        self.assertIn('<text fill="#111" stroke="none" font-size="12">', out)
        self.assertIn('<tspan>USB</tspan>', out)
        self.assertIn('<line x1="1" x2="10" stroke="#fff" stroke-width="3"/>', out)
        self.assertNotIn('paint-order="stroke"', out)

    def test_only_white_stroked_text_is_modified(self):
        source = (
            '<svg><text fill="#333" stroke="#222" stroke-width="2">PIN</text>'
            '<text fill="#111" stroke="#ffffff" stroke-width="3">AMP</text>'
            '<text fill="#333">R1</text>'
            '<path d="M 0 0 L 5 5" stroke="#fff" /></svg>'
        )
        out = schematic_svg_for_qt(source)
        self.assertIn('<text fill="#333" stroke="#222" stroke-width="2">PIN</text>', out)
        self.assertIn('<text fill="#111" stroke="none">AMP</text>', out)
        self.assertIn('<text fill="#333">R1</text>', out)
        self.assertIn('<path d="M 0 0 L 5 5" stroke="#fff" />', out)

    def test_retains_source_and_is_idempotent(self):
        source = '<svg><text stroke="white" fill="#111" stroke-width="3">TVS</text></svg>'
        original = source[:]
        out = schematic_svg_for_qt(source)
        self.assertEqual(source, original)
        self.assertEqual(schematic_svg_for_qt(out), out)
        self.assertIn('fill="#111"', out)
        self.assertIn('stroke="none"', out)


if __name__ == "__main__":
    unittest.main()
