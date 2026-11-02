#!/usr/bin/env python3
"""Build every edition of the Just In Case library from content/.

    python3 tools/build.py              build all editions into dist/
    python3 tools/build.py --check      validate content only (used by CI)
    python3 tools/build.py --readme     also refresh the contents table in README.md
    python3 tools/build.py --wrap 40    hard-wrap the text editions for tiny screens

Standard library only (Python 3.8+), so the library can rebuild itself on a
Raspberry Pi or an old laptop with no internet.
"""

import argparse
import configparser
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
import zipfile
from html import escape
from urllib.parse import quote
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import icon  # noqa: E402
import mdlite  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
IMAGES = CONTENT / "images"
DIST = ROOT / "dist"
ESP32_DATA = ROOT / "hardware" / "esp32" / "JustInCase" / "data"
README = ROOT / "README.md"
EDITIONS = ROOT / "tools" / "editions.ini"
NAME = "just-in-case"

PRIORITIES = ("critical", "important", "useful")
REVIEWS = ("no", "community", "expert")
FIELDS = ("title", "summary", "priority", "order", "tags", "reviewed", "updated")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_ID = 24
STAR = "★"
SVG_MAX = 12 * 1024
SVG_NS = "{http://www.w3.org/2000/svg}"
SVG_CLASSES = {"bg", "fill", "accent", "accent-fill", "muted"}
SVG_FORBIDDEN = {"script", "style", "foreignObject", "image", "use", "iframe", "a"}
# File space on a 4 MB ESP32: the "No OTA" layout (used by the one-click installer
# and recommended in the guide) gives 0x1E0000 bytes; the Arduino default 0x160000.
# LittleFS stores each file in whole 4 KB blocks, plus some metadata.
ESP32_FS_BYTES = 0x1E0000
ESP32_DEFAULT_FS_BYTES = 0x160000
FS_BLOCK = 4096


# ---- loading ----------------------------------------------------------------

class Article:
    def __init__(self, lang, category, aid, path):
        self.lang = lang
        self.category = category
        self.id = aid
        self.path = path
        self.meta = {}
        self.doc = None

    title = property(lambda self: self.meta.get("title", self.id))
    summary = property(lambda self: self.meta.get("summary", ""))
    priority = property(lambda self: self.meta.get("priority", "useful"))
    reviewed = property(lambda self: self.meta.get("reviewed", "no"))
    updated = property(lambda self: self.meta.get("updated", ""))

    @property
    def order(self):
        try:
            return int(self.meta.get("order", 50))
        except ValueError:
            return 50

    @property
    def tags(self):
        return [t.strip() for t in self.meta.get("tags", "").split(",") if t.strip()]

    @property
    def critical(self):
        return self.priority == "critical"


class Library:
    """All articles of one language, validated."""

    def __init__(self, lang, fallback_strings=None, draft=False):
        self.lang = lang
        self.draft = draft
        self.dir = CONTENT / lang
        self.errors = []
        self.warnings = []
        self.strings = dict(fallback_strings or {})
        self.strings.update(read_keyvalues(self.dir / "strings.txt"))
        self.categories = read_categories(self.dir / "categories.txt")
        self.category_title = {c: t for c, t, _ in self.categories}
        self.articles = []
        self.by_id = {}
        self.cards = []  # (title, blocks)
        self.load()
        self.load_cards()

    def rel(self, path):
        return str(path.relative_to(ROOT))

    def error(self, path, line, msg):
        self.errors.append((self.rel(path), line, msg))

    def warn(self, path, line, msg):
        self.warnings.append((self.rel(path), line, msg))

    def load(self):
        order = {c: n for n, (c, _, _) in enumerate(self.categories)}
        for folder in sorted(p for p in self.dir.iterdir() if p.is_dir()):
            for path in sorted(folder.glob("*.md")):
                if folder.name not in order:
                    self.error(path, 0, "unknown category folder '%s' (see categories.txt)" % folder.name)
                    continue
                self.load_article(folder.name, path)
        self.articles.sort(key=lambda a: (order[a.category], a.order, a.title.lower()))
        self.checked_svgs = {}
        for a in self.articles:
            self.check_links(a)
            self.check_pictures(a)

    def check_pictures(self, a):
        for line, src in a.doc.images:
            m = mdlite.IMAGE_PATH.match(src)
            if not m:
                continue
            path = IMAGES / (m.group(1) + ".svg")
            if src not in self.checked_svgs:
                self.checked_svgs[src] = check_svg(path) if path.exists() else ["file not found"]
            for msg in self.checked_svgs[src]:
                self.error(a.path, line, "picture %s: %s" % (src, msg))

    def load_cards(self):
        """Pocket cards: one file, each '## ' heading starts a card."""
        path = self.dir / "cards.md"
        if not path.exists():
            return
        cards = Article(self.lang, "cards", "cards", path)
        meta, body, body_line = parse_front_matter(path.read_text(encoding="utf-8").replace("\r\n", "\n"))
        cards.meta = meta or {}
        cards.doc = mdlite.parse(body, body_line)
        for line, msg in cards.doc.errors:
            self.error(path, line, msg)
        self.check_links(cards)
        self.check_pictures(cards)
        for b in cards.doc.blocks:
            if b[0] == "h" and b[1] == 2:
                self.cards.append((mdlite.plain(b[2]), []))
            elif self.cards:
                self.cards[-1][1].append(b)
            else:
                self.error(path, 0, "text before the first '## ' card title")
        r = mdlite.TextRenderer(lambda href, text: "", {})
        for title, blocks in self.cards:
            words = len(r.render([b for b in blocks if b[0] != "img"]).split())  # pictures have a fixed height
            if words > 110:
                self.warn(path, 0, "card '%s' has %d words; keep cards under 110 so they fit when printed" % (title, words))

    def load_article(self, category, path):
        aid = path.stem
        if not ID_RE.match(aid) or len(aid) > MAX_ID:
            self.error(path, 0, "file name must be lowercase letters, digits and hyphens, at most %d characters" % MAX_ID)
        if aid in self.by_id:
            self.error(path, 0, "id '%s' is already used by %s" % (aid, self.rel(self.by_id[aid].path)))
            return
        a = Article(self.lang, category, aid, path)
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        meta, body, body_line = parse_front_matter(text)
        if meta is None:
            self.error(path, 1, "file must start with a front matter block between two '---' lines")
            return
        a.meta = meta
        self.check_meta(a)
        a.doc = mdlite.parse(body, body_line)
        for line, msg in a.doc.errors:
            self.error(path, line, msg)
        for line, msg in a.doc.warnings:
            self.warn(path, line, msg)
        self.check_structure(a)
        self.articles.append(a)
        self.by_id[aid] = a

    def check_meta(self, a):
        m = a.meta
        for key in FIELDS:
            if not m.get(key):
                self.error(a.path, 1, "front matter is missing '%s'" % key)
        for key in m:
            if key not in FIELDS:
                self.warn(a.path, 1, "unknown front matter field '%s'" % key)
        if m.get("priority") and m["priority"] not in PRIORITIES:
            self.error(a.path, 1, "priority must be one of: " + ", ".join(PRIORITIES))
        if m.get("reviewed") and m["reviewed"] not in REVIEWS:
            self.error(a.path, 1, "reviewed must be one of: " + ", ".join(REVIEWS))
        if m.get("order") and not m["order"].isdigit():
            self.error(a.path, 1, "order must be a whole number")
        if m.get("updated") and not DATE_RE.match(m["updated"]):
            self.error(a.path, 1, "updated must be a date like 2026-11-01")
        if len(m.get("title", "")) > 60:
            self.warn(a.path, 1, "title is longer than 60 characters")
        if len(m.get("summary", "")) > 200:
            self.warn(a.path, 1, "summary is longer than 200 characters")

    def check_structure(self, a):
        blocks = a.doc.blocks
        if not blocks:
            self.error(a.path, 0, "article has no content")
            return
        if blocks[0][0] == "h":
            self.error(a.path, 0, "body must start with a callout or paragraph, not a heading")
        sections = [mdlite.plain(b[2]) for b in blocks if b[0] == "h" and b[1] == 2]
        sources = self.strings.get("sources", "Sources")
        if not sections or sections[-1] != sources:
            self.error(a.path, 0, "the last section must be '## %s'" % sources)
        elif blocks[-1][0] == "h":
            self.error(a.path, 0, "the '## %s' section is empty" % sources)
        if self.lang == "en":
            m = POINTER_RE.search(blocks_text(nano_blocks(a, self.strings)))
            if m:
                self.error(a.path, 0, "the opening warnings and quick steps must stand alone (short editions show only "
                                      "them), but they point elsewhere: '%s'" % m.group(0).strip())
        words = count_words(a)
        if words < 250:
            self.warn(a.path, 0, "only %d words; is this article finished?" % words)
        elif words > 2600:
            self.warn(a.path, 0, "%d words; consider splitting this article" % words)

    def check_links(self, a):
        for line, href in a.doc.links:
            m = mdlite.INTERNAL_LINK.match(href)
            if not m:
                continue
            category, target = m.groups()
            t = self.by_id.get(target)
            if t is None:
                msg = "link to missing article '%s'" % href
                if self.lang == "en" and not self.draft:
                    self.error(a.path, line, msg)
                else:
                    why = "draft build" if self.lang == "en" else "not translated yet"
                    self.warn(a.path, line, msg + " (%s; shown as plain text)" % why)
            elif t.category != category:
                self.error(a.path, line, "link '%s': article '%s' is in '%s', not '%s'" % (href, target, t.category, category))


def parse_front_matter(text):
    if not text.startswith("---\n"):
        return None, text, 1
    end = text.find("\n---\n", 3)
    if end < 0:
        return None, text, 1
    meta = {}
    for line in text[4:end].split("\n"):
        if line.strip() and not line.lstrip().startswith("#"):
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    body_line = text[:end + 5].count("\n") + 1
    return meta, text[end + 5:], body_line


def check_svg(path):
    """Problems that would make a picture unsafe or unreadable when inlined into pages."""
    data = path.read_bytes()
    errors = []
    if len(data) > SVG_MAX:
        errors.append("is %d KB; keep pictures under %d KB" % (len(data) // 1024, SVG_MAX // 1024))
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        return errors + ["is not well-formed SVG (%s)" % e]
    if root.tag != SVG_NS + "svg":
        return errors + ['root must be <svg xmlns="http://www.w3.org/2000/svg">']
    for attr in ("viewBox", "width", "height"):
        if not root.get(attr):
            errors.append("the <svg> element needs a %s attribute" % attr)
    for el in root.iter():
        tag = el.tag.replace(SVG_NS, "")
        if tag in SVG_FORBIDDEN:
            errors.append("<%s> is not allowed" % tag)
        for key, value in el.attrib.items():
            name = key.split("}")[-1]
            if name.startswith("on") or name == "id" or name == "style":
                errors.append("attribute '%s' is not allowed" % name)
            elif name == "href" and not value.startswith("#"):
                errors.append("links to other files are not allowed")
            elif name == "class" and not set(value.split()) <= SVG_CLASSES:
                errors.append("class '%s' is not allowed (use: %s)" % (value, ", ".join(sorted(SVG_CLASSES))))
        if tag == "text":
            words = "".join(el.itertext()).strip()
            if len(words) > 3:
                errors.append("text '%s': pictures hold only short labels like 1, 2, A; explain them in the legend" % words)
    return sorted(set(errors))


def inline_svg(src, alt):
    """The SVG markup itself, ready to drop into an HTML page."""
    m = mdlite.IMAGE_PATH.match(src)
    text = (IMAGES / (m.group(1) + ".svg")).read_text(encoding="utf-8")
    text = re.sub(r"<\?xml[^>]*\?>|<!--.*?-->", "", text, flags=re.S).strip()
    return text.replace("<svg", '<svg role="img" aria-label="%s"' % escape(alt), 1)


def read_keyvalues(path):
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                out[key.strip()] = value.strip()
    return out


def read_categories(path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            parts = [p.strip() for p in line.split("|")]
            out.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return out


def count_words(a):
    return len(article_text(a).split())


def article_text(a):
    return blocks_text(a.doc.blocks)


def blocks_text(blocks):
    return mdlite.TextRenderer(lambda href, text: "", {}).render(blocks)


def nano_blocks(a, strings, note=True):
    """The short version: the opening warnings and the quick steps, then a note.

    Articles without a quick steps section give their first section instead.
    """
    blocks = a.doc.blocks
    heads = [i for i, b in enumerate(blocks) if b[0] == "h" and b[1] == 2]
    first = heads[0] if heads else len(blocks)
    quick = strings.get("quick_steps", "Quick steps").lower()
    pick = next((i for i in heads if mdlite.plain(blocks[i][2]).lower().startswith(quick)),
                heads[0] if heads else None)
    out = list(blocks[:first])
    if pick is not None:
        end = next((i for i in heads if i > pick), len(blocks))
        out += blocks[pick:end]
    if note:
        out.append(("callout", "NOTE", [("p", [("t", strings["nano_note"])])]))
    return out


def strip_pictures(blocks):
    out = []
    for b in blocks:
        if b[0] == "img":
            continue
        out.append(("callout", b[1], strip_pictures(b[2])) if b[0] == "callout" else b)
    return out


def pictures_in(blocks):
    found = []
    for b in blocks:
        if b[0] == "img":
            found.append(b[1])
        elif b[0] == "callout":
            found += pictures_in(b[2])
    return found


# Phrases that point elsewhere in the same article. Short editions show only the
# warnings and quick steps, where "the table below" does not exist.
POINTER_RE = re.compile(
    r"\((?:see )?(?:below|above)\)|\b(?:see|steps|table|list|section|checklist|details|instructions|signs)"
    r"\s+(?:\w+\s+)?(?:below|above)\b|\bbelow\s*[.:)]", re.I)


# ---- editions ---------------------------------------------------------------

LEVELS = ("full", "nano", "omit")


class Edition:
    """A selection of articles at a level of detail, numbered for navigation (1.1, 1.2, ...).

    levels maps each priority to "full" (the whole article), "nano" (only the
    warnings and quick steps) or "omit". drawings=False leaves pictures out.
    """

    def __init__(self, lib, core=False, levels=None, drawings=True, note_each=True):
        self.lib = lib
        self.s = lib.strings
        if levels is None:
            levels = {p: "full" if p == "critical" or not core else "omit" for p in PRIORITIES}
        self.levels = levels
        self.drawings = drawings
        self.short = "nano" in levels.values()
        self.core = any(level != "full" for level in levels.values())  # some articles shortened or left out
        self.articles = [a for a in lib.articles if levels[a.priority] != "omit"]
        self._blocks = {}
        for a in self.articles:
            blocks = a.doc.blocks if levels[a.priority] == "full" else nano_blocks(a, self.s, note_each)
            self._blocks[a.id] = blocks if drawings else strip_pictures(blocks)
        self.ids = {a.id for a in self.articles}
        self.groups = []
        self.number = {}
        for cat, title, desc in lib.categories:
            items = [a for a in self.articles if a.category == cat]
            if items:
                self.groups.append((cat, title, desc, items))
                n = len(self.groups)
                for k, a in enumerate(items, 1):
                    self.number[a.id] = "%d.%d" % (n, k)
        self.words = sum(len(blocks_text(self._blocks[a.id]).split()) for a in self.articles)
        self.date = max((a.updated for a in self.articles), default="")
        version = os.environ.get("JIC_VERSION", "").strip()
        self.label = "%s (%s)" % (version, self.date) if version else self.date
        self.labels = {k: self.s.get(v, v.upper()) for k, v in
                       (("caution", "danger"), ("warning", "warning"), ("important", "important"),
                        ("tip", "tip"), ("note", "note"), ("picture", "picture"))}
        if all(level == "full" for level in levels.values()):
            self.title = self.s["library_name"]
        elif "nano" in levels.values():
            self.title = "%s - %s" % (self.s["library_name"], self.s["short_edition"])
        else:
            self.title = self.s["library_name"] + " - Core"

    def blocks(self, a):
        """The article's content in this edition."""
        return self._blocks[a.id]

    def describe(self):
        """What this edition holds, in a few words, for the device page."""
        n = {level: sum(1 for a in self.lib.articles if self.levels[a.priority] == level) for level in LEVELS}
        parts = []
        if n["full"]:
            parts.append("%d articles in full" % n["full"])
        if n["nano"]:
            parts.append("%d as warnings and quick steps only" % n["nano"])
        text = ", ".join(parts)
        return text + (", with drawings" if self.drawings and pictures_in(
            [b for a in self.articles for b in self.blocks(a)]) else "")

    def target(self, href):
        """The article an internal link points to, or None (external, or not in this edition)."""
        m = mdlite.INTERNAL_LINK.match(href)
        if not m:
            return None
        a = self.lib.by_id.get(m.group(2))
        return a if a and a.id in self.ids else None

    def resolver(self, url_for):
        def resolve(href):
            if mdlite.EXTERNAL_LINK.match(href):
                return href
            a = self.target(href)
            return url_for(a) if a else None
        return resolve

    def stats_line(self):
        return "%s %s · %d %s · %s %s" % (
            self.s["edition"], self.label, len(self.articles), self.s["articles"],
            "{:,}".format(self.words), self.s["words"])

    def review_note(self, a):
        return self.s.get("review_" + a.reviewed, "")

    def star(self, a):
        return STAR + " " if a.critical else ""


DOWNLOAD_LABELS = {
    "html": "Whole library as one web page (open it in any browser, offline)",
    "epub": "E-book (EPUB) for e-readers and phone book apps",
    "txt": "Plain text (works on almost anything)",
    "core-txt": "Core edition, plain ASCII text (MP3 players, tiny screens)",
}


def lang_suffix(lang):
    return "" if lang == "en" else "." + lang


def lang_href(current, target):
    """Link between site languages: English at site/, others at site/<lang>/."""
    if current == target:
        return "index.html"
    up = "" if current == "en" else "../"
    return up + ("index.html" if target == "en" else target + "/index.html")


# ---- shared HTML pieces -----------------------------------------------------

CSS = """
:root{--bg:#fffdf8;--fg:#161616;--muted:#4d4d4d;--line:#cfc9bb;--link:#0b4fa8;--box:#f2efe6;
--danger:#b00020;--warning:#9a4d00;--important:#5b2a9e;--tip:#1d6b2f;--note:#1f4f8f}
@media (prefers-color-scheme:dark){:root{--bg:#111;--fg:#e9e7e2;--muted:#b0aca3;--line:#3b3934;
--link:#8ab4ff;--box:#1d1c19;--danger:#ff6b6b;--warning:#ffa94d;--important:#c4a5ff;--tip:#69db7c;--note:#74c0fc}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
body{margin:0 auto;max-width:44rem;padding:0 16px 4rem;background:#fffdf8;background:var(--bg);color:#161616;color:var(--fg);
font:1.05rem/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",Arial,sans-serif;overflow-wrap:break-word}
h1,h2,h3,h4,h5{line-height:1.25;margin:1.6em 0 .5em}
h1{font-size:1.9rem}
a{color:var(--link)}
li{margin:.25em 0}
.summary{font-size:1.1em;color:var(--muted)}
.callout{border-left:6px solid #777;border-color:var(--c);padding:.1rem .9rem;margin:1rem 0;background:var(--box)}
[dir=rtl] .callout{border-left:0;border-right:6px solid #777;border-right-color:var(--c)}
.callout-label{font-weight:700;letter-spacing:.06em;color:var(--c);margin:.6rem 0 .2rem}
.callout-caution{--c:var(--danger)}.callout-warning{--c:var(--warning)}.callout-important{--c:var(--important)}
.callout-tip{--c:var(--tip)}.callout-note{--c:var(--note)}
.table{overflow-x:auto;margin:1rem 0}
table{border-collapse:collapse;width:100%;font-size:.95em}
th,td{border:1px solid var(--line);padding:.35rem .5rem;text-align:start;vertical-align:top}
th{background:var(--box)}
pre{background:var(--box);padding:.75rem;overflow-x:auto;font:.85rem/1.3 ui-monospace,Menlo,Consolas,monospace}
code{font-family:ui-monospace,Menlo,Consolas,monospace;background:var(--box);padding:0 .2em}
.meta{font-size:.85em;color:var(--muted);border-top:1px solid var(--line);padding-top:.5rem;margin-top:2rem}
.disclaimer{border:2px solid var(--line);padding:.6rem .8rem}
.toc,.toc ul{padding-inline-start:1.2rem}
.toc>li{margin:.8em 0}
.catdesc{color:var(--muted);margin-top:-.3rem}
input[type=search]{width:100%;font-size:1.15rem;padding:.65rem;border:2px solid var(--fg);border-radius:6px;background:var(--bg);color:var(--fg)}
#results{padding-inline-start:1.4rem}
.bar{padding:.8rem 0;border-bottom:1px solid var(--line);font-size:.95em}
.pager{display:flex;justify-content:space-between;gap:1rem;margin:2rem 0;flex-wrap:wrap}
.downloads li{margin:.5em 0}
.device{border-top:1px solid var(--line);padding-top:.2rem}
.device h2{font-size:1.1rem;margin:.9rem 0 .3rem}
.device p{margin:.2rem 0}
figure.diagram{margin:1.2rem 0;break-inside:avoid}
figure.diagram svg{display:block;width:100%;max-width:30rem;height:auto;margin:0 auto;color:var(--fg)}
figure.diagram .bg{fill:var(--bg)}
figure.diagram .accent{stroke:var(--danger)}
figure.diagram .accent-fill{fill:var(--danger)}
figure.diagram .muted{stroke:var(--muted)}
figcaption{font-size:.92em;color:var(--muted);margin-top:.4rem}
@media print{
body{max-width:none;padding:0;font-size:10.5pt;background:#fff;color:#000}
#search,.noprint,.back,.bar,.pager{display:none!important}
.category{break-before:page}
.callout,table,pre{break-inside:avoid}
h2,h3,h4,h5{break-after:avoid}
a{color:inherit;text-decoration:none}
.callout{background:none}
}
""".strip()

# Cards print 4 per sheet: 98 x 130 mm each fits both A4 and US Letter paper.
CARDS_CSS = """
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(17rem,1fr));gap:1rem;margin-top:1rem}
.card{border:2px dashed var(--line);border-radius:8px;padding:.5rem .8rem;font-size:.95rem;break-inside:avoid}
.card h2{font-size:1.15rem;margin:.2rem 0 .5rem}
.card p,.card ul,.card ol{margin:.35rem 0}
.card ul,.card ol{padding-inline-start:1.3rem}
.card li{margin:.1rem 0}
.card table{font-size:.9em}
.card figure.diagram{margin:.4rem 0}
.card figcaption{font-size:.85em}
.card-foot{font-size:.75rem;color:var(--muted);border-top:1px solid var(--line);padding-top:.2rem;margin-top:.5rem}
@media print{
@page{margin:5mm}
body{max-width:none;padding:0}
.cards{grid-template-columns:98mm 98mm;grid-auto-rows:130mm;gap:3mm;justify-content:center;margin:0}
.card{font-size:10pt;line-height:1.32;overflow:hidden;border:1px dashed #888;border-radius:0;padding:3mm 4mm}
.card h2{font-size:13pt;margin:0 0 2mm}
.card figure.diagram{margin:1mm 0}
.card figure.diagram svg{max-height:25mm}
.card figcaption{font-size:7.6pt;margin-top:.5mm}
.card:nth-child(4n){break-after:page}
}
""".strip()

# The single file nests one level deeper (category h2, article h3, sections h4/h5).
SINGLE_CSS = """
main h2{font-size:1.75rem;border-bottom:3px solid var(--fg);padding-bottom:.3rem}
main h3{font-size:1.45rem;margin-top:2.4em}
main h4{font-size:1.2rem}
main h5{font-size:1.05rem}
""".strip()

EPUB_CSS = """
body{font-family:serif;line-height:1.45}
h1,h2,h3,h4{font-family:sans-serif;line-height:1.2}
h2{margin-top:2em;page-break-before:always}
.summary{font-style:italic}
.callout{border-left:5px solid #555;padding:.1em .8em;margin:1em 0}
.callout-label{font-family:sans-serif;font-weight:bold;letter-spacing:.05em;margin:.4em 0 .2em}
.callout-caution{border-left-width:9px}
table{border-collapse:collapse;width:100%;margin:1em 0}
th,td{border:1px solid #777;padding:.25em .4em;vertical-align:top;text-align:left}
pre{font-family:monospace;font-size:.8em;white-space:pre}
.meta{font-size:.8em;margin-top:1.5em}
figure{margin:1em 0;text-align:center;page-break-inside:avoid}
figure img{max-width:100%}
figcaption{font-size:.85em;text-align:left}
""".strip()

SEARCH_INLINE_JS = r"""
(function(){
var box=document.getElementById('search'),q=document.getElementById('q'),out=document.getElementById('results'),none=document.getElementById('none'),items=null;
if(!box||!q)return;box.hidden=false;
function txt(el,tag,cls){var e=el.getElementsByTagName(tag);for(var i=0;i<e.length;i++){if(!cls||e[i].className===cls)return e[i].textContent.toLowerCase();}return '';}
function load(){items=[];var a=document.getElementsByTagName('article');for(var i=0;i<a.length;i++){var h=a[i].getElementsByTagName('h3')[0];items.push({id:a[i].id,t:h?h.textContent:a[i].id,c:!!h&&h.textContent.indexOf('\u2605')>=0,s:txt(a[i],'p','summary'),g:(a[i].getAttribute('data-tags')||'').toLowerCase(),x:a[i].textContent.toLowerCase()});}}
function norm(w){return w.replace(/oea/g,'ea').replace(/aem/g,'em').replace(/paed/g,'ped').replace(/oes/g,'es');}function count(x,w){var c=0,i=x.indexOf(w);while(i>=0&&c<5){c++;i=x.indexOf(w,i+w.length);}return c;}
function pts(it,t,x){var n=0;if(t.indexOf(x)>=0)n+=10;if(it.g.indexOf(x)>=0)n+=5;if(it.s.indexOf(x)>=0)n+=2;return n+count(it.x,x);}
function score(it,w){var t=it.t.toLowerCase(),n=it.c?1:0;for(var j=0;j<w.length;j++){var p=Math.max(pts(it,t,w[j]),pts(it,t,norm(w[j])));if(!p)return -1;n+=p;}return n;}
q.oninput=function(){if(!items)load();var w=q.value.toLowerCase().split(/\s+/).filter(function(s){return s;}),hits=[];out.innerHTML='';none.hidden=true;if(!w.length)return;
for(var i=0;i<items.length;i++){var n=score(items[i],w);if(n>=0)hits.push([n,i]);}
hits.sort(function(a,b){return b[0]-a[0]||a[1]-b[1];});none.hidden=hits.length>0;
for(var k=0;k<hits.length&&k<40;k++){var it2=items[hits[k][1]],li=document.createElement('li'),l=document.createElement('a');l.href='#'+it2.id;l.textContent=it2.t;li.appendChild(l);out.appendChild(li);}};
})();
""".strip()

SEARCH_SITE_JS = r"""
(function(){
var box=document.getElementById('search'),q=document.getElementById('q'),out=document.getElementById('results'),none=document.getElementById('none'),items=null,loading=false;
if(!box||!q)return;box.hidden=false;
function load(){if(items||loading)return;loading=true;var r=new XMLHttpRequest();r.open('GET','index.json');r.onload=function(){try{items=JSON.parse(r.responseText);}catch(e){items=[];}run();};r.send();}
function norm(w){return w.replace(/oea/g,'ea').replace(/aem/g,'em').replace(/paed/g,'ped').replace(/oes/g,'es');}function pts(it,t,s,x){var n=0;if(t.indexOf(x)>=0)n+=10;if(it.g.indexOf(x)>=0)n+=5;if(s.indexOf(x)>=0)n+=2;if(it.f.indexOf(x)>=0)n+=4;if(!n&&it.k.indexOf(x)>=0)n=0.5;return n;}
function score(it,w){var t=it.t.toLowerCase(),s=it.s.toLowerCase(),n=it.p==='critical'?1:0;for(var j=0;j<w.length;j++){var p=Math.max(pts(it,t,s,w[j]),pts(it,t,s,norm(w[j])));if(!p)return -1;n+=p;}return n;}
function run(){if(!items){load();return;}var w=q.value.toLowerCase().split(/\s+/).filter(function(s){return s;}),hits=[];out.innerHTML='';none.hidden=true;if(!w.length)return;
for(var i=0;i<items.length;i++){var n=score(items[i],w);if(n>=0)hits.push([n,i]);}
hits.sort(function(a,b){return b[0]-a[0]||a[1]-b[1];});none.hidden=hits.length>0;
for(var k=0;k<hits.length&&k<40;k++){var it2=items[hits[k][1]],li=document.createElement('li'),l=document.createElement('a');l.href=it2.u||it2.i+'.html';l.textContent=it2.t;li.appendChild(l);var sm=document.createElement('div');sm.textContent=it2.s;li.appendChild(sm);out.appendChild(li);}}
q.onfocus=load;q.oninput=run;
})();
""".strip()


FAVICON = '<link rel="icon" href="data:image/svg+xml,%s">' % quote(icon.svg())
APP_HEAD = ('<link rel="manifest" href="manifest.webmanifest">\n<meta name="theme-color" content="#1e3a2f">\n'
            '<link rel="icon" href="icon.svg" type="image/svg+xml">\n<link rel="apple-touch-icon" href="icon-192.png">')


def html_page(lang, direction, title, body, css=None, css_href=None, script=None, script_src=None, app=False):
    head = ['<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>%s</title>" % escape(title), APP_HEAD if app else FAVICON]
    if css:
        head.append("<style>%s</style>" % css)
    if css_href:
        head.append('<link rel="stylesheet" href="%s">' % css_href)
    tail = ""
    if script:
        tail += "<script>%s</script>\n" % script
    for src in ([script_src] if isinstance(script_src, str) else script_src or []):
        tail += '<script src="%s"></script>\n' % src
    if app:
        tail += '<script src="app.js"></script>\n'
    return '<!DOCTYPE html>\n<html lang="%s" dir="%s">\n<head>\n%s\n</head>\n<body>\n%s\n%s</body>\n</html>\n' % (
        lang, direction, "\n".join(head), body, tail)


def search_box(s):
    return ('<div id="search" class="noprint" hidden>\n<label for="q"><strong>%s</strong></label>\n'
            '<input type="search" id="q" placeholder="%s" autocomplete="off">\n'
            '<ol id="results"></ol>\n<p id="none" hidden>%s</p>\n</div>') % (
        escape(s["search"]), escape(s["search_placeholder"]), escape(s["no_results"]))


def article_html(ed, a, url_for, heading_tag, heading_shift, number=True, back=True, picture=inline_svg):
    r = mdlite.HtmlRenderer(ed.resolver(url_for), ed.labels, heading_shift, a.id, picture)
    num = ed.number[a.id] + " " if number else ""
    parts = ["<%s>%s%s%s</%s>" % (heading_tag, num, ed.star(a), escape(a.title), heading_tag),
             '<p class="summary">%s</p>' % escape(a.summary),
             r.render(ed.blocks(a))]
    meta = "%s · %s %s" % (escape(ed.review_note(a)), escape(ed.s["updated"]), escape(a.updated))
    if back:
        meta += ' · <a class="back" href="#top">%s</a>' % escape(ed.s["back_to_top"])
    parts.append('<p class="meta">%s</p>' % meta)
    return "\n".join(parts)


# ---- pocket cards -----------------------------------------------------------

def map_inlines(blocks, f):
    """Apply f to every inline list in a block tree."""
    out = []
    for b in blocks:
        k = b[0]
        if k == "h":
            out.append(("h", b[1], f(b[2])))
        elif k == "p":
            out.append(("p", f(b[1])))
        elif k == "list":
            out.append(("list", b[1], b[2], [(f(t), [map_inlines([c], f)[0] for c in ch]) for t, ch in b[3]]))
        elif k == "callout":
            out.append(("callout", b[1], map_inlines(b[2], f)))
        elif k == "table":
            out.append(("table", [f(c) for c in b[1]], [[f(c) for c in row] for row in b[2]]))
        else:
            out.append(b)
    return out


def numbered_links(ed):
    """Replace article links with '6.2 Title', for paper where links cannot be clicked."""
    def f(nodes):
        out = []
        for n in nodes:
            if n[0] == "a":
                t = ed.target(n[1])
                out.append(("t", "%s %s" % (ed.number[t.id], t.title)) if t else ("t", mdlite.plain(n[2])))
            elif n[0] in ("b", "i"):
                out.append((n[0], f(n[1])))
            else:
                out.append(n)
        return out
    return f


def cards_html(ed, url_for=None):
    """The cards as HTML sections. Without url_for, links become printed article numbers."""
    parts = []
    for title, blocks in ed.lib.cards:
        if url_for is None:
            blocks = map_inlines(blocks, numbered_links(ed))
        r = mdlite.HtmlRenderer(ed.resolver(url_for or (lambda t: None)), ed.labels, 0, "card-" + mdlite.slug(title), inline_svg)
        parts.append('<section class="card">\n<h2>%s</h2>\n%s\n<p class="card-foot">%s \u00b7 %s</p>\n</section>' % (
            escape(title), r.render(blocks), escape(ed.s["library_name"]), escape(ed.label)))
    return '<div class="cards">\n%s\n</div>' % "\n".join(parts)


def build_cards_page(ed, standalone=True, url_for=None):
    s = ed.s
    head = ['<header class="noprint">', "<h1>%s</h1>" % escape(s["cards_title"]),
            "<p>%s</p>" % escape(s["cards_intro"]), "</header>"]
    if not standalone:
        head.insert(0, '<nav class="bar noprint"><a href="index.html">%s</a></nav>' % escape(s["library_name"]))
    body = "\n".join(head) + "\n" + cards_html(ed, None if standalone else (url_for or (lambda t: t.id + ".html")))
    title = "%s - %s" % (s["cards_title"], s["library_name"])
    if standalone:
        return html_page(ed.lib.lang, s.get("direction", "ltr"), title, body, css=CSS + "\n" + CARDS_CSS)
    return html_page(ed.lib.lang, s.get("direction", "ltr"), title, body, css_href="style.css", app=True)


# ---- printed book (PDF via WeasyPrint) --------------------------------------

BOOK_CSS = """
@page{size:A4;margin:18mm 17mm 20mm;
 @top-left{content:string(category);font:8pt sans-serif;color:#555}
 @top-right{content:string(article);font:8pt sans-serif;color:#555}
 @bottom-center{content:counter(page);font:9pt sans-serif}}
@page cover{@top-left{content:none}@top-right{content:none}@bottom-center{content:none}}
@page front{@top-left{content:none}@top-right{content:none}}
body{font:10.5pt/1.42 "DejaVu Serif","Noto Serif",Georgia,serif;color:#000}
h1,h2,h3,h4,h5,.callout-label,.toc,.index,figcaption,.meta,.card-foot{font-family:"DejaVu Sans","Noto Sans",Helvetica,Arial,sans-serif}
.cover{page:cover;text-align:center;padding-top:45mm;break-after:page}
.cover svg{width:34mm;height:34mm}
.cover h1{font-size:34pt;margin:8mm 0 4mm}
.cover .tagline{font-size:14pt}
.cover .small{font-size:9.5pt;margin-top:30mm;text-align:left}
.front{page:front;break-after:page}
.toc ol{list-style:none;padding:0;margin:0}
.toc li{margin:0}
.toc .cat{font-weight:bold;margin-top:3mm}
.toc .art{padding-left:6mm;font-size:9.5pt}
.toc a{color:#000;text-decoration:none}
.toc a::after{content:leader('.') target-counter(attr(href),page)}
h2.cat{string-set:category content();break-before:page;font-size:20pt;border-bottom:2pt solid #000;padding-bottom:2mm}
article h3{string-set:article content();font-size:14pt;margin:9mm 0 1mm;break-after:avoid}
h4{font-size:11.5pt;margin:5mm 0 1.5mm;break-after:avoid}
h5{font-size:10.5pt;margin:4mm 0 1mm;break-after:avoid}
.summary{font-style:italic;margin-top:0}
p{margin:1.6mm 0}
ul,ol{margin:1.6mm 0;padding-left:6mm}
li{margin:.6mm 0}
a{color:#000;text-decoration:none}
.callout{border-left:3.5pt solid #000;padding:.5mm 3mm;margin:3mm 0;break-inside:avoid;background:#f2f2f2}
.callout-caution{border-left-width:6pt}
.callout-label{font-weight:bold;letter-spacing:.06em;font-size:9pt;margin:1.5mm 0 .5mm}
table{border-collapse:collapse;width:100%;font-size:9pt;margin:2.5mm 0;break-inside:avoid}
th,td{border:.6pt solid #666;padding:1mm 1.5mm;vertical-align:top;text-align:left}
th{background:#e6e6e6}
pre{font:7.6pt/1.25 "DejaVu Sans Mono",Menlo,monospace;break-inside:avoid;margin:2mm 0}
code{font-family:"DejaVu Sans Mono",Menlo,monospace;font-size:.9em}
figure.diagram{margin:3mm 0;break-inside:avoid;text-align:center}
figure.diagram svg{width:120mm;max-width:100%;height:auto;max-height:75mm}
figcaption{font-size:8.5pt;text-align:left;margin-top:1mm}
.meta{font-size:8pt;color:#555;margin-top:3mm}
.index{break-before:page}
.index h2{font-size:20pt}
.index .cols{columns:2;column-gap:8mm;font-size:8.6pt;line-height:1.3}
.index h4{font-size:10pt;margin:3mm 0 1mm}
.index p{margin:0;padding-left:3mm;text-indent:-3mm}
.index a::after{content:target-counter(attr(href),page)}
.index a+a::before{content:", "}
article a[href^="#"]::after{content:" (p. " target-counter(attr(href),page) ")"}
""".strip()


def book_index(ed):
    """Back-of-book index: every tag, with links to the articles that use it."""
    entries = {}
    for a in ed.articles:
        for tag in a.tags:
            entries.setdefault(tag.lower(), [])
            if a.id not in entries[tag.lower()]:
                entries[tag.lower()].append(a.id)
    out = []
    letter = None
    for tag in sorted(entries, key=lambda t: (t.lstrip("0123456789").lower() or t, t)):
        first = tag[0].upper() if tag[0].isalpha() else "#"
        if first != letter:
            letter = first
            out.append("<h4>%s</h4>" % letter)
        refs = "".join('<a href="#%s"></a>' % aid for aid in entries[tag])
        out.append("<p>%s %s</p>" % (escape(tag), refs))
    return "\n".join(out)


POCKET_CSS = """
@page{size:A6;margin:9mm 8mm 11mm;
 @top-left{content:none}
 @top-right{content:string(article);font:6.5pt sans-serif;color:#555}
 @bottom-center{content:counter(page);font:7pt sans-serif}}
body{font-size:8.4pt;line-height:1.32}
.cover{padding-top:18mm}
.cover svg{width:20mm;height:20mm}
.cover h1{font-size:18pt}
.cover .tagline{font-size:10pt}
.cover .small{font-size:7pt;margin-top:12mm}
h2.cat{font-size:13pt}
article h3{font-size:10pt;margin:5mm 0 1mm}
h4{font-size:9pt;margin:3mm 0 1mm}
.toc .art{font-size:7.5pt}
.callout{padding:.3mm 2mm;margin:2mm 0}
table{font-size:7.5pt}
.index .cols{font-size:7pt;column-gap:5mm}
""".strip()


def build_book_html(ed, repo, pocket=False):
    s = ed.s
    star = icon.svg().replace("<svg", '<svg role="img" aria-label="%s"' % escape(s["library_name"]), 1)
    out = ['<section class="cover">', star, "<h1>%s</h1>" % escape(ed.title),
           '<p class="tagline">%s</p>' % escape(s["tagline"]), "<p>%s</p>" % escape(ed.stats_line()),
           '<div class="small"><p><strong>%s</strong></p><p>%s</p>%s</div>' % (
               escape(s["disclaimer"]), license_html(s), "<p>%s</p>" % escape(repo) if repo else ""),
           "</section>",
           '<section class="front">', "<h2>%s</h2>" % escape(s["book_howto_title"]),
           "<p>%s</p>" % escape(s["book_howto"]), "<p>%s</p>" % escape(s["nano_note"]) if ed.short else "",
           "<p>%s</p>" % escape(s["start_here"]),
           "<p>%s</p>" % escape(s["legend"]), "</section>",
           '<nav class="toc front">', "<h2>%s</h2>" % escape(s["contents"]), "<ol>"]
    for n, (cat, title, desc, items) in enumerate(ed.groups, 1):
        out.append('<li class="cat"><a href="#c-%s">%d %s</a></li>' % (cat, n, escape(title)))
        out += ['<li class="art"><a href="#%s">%s %s%s</a></li>' % (
            a.id, ed.number[a.id], ed.star(a), escape(a.title)) for a in items]
    out += ["</ol>", "</nav>"]
    for n, (cat, title, desc, items) in enumerate(ed.groups, 1):
        out.append('<section id="c-%s">' % cat)
        out.append('<h2 class="cat">%d %s</h2>' % (n, escape(title)))
        out.append('<p class="summary">%s</p>' % escape(desc))
        for a in items:
            out.append('<article id="%s">' % a.id)
            out.append(article_html(ed, a, lambda t: "#" + t.id, "h3", 2, back=False))
            out.append("</article>")
        out.append("</section>")
    if not pocket:
        out += ['<section class="index">', "<h2>%s</h2>" % escape(s["index"]), '<div class="cols">',
                book_index(ed), "</div>", "</section>"]
    css = BOOK_CSS + ("\n" + POCKET_CSS if pocket else "")
    return html_page(ed.lib.lang, s.get("direction", "ltr"), ed.title, "\n".join(out), css=css)


# ---- single-file HTML -------------------------------------------------------

def build_single_html(ed, repo):
    s = ed.s
    out = ['<header id="top">', "<h1>%s</h1>" % escape(ed.title),
           '<p class="summary">%s</p>' % escape(s["tagline"]),
           '<p class="meta">%s%s</p>' % (escape(ed.stats_line()),
                                         ' · <a href="%s">%s</a>' % (escape(repo), escape(repo)) if repo else ""),
           '<p class="disclaimer">%s</p>' % escape(s["disclaimer"]), "</header>",
           search_box(s), '<nav id="contents">', "<h2>%s</h2>" % escape(s["contents"]),
           "<p>%s %s</p>" % (escape(s["legend"]), escape(s["start_here"])), '<ol class="toc">']
    for cat, title, desc, items in ed.groups:
        links = "\n".join('<li><a href="#%s">%s%s</a></li>' % (a.id, ed.star(a), escape(a.title)) for a in items)
        out.append('<li><a href="#c-%s"><strong>%s</strong></a> – %s\n<ul>\n%s\n</ul></li>' % (
            cat, escape(title), escape(desc), links))
    out += ["</ol>", "</nav>", "<main>"]
    for n, (cat, title, desc, items) in enumerate(ed.groups, 1):
        out.append('<section class="category" id="c-%s">' % cat)
        out.append("<h2>%d. %s</h2>" % (n, escape(title)))
        out.append('<p class="catdesc">%s</p>' % escape(desc))
        for a in items:
            out.append('<article id="%s" data-tags="%s">' % (a.id, escape(", ".join(a.tags))))
            out.append(article_html(ed, a, lambda t: "#" + t.id, "h3", 2))
            out.append("</article>")
        out.append("</section>")
    out += ["</main>", '<footer class="meta">%s</footer>' % license_html(s)]
    return html_page(ed.lib.lang, s.get("direction", "ltr"), ed.title, "\n".join(out),
                     css=CSS + "\n" + SINGLE_CSS, script=SEARCH_INLINE_JS)


def license_html(s):
    return ("%s · Content: CC BY-SA 4.0 · Code: MIT. Copy it, print it, share it, translate it." %
            escape(s["library_name"]))


# ---- multi-page site (ESP32, Raspberry Pi, GitHub Pages) --------------------

APP_JS = r"""
(function(){
if(!('serviceWorker' in navigator))return;
var h=location.hostname;
if(location.protocol!=='https:'&&h!=='localhost'&&h!=='127.0.0.1')return;
navigator.serviceWorker.register('sw.js').then(function(){var t=document.getElementById('install');if(t)t.hidden=false;}).catch(function(){});
})();
""".strip()

SW_JS = r"""
var CACHE='jic-%s';
var FILES=%s;
self.addEventListener('install',function(e){e.waitUntil(caches.open(CACHE).then(function(c){return c.addAll(FILES);}).then(function(){return self.skipWaiting();}));});
self.addEventListener('activate',function(e){e.waitUntil(caches.keys().then(function(ks){return Promise.all(ks.filter(function(k){return k.indexOf('jic-')===0&&k!==CACHE;}).map(function(k){return caches.delete(k);}));}).then(function(){return self.clients.claim();}));});
self.addEventListener('fetch',function(e){if(e.request.method!=='GET')return;e.respondWith(caches.match(e.request,{ignoreSearch:true}).then(function(r){return r||fetch(e.request).catch(function(){return caches.match('index.html');});}));});
""".strip()


def write_app_files(ed, outdir, skip):
    """Icons, web app manifest and a service worker that keeps the whole site offline."""
    s = ed.s
    (outdir / "icon.svg").write_text(icon.svg(), encoding="utf-8")
    for size in (192, 512):
        (outdir / ("icon-%d.png" % size)).write_bytes(icon.png(size))
    icons = [{"src": "icon-%d.png" % n, "sizes": "%dx%d" % (n, n), "type": "image/png", "purpose": purpose}
             for n in (192, 512) for purpose in ("any", "maskable")]
    manifest = {"name": s["library_name"],
                "short_name": s["library_name"], "description": s["tagline"], "lang": ed.lib.lang,
                "dir": s.get("direction", "ltr"), "start_url": "./index.html", "scope": "./",
                "display": "standalone", "background_color": "#fffdf8", "theme_color": "#1e3a2f",
                "icons": icons + [{"src": "icon.svg", "sizes": "any", "type": "image/svg+xml"}]}
    (outdir / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    (outdir / "app.js").write_text(APP_JS + "\n", encoding="utf-8")
    files = sorted(p.name for p in outdir.iterdir() if p.is_file() and p.name not in skip and p.name != "sw.js")
    version = hashlib.sha1(b"".join((outdir / f).read_bytes() for f in files)).hexdigest()[:12]
    (outdir / "sw.js").write_text(SW_JS % (version, json.dumps(["./"] + files)) + "\n", encoding="utf-8")


def build_site(ed, outdir, downloads, languages, pages="article"):
    """The multi-page website. pages="category" puts each topic on one page: far fewer
    files, which matters on tiny file systems that use a whole block per file."""
    s = ed.s
    lang = ed.lib.lang
    direction = s.get("direction", "ltr")
    by_category = pages == "category"

    def url_for(a):
        return "c-%s.html#%s" % (a.category, a.id) if by_category else a.id + ".html"

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "style.css").write_text(CSS + "\n" + CARDS_CSS + "\n", encoding="utf-8")
    (outdir / "search.js").write_text(SEARCH_SITE_JS + "\n", encoding="utf-8")

    index = []
    for a in ed.articles:
        found = re.findall(r"\w{3,}", blocks_text(ed.blocks(a)).lower())
        counts = {}
        for w in found:
            counts[w] = counts.get(w, 0) + 1
        frequent = sorted(w for w, n in counts.items() if n >= 4 and len(w) > 3)
        index.append({"i": a.id, "u": url_for(a), "t": a.title, "s": a.summary, "p": a.priority,
                      "g": ", ".join(a.tags).lower(), "f": " ".join(frequent), "k": " ".join(sorted(counts))})
    (outdir / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    home = escape(s["library_name"])
    body = ["<header id=\"top\">", "<h1>%s</h1>" % escape(ed.title), '<p class="summary">%s</p>' % escape(s["tagline"]),
            '<p class="meta">%s</p>' % escape(ed.stats_line()),
            '<p class="disclaimer">%s</p>' % escape(s["disclaimer"]), "</header>", search_box(s),
            '<p id="install" class="noprint" hidden>%s</p>' % escape(s["install_tip"])]
    body.append('<h2>Save the whole library to this device</h2>\n<ul class="downloads">')
    for fname, label in downloads:
        body.append('<li><a href="%s" download>%s</a></li>' % (fname, escape(label)))
    if ed.lib.cards:
        body.append('<li><a href="cards.html">%s</a></li>' % escape(s["cards_link"]))
    body.append('<li><a href="devices.html">%s</a></li>' % escape(s["devices_link"]))
    body.append("</ul>")
    if len(languages) > 1:
        links = " \u00b7 ".join('<a href="%s" lang="%s">%s</a>' % (lang_href(lang, l), l, l) for l in languages)
        body.append("<p>%s</p>" % links)
    body.append("<h2>%s</h2>\n<p>%s %s</p>" % (escape(s["contents"]), escape(s["legend"]), escape(s["start_here"])))
    for cat, title, desc, items in ed.groups:
        heading = '<a href="c-%s.html">%s</a>' % (cat, escape(title)) if by_category else escape(title)
        body.append('<h3 id="c-%s">%s</h3>\n<p class="catdesc">%s</p>\n<ul>' % (cat, heading, escape(desc)))
        body += ['<li><a href="%s">%s%s</a></li>' % (url_for(a), ed.star(a), escape(a.title)) for a in items]
        body.append("</ul>")
    body.append('<footer class="meta">%s</footer>' % license_html(s))
    if ed.lib.cards:
        (outdir / "cards.html").write_text(build_cards_page(ed, standalone=False, url_for=url_for), encoding="utf-8")
    (outdir / "index.html").write_text(
        html_page(lang, direction, ed.title, "\n".join(body), css_href="style.css", script_src="search.js", app=True),
        encoding="utf-8")

    def pager(prev, nxt):
        out = ['<nav class="pager">']
        if prev:
            out.append('<a rel="prev" href="%s">\u2190 %s</a>' % prev)
        if nxt:
            out.append('<a rel="next" href="%s">%s \u2192</a>' % nxt)
        return "\n".join(out + ["</nav>"])

    footer = '<footer class="meta">%s</footer>' % escape(s["disclaimer"])
    if by_category:
        groups = ed.groups
        for n, (cat, title, desc, items) in enumerate(groups):
            bar = '<nav class="bar"><a href="index.html">%s</a></nav>' % home
            parts = [bar, "<main>", "<h1>%s</h1>" % escape(title), '<p class="catdesc">%s</p>' % escape(desc)]
            for a in items:
                parts += ['<article id="%s">' % a.id, article_html(ed, a, url_for, "h2", 1, number=False, back=False),
                          "</article>"]
            prev = ("c-%s.html" % groups[n - 1][0], escape(groups[n - 1][1])) if n > 0 else None
            nxt = ("c-%s.html" % groups[n + 1][0], escape(groups[n + 1][1])) if n + 1 < len(groups) else None
            parts += [pager(prev, nxt), "</main>", footer]
            (outdir / ("c-%s.html" % cat)).write_text(
                html_page(lang, direction, "%s - %s" % (title, s["library_name"]), "\n".join(parts),
                          css_href="style.css", app=True), encoding="utf-8")
    else:
        seq = ed.articles
        for n, a in enumerate(seq):
            cat_title = ed.lib.category_title[a.category]
            bar = '<nav class="bar"><a href="index.html">%s</a> \u203a <a href="index.html#c-%s">%s</a></nav>' % (
                home, a.category, escape(cat_title))
            prev = (url_for(seq[n - 1]), escape(seq[n - 1].title)) if n > 0 else None
            nxt = (url_for(seq[n + 1]), escape(seq[n + 1].title)) if n + 1 < len(seq) else None
            page = "\n".join([bar, '<main><article id="%s">' % a.id,
                              article_html(ed, a, url_for, "h1", 0, number=False, back=False),
                              "</article>", pager(prev, nxt), "</main>", footer])
            (outdir / (a.id + ".html")).write_text(
                html_page(lang, direction, "%s - %s" % (a.title, s["library_name"]), page, css_href="style.css",
                          app=True), encoding="utf-8")
    (outdir / "devices.html").write_text(build_devices_page(ed.lib, [], set()), encoding="utf-8")
    write_app_files(ed, outdir, {name for name, _ in downloads})


# ---- EPUB (Kobo, PocketBook, phones; converted to AZW3 for Kindle) ---------

def xhtml(lang, title, body, css="style.css"):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="%s" xml:lang="%s">\n'
            '<head>\n<meta charset="utf-8"/>\n<title>%s</title>\n<link rel="stylesheet" type="text/css" href="%s"/>\n</head>\n'
            "<body>\n%s\n</body>\n</html>\n") % (lang, lang, escape(title), css, body)


def build_epub(ed, path, repo):
    s = ed.s
    lang = ed.lib.lang
    direction = s.get("direction", "ltr")
    uid = "urn:uuid:%s" % uuid.uuid5(uuid.NAMESPACE_URL, "https://just-in-case/" + lang)
    files = []  # (name, text, media type, manifest id)

    title_body = "<h1>%s</h1>\n<p>%s</p>\n<p>%s</p>\n<p><strong>%s</strong></p>\n<p>%s</p>%s" % (
        escape(ed.title), escape(s["tagline"]), escape(ed.stats_line()), escape(s["disclaimer"]),
        license_html(s), "\n<p>%s</p>" % escape(repo) if repo else "")
    files.append(("title.xhtml", xhtml(lang, ed.title, title_body), "title"))

    nav = ['<nav epub:type="toc" id="toc">', "<h1>%s</h1>" % escape(s["contents"]), "<ol>"]
    ncx = []
    play = 0
    for cat, title, desc, items in ed.groups:
        fname = "c-%s.xhtml" % cat
        play += 1
        ncx.append('<navPoint id="np-%d" playOrder="%d"><navLabel><text>%s</text></navLabel><content src="%s"/>' % (
            play, play, escape(title), fname))
        sub = []
        for a in items:
            play += 1
            ncx.append('<navPoint id="np-%d" playOrder="%d"><navLabel><text>%s%s</text></navLabel><content src="%s#%s"/></navPoint>' % (
                play, play, ed.star(a), escape(a.title), fname, a.id))
            sub.append('<li><a href="%s#%s">%s%s</a></li>' % (fname, a.id, ed.star(a), escape(a.title)))
        ncx.append("</navPoint>")
        nav.append('<li><a href="%s">%s</a>\n<ol>\n%s\n</ol></li>' % (fname, escape(title), "\n".join(sub)))

        body = ['<section id="c-%s">' % cat, "<h1>%s</h1>" % escape(title), '<p class="summary">%s</p>' % escape(desc)]
        for a in items:
            body.append('<section id="%s">' % a.id)
            body.append(article_html(ed, a, lambda t: "c-%s.xhtml#%s" % (t.category, t.id), "h2", 1, back=False,
                                     picture=epub_picture))
            body.append("</section>")
        body.append("</section>")
        files.append((fname, xhtml(lang, title, "\n".join(body)), "c-" + cat))
    nav += ["</ol>", "</nav>"]
    files.insert(1, ("nav.xhtml", xhtml(lang, s["contents"], "\n".join(nav)), "nav"))

    ncx_doc = ('<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="%s">\n'
               '<head><meta name="dtb:uid" content="%s"/><meta name="dtb:depth" content="2"/>'
               '<meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>\n'
               "<docTitle><text>%s</text></docTitle>\n<navMap>\n%s\n</navMap>\n</ncx>\n") % (
        lang, uid, escape(ed.title), "\n".join(ncx))

    pictures = sorted({mdlite.IMAGE_PATH.match(src).group(1)
                       for a in ed.articles for src in pictures_in(ed.blocks(a))})
    manifest = ['<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                '<item id="css" href="style.css" media-type="text/css"/>']
    manifest += ['<item id="img-%s" href="images/%s.svg" media-type="image/svg+xml"/>' % (n, n) for n in pictures]
    for name, _, mid in files:
        props = ' properties="nav"' if mid == "nav" else ""
        manifest.append('<item id="%s" href="%s" media-type="application/xhtml+xml"%s/>' % (mid, name, props))
    spine = "\n".join('<itemref idref="%s"/>' % mid for _, _, mid in files)
    opf = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" xml:lang="%s" dir="%s">\n'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
           '<dc:identifier id="uid">%s</dc:identifier>\n<dc:title>%s</dc:title>\n<dc:language>%s</dc:language>\n'
           "<dc:creator>Just In Case contributors</dc:creator>\n<dc:rights>CC BY-SA 4.0</dc:rights>\n"
           "<dc:date>%s</dc:date>\n<dc:description>%s</dc:description>\n"
           '<meta property="dcterms:modified">%sT00:00:00Z</meta>\n</metadata>\n'
           "<manifest>\n%s\n</manifest>\n"
           '<spine toc="ncx" page-progression-direction="%s">\n%s\n</spine>\n</package>\n') % (
        lang, direction, uid, escape(ed.title), lang, ed.date, escape(s["tagline"]), ed.date,
        "\n".join(manifest), direction, spine)

    container = ('<?xml version="1.0" encoding="utf-8"?>\n'
                 '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>\n'
                 "</container>\n")

    entries = [("META-INF/container.xml", container), ("OEBPS/content.opf", opf),
               ("OEBPS/toc.ncx", ncx_doc), ("OEBPS/style.css", EPUB_CSS + "\n")]
    entries += [("OEBPS/" + name, text) for name, text, _ in files]
    entries += [("OEBPS/images/%s.svg" % n, (IMAGES / (n + ".svg")).read_text(encoding="utf-8")) for n in pictures]
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zip_info("mimetype", zipfile.ZIP_STORED), "application/epub+zip")
        for name, text in entries:
            z.writestr(zip_info(name, zipfile.ZIP_DEFLATED), text.encode("utf-8"))
    return [text for _, text, _ in files] + [opf, ncx_doc, container]


def epub_picture(src, alt):
    return '<img src="images/%s.svg" alt="%s"/>' % (mdlite.IMAGE_PATH.match(src).group(1), escape(alt))


def zip_info(name, method):
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = method
    info.external_attr = 0o644 << 16
    return info


# ---- plain text -------------------------------------------------------------

def build_text(ed, repo, ascii_only=False, width=None, split=False):
    """The edition as plain text. With split=True, returns (index_text, [(number, category, text)])
    so each topic can go in its own small file."""
    s = ed.s
    rule = "=" * (width or 60)
    thin = "-" * (width or 60)

    def note(href, text):
        if mdlite.EXTERNAL_LINK.match(href):
            return " (%s)" % href
        t = ed.target(href)
        if t is None:
            m = mdlite.INTERNAL_LINK.match(href)
            other = ed.lib.by_id.get(m.group(2)) if m else None
            return " (%s: %s)" % ("full edition" if ed.core else s["see"], other.title) if other else ""
        num = ed.number[t.id]
        if text.strip().lower() == t.title.lower():
            return " (%s %s)" % (s["see"], num)
        return " (%s %s %s)" % (s["see"], num, t.title)

    r = mdlite.TextRenderer(note, ed.labels, width, mdlite.to_ascii if ascii_only else None)
    convert = mdlite.to_ascii if ascii_only else (lambda t: t)

    def w(text, first="", rest=""):
        return r.wrap(text, width, first, rest)

    head = [w(ed.title.upper()), w(s["tagline"]), w(ed.stats_line())]
    if repo:
        head.append(repo)
    head += ["", w(s["disclaimer"])] + (["", w(s["nano_note"])] if ed.short else []) + [
        "", w(s["legend"]), w(s["start_here"]), "", rule, s["contents"].upper(), rule]
    for n, (cat, title, desc, items) in enumerate(ed.groups, 1):
        head.append("")
        head.append(w("%d %s" % (n, title.upper())))
        for a in items:
            num = ed.number[a.id]
            head.append(w("%s %s%s" % (num, ed.star(a), a.title), "  ", "  " + " " * (len(num) + 1)))
    foot = ["", rule, w("%s - Content: CC BY-SA 4.0 - Code: MIT" % s["library_name"]), rule, ""]

    sections = []
    for n, (cat, title, desc, items) in enumerate(ed.groups, 1):
        out = ["", "", rule, w("%d %s" % (n, title.upper())), w(desc), rule]
        for a in items:
            pri = s.get("priority_" + a.priority, a.priority).upper()
            out += ["", thin, w("%s %s%s  [%s]" % (ed.number[a.id], ed.star(a), a.title.upper(), pri)), thin, ""]
            out.append(w(a.summary))
            out.append("")
            out.append(r.render(ed.blocks(a)))
            out.append("")
            out.append(w("(%s. %s %s)" % (ed.review_note(a), s["updated"], a.updated)))
        sections.append((n, cat, "\n".join(out)))
    if split:
        index = convert("\n".join(head + foot))
        return index, [(n, cat, convert("\n".join([w(ed.title.upper())] + text.split("\n")[2:] + foot)))
                       for n, cat, text in sections]
    return convert("\n".join(head + [t for _, _, t in sections] + foot))


def mp3_names(ed):
    """Short upper-case 8.3 file names that old players and FAT file systems accept."""
    return ["%02d%s.TXT" % (n, re.sub(r"[^A-Z0-9]", "", cat.upper())[:6]) for n, (cat, _, _, _) in enumerate(ed.groups, 1)]


def write_mp3(ed, repo, path, folder):
    """One ASCII file with Windows line endings, plus one small file per topic."""
    crlf = lambda t: t.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_bytes(crlf(build_text(ed, repo, ascii_only=True)).encode("ascii"))
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    index, parts = build_text(ed, repo, ascii_only=True, split=True)
    names = mp3_names(ed)
    listing = "\n".join("%s  %s" % (name, title.upper()) for name, (_, title, _, _) in zip(names, ed.groups))
    (folder / "00INDEX.TXT").write_bytes(crlf(index + "\nFILES\n" + mdlite.to_ascii(listing) + "\n").encode("ascii"))
    for name, (_, _, text) in zip(names, parts):
        (folder / name).write_bytes(crlf(text).encode("ascii"))


# ---- README contents table --------------------------------------------------

def readme_table(lib):
    rows = ["| Category | Articles (%s = critical) |" % STAR, "|---|---|"]
    for cat, title, _ in lib.categories:
        items = [a for a in lib.articles if a.category == cat]
        if items:
            links = " · ".join("[%s%s](content/%s/%s/%s.md)" % (
                STAR + " " if a.critical else "", a.title, lib.lang, a.category, a.id) for a in items)
            rows.append("| **%s** | %s |" % (title, links))
    total = sum(count_words(a) for a in lib.articles)
    rows.append("")
    rows.append("*%d articles, %s words. Full outline and what is still missing: [ROADMAP.md](ROADMAP.md).*" % (
        len(lib.articles), "{:,}".format(total)))
    return "\n".join(rows)


def update_readme(lib, results=None):
    text = README.read_text(encoding="utf-8")
    blocks = [("<!-- BEGIN CONTENTS (generated by tools/build.py --readme) -->", "<!-- END CONTENTS -->",
               readme_table(lib))]
    if results:
        blocks.append(("<!-- BEGIN DEVICES (generated by tools/build.py --readme) -->", "<!-- END DEVICES -->",
                       devices_markdown(results)))
    for begin, end, table in blocks:
        if begin not in text or end not in text:
            print("README.md has no %s markers; skipped" % begin.split("(")[0].strip("<!- "))
            continue
        head, rest = text.split(begin, 1)
        _, tail = rest.split(end, 1)
        text = head + begin + "\n" + table + "\n" + end + tail
    README.write_text(text, encoding="utf-8")
    print("Updated README.md tables")


# ---- main -------------------------------------------------------------------

def repo_url():
    if os.environ.get("JIC_REPO_URL"):
        return os.environ["JIC_REPO_URL"]
    if os.environ.get("GITHUB_REPOSITORY"):
        return "%s/%s" % (os.environ.get("GITHUB_SERVER_URL", "https://github.com"), os.environ["GITHUB_REPOSITORY"])
    try:
        url = subprocess.run(["git", "-C", str(ROOT), "config", "--get", "remote.origin.url"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
    m = re.match(r"^(?:git@|ssh://git@)([^:/]+)[:/](.+?)(?:\.git)?$", url)
    if m:
        return "https://%s/%s" % m.groups()
    return url[:-4] if url.endswith(".git") else url


def report(libs):
    errors = warnings = 0
    for lib in libs:
        for kind, items in (("error", lib.errors), ("warning", lib.warnings)):
            for path, line, msg in items:
                print("%s:%s: %s: %s" % (path, line, kind, msg))
        errors += len(lib.errors)
        warnings += len(lib.warnings)
    total = sum(len(lib.articles) for lib in libs)
    print("Checked %d articles in %d language(s): %d error(s), %d warning(s)" % (total, len(libs), errors, warnings))
    return errors


def size(path):
    if path.is_dir():
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    return path.stat().st_size


def flash_usage(folder):
    """Estimated LittleFS space: whole blocks per file, plus metadata pairs for the
    directory (checked against mklittlefs: 76 files took 226 data + 5 other blocks)."""
    files = [p.stat().st_size for p in folder.rglob("*") if p.is_file()]
    blocks = sum(-(-n // FS_BLOCK) for n in files) + 2 + 2 * -(-len(files) // 32)
    return blocks * FS_BLOCK


def kb(n):
    return "%7.0f KB" % (n / 1024.0)


def write_esp_data(ed, dest, languages, pages="article", download=None):
    """The site, gzipped for a microcontroller's small flash (the sketch serves .gz directly).

    download is (file name, label, html text) for the single-file library visitors
    can save, or None. EPUB and text copies are left out: they would not fit.
    """
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp)
        offered = [(download[0], download[1])] if download else []
        build_site(ed, site, offered, languages, pages)
        if download:
            (site / download[0]).write_text(download[2], encoding="utf-8")
        for p in sorted(site.rglob("*")):
            if p.is_file():
                target = Path(str(dest / p.relative_to(site)) + ".gz")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(gzip.compress(p.read_bytes(), 9, mtime=0))


# ---- device editions (tools/editions.ini) -----------------------------------

FORMATS = ("html", "site", "epub", "txt", "ascii", "mp3", "cards", "book", "pocket", "esp")
SHRINK_STEPS = ("drawings", "useful:nano", "important:nano", "useful:omit", "important:omit",
                "download:core", "download:nano", "download:none")


class BuildError(Exception):
    pass


def read_editions(path=EDITIONS):
    """The device editions, in build order, checked for mistakes."""
    cp = configparser.ConfigParser(inline_comment_prefixes=("#",), interpolation=None)
    cp.read(path, encoding="utf-8")
    editions = []
    for name in cp.sections():
        c = cp[name]
        e = {"name": name, "format": c.get("format", ""), "devices": c.get("devices", ""),
             "label": c.get("label", ""), "offer": c.getboolean("offer", False),
             "levels": {pri: c.get(pri, "full") for pri in PRIORITIES},
             "drawings": c.getboolean("drawings", True), "budget": c.getint("budget", 0),
             "shrink": [x.strip() for x in c.get("shrink", "").split(",") if x.strip()],
             "pages": c.get("pages", "article"), "download": c.get("download", "full"),
             "dest": c.get("dest", "")}
        problems = []
        if e["format"] not in FORMATS:
            problems.append("format must be one of: " + ", ".join(FORMATS))
        problems += ["%s must be full, nano or omit" % pri for pri, lv in e["levels"].items() if lv not in LEVELS]
        problems += ["unknown shrink step '%s'" % st for st in e["shrink"] if st not in SHRINK_STEPS]
        if e["pages"] not in ("article", "category"):
            problems.append("pages must be article or category")
        if e["download"] not in ("full", "core", "nano", "none"):
            problems.append("download must be full, core, nano or none")
        if e["format"] == "esp" and not e["dest"]:
            problems.append("esp editions need a dest folder")
        if problems:
            raise BuildError("%s [%s]: %s" % (path.name, name, "; ".join(problems)))
        editions.append(e)
    return editions


def output_path(e, lang):
    """dist/<name>, with .<lang> before the extension for translations."""
    if e["format"] == "site":
        return DIST / "site" if lang == "en" else DIST / "site" / lang
    if e["format"] == "esp":
        return ROOT / e["dest"]
    stem, dot, ext = e["name"].rpartition(".")
    return DIST / ("%s%s.%s" % (stem, lang_suffix(lang), ext) if dot else e["name"] + lang_suffix(lang))


def single_html_for(lib, kind, repo):
    """The single-file library that a hotspot offers for saving."""
    if kind == "none":
        return None
    levels = {"full": {p: "full" for p in PRIORITIES},
              "core": {"critical": "full", "important": "omit", "useful": "omit"},
              "nano": {p: "nano" for p in PRIORITIES}}[kind]
    name = {"full": NAME, "core": NAME + "-core", "nano": NAME + "-short"}[kind] + lang_suffix(lib.lang) + ".html"
    label = {"full": DOWNLOAD_LABELS["html"], "core": "Core edition: the critical articles in one web page",
             "nano": "Short edition: every article's warnings and quick steps, in one web page"}[kind]
    return name, label, build_single_html(Edition(lib, levels=levels, drawings=kind == "full"), repo)


def write_edition(e, lib, ed, download, repo, width, offered, languages):
    """Write one edition; return its path and the size its budget is measured against."""
    path = output_path(e, lib.lang)
    fmt = e["format"]
    if fmt in ("html", "txt", "ascii", "cards", "book", "pocket"):
        text = {"html": lambda: build_single_html(ed, repo),
                "txt": lambda: build_text(ed, repo, width=width),
                "ascii": lambda: build_text(ed, repo, ascii_only=True, width=width),
                "cards": lambda: build_cards_page(ed),
                "book": lambda: build_book_html(ed, repo),
                "pocket": lambda: build_book_html(ed, repo, pocket=True)}[fmt]()
        path.write_text(text, encoding="ascii" if fmt == "ascii" else "utf-8")
        return path, path.stat().st_size
    if fmt == "epub":
        build_epub(ed, path, repo)
        return path, path.stat().st_size
    if fmt == "mp3":
        write_mp3(ed, repo, path, path.parent / ("mp3" + lang_suffix(lib.lang)))
        return path, path.stat().st_size
    if fmt == "site":
        if path.exists():
            for f in path.iterdir():
                if f.is_file():
                    f.unlink()
        build_site(ed, path, [(f.name, label) for f, label in offered], languages, e["pages"])
        for f, _ in offered:
            shutil.copy2(f, path / f.name)
        # Only this language's own files: not the installer images or other languages in subfolders.
        return path, sum(f.stat().st_size for f in path.iterdir() if f.is_file())
    write_esp_data(ed, path, languages, e["pages"], single_html_for(lib, download, repo))
    return path, flash_usage(path)


def build_edition(e, lib, repo, width, offered, languages):
    """Build an edition, shrinking it step by step until it fits its budget."""
    levels, drawings, download = dict(e["levels"]), e["drawings"], e["download"]
    steps, applied = list(e["shrink"]), []
    while True:
        ed = Edition(lib, levels=levels, drawings=drawings, note_each=e["format"] not in ("pocket", "mp3"))
        path, used = write_edition(e, lib, ed, download, repo, width, offered, languages)
        if not e["budget"] or used <= e["budget"] * 1024:
            return {"edition": e, "ed": ed, "path": path, "size": used, "shrunk": applied, "download": download}
        if not steps:
            raise BuildError("%s needs %d KB, more than its %d KB budget%s. Raise the budget or add shrink steps "
                             "in tools/editions.ini." % (e["name"], used // 1024, e["budget"],
                                                         ", even after cutting: " + ", ".join(applied) if applied else ""))
        step = steps.pop(0)
        what, _, how = step.partition(":")
        if what == "drawings":
            drawings = False
        elif what == "download":
            download = how
        else:
            levels[what] = how
        applied.append(step)


def build_devices_page(lib, results, available):
    """The "Which file for my device?" page. Files on this site are linked."""
    s = lib.strings
    rows = []
    for r in results:
        e = r["edition"]
        name = r["path"].name if e["format"] not in ("site", "esp") else (
            "this website" if e["format"] == "site" else "the hotspot firmware (see flash/)")
        link = '<a href="%s">%s</a>' % (r["path"].name, escape(name)) if r["path"].name in available else escape(name)
        what = "pocket cards" if e["format"] == "cards" else r["ed"].describe()
        if r["shrunk"]:
            what += " (cut to fit: %s)" % ", ".join(r["shrunk"])
        devices = " \u00b7 ".join(escape(d.strip()) for d in e["devices"].split(";") if d.strip())
        rows.append('<section class="device"><h2>%s</h2>\n<p><strong>%s</strong> \u00b7 %d KB</p>\n<p>%s</p></section>'
                    % (devices, link, r["size"] // 1024, escape(what)))
    table = "\n".join(rows)
    body = ['<nav class="bar"><a href="index.html">%s</a></nav>' % escape(s["library_name"]), "<main>",
            "<h1>%s</h1>" % escape(s["devices_title"]), "<p>%s</p>" % escape(s["devices_intro"]), table,
            "</main>", '<footer class="meta">%s</footer>' % license_html(s)]
    return html_page(lib.lang, s.get("direction", "ltr"), s["devices_title"], "\n".join(body), css_href="style.css")


def devices_markdown(results):
    """The device table for README.md."""
    rows = ["| Device | File | What it holds | Size |", "|---|---|---|---|"]
    for r in results:
        e = r["edition"]
        name = {"site": "`dist/site/` (website)", "esp": "`%s/`" % e["dest"]}.get(e["format"], "`%s`" % r["path"].name)
        what = "16 pocket cards" if e["format"] == "cards" else r["ed"].describe()
        devices = "; ".join(d.strip() for d in e["devices"].split(";") if d.strip())
        rows.append("| %s | %s | %s | %d KB |" % (devices, name, what, r["size"] // 1024))
    return "\n".join(rows)


def build(lib, languages, repo, width, esp32, only=None):
    """Build every device edition in tools/editions.ini for one language."""
    DIST.mkdir(exist_ok=True)
    results, offered = [], []
    for e in read_editions():
        if only and e["name"] not in only:
            continue
        if e["format"] == "esp" and (not esp32 or lib.lang != "en"):
            continue
        if e["format"] == "cards" and not lib.cards:
            continue
        r = build_edition(e, lib, repo, width, offered, languages)
        results.append(r)
        if e["offer"]:
            offered.append((r["path"], e["label"]))

    # The device page needs every size, so it is written last, into each site.
    for r in results:
        if r["edition"]["format"] == "site":
            page = build_devices_page(lib, results, {f.name for f, _ in offered})
            (r["path"] / "devices.html").write_text(page, encoding="utf-8")
        elif r["edition"]["format"] == "esp":
            have = {p.name[:-3] for p in r["path"].iterdir()}
            page = build_devices_page(lib, results, have)
            (r["path"] / "devices.html.gz").write_bytes(gzip.compress(page.encode("utf-8"), 9, mtime=0))

    full = next((r["ed"] for r in results if r["edition"]["format"] == "site"), Edition(lib))
    print("\nBuilt %s (%s): %s" % (lib.strings["library_name"], lib.lang, full.stats_line()))
    for r in results:
        e = r["edition"]
        shown = r["path"].relative_to(ROOT)
        limit = " of %d KB" % e["budget"] if e["budget"] else ""
        unit = "flash" if e["format"] == "esp" else ""
        print("  %-38s %6d KB%s %s%s" % (str(shown) + ("/" if r["path"].is_dir() else ""), r["size"] // 1024,
                                       limit, unit, "  cut to fit: " + ", ".join(r["shrunk"]) if r["shrunk"] else ""))
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate content only")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--lang", action="append", help="language code to build (default: all in content/)")
    ap.add_argument("--readme", action="store_true", help="refresh the contents table in README.md")
    ap.add_argument("--wrap", type=int, default=None, metavar="N", help="hard-wrap text editions at N columns")
    ap.add_argument("--draft", action="store_true", help="allow links to articles that are not written yet")
    ap.add_argument("--no-esp32", action="store_true", help="do not write the ESP32 flash data folders")
    ap.add_argument("--only", action="append", metavar="NAME", help="build only this edition from tools/editions.ini")
    args = ap.parse_args()

    languages = sorted(p.name for p in CONTENT.iterdir() if p.is_dir() and (p / "categories.txt").exists())
    languages.sort(key=lambda l: l != "en")
    wanted = args.lang or languages
    en_strings = read_keyvalues(CONTENT / "en" / "strings.txt")
    libs = [Library(lang, en_strings, args.draft) for lang in wanted]

    errors = report(libs)
    if args.strict:
        errors += sum(len(lib.warnings) for lib in libs)
    if errors:
        print("Fix the errors above, then build again.")
        return 1
    try:
        read_editions()
    except BuildError as e:
        print("error: %s" % e)
        return 1
    if args.check:
        return 0
    repo = repo_url()
    try:
        for lib in libs:
            results = build(lib, languages, repo, args.wrap, not args.no_esp32, args.only)
            if args.readme and lib.lang == "en":
                update_readme(lib, results)
    except BuildError as e:
        print("error: %s" % e)
        return 1
    print("\nDone. Open dist/%s.html in any browser." % NAME)
    return 0


if __name__ == "__main__":
    sys.exit(main())
