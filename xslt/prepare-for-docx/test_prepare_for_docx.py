#!/usr/bin/env python3
"""
prepare_for_docx.py

Python equivalent of prepare-for-docx.xsl.
Transforms NLB/Statped EPUB-style XHTML into pre-processed XHTML for DOCX conversion.

Usage:
    python prepare_for_docx.py input.xhtml output.xhtml
"""

import re
import sys
from lxml import etree

XHTML = "http://www.w3.org/1999/xhtml"
EPUB  = "http://www.idpf.org/2007/ops"

H = f"{{{XHTML}}}"
E = f"{{{EPUB}}}"

IMG_ALT_MAP = {
    "photo": "foto", "illustration": "illustrasjon", "figure": "figur",
    "symbol": "symbol", "map": "kart", "drawing": "tegning",
    "comic": "tegneserie", "logo": "logo",
}


# ─── Low-level helpers ────────────────────────────────────────────────────────

def local(el):
    tag = el.tag
    return tag.split("}")[1] if isinstance(tag, str) and "{" in tag else (tag or "")

def types(el):
    return el.get(f"{E}type", "").split()

def classes(el):
    return el.get("class", "").split()

def all_text(el):
    return "".join(el.itertext())

def is_heading(el):
    return bool(re.match(r"^h[1-6]$", local(el)))

def heading_level(el):
    m = re.match(r"^h([1-6])$", local(el))
    return int(m.group(1)) if m else None

def ancestors(el):
    a = el.getparent()
    while a is not None:
        yield a
        a = a.getparent()

def has_ancestor(el, fn):
    return any(fn(a) for a in ancestors(el))

def has_ancestor_tag(el, *tags):
    s = set(tags)
    return has_ancestor(el, lambda a: local(a) in s)

def in_toc(el):
    return has_ancestor(el, lambda a: local(a) == "section" and "toc" in types(a))

def in_glossary(el):
    return has_ancestor(el, lambda a: local(a) == "aside" and "glossary" in classes(a))

def get_meta(root, name):
    for m in root.iter(f"{H}meta"):
        if m.get("name") == name:
            return m.get("content", "")
    return ""

def h(tag, attrib=None, text=None, tail=None):
    """Create an XHTML element."""
    el = etree.Element(f"{H}{tag}")
    if attrib:
        for k, v in attrib.items():
            el.set(k, v)
    if text is not None:
        el.text = text
    if tail is not None:
        el.tail = tail
    return el

def empty_p():
    return h("p")

def no_span(text):
    s = h("span", {"xml:lang": "no", "lang": "no"}, text)
    return s

def append_text(el, text):
    """Append text to el.text or last child's tail."""
    if len(el) == 0:
        el.text = (el.text or "") + text
    else:
        el[-1].tail = (el[-1].tail or "") + text

def copy_el(el):
    new = etree.Element(el.tag)
    new.attrib.update(el.attrib)
    new.text = el.text
    new.tail = el.tail
    return new


# ─── Pagebreak helpers ────────────────────────────────────────────────────────

def pb_title(el):
    return el.get("title") or (el.text or "")

def pb_display(title):
    """Extract the display page number from a title (after last hyphen if present)."""
    return title.split("-")[-1] if "-" in title else title

def is_roman(s):
    return bool(re.match(r"^[IVXLCDMivxlcdm]+$", s)) if s else False

def all_pagebreaks(root):
    return [el for el in root.iter(f"{H}span", f"{H}div") if "pagebreak" in types(el)]

def move_page_top_level(el):
    for a in ancestors(el):
        ln = local(a)
        if re.match(r"h[1-6]|^(table|th|td|p|li)$", ln):
            return False
        if ln == "section" and "toc" in types(a):
            if any("list-type-none" in classes(ol) for ol in a.iter(f"{H}ol")):
                return False
    return True

def move_page_before(el):
    ln = local(el)
    if re.match(r"h[1-6]|^(table|th|td)$", ln):
        return True
    for a in ancestors(el):
        if local(a) == "section" and "toc" in types(a):
            if any("list-type-none" in classes(ol) for ol in a.iter(f"{H}ol")):
                return True
    return False


# ─── Transformer ─────────────────────────────────────────────────────────────

class Transformer:
    def __init__(self, root):
        self.root = root
        pbs = all_pagebreaks(root)
        self.max_page = pb_display(pb_title(pbs[-1])) if pbs else ""
        sf = get_meta(root, "startPagenumberingFrom")
        self.start_from = int(sf) if sf.isdigit() else 0

    # ── Pagebreak creation ────────────────────────────────────────────────────

    def make_pb_div(self, pb_el):
        """Create a <div epub:type="pagebreak"> element, or None if filtered."""
        title = pb_title(pb_el)
        page_num = pb_display(title)
        roman = is_roman(title)
        is_int = re.match(r"^\d+$", page_num) is not None
        page_int = int(page_num) if is_int else None

        if not roman and not (is_int and page_int >= self.start_from):
            return None

        div = h("div")
        div.set(f"{E}type", "pagebreak")
        for k, v in pb_el.attrib.items():
            if k != f"{E}type":
                div.set(k, v)
        div.set("title", page_num)
        display = title if "-" in title else page_num
        div.text = f"--- {display} til {self.max_page}"
        return div

    def emit_pb(self, pb_el, skip_leading_p=False):
        """Return list of elements (optional empty p + pagebreak div)."""
        result = []
        # Avoid empty p if inside li/figcaption/caption/figure.image ancestor-p chain
        avoid_p = skip_leading_p or has_ancestor(
            pb_el,
            lambda a: local(a) == "p" and has_ancestor(
                a, lambda b: local(b) in ("li", "figcaption", "caption")
            )
        )
        if not avoid_p:
            result.append(empty_p())
        div = self.make_pb_div(pb_el)
        if div is not None:
            result.append(div)
        return result

    # ── Main dispatch ─────────────────────────────────────────────────────────

    def transform(self, el):
        """Transform one element; returns a list of new elements."""
        if not isinstance(el.tag, str):
            return []  # drop comments / PIs

        ln = local(el)
        cl = classes(el)
        tp = types(el)

        # ── span.answer / span.answer_1 ──────────────────────────────────────
        if ln == "span" and "answer" in cl:
            return [h("span", text="....", tail=el.tail)]
        if ln == "span" and "answer_1" in cl:
            return [h("span", text="_", tail=el.tail)]

        # ── div.list-enumeration-1 ────────────────────────────────────────────
        if ln == "div" and "list-enumeration-1" in cl:
            p = h("p")
            spans = [s for s in el.iter(f"{H}span")]
            for i, s in enumerate(spans):
                for tc in self.transform(s):
                    p.append(tc)
                if i < len(spans) - 1:
                    last_text = all_text(s)
                    sep = ", " if not last_text.endswith(".") else " "
                    append_text(p, sep)
            p.tail = el.tail
            return [p]

        # ── span.lic ──────────────────────────────────────────────────────────
        if ln == "span" and "lic" in cl:
            result = self.transform_children(el)
            nxt = el.getnext()
            if nxt is not None and local(nxt) == "span":
                append_text_to_last(result, " ")
            carry_tail(result, el.tail)
            return result

        # ── Empty th/td ───────────────────────────────────────────────────────
        if ln == "th" and all_text(el).strip() == "":
            new = copy_el(el); new.text = "--"; return [new]

        if ln == "td" and all_text(el).strip() == "":
            in_task = has_ancestor(el, lambda a: local(a) == "section"
                                   and bool(re.match(r"^(oppgaver1|task)$", " ".join(classes(a)))))
            in_thead = has_ancestor_tag(el, "thead")
            filler = "...." if (in_task and not in_thead) else "--"
            new = copy_el(el); new.text = filler; return [new]

        # ── thead td.empty ────────────────────────────────────────────────────
        if ln == "td" and has_ancestor_tag(el, "thead") and all_text(el).strip() == "":
            new = copy_el(el); new.text = "--"; return [new]

        # ── li/ol or li/ul without preceding content ──────────────────────────
        if ln in ("ol", "ul"):
            parent = el.getparent()
            if parent is not None and local(parent) == "li":
                has_prev = bool(parent.text and parent.text.strip()) or any(
                    isinstance(s.tag, str) for s in el.itersiblings(preceding=True)
                )
                if not has_prev:
                    dummy = h("span", {"class": "dummyToIncludeNumbering"},
                              text="STATPED_DUMMYTEXT_LI_OL")
                    return [dummy] + self.identity(el)

        # ── h1-h6 not in toc/glossary ─────────────────────────────────────────
        if is_heading(el) and not in_toc(el) and not in_glossary(el):
            return self.transform_heading(el)

        # ── aside.glossary headings ───────────────────────────────────────────
        if is_heading(el) and in_glossary(el):
            p = h("p")
            p.text = "_"
            for tc in self.transform_children(el):
                p.append(tc)
            append_text(p, "_")
            p.tail = el.tail
            return [p]

        # ── colophon headings → drop ──────────────────────────────────────────
        if is_heading(el):
            parent = el.getparent()
            if parent is not None and local(parent) == "section" and "colophon" in types(parent):
                return []

        # ── Pagebreak: span inside p → drop (will be re-emitted after p) ─────
        if ln == "span" and "pagebreak" in tp and has_ancestor_tag(el, "p"):
            return []

        # ── Pagebreak: block element that contains pagebreaks to promote ───────
        if (ln not in ("p",) and not is_heading(el) and ln != "table"
                and self._has_pbs(el) and move_page_top_level(el)
                and not move_page_before(el)):
            pass  # fall through to identity; promotion handled in p/special cases

        # ── Elements where pagebreaks move BEFORE (headings/tables handled sep.)─
        if (ln not in ("p",) and not is_heading(el) and ln != "table"
                and "pagebreak" not in tp
                and self._has_pbs(el) and move_page_before(el)
                and move_page_top_level(el)):
            result = []
            for pb in el.iter(f"{H}span", f"{H}div"):
                if "pagebreak" in types(pb):
                    result += self.emit_pb(pb)
            result += self.identity(el)
            return result

        # ── p → identity + emit pagebreaks after ──────────────────────────────
        if ln == "p":
            parent = el.getparent()
            # figcaption/p, figure.image/aside/p, caption/p with pagebreaks
            special_parent = (
                has_ancestor_tag(el, "figcaption", "caption")
                or (parent is not None and local(parent) == "aside"
                    and has_ancestor(el, lambda a: local(a) == "figure"
                                    and "image" in classes(a)))
            )
            if special_parent:
                return self.transform_special_p(el)
            # Normal p
            result = self.identity(el)
            if move_page_top_level(el):
                for pb in el.iter(f"{H}span"):
                    if "pagebreak" in types(pb):
                        result += self.emit_pb(pb, skip_leading_p=False)
            return result

        # ── Standalone pagebreak div/span ─────────────────────────────────────
        if ln in ("div", "span") and "pagebreak" in tp:
            parent = el.getparent()
            if parent is not None and not move_page_before(parent) and move_page_top_level(parent):
                if not has_ancestor_tag(el, "li"):
                    if ln == "div" or (ln == "span" and not has_ancestor_tag(el, "p")):
                        return self.emit_pb(el)

        # ── aside.sidebar, div.linegroup ──────────────────────────────────────
        if (ln == "aside" and "sidebar" in cl) or (ln == "div" and "linegroup" in cl):
            return [empty_p()] + self.identity(el)

        # ── div.ramme / div.generisk-ramme ────────────────────────────────────
        if ln == "div" and ("ramme" in cl or "generisk-ramme" in cl):
            return [empty_p()] + self.identity(el) + [empty_p()]

        # ── div.ramdoc / aside.ramdoc ─────────────────────────────────────────
        if ln in ("div", "aside") and "ramdoc" in cl:
            new = copy_el(el)
            label = h("p"); label.append(no_span("Ramme:"))
            new.append(label)
            for tc in self.transform_children(el):
                new.append(tc)
            new.tail = el.tail
            return [empty_p(), new]

        # ── img ───────────────────────────────────────────────────────────────
        if ln == "img":
            alt = IMG_ALT_MAP.get(el.get("alt", ""), el.get("alt", ""))
            return [h("span", text=f"[{alt}]", tail=el.tail)]

        # ── figure.image-series ───────────────────────────────────────────────
        if ln == "figure" and "image-series" in cl:
            return self.transform_children(el)

        # ── figure.image ──────────────────────────────────────────────────────
        if ln == "figure" and "image" in cl:
            return self.transform_figure_image(el)

        # ── figcaption inside image-series ────────────────────────────────────
        if ln == "figcaption":
            parent = el.getparent()
            if parent is not None and "image-series" in classes(parent):
                p = h("p", text="Bildeserie: ")
                for tc in self.transform_children(el):
                    p.append(tc)
                p.tail = el.tail
                return [empty_p(), p]
            # Normal figcaption
            p = h("p", attrib={"lang": "no", "xml:lang": "no"}, text="Bildetekst: ")
            for tc in self.transform_children(el):
                p.append(tc)
            p.tail = el.tail
            return [p]

        # ── TOC ol ────────────────────────────────────────────────────────────
        if ln == "ol":
            parent = el.getparent()
            if parent is not None and local(parent) == "section" and "toc" in types(parent):
                return self.transform_toc_ol(el)
            # Deep nested toc ol → drop
            if in_toc(el):
                depth = sum(1 for a in ancestors(el) if local(a) == "li")
                if depth >= 2:
                    return []

        # ── TOC li ────────────────────────────────────────────────────────────
        if ln == "li" and in_toc(el):
            return self.transform_toc_li(el)

        # ── li with li-level pagebreaks ───────────────────────────────────────
        if ln == "li" and not has_ancestor_tag(el, "section"):
            if (not move_page_before(el) and self._has_pbs(el)
                    and not self._has_pbs_in_nested_li(el)):
                result = self.identity(el)
                for pb in el.iter(f"{H}span"):
                    if "pagebreak" in types(pb):
                        result[-1].append(self.make_pb_div(pb) or h("span"))

                return result

        # ── em / strong ───────────────────────────────────────────────────────
        if ln in ("em", "strong"):
            result = [h("span", text="_")]
            result += self.transform_children(el)
            last = h("span", text="_", tail=el.tail)
            result.append(last)
            return result

        # ── table ─────────────────────────────────────────────────────────────
        if ln == "table":
            return self.transform_table(el)

        # ── top-level ol/ul ───────────────────────────────────────────────────
        if ln in ("ol", "ul"):
            parent = el.getparent()
            if parent is not None and local(parent) not in ("ol", "ul"):
                # ul.list-unstyled (priority 2)
                if ln == "ul" and "list-unstyled" in cl:
                    return self.transform_list_unstyled(el)
                result = self.identity(el)
                result.append(empty_p())
                return result

        # ── dl ────────────────────────────────────────────────────────────────
        if ln == "dl":
            return self.transform_dl(el)

        # ── p before dl ───────────────────────────────────────────────────────
        if ln == "p":
            prev = el.getprevious()
            nxt = el.getnext()
            if (prev is None or local(prev) != "p") and nxt is not None and local(nxt) == "dl":
                new = copy_el(el)
                dummy = h("span", text="STATPED_DUMMYTEXT_P_BEFORE_DL")
                new.text = None
                new.insert(0, dummy)
                for tc in self.transform_children(el):
                    new.append(tc)
                return [new]

        # ── dt ────────────────────────────────────────────────────────────────
        if ln == "dt":
            span = h("span")
            span.attrib.update(el.attrib)
            children = self.transform_children(el, clean_text=True)
            append_children(span, children)
            span.tail = el.tail
            return [span]

        # ── dd ────────────────────────────────────────────────────────────────
        if ln == "dd":
            span = h("span")
            span.attrib.update(el.attrib)
            children = self.transform_children(el, clean_text=True)
            append_children(span, children)
            span.tail = el.tail
            return [span]

        # ── sub ───────────────────────────────────────────────────────────────
        if ln == "sub":
            txt = all_text(el)
            content = f"\\({txt})" if len(txt) > 1 else f"\\{txt}"
            return [h("span", text=content, tail=el.tail)]

        # ── sup ───────────────────────────────────────────────────────────────
        if ln == "sup":
            txt = all_text(el)
            content = f"^({txt})" if len(txt) > 1 else f"^{txt}"
            return [h("span", text=content, tail=el.tail)]

        # ── head ──────────────────────────────────────────────────────────────
        if ln == "head":
            new = copy_el(el)
            for tc in self.transform_children(el):
                new.append(tc)
            style = etree.SubElement(new, f"{H}style")
            style.text = "div.pagebreak {page-break-after:avoid;}"
            new.tail = el.tail
            return [new]

        # ── Default: identity ─────────────────────────────────────────────────
        return self.identity(el)

    # ── Template helpers ──────────────────────────────────────────────────────

    def transform_heading(self, el):
        result = []
        ln = local(el)
        lvl = heading_level(el)
        prev = el.getprevious()
        parent = el.getparent()

        add_p = True
        # Don't add if preceding sibling (last) is page-normal
        if prev is not None:
            sibs = list(el.itersiblings(preceding=True))
            if sibs and local(sibs[-1]) in ("div", "span") and "page-normal" in classes(sibs[-1]):
                add_p = False
        # Don't add if immediately preceded by another heading
        if prev is not None and is_heading(prev):
            add_p = False
        # Don't add if first child and parent's prev sibling is heading
        if parent is not None:
            kids = [c for c in parent if isinstance(c.tag, str)]
            if kids and kids[0] is el:
                par_prev = parent.getprevious()
                if par_prev is not None and is_heading(par_prev):
                    add_p = False
        # Don't add if heading contains pagebreak span
        if any("pagebreak" in types(s) for s in el.iter(f"{H}span")):
            add_p = False

        if add_p:
            result.append(empty_p())

        new_h = h(ln)
        new_h.attrib.update(el.attrib)
        append_text(new_h, f"xxx{lvl} ")
        for tc in self.transform_children(el):
            new_h.append(tc)
        new_h.tail = el.tail
        result.append(new_h)
        return result

    def transform_special_p(self, el):
        """figcaption/p, figure.image/aside/p, caption/p."""
        result = self.identity(el)
        siblings = list(el.itersiblings())
        nxt = el.getnext()
        if el != el.getparent()[-1] if el.getparent() is not None else False:
            if nxt is not None and local(nxt) not in ("ol", "ul", "table"):
                result.append(h("br"))
        for pb in el.iter(f"{H}span"):
            if "pagebreak" in types(pb):
                result += self.emit_pb(pb)
        return result

    def transform_figure_image(self, el):
        result = [empty_p()]
        img_el = el.find(f"{H}img")
        alt = IMG_ALT_MAP.get(img_el.get("alt", ""), img_el.get("alt", "")) if img_el is not None else ""
        bilde = h("p", {"lang": "no", "xml:lang": "no"}, text=f"Bilde: {alt}")
        result.append(bilde)

        aside = el.find(f"{H}aside")
        if aside is not None:
            aside_text = all_text(aside).strip()
            if aside_text not in ("¤", "*"):
                p = h("p", {"lang": "no", "xml:lang": "no"}, text="Forklaring: ")
                for tc in self.transform_children(aside):
                    p.append(tc)
                result.append(p)

        figcap = el.find(f"{H}figcaption")
        if figcap is not None:
            p = h("p", {"lang": "no", "xml:lang": "no"}, text="Bildetekst: ")
            for tc in self.transform_children(figcap):
                p.append(tc)
            result.append(p)

        result.append(empty_p())
        return result

    def transform_toc_ol(self, el):
        result = []
        for pb in el.iter(f"{H}span", f"{H}div"):
            if "pagebreak" in types(pb):
                result += self.emit_pb(pb)

        new_ol = copy_el(el)
        new_ol.attrib.update(el.attrib)
        # Add Merknad as first item
        merknad_li = h("li")
        s = h("span", {"xml:lang": "no", "lang": "no"}, text="xxx1 ")
        merknad_li.append(s)
        a = h("a", {"href": "#statped_merknad"})
        lic = h("span", {"class": "lic"})
        lic.append(h("span", {"xml:lang": "no", "lang": "no"}, text="Merknad"))
        a.append(lic)
        merknad_li.append(a)
        new_ol.append(merknad_li)

        for child in el:
            if not isinstance(child.tag, str):
                continue
            for tc in self.transform(child):
                new_ol.append(tc)
        result.append(new_ol)
        return result

    def transform_toc_li(self, el):
        # Drop Kolofon items
        if all_text(el).strip().startswith("Kolofon"):
            return []
        depth = sum(1 for a in ancestors(el) if local(a) == "li") + 1
        new_li = copy_el(el)
        append_text(new_li, f"xxx{depth} ")
        for child in el:
            if not isinstance(child.tag, str):
                continue
            if local(child) in ("ol", "ul"):
                anc_li = sum(1 for a in ancestors(child) if local(a) == "li")
                if anc_li >= 2:
                    continue
            for tc in self.transform(child):
                new_li.append(tc)
        new_li.tail = el.tail
        return [new_li]

    def transform_table(self, el):
        result = []
        has_pbs = self._has_pbs(el)
        if not has_pbs:
            result.append(empty_p())
        caption = el.find(f"{H}caption")
        cap_p = h("p", text="Tabell: ")
        if caption is not None:
            for tc in self.transform_children(caption):
                cap_p.append(tc)
        result.append(cap_p)

        new_table = copy_el(el)
        for child in el:
            if not isinstance(child.tag, str):
                continue
            if local(child) == "caption":
                continue
            for tc in self.transform(child):
                new_table.append(tc)
        new_table.tail = el.tail
        result.append(new_table)
        return result

    def transform_list_unstyled(self, el):
        result = []
        in_table = has_ancestor_tag(el, "table")
        for li in el:
            if local(li) != "li":
                continue
            p = h("p")
            if not in_table:
                p.append(h("span", text="STATPED_DUMMYTEXT_LIST_UNSTYLED"))
            for tc in self.transform_children(li):
                p.append(tc)
            result.append(p)
        if not has_ancestor_tag(el, "table", "ul", "ol"):
            result.append(empty_p())
        return result

    def transform_dl(self, el):
        result = []
        groups = []
        current = []
        for child in el:
            if not isinstance(child.tag, str):
                continue
            if local(child) == "dt":
                if current:
                    groups.append(current)
                current = [child]
            else:
                current.append(child)
        if current:
            groups.append(current)

        for group in groups:
            p = h("p", text="STATPED_DUMMYTEXT_DL")
            for item in group:
                for tc in self.transform(item):
                    p.append(tc)
            result.append(p)
        if result:
            result[-1].tail = el.tail
        return result

    def transform_children(self, el, clean_text=False):
        result = []
        for child in el:
            if not isinstance(child.tag, str):
                continue
            if clean_text and local(child) in ("dt", "dd"):
                for tc in self.transform_dt_dd_text(child):
                    result.append(tc)
            else:
                result += self.transform(child)
        return result

    def transform_dt_dd_text(self, el):
        """dt/dd: strip sound annotations, rename to span."""
        span = h("span")
        span.attrib.update(el.attrib)
        # Process text nodes with cleaning
        full_text = all_text(el)
        cleaned = re.sub(r"\s/\S[^/]*?/", "", full_text)
        cleaned = re.sub(r"\s\[[^\]]*?\]", "", cleaned)
        cleaned = re.sub(r":\s*$", ": ", cleaned)
        cleaned = re.sub(r"\[[^\]]*?\]", "", cleaned)
        span.text = cleaned
        span.tail = el.tail
        return [span]

    def identity(self, el):
        new = copy_el(el)
        for child in el:
            if not isinstance(child.tag, str):
                continue
            for tc in self.transform(child):
                new.append(tc)
        new.tail = el.tail
        return [new]

    def _has_pbs(self, el):
        return any("pagebreak" in types(pb) for pb in el.iter(f"{H}span", f"{H}div"))

    def _has_pbs_in_nested_li(self, el):
        for li in el.iter(f"{H}li"):
            if li is el:
                continue
            if self._has_pbs(li):
                return True
        return False

    # ── Body ─────────────────────────────────────────────────────────────────

    def transform_body(self, el):
        root = self.root
        # Metadata
        title_el = root.find(f"{H}head/{H}title")
        title = title_el.text if title_el is not None else ""

        def get_reordered_meta(name):
            vals = []
            for m in root.iter(f"{H}meta"):
                if m.get("name") == name:
                    v = m.get("content", "")
                    vals.append(re.sub(r"^(.*),\s*(.*)$", r"\2 \1", v))
            return vals

        languages = get_reordered_meta("dc:language")
        authors   = get_reordered_meta("dc:creator")
        pub_orig  = get_meta(root, "dc:publisher.original")
        issued_orig  = get_meta(root, "dc:issued.original")
        edition_orig = get_meta(root, "schema:bookEdition.original")
        edition_orig = re.sub(r"^(\d+\.?)$", r"\1.utg.", edition_orig)
        edition_orig = re.sub(r"\.+", ".", edition_orig)
        isbn = get_meta(root, "schema:isbn")
        doc_lang = get_meta(root, "dc:language")

        pbs = all_pagebreaks(root)
        first_page = pb_display(pb_title(pbs[0])) if pbs else ""
        last_page  = pb_display(pb_title(pbs[-1])) if pbs else ""

        new_body = copy_el(el)

        # ── Metadata paragraph ──────────────────────────────────────────────
        meta_p = h("p", {"xml:lang": "no", "lang": "no"})
        meta_p.text = title
        if len(languages) > 1:
            meta_p.text += " - " + "/".join(languages)
        elif len(languages) == 1:
            meta_p.text += f" - {languages[0]}"

        br1 = h("br")
        page_range = f"(s. {first_page}-{last_page})" if first_page else ""
        if len(authors) > 1:
            author_str = " og ".join(authors)
        elif len(authors) == 1:
            author_str = authors[0]
        else:
            author_str = ""
        br1.tail = page_range + (f" - {author_str}" if author_str else "")
        meta_p.append(br1)

        br2 = h("br")
        pub_parts = pub_orig
        if issued_orig:   pub_parts += f" {issued_orig}"
        if edition_orig:  pub_parts += f" - {edition_orig}"
        if isbn:          pub_parts += f" - ISBN: {isbn}"
        br2.tail = pub_parts
        meta_p.append(br2)
        new_body.append(meta_p)

        # ── TOC ─────────────────────────────────────────────────────────────
        for sec in el:
            if local(sec) == "section" and "toc" in types(sec):
                for tc in self.transform(sec):
                    new_body.append(tc)

        # ── Merknad block ────────────────────────────────────────────────────
        mdiv = h("div")
        mdiv.append(empty_p())
        h1 = h("h1", {"id": "statped_merknad"})
        h1.append(no_span("xxx1 Generell merknad for Statpeds leselistbøker:"))
        mdiv.append(h1)
        for note in [
            "Filen har en klikkbar innholdsfortegnelse.",
            "xxx innleder overskrifter. Overskriftsnivået vises med tall: xxx1, xxx2 osv.",
            "--- innleder sidetallet.",
            "Uthevingstegnet er slik: _.",
            "Eksempel: _Denne setningen er uthevet._",
            "Ordforklaringer, gloser eller stikkord finner du etter hovedteksten og eventuelle bilder.",
            "Eventuelle stikkordsregistre og kilder er utelatt. Kolofonen og baksideteksten finner du til slutt i denne filen.",
        ]:
            p = h("p"); p.append(no_span(note)); mdiv.append(p)
        new_body.append(mdiv)

        # ── Main content ─────────────────────────────────────────────────────
        excluded = {"toc", "backmatter", "index", "colophon", "titlepage", "cover"}
        for child in el:
            if not isinstance(child.tag, str):
                continue
            if local(child) == "section" and bool(set(types(child)) & excluded):
                continue
            for tc in self.transform(child):
                new_body.append(tc)
        new_body.append(empty_p())

        # ── Ettertekst ───────────────────────────────────────────────────────
        new_body.append(h("p", text="Ettertekst:"))
        for sec in el:
            if local(sec) == "section":
                st = set(types(sec))
                if "backmatter" in st and "index" not in st and "colophon" not in st:
                    for tc in self.transform(sec):
                        new_body.append(tc)
        new_body.append(empty_p())

        # ── Kolofon ──────────────────────────────────────────────────────────
        new_body.append(h("p", text="Kolofon:"))
        for sec in el:
            if local(sec) == "section" and "colophon" in types(sec):
                for tc in self.transform(sec):
                    new_body.append(tc)
        new_body.append(empty_p())

        # ── Baksidetekst ─────────────────────────────────────────────────────
        new_body.append(h("p", text="Baksidetekst:"))
        for sec in el:
            if local(sec) == "section" and "cover" in types(sec):
                for sub in sec:
                    if local(sub) == "section" and "rearcover" in classes(sub):
                        for tc in self.transform(sub):
                            new_body.append(tc)
        new_body.append(empty_p())

        # ── Copyright ────────────────────────────────────────────────────────
        if doc_lang == "nn":
            cr_s = h("span", {"xml:lang": "nn", "lang": "nn"}, text="Opphavsrett Statped:")
            cr_br = h("br")
            cr_br.tail = (
                "Denne boka er lagd til rette for elevar med synssvekking. "
                "Ifølgje lov om opphavsrett kan ho ikkje brukast av andre. "
                "Teksten er tilpassa for lesing med skjermlesar og leselist. "
                "Kopiering er berre tillate til eige bruk. "
                "Brot på desse avtalevilkåra, slik som ulovleg kopiering eller medverknad til ulovleg "
                "kopiering, kan medføre ansvar etter åndsverklova."
            )
            cr_s.append(cr_br)
        else:
            cr_s = h("span", {"xml:lang": "no", "lang": "no"}, text="Opphavsrett Statped:")
            cr_br = h("br")
            cr_br.tail = (
                "Denne boka er tilrettelagt for elever med synssvekkelse. "
                "Ifølge lov om opphavsrett kan den ikke brukes av andre. "
                "Teksten er tilpasset for lesing med skjermleser og leselist. "
                "Kopiering er kun tillatt til eget bruk. "
                "Brudd på disse avtalevilkårene, som ulovlig kopiering eller medvirkning til ulovlig kopiering, "
                "kan medføre ansvar etter åndsverkloven."
            )
            cr_s.append(cr_br)

        cr_p = h("p")
        cr_p.append(cr_s)
        new_body.append(cr_p)
        new_body.tail = el.tail
        return [new_body]

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self):
        root = self.root
        new_html = copy_el(root)
        for child in root:
            if not isinstance(child.tag, str):
                continue
            if local(child) == "body":
                for tc in self.transform_body(child):
                    new_html.append(tc)
            else:
                for tc in self.transform(child):
                    new_html.append(tc)
        return new_html


# ─── Utility functions ────────────────────────────────────────────────────────

def append_children(parent, children):
    for c in children:
        if isinstance(c, etree._Element):
            parent.append(c)

def append_text_to_last(result, text):
    if result:
        last = result[-1]
        if isinstance(last, etree._Element):
            last.tail = (last.tail or "") + text

def carry_tail(result, tail):
    if tail and result:
        last = result[-1]
        if isinstance(last, etree._Element):
            last.tail = (last.tail or "") + tail


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} input.xhtml output.xhtml")
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    parser = etree.XMLParser(remove_comments=True, resolve_entities=False)
    tree = etree.parse(input_path, parser)
    root = tree.getroot()

    transformer = Transformer(root)
    new_root = transformer.run()

    new_tree = etree.ElementTree(new_root)
    new_tree.write(
        output_path,
        xml_declaration=True,
        encoding="UTF-8",
        method="xml",
        pretty_print=True,
    )
    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
