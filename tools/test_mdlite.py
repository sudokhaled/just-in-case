"""Tests for the Markdown subset parser and renderers.

    python3 -m unittest discover -s tools -p "test_*.py"
"""

import unittest
import xml.etree.ElementTree as ET

import mdlite

LABELS = {"caution": "DANGER", "warning": "WARNING", "tip": "TIP", "note": "NOTE", "important": "IMPORTANT"}


def html(text, resolve=lambda href: href):
    doc = mdlite.parse(text)
    return doc, mdlite.HtmlRenderer(resolve, LABELS).render(doc.blocks)


def text(text, width=None):
    doc = mdlite.parse(text)
    return mdlite.TextRenderer(lambda href, t: " (see %s)" % href, LABELS, width).render(doc.blocks)


class ParseTests(unittest.TestCase):
    def test_paragraph_and_inline(self):
        doc, out = html("Boil for **1 minute**, *then* use `chlorine`.")
        self.assertEqual(doc.errors, [])
        self.assertEqual(out, "<p>Boil for <strong>1 minute</strong>, <em>then</em> use <code>chlorine</code>.</p>")

    def test_math_star_is_not_italic(self):
        _, out = html("Use 5 * 3 drops.")
        self.assertEqual(out, "<p>Use 5 * 3 drops.</p>")

    def test_escaping(self):
        _, out = html("Water <5°C & salt > 2%")
        self.assertIn("&lt;5°C &amp; salt &gt; 2%", out)

    def test_headings(self):
        doc, out = html("Intro.\n\n## Quick steps\n\n### Boiling")
        self.assertEqual(doc.errors, [])
        self.assertIn('<h2 id="quick-steps">Quick steps</h2>', out)
        self.assertIn('<h3 id="boiling">Boiling</h3>', out)

    def test_heading_levels_rejected(self):
        doc = mdlite.parse("# Title\n\n#### Deep")
        self.assertEqual(len(doc.errors), 2)

    def test_nested_lists(self):
        doc, out = html("1. Clear it.\n2. Kill germs:\n   - Boil\n   - Bleach\n3. Store it.")
        self.assertEqual(doc.errors, [])
        self.assertIn("<ol>", out)
        self.assertIn("<li>Kill germs:\n<ul>\n<li>Boil</li>\n<li>Bleach</li>\n</ul></li>", out)
        self.assertIn("<li>Store it.</li>", out)

    def test_list_start_number(self):
        _, out = html("3. Third\n4. Fourth")
        self.assertIn('<ol start="3">', out)

    def test_list_with_blank_lines_stays_one_list(self):
        doc = mdlite.parse("- a\n\n- b\n\nAfter.")
        self.assertEqual([b[0] for b in doc.blocks], ["list", "p"])
        self.assertEqual(len(doc.blocks[0][3]), 2)

    def test_star_bullets_rejected(self):
        doc = mdlite.parse("* item")
        self.assertTrue(any("'-'" in m for _, m in doc.errors))

    def test_callout(self):
        doc, out = html("> [!CAUTION]\n> **Never** drink seawater.\n>\n> - Not even mixed.")
        self.assertEqual(doc.errors, [])
        self.assertIn('<div class="callout callout-caution"><p class="callout-label">DANGER</p>', out)
        self.assertIn("<ul>\n<li>Not even mixed.</li>\n</ul>", out)

    def test_plain_quote_rejected(self):
        doc = mdlite.parse("> just a quote")
        self.assertEqual(len(doc.errors), 1)

    def test_table(self):
        doc, out = html("| Water | Bleach |\n|---|---|\n| 1 liter | 2 drops |")
        self.assertEqual(doc.errors, [])
        self.assertIn("<th>Water</th><th>Bleach</th>", out)
        self.assertIn("<td>1 liter</td><td>2 drops</td>", out)

    def test_table_cell_count_checked(self):
        doc = mdlite.parse("| a | b |\n|---|---|\n| 1 |")
        self.assertEqual(len(doc.errors), 1)

    def test_code_block_keeps_spacing(self):
        doc, out = html("```\n  /\\\n /  \\\n```")
        self.assertEqual(doc.errors, [])
        self.assertEqual(out, "<pre>  /\\\n /  \\</pre>")

    def test_unclosed_code_block(self):
        doc = mdlite.parse("```\nart")
        self.assertEqual(len(doc.errors), 1)

    def test_links(self):
        doc, out = html("See [water](../water/purify-water.md) and [WHO](https://who.int).",
                        resolve=lambda h: "#purify-water" if h.startswith("..") else h)
        self.assertEqual(doc.errors, [])
        self.assertEqual(doc.links, [(1, "../water/purify-water.md"), (1, "https://who.int")])
        self.assertIn('<a href="#purify-water">water</a>', out)
        self.assertIn('<a href="https://who.int">WHO</a>', out)

    def test_unresolved_link_renders_text(self):
        _, out = html("See [water](../water/purify-water.md).", resolve=lambda h: None)
        self.assertEqual(out, "<p>See water.</p>")

    def test_bad_link_rejected(self):
        doc = mdlite.parse("[x](purify-water)")
        self.assertEqual(len(doc.errors), 1)

    def test_forbidden_constructs(self):
        for bad in ("<b>x</b>", "a &amp; b", "![knot](knot.svg)", "---"):
            self.assertTrue(mdlite.parse(bad).errors, bad)

    def test_html_in_code_span_is_allowed(self):
        self.assertEqual(mdlite.parse("Type `<enter>`.").errors, [])

    def test_hard_wrapped_paragraph_is_joined(self):
        doc = mdlite.parse("One line\ncontinues here.")
        self.assertEqual(len(doc.blocks), 1)
        self.assertEqual(mdlite.plain(doc.blocks[0][1]), "One line continues here.")
        self.assertEqual(len(doc.warnings), 1)

    def test_line_numbers(self):
        doc = mdlite.parse("ok\n\n#### bad", first_line=10)
        self.assertEqual(doc.errors[0][0], 12)

    def test_unique_heading_ids(self):
        _, out = html("## Steps\n\n## Steps")
        self.assertIn('id="steps"', out)
        self.assertIn('id="steps-2"', out)

    def test_html_is_well_formed_xml(self):
        src = ("> [!WARNING]\n> Hot & < 5 > 2\n\n## A & B\n\n1. x\n   - y\n\n"
               "| a | b |\n|---|---|\n| **1** | [l](https://x.org/?a=1&b=2) |\n\n```\n<pre> & \n```")
        doc, out = html(src)
        self.assertEqual(doc.errors, [])
        ET.fromstring("<div>%s</div>" % out)


class PictureTests(unittest.TestCase):
    def test_picture_block(self):
        doc, out = html("![1 Head back. 2 Knee bent.](../../images/recovery.svg)",
                        resolve=lambda h: h)
        self.assertEqual(doc.errors, [])
        self.assertEqual(doc.images, [(1, "../../images/recovery.svg")])
        self.assertIn('<figure class="diagram"><img src="../../images/recovery.svg"', out)
        self.assertIn("<figcaption>1 Head back. 2 Knee bent.</figcaption>", out)

    def test_picture_in_text_edition(self):
        out = text("![1 Head back.](../../images/recovery.svg)")
        self.assertEqual(out, "[Picture: 1 Head back.]")

    def test_picture_path_checked(self):
        self.assertEqual(len(mdlite.parse("![x](images/a.png)").errors), 1)

    def test_inline_picture_rejected(self):
        self.assertEqual(len(mdlite.parse("See ![x](../../images/a.svg) here.").errors), 1)


class TextTests(unittest.TestCase):
    def test_text_rendering(self):
        out = text("> [!CAUTION]\n> Never.\n\n## Quick steps\n\n1. Boil.\n   - Long.\n\n"
                   "| Water | Dose |\n|---|---|\n| 1 L | 2 drops |\n\nSee [x](../a/b.md).")
        self.assertIn(">> DANGER\n>> Never.", out)
        self.assertIn("== QUICK STEPS ==", out)
        self.assertIn("1. Boil.\n   - Long.", out)
        self.assertIn("- 1 L: Dose: 2 drops", out)
        self.assertIn("See x (see ../a/b.md).", out)

    def test_wrapping(self):
        out = text("- " + "word " * 20, width=30)
        lines = out.split("\n")
        self.assertTrue(all(len(l) <= 30 for l in lines))
        self.assertTrue(lines[1].startswith("  word"))

    def test_ascii(self):
        self.assertEqual(mdlite.to_ascii("38°C (100°F) – “safe” ★ ½ ≥ 2"), '38 deg C (100 deg F) - "safe" * 1/2 >= 2')
        self.assertEqual(mdlite.to_ascii("café"), "cafe")


if __name__ == "__main__":
    unittest.main()
