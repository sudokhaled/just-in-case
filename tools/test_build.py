"""Integration tests: build every edition from the real content and check the output.

    python3 -m unittest discover -s tools -p "test_*.py"
"""

import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import build


def json_list(sw):
    import json
    return json.loads(re.search(r"var FILES=(\[.*?\]);", sw).group(1))


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        strings = build.read_keyvalues(build.CONTENT / "en" / "strings.txt")
        cls.lib = build.Library("en", strings)
        cls.full = build.Edition(cls.lib)
        cls.core = build.Edition(cls.lib, core=True)

    def test_content_has_no_errors(self):
        self.assertEqual(self.lib.errors, [])

    def test_core_is_only_critical(self):
        self.assertTrue(self.core.articles)
        self.assertTrue(all(a.critical for a in self.core.articles))

    def test_single_html_links_all_resolve(self):
        for ed in (self.full, self.core):
            page = build.build_single_html(ed, "")
            ids = set(re.findall(r' id="([^"]+)"', page))
            for target in re.findall(r'href="#([^"]+)"', page):
                self.assertIn(target, ids, "broken link #%s" % target)

    def test_epub_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.epub"
            build.build_epub(self.full, path, "")
            with zipfile.ZipFile(path) as z:
                first = z.infolist()[0]
                self.assertEqual(first.filename, "mimetype")
                self.assertEqual(first.compress_type, zipfile.ZIP_STORED)
                names = set(z.namelist())
                ids = {}
                for name in names:
                    if name.endswith((".xhtml", ".opf", ".ncx", ".xml")):
                        root = ET.fromstring(z.read(name))
                        ids[name] = {e.get("id") for e in root.iter() if e.get("id")}
                # Every manifest item exists, and every internal link resolves.
                opf = z.read("OEBPS/content.opf").decode()
                for href in re.findall(r'<item [^>]*href="([^"]+)"', opf):
                    self.assertIn("OEBPS/" + href, names)
                for name in names:
                    if name.endswith(".xhtml"):
                        for href in re.findall(r'href="([^"#:]*\.xhtml)(?:#([^"]+))?"', z.read(name).decode()):
                            target = "OEBPS/" + href[0]
                            self.assertIn(target, names, "%s links to missing %s" % (name, target))
                            if href[1]:
                                self.assertIn(href[1], ids[target], "%s links to missing #%s" % (name, href[1]))

    def test_svg_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.svg"
            good.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 10 10">'
                            '<rect class="bg" width="10" height="10" fill="#fff"/><text>1</text></svg>')
            self.assertEqual(build.check_svg(good), [])
            bad = Path(tmp) / "bad.svg"
            bad.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" onload="x()">'
                           '<script>alert(1)</script><text>Danger here</text><a href="http://x.org"/></svg>')
            problems = " ".join(build.check_svg(bad))
            for word in ("width", "script", "onload", "short labels", "<a>"):
                self.assertIn(word, problems)

    def test_cards(self):
        self.assertGreaterEqual(len(self.lib.cards), 10)
        page = build.build_cards_page(self.full)
        self.assertEqual(page.count('<section class="card">'), len(self.lib.cards))
        self.assertNotIn("<a href", page.split("<body>")[1])  # printed cards show article numbers, not links

    def test_book_references_resolve(self):
        page = build.build_book_html(self.full, "")
        ids = set(re.findall(r' id="([^"]+)"', page))
        targets = re.findall(r'href="#([^"]+)"', page)
        self.assertGreater(len(targets), 500)
        for target in targets:
            self.assertIn(target, ids, "broken book reference #%s" % target)

    def test_offline_app_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build.build_site(self.full, out, [], ["en"])
            sw = (out / "sw.js").read_text()
            listed = json_list(sw)
            self.assertIn("index.html", listed)
            for name in listed:
                if name != "./":
                    self.assertTrue((out / name).exists(), "service worker lists missing file %s" % name)
            self.assertEqual((out / "icon-192.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_core_text_is_ascii(self):
        text = build.build_text(self.core, "", ascii_only=True)
        text.encode("ascii")

    def test_text_wrapping(self):
        text = build.build_text(self.core, "", ascii_only=True, width=40)
        code_lines = set()
        for a in self.core.articles:
            for b in a.doc.blocks:
                if b[0] == "code":
                    code_lines.update(build.mdlite.to_ascii(b[1]).split("\n"))
        for line in text.split("\n"):
            if line not in code_lines and " " in line.strip():
                self.assertLessEqual(len(line), 40, line)

    def test_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build.build_site(self.full, out, [], ["en"])
            pages = {p.name for p in out.glob("*.html")}
            self.assertEqual(len(pages), len(self.full.articles) + 2 + (1 if self.lib.cards else 0))  # + index, devices
            for page in out.glob("*.html"):
                for href in re.findall(r'href="([^"#:]+\.html)', page.read_text(encoding="utf-8")):
                    self.assertIn(href, pages, "%s links to missing %s" % (page.name, href))



class EditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        strings = build.read_keyvalues(build.CONTENT / "en" / "strings.txt")
        cls.lib = build.Library("en", strings)
        cls.nano = build.Edition(cls.lib, levels={p: "nano" for p in build.PRIORITIES}, drawings=False)

    def test_short_version_is_warnings_and_quick_steps(self):
        a = self.lib.by_id["burns"]
        blocks = self.nano.blocks(a)
        self.assertEqual(blocks[0][:2], ("callout", "CAUTION"))
        headings = [build.mdlite.plain(b[2]) for b in blocks if b[0] == "h" and b[1] == 2]
        self.assertEqual(headings, ["Quick steps"])
        self.assertEqual(blocks[-1][:2], ("callout", "NOTE"))
        self.assertLess(len(build.blocks_text(blocks)), len(build.article_text(a)) / 3)

    def test_every_short_version_stands_alone(self):
        for a in self.lib.articles:
            text = build.blocks_text(self.nano.blocks(a))
            self.assertIsNone(build.POINTER_RE.search(text), a.id)

    def test_pointer_check(self):
        for bad in ("see the table below.", "Decide how serious it is (below).", "the danger signs below"):
            self.assertTrue(build.POINTER_RE.search(bad), bad)
        for good in ("5-7 cm above the wound", "a fist above the navel", "below the water line"):
            self.assertIsNone(build.POINTER_RE.search(good), good)

    def test_no_drawings(self):
        for a in self.nano.articles:
            self.assertEqual(build.pictures_in(self.nano.blocks(a)), [])

    def test_editions_file_is_valid(self):
        editions = build.read_editions()
        names = [e["name"] for e in editions]
        self.assertIn("just-in-case-mp3.txt", names)
        self.assertIn("esp-small", names)
        for e in editions:  # downloads must be built before the site that offers them
            if e["format"] in ("site", "esp"):
                offered = [x["name"] for x in editions if x["offer"]]
                self.assertTrue(all(names.index(o) < names.index(e["name"]) for o in offered), e["name"])

    def test_bad_editions_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "editions.ini"
            bad.write_text("[x]\nformat = floppy\ncritical = tiny\nshrink = everything\n")
            with self.assertRaises(build.BuildError) as err:
                build.read_editions(bad)
            for word in ("format", "critical", "everything"):
                self.assertIn(word, str(err.exception))

    def test_budget_shrinks_in_order_then_refuses(self):
        e = next(x for x in build.read_editions() if x["name"] == "esp-small")
        with tempfile.TemporaryDirectory() as tmp:
            r = build.build_edition(dict(e, dest=tmp + "/a", budget=330), self.lib, "", None, [], ["en"])
            self.assertTrue(r["shrunk"])
            self.assertEqual(r["shrunk"], e["shrink"][:len(r["shrunk"])])
            self.assertLessEqual(r["size"], 330 * 1024)
            with self.assertRaises(build.BuildError):
                build.build_edition(dict(e, dest=tmp + "/b", budget=10), self.lib, "", None, [], ["en"])

    def test_mp3_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            single, folder = Path(tmp) / "mp3.txt", Path(tmp) / "mp3"
            build.write_mp3(self.nano, "", single, folder)
            files = [single] + sorted(folder.iterdir())
            self.assertEqual(len(files), len(self.nano.groups) + 2)
            for f in files:
                data = f.read_bytes()
                data.decode("ascii")
                self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), f.name)
            for f in folder.iterdir():
                self.assertRegex(f.name, r"^[0-9A-Z]{1,8}\.TXT$")

    def test_topic_pages_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build.build_site(self.nano, out, [], ["en"], pages="category")
            pages = {p.name: p.read_text(encoding="utf-8") for p in out.glob("*.html")}
            self.assertEqual(sum(1 for n in pages if n.startswith("c-")), len(self.nano.groups))
            ids = {n: set(re.findall(r' id="([^"]+)"', t)) for n, t in pages.items()}
            for name, text in pages.items():
                for page, anchor in re.findall(r'href="([^"#:]+\.html)(?:#([^"]+))?"', text):
                    self.assertIn(page, pages, "%s -> %s" % (name, page))
                    if anchor:
                        self.assertIn(anchor, ids[page], "%s -> %s#%s" % (name, page, anchor))


if __name__ == "__main__":
    unittest.main()
