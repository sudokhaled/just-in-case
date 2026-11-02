"""Parser and renderers for the strict Markdown subset in STYLE_GUIDE.md.

Standard library only, so the library can rebuild itself anywhere Python 3.8+
runs, including a Raspberry Pi with no network. The HTML output is also
well-formed XHTML, so the same renderer feeds the EPUB builder.

Block nodes are tuples whose first item is the type:
    ("h", level, inlines)
    ("p", inlines)
    ("list", ordered, start, items)     items: [(inlines, [list nodes])]
    ("callout", kind, blocks)           kind: NOTE TIP IMPORTANT WARNING CAUTION
    ("table", header, rows)             header: [inlines], rows: [[inlines]]
    ("code", text)
    ("img", src, alt)                   a picture on a line of its own

Inline nodes:
    ("t", text) ("code", text) ("b", inlines) ("i", inlines) ("a", href, inlines)
"""

import re
import textwrap
import unicodedata
from html import escape

CALLOUT_KINDS = ("NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION")
CODE_WIDTH = 60

INTERNAL_LINK = re.compile(r"^\.\./([a-z0-9-]+)/([a-z0-9-]+)\.md$")
IMAGE_PATH = re.compile(r"^\.\./\.\./images/([a-z0-9-]+)\.svg$")
EXTERNAL_LINK = re.compile(r"^https?://\S+$")

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST_ITEM = re.compile(r"^( *)([-*+]|\d{1,3}[.)])\s+(.*)$")
_CALLOUT = re.compile(r"^\[!([A-Z]+)\]\s*$")
_TABLE_SEP = re.compile(r"^:?-+:?$")
_INLINE = re.compile(
    r"`(?P<code>[^`]+)`"
    r"|\[(?P<ltext>[^\]]+)\]\((?P<href>[^)\s]+)\)"
    r"|\*\*(?P<bold>.+?)\*\*"
    r"|\*(?P<ital>[^*\s](?:[^*]*?[^*\s])?)\*"
)
_RAW_HTML = re.compile(r"<[A-Za-z/!]")
_ENTITY = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[A-Za-z]+);")
_IMAGE = re.compile(r"!\[[^\]]*\]\(")
_IMAGE_LINE = re.compile(r"^!\[([^\]]+)\]\((\S+)\)\s*$")
_CODE_SPAN = re.compile(r"`[^`]+`")


class Document:
    """Parse result: block tree plus problems found and links used."""

    def __init__(self):
        self.blocks = []
        self.errors = []    # (line, message): the file must be fixed
        self.warnings = []  # (line, message): worth fixing
        self.links = []     # (line, href)
        self.images = []    # (line, src)


def parse(text, first_line=1):
    """Parse Markdown text into a Document."""
    doc = Document()
    lines = text.replace("\r\n", "\n").replace("\t", "    ").split("\n")
    numbered = [(first_line + n, line.rstrip()) for n, line in enumerate(lines)]
    doc.blocks = _Parser(doc).blocks(numbered, top=True)
    return doc


class _Parser:
    def __init__(self, doc):
        self.doc = doc

    def error(self, line, msg):
        self.doc.errors.append((line, msg))

    def warn(self, line, msg):
        self.doc.warnings.append((line, msg))

    # ---- blocks ---------------------------------------------------------

    def blocks(self, lines, top):
        out = []
        i = 0
        while i < len(lines):
            num, line = lines[i]
            if not line.strip():
                i += 1
            elif line.startswith("```"):
                i = self.code(lines, i, out)
            elif line.startswith("#"):
                self.heading(num, line, top, out)
                i += 1
            elif line.startswith(">"):
                i = self.callout(lines, i, out)
            elif _IMAGE_LINE.match(line):
                self.image(num, line, out)
                i += 1
            elif line.startswith("|"):
                i = self.table(lines, i, out)
            elif _LIST_ITEM.match(line):
                indent = len(_LIST_ITEM.match(line).group(1))
                if indent:
                    self.error(num, "list must start at the left margin, not indented")
                node, i = self.list(lines, i, indent)
                out.append(node)
            elif line.strip() in ("---", "***", "___"):
                self.error(num, "horizontal rules are not used inside articles")
                i += 1
            elif line[0] == " ":
                self.error(num, "unexpected indentation (nested list items need a parent item)")
                i += 1
            else:
                i = self.paragraph(lines, i, out)
        return out

    def code(self, lines, i, out):
        start = lines[i][0]
        body = []
        i += 1
        while i < len(lines) and not lines[i][1].startswith("```"):
            num, line = lines[i]
            if len(line) > CODE_WIDTH:
                self.warn(num, "diagram line is %d characters; keep it to %d for small screens" % (len(line), CODE_WIDTH))
            body.append(line)
            i += 1
        if i == len(lines):
            self.error(start, "code block is never closed with ```")
        out.append(("code", "\n".join(body)))
        return i + 1

    def image(self, num, line, out):
        m = _IMAGE_LINE.match(line)
        alt, src = m.group(1).strip(), m.group(2)
        if not IMAGE_PATH.match(src):
            self.error(num, "picture '%s' must be ../../images/<name>.svg" % src)
        self.doc.images.append((num, src))
        out.append(("img", src, alt))

    def heading(self, num, line, top, out):
        m = _HEADING.match(line)
        if not m:
            self.error(num, "heading needs a space after the # signs")
            return
        level = len(m.group(1))
        if not top:
            self.error(num, "headings are not allowed inside callouts")
        if level not in (2, 3):
            self.error(num, "use ## for sections and ### for sub-sections only (found %s)" % m.group(1))
        out.append(("h", min(max(level, 2), 3), self.inline(num, m.group(2))))

    def callout(self, lines, i, out):
        start = lines[i][0]
        inner = []
        while i < len(lines) and lines[i][1].startswith(">"):
            num, line = lines[i]
            content = line[1:]
            if content.startswith(" "):
                content = content[1:]
            if content.startswith(">"):
                self.error(num, "nested callouts are not allowed")
            inner.append((num, content))
            i += 1
        m = _CALLOUT.match(inner[0][1].strip())
        if not m or m.group(1) not in CALLOUT_KINDS:
            self.error(start, "a quote block must start with one of: " + ", ".join("[!%s]" % k for k in CALLOUT_KINDS))
            kind = "NOTE"
            body = inner
        else:
            kind = m.group(1)
            body = inner[1:]
        blocks = self.blocks(body, top=False)
        if not blocks:
            self.error(start, "callout is empty")
        out.append(("callout", kind, blocks))
        return i

    def table(self, lines, i, out):
        start = lines[i][0]
        rows = []
        while i < len(lines) and lines[i][1].startswith("|"):
            rows.append(lines[i])
            i += 1
        cells = [(num, _split_row(line)) for num, line in rows]
        if len(cells) < 3:
            self.error(start, "a table needs a header row, a |---| separator row and at least one data row")
            return i
        sep_num, sep = cells[1]
        if not all(_TABLE_SEP.match(c) for c in sep):
            self.error(sep_num, "second table row must be the separator, like |---|---|")
            return i
        width = len(cells[0][1])
        for num, row in cells[1:]:
            if len(row) != width:
                self.error(num, "table row has %d cells; the header has %d" % (len(row), width))
        header = [self.inline(start, c) for c in cells[0][1]]
        body = [[self.inline(num, c) for c in row] for num, row in cells[2:]]
        out.append(("table", header, body))
        return i

    def list(self, lines, i, indent):
        items = []
        ordered = None
        start = 1
        while i < len(lines):
            num, line = lines[i]
            if not line.strip():
                # A blank line ends the list unless the list continues after it.
                j = i + 1
                while j < len(lines) and not lines[j][1].strip():
                    j += 1
                nxt = _LIST_ITEM.match(lines[j][1]) if j < len(lines) else None
                if nxt and len(nxt.group(1)) >= indent:
                    i = j
                    continue
                break
            m = _LIST_ITEM.match(line)
            if not m:
                if line.startswith(" ") and items:
                    # A wrapped continuation line: join it to the item.
                    self.warn(num, "list item is hard-wrapped; keep each item on one line")
                    text, children = items[-1]
                    items[-1] = (text + self.inline(num, " " + line.strip()), children)
                    i += 1
                    continue
                break
            depth = len(m.group(1))
            if depth < indent:
                break
            if depth > indent:
                if not items:
                    self.error(num, "nested list item has no parent item")
                    items.append(([], []))
                child, i = self.list(lines, i, depth)
                items[-1][1].append(child)
                continue
            marker = m.group(2)
            is_ordered = marker[0].isdigit()
            if marker in ("*", "+"):
                self.error(num, "use '-' for bullet lists")
            if marker[-1] == ")":
                self.error(num, "use '1.' for numbered lists, not '1)'")
            if ordered is None:
                ordered = is_ordered
                if is_ordered:
                    start = int(marker[:-1])
            elif ordered != is_ordered:
                break  # A different list type starts a new list.
            items.append((self.inline(num, m.group(3)), []))
            i += 1
        return ("list", bool(ordered), start, items), i

    def paragraph(self, lines, i, out):
        num, text = lines[i]
        i += 1
        while i < len(lines):
            nxt = lines[i][1]
            if not nxt.strip() or nxt[0] in "#>|`" or _LIST_ITEM.match(nxt):
                break
            self.warn(lines[i][0], "paragraph is hard-wrapped; keep each paragraph on one line")
            text += " " + nxt.strip()
            i += 1
        out.append(("p", self.inline(num, text)))
        return i

    # ---- inline ---------------------------------------------------------

    def inline(self, num, text):
        plain = _CODE_SPAN.sub("", text)
        if _IMAGE.search(plain):
            self.error(num, "a picture must be on a line of its own: ![legend](../../images/name.svg)")
        if _RAW_HTML.search(plain):
            self.error(num, "raw HTML is not allowed")
        if _ENTITY.search(plain):
            self.error(num, "HTML entities are not allowed; type the character itself")
        return self._inline(num, text)

    def _inline(self, num, text):
        nodes = []
        pos = 0
        for m in _INLINE.finditer(text):
            if m.start() > pos:
                nodes.append(("t", text[pos:m.start()]))
            if m.group("code") is not None:
                nodes.append(("code", m.group("code")))
            elif m.group("href") is not None:
                href = m.group("href")
                if m.start() and text[m.start() - 1] == "!":
                    nodes.append(("t", m.group(0)))  # A misplaced picture: inline() already reported it.
                else:
                    if not (INTERNAL_LINK.match(href) or EXTERNAL_LINK.match(href)):
                        self.error(num, "link '%s' must be ../<category>/<id>.md or start with https://" % href)
                    self.doc.links.append((num, href))
                    nodes.append(("a", href, self._inline(num, m.group("ltext"))))
            elif m.group("bold") is not None:
                nodes.append(("b", self._inline(num, m.group("bold"))))
            else:
                nodes.append(("i", self._inline(num, m.group("ital"))))
            pos = m.end()
        if pos < len(text):
            nodes.append(("t", text[pos:]))
        return nodes


def _split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


# ---- helpers ----------------------------------------------------------------

def plain(nodes):
    """Inline nodes as unformatted text."""
    out = []
    for n in nodes:
        if n[0] in ("t", "code"):
            out.append(n[1])
        elif n[0] == "a":
            out.append(plain(n[2]))
        else:
            out.append(plain(n[1]))
    return "".join(out)


def slug(text):
    s = unicodedata.normalize("NFKD", text.lower())
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    return re.sub(r"[\s_-]+", "-", s).strip("-") or "section"


_ASCII = {
    "‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
    "—": "-", "…": "...", "×": "x",
    "≥": ">=", "≤": "<=", "±": "+/-", "µ": "u", "μ": "u",
    "½": "1/2", "¼": "1/4", "¾": "3/4", "★": "*", "●": "*",
    "○": "o", "→": "->", "←": "<-", "↑": "^", "↓": "v",
    "✅": "[x]", " ": " ", "•": "*", "²": "2", "³": "3",
    "′": "'", "″": '"', "≈": "~", "≠": "!=", "÷": "/",
}


def to_ascii(text):
    """Best-effort ASCII for devices that cannot show UTF-8."""
    out = []
    for n, ch in enumerate(text):
        if ord(ch) < 128:
            out.append(ch)
        elif ch == "°":
            # 38°C -> 38 deg C
            before = " " if n and text[n - 1] not in " (" else ""
            after = " " if n + 1 < len(text) and text[n + 1].isalnum() else ""
            out.append(before + "deg" + after)
        elif ch in _ASCII:
            out.append(_ASCII[ch])
        else:
            base = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()
            out.append(base or "?")
    return "".join(out)


# ---- HTML -------------------------------------------------------------------

class HtmlRenderer:
    """Renders blocks as HTML that is also well-formed XHTML.

    resolve(href) returns the URL to use, or None to render the link text
    without a link (for example a target that is not in this edition).
    """

    def __init__(self, resolve, labels, heading_shift=0, id_prefix="", picture=None):
        self.resolve = resolve
        self.labels = labels
        self.picture = picture or (lambda src, alt: '<img src="%s" alt="%s"/>' % (escape(src), escape(alt)))
        self.shift = heading_shift
        self.prefix = id_prefix
        self.used_ids = set()

    def render(self, blocks):
        return "\n".join(self.block(b) for b in blocks)

    def block(self, b):
        kind = b[0]
        if kind == "h":
            level = min(b[1] + self.shift, 6)
            text = self.inline(b[2])
            return '<h%d id="%s">%s</h%d>' % (level, self.unique_id(plain(b[2])), text, level)
        if kind == "p":
            return "<p>%s</p>" % self.inline(b[1])
        if kind == "list":
            return self.list(b)
        if kind == "callout":
            k = b[1].lower()
            return '<div class="callout callout-%s"><p class="callout-label">%s</p>\n%s\n</div>' % (
                k, escape(self.labels.get(k, b[1])), self.render(b[2]))
        if kind == "table":
            head = "".join("<th>%s</th>" % self.inline(c) for c in b[1])
            rows = "\n".join(
                "<tr>%s</tr>" % "".join("<td>%s</td>" % self.inline(c) for c in row) for row in b[2])
            return '<div class="table"><table>\n<thead><tr>%s</tr></thead>\n<tbody>\n%s\n</tbody>\n</table></div>' % (head, rows)
        if kind == "code":
            return "<pre>%s</pre>" % escape(b[1], quote=False)
        if kind == "img":
            return '<figure class="diagram">%s<figcaption>%s</figcaption></figure>' % (
                self.picture(b[1], b[2]), escape(b[2], quote=False))
        raise ValueError(kind)

    def list(self, b):
        _, ordered, start, items = b
        tag = "ol" if ordered else "ul"
        attr = ' start="%d"' % start if ordered and start != 1 else ""
        parts = []
        for text, children in items:
            inner = self.inline(text) + "".join("\n" + self.list(c) for c in children)
            parts.append("<li>%s</li>" % inner)
        return "<%s%s>\n%s\n</%s>" % (tag, attr, "\n".join(parts), tag)

    def unique_id(self, text):
        base = (self.prefix + "--" if self.prefix else "") + slug(text)
        uid, n = base, 2
        while uid in self.used_ids:
            uid, n = "%s-%d" % (base, n), n + 1
        self.used_ids.add(uid)
        return uid

    def inline(self, nodes):
        out = []
        for n in nodes:
            k = n[0]
            if k == "t":
                out.append(escape(n[1], quote=False))
            elif k == "code":
                out.append("<code>%s</code>" % escape(n[1], quote=False))
            elif k == "b":
                out.append("<strong>%s</strong>" % self.inline(n[1]))
            elif k == "i":
                out.append("<em>%s</em>" % self.inline(n[1]))
            else:
                url = self.resolve(n[1])
                inner = self.inline(n[2])
                out.append('<a href="%s">%s</a>' % (escape(url), inner) if url else inner)
        return "".join(out)


# ---- plain text -------------------------------------------------------------

class TextRenderer:
    """Renders blocks as plain text for e-readers, MP3 players and serial screens.

    link_note(href, text) returns what to append after a link's text,
    for example " (see: Finding Water)". width=None leaves lines unwrapped
    so the device can wrap them to fit its own screen.
    """

    def __init__(self, link_note, labels, width=None, convert=None):
        self.link_note = link_note
        self.labels = labels
        self.width = width
        self.convert = convert or (lambda s: s)

    def render(self, blocks, width=None):
        width = self.width if width is None else width
        return "\n\n".join(self.block(b, width) for b in blocks)

    def wrap(self, text, width, first="", rest=""):
        text = self.convert(text)  # before wrapping: conversion can change the length
        if not width:
            return first + text
        return textwrap.fill(text, width, initial_indent=first, subsequent_indent=rest,
                             break_long_words=False, break_on_hyphens=False)

    def block(self, b, width):
        kind = b[0]
        if kind == "h":
            text = self.inline(b[2])
            return self.wrap("== %s ==" % text.upper() if b[1] == 2 else "-- %s --" % text, width)
        if kind == "p":
            return self.wrap(self.inline(b[1]), width)
        if kind == "list":
            return self.list(b, width, 0)
        if kind == "callout":
            inner = self.render(b[2], width - 3 if width else None)
            label = self.labels.get(b[1].lower(), b[1])
            lines = [label] + inner.split("\n")
            return "\n".join((">> " + ln).rstrip() for ln in lines)
        if kind == "table":
            header = [self.inline(c) for c in b[1]]
            out = []
            for row in b[2]:
                cells = [self.inline(c) for c in row]
                rest = "; ".join("%s: %s" % (h, c) for h, c in zip(header[1:], cells[1:]) if c)
                line = cells[0] + (": " + rest if rest else "")
                out.append(self.wrap(line, width, "- ", "  "))
            return "\n".join(out)
        if kind == "code":
            return self.convert(b[1])
        if kind == "img":
            return self.wrap("[%s: %s]" % (self.labels.get("picture", "Picture"), b[2]), width)
        raise ValueError(kind)

    def list(self, b, width, depth):
        _, ordered, start, items = b
        pad = "   " * depth
        out = []
        for n, (text, children) in enumerate(items):
            marker = "%d. " % (start + n) if ordered else "- "
            out.append(self.wrap(self.inline(text), width, pad + marker, pad + " " * len(marker)))
            for child in children:
                out.append(self.list(child, width, depth + 1))
        return "\n".join(out)

    def inline(self, nodes):
        out = []
        for n in nodes:
            if n[0] in ("t", "code"):
                out.append(n[1])
            elif n[0] == "a":
                text = self.inline(n[2])
                out.append(text + self.link_note(n[1], text))
            else:
                out.append(self.inline(n[1]))
        return "".join(out)
