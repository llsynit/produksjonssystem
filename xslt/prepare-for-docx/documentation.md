# prepare-for-docx.xsl — Documentation

This is an **XSLT 2.0 stylesheet** that transforms NLB/Statped EPUB-style XHTML content into a pre-processed XHTML format optimised for conversion to DOCX (Word format). It is specifically tailored for **braille reading list books** for visually impaired users.

---

## Overall Strategy

It uses an **identity transform** as its base (copies everything by default), then overrides specific elements with custom rules. Everything not explicitly matched is copied as-is.

---

## What It Transforms

### 📄 Document Header (Metadata block)

At the `<body>` level, it **injects a rich metadata paragraph** at the very top of the document, pulling from `<meta>` tags in `<head>`:

- Book title + language(s)
- Page range (first page – last page)
- Author(s), publisher, publication year, edition, ISBN

It also **restructures section order**: TOC first, then main content, then backmatter, then colophon, then rear cover text — each with a labeled separator paragraph (`Ettertekst:`, `Kolofon:`, `Baksidetekst:`).

---

### 📑 Headings (`h1`–`h6`)

- Prefixes every heading with `xxx` + the level number — e.g., a `<h2>` becomes `xxx2 Heading text`. This is a **braille/screen-reader convention** for marking heading levels in plain text.
- Inserts an **empty `<p>`** before most headings (spacing for DOCX rendering), with smart exceptions (e.g., no extra space if the preceding element is already a page number or another heading).

---

### 📌 Page Breaks

This is the most complex part. It handles three scenarios:

| Location | Behaviour |
|---|---|
| Inside `<p>` | The `<span epub:type="pagebreak">` is **removed** from inside `<p>` and re-emitted *after* the `<p>` as a top-level `<div>` |
| Inside headings/tables | Pagebreaks are **promoted before** the heading/table |
| Elsewhere | Kept in place and reformatted |

The page break is rendered as: `--- 42 til 187` (i.e., `--- [current page] til [last page]`), in Norwegian. It handles:

- Roman numeral page numbers (treated separately)
- Page titles with hyphens like `ch2-122` (only digits after the hyphen are used as the display page number)
- A `startPagenumberingFrom` metadata value to suppress early unnumbered pages

---

### 🖼️ Images (`<img>`, `<figure>`)

- `<img>` tags are replaced with `[foto]`, `[illustrasjon]`, `[figur]`, etc. — translating the `alt` attribute from English to Norwegian.
- `<figure class="image">` is replaced with:
  - `Bilde: [type]`
  - `Forklaring: [alt text]` (if present and not a placeholder)
  - `Bildetekst: [caption]`
- `<figure class="image-series">` prefixed with `Bildeserie:`.

---

### 🔵 Emphasis / Styling

- `<em>` and `<strong>` → wrapped in underscores: `_bold text_` (braille-friendly inline emphasis marker).
- `<sub>` → `\x` or `\(x)` for multi-char subscripts.
- `<sup>` → `^x` or `^(x)` for multi-char superscripts.

---

### 📋 Tables

- Prefixes every table with a `Tabell: [caption]` paragraph.
- Empty `<th>` and `<td>` cells get filled with `--` (except in task sections, where they get `....` instead).

---

### 📝 Lists

- Top-level `<ol>` and `<ul>` get an empty `<p>` appended after them.
- `<ul class="list-unstyled">` items are flattened: each `<li>` becomes a `<p>` prefixed with a dummy text marker (`STATPED_DUMMYTEXT_LIST_UNSTYLED`) used for Word style mapping later.
- Nested lists that start a `<li>` without preceding content get a `STATPED_DUMMYTEXT_LI_OL` span prepended (so Word knows to apply numbering).

---

### 📖 Table of Contents

- Adds a "Merknad" (note/remark) entry as the first item, linking to the injected `#statped_merknad` section.
- Each TOC `<li>` is prefixed with `xxx[depth]` (e.g., `xxx1`, `xxx2`) matching the heading level convention.
- Deeply nested TOC levels (3+) are removed.
- TOC items starting with "Kolofon" are suppressed.

---

### 🗂️ Special Sections / Blocks

| Element | Behaviour |
|---|---|
| `<aside class="sidebar">`, `<div class="linegroup">` | Empty `<p>` prepended |
| `<div class="ramme">`, `<div class="generisk-ramme">` | Empty `<p>` before and after |
| `<div class="ramdoc">`, `<aside class="ramdoc">` | Gets a "Ramme:" label added |
| `<aside class="glossary"> h1–h6` | Heading replaced with `_term_` (italic-like) |
| `<span class="answer">` | Replaced with `....` |
| `<span class="answer_1">` | Replaced with `_` |
| `<div class="list-enumeration-1">` | Flattened to comma-separated `<p>` |

---

### 📢 Legal Notice

At the end of `<body>`, it injects a **Statped copyright notice** in Norwegian Bokmål or Nynorsk depending on the `dc:language` metadata — stating that the book is adapted for visually impaired users and cannot be redistributed.

---

### 📘 Merknad (General Note) Block

Injected right after the TOC, a fixed-text block titled "Generell merknad for Statpeds leselistbøker" explains the document's formatting conventions to the reader:

- `xxx` = heading indicator
- `---` = page number indicator
- `_` = emphasis marker

---

### 🧹 Dictionary Lists (`<dl>`, `<dt>`, `<dd>`)

- `<dl>` is reformatted: each `<dt>` + its `<dd>` entries become a single `<p>` starting with `STATPED_DUMMYTEXT_DL`.
- `<dt>` and `<dd>` are renamed to `<span>`.
- Sound annotation text inside `/…/` or `[…]` in `<dt>`/`<dd>` text is **stripped out**.

---

### 🗑️ Index (`section[epub:type="index"]`)

The index is **dropped entirely** — there is no template that processes it. It is excluded in two places within the `<body>` template:

1. **Main content pass** — excluded alongside `toc`, `backmatter`, `colophon`, `titlepage`, and `cover`:
   ```xml
   <xsl:apply-templates
      select="* except section[f:types(.) = ('toc', 'backmatter', 'index', 'colophon', 'titlepage', 'cover')]" />
   ```

2. **Backmatter pass** — even if a section has both `backmatter` and `index` types, it is still excluded:
   ```xml
   <xsl:apply-templates
      select="section[f:types(.) = 'backmatter' and not(f:types(.) = 'index' or f:types(.) = 'colophon')]" />
   ```

This is intentional and is documented in the fixed "Merknad" text block the stylesheet injects:

> *«Eventuelle stikkordsregistre og kilder er utelatt.»*
> ("Any subject indexes and sources have been omitted.")

---

## Summary

This stylesheet converts a rich, semantic EPUB/XHTML document into a **flattened, annotated XHTML** intermediate format where:

- Visual/structural semantics (headings, page numbers, emphasis) are represented as **plain-text markers** (`xxx`, `---`, `_`)
- Images become descriptive text labels
- Sections are reordered per Statped's reading list convention
- DOCX-specific dummy text markers (`STATPED_DUMMYTEXT_*`) are planted as hooks for downstream Word style mapping
