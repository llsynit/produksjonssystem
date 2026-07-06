#!/usr/bin/env python3
"""
Tester ny metadata.py med siste fallback fra EPUBens package.opf.

Dette skriptet tester særlig disse metodene:

    Metadata._read_epub_package_metadata(epub)
    Metadata.get_creative_work_from_epub(epub)
    Metadata.get_edition_from_epub(identifier, format="json"/"opf"/"html")

Det bruker en liten LocalEpub-klasse og monkeypatcher metadata-modulens Epub-symbol,
slik at testen kan kjøres på enten en .epub-fil eller en allerede utpakket EPUB-mappe
uten å være avhengig av hele Epub-klassen i produksjonssystemet.

Eksempler:

    python3 test_metadata_epub_fallback.py 864230 \
      --project-dir produksjonssystem \
      --epub-path /path/to/864230.epub \
      --publication-format XHTML

    python3 test_metadata_epub_fallback.py 864230 \
      --project-dir produksjonssystem \
      --epub-path /path/to/unzipped_epub_dir \
      --publication-format XHTML
"""

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import traceback
import zipfile
from pathlib import Path

from lxml import etree as ElementTree


def print_header(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_json(obj, max_chars=6000):
    try:
        text = json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        text = repr(obj)

    if len(text) > max_chars:
        print(text[:max_chars])
        print("\n... [avkortet]")
    else:
        print(text)


def print_text(text, max_chars=4000):
    if text is None:
        print("None")
        return

    text = str(text)

    if len(text) > max_chars:
        print(text[:max_chars])
        print("\n... [avkortet]")
    else:
        print(text)


def try_parse_xml(label, text):
    print_header("XML-sjekk: {}".format(label))

    if text is None:
        print("FEIL: Ingen tekst å parse.")
        return False

    try:
        ElementTree.fromstring(str(text).encode("utf-8"))
        print("OK: kunne parses som XML med lxml.")
        return True
    except Exception:
        print("FEIL: kunne ikke parses som XML.")
        print(traceback.format_exc())
        return False


class LocalEpub:
    """
    Minimal EPUB-wrapper for å teste metadata.py sine EPUB-fallback-metoder.

    Den implementerer bare det metadata.py trenger:
      - isinstance(epub, Epub), via monkeypatch av metadata_module.Epub = LocalEpub
      - isepub()
      - book_path
      - opf_path()
      - identifier()
      - get_opf_package_element()
    """

    def __init__(self, epub_path):
        self.original_path = Path(epub_path).expanduser().resolve()
        self._tmpdir = None

        if not self.original_path.exists():
            raise FileNotFoundError(str(self.original_path))

        if self.original_path.is_file():
            if not zipfile.is_zipfile(self.original_path):
                raise ValueError("Filen er ikke en zip/epub: {}".format(self.original_path))

            self._tmpdir = tempfile.TemporaryDirectory(prefix="metadata-epub-test-")
            with zipfile.ZipFile(self.original_path, "r") as zf:
                zf.extractall(self._tmpdir.name)
            self.book_path = self._tmpdir.name

        else:
            self.book_path = str(self.original_path)

        self._opf_relpath = self._find_opf_relpath()
        self._opf_abs_path = os.path.join(self.book_path, self._opf_relpath)
        self._package_element = None

    def cleanup(self):
        if self._tmpdir is not None:
            self._tmpdir.cleanup()

    def isepub(self):
        return True

    def opf_path(self):
        return self._opf_relpath

    def identifier(self):
        root = self.get_opf_package_element()
        metadata_nodes = root.xpath("//*[local-name()='metadata']")
        if not metadata_nodes:
            return None

        metadata = metadata_nodes[0]

        # Foretrekk pub-identifier, slik produksjonskoden gjør.
        for el in metadata.xpath("./*[local-name()='identifier']"):
            value = "".join(el.itertext()).strip()
            if value and el.get("id") == "pub-identifier":
                return value

        for el in metadata.xpath("./*[local-name()='identifier']"):
            value = "".join(el.itertext()).strip()
            if value:
                return value

        return None

    def title(self):
        root = self.get_opf_package_element()
        values = root.xpath("string(//*[local-name()='metadata']/*[local-name()='title'][1])")
        return values.strip() if values else ""

    def get_opf_package_element(self):
        if self._package_element is None:
            parser = ElementTree.XMLParser(remove_blank_text=False, recover=False)
            self._package_element = ElementTree.parse(self._opf_abs_path, parser).getroot()
        return self._package_element

    def update_prefixes(self):
        return None

    def refresh_metadata(self):
        return None

    def _find_opf_relpath(self):
        container_path = os.path.join(self.book_path, "META-INF", "container.xml")

        if os.path.isfile(container_path):
            tree = ElementTree.parse(container_path)
            rootfiles = tree.xpath("//*[local-name()='rootfile']/@full-path")
            if rootfiles:
                rel = rootfiles[0]
                abs_path = os.path.join(self.book_path, rel)
                if os.path.isfile(abs_path):
                    return rel

        # Fallback: finn første .opf
        candidates = []
        for dirpath, _, filenames in os.walk(self.book_path):
            for filename in filenames:
                if filename.lower().endswith(".opf"):
                    abs_path = os.path.join(dirpath, filename)
                    rel = os.path.relpath(abs_path, self.book_path)
                    candidates.append(rel)

        if not candidates:
            raise FileNotFoundError("Fant ingen .opf-fil i {}".format(self.book_path))

        # Foretrekk package.opf hvis mulig.
        candidates.sort(key=lambda x: (os.path.basename(x).lower() != "package.opf", x))
        return candidates[0]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "produksjonsnummer",
        nargs="?",
        default=None,
        help="Forventet produksjonsnummer. Hvis utelatt brukes dc:identifier fra EPUBen.",
    )

    parser.add_argument(
        "--project-dir",
        default="produksjonssystem",
        help="Mappe som inneholder core/utils/metadata.py. Default: produksjonssystem",
    )

    parser.add_argument(
        "--epub-path",
        required=True,
        help="Sti til .epub-fil eller utpakket EPUB-mappe.",
    )

    parser.add_argument(
        "--publication-format",
        default="XHTML",
        help="Format som skal brukes i creative_work fallback. Default: XHTML",
    )

    parser.add_argument(
        "--force-insert-smoke-test",
        action="store_true",
        help=(
            "Kjør en mer omfattende smoke-test av insert_metadata() på en midlertidig kopi. "
            "Dette er mer invasivt, men original-EPUBen endres ikke."
        ),
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    report = logging.getLogger("metadata-epub-fallback-test")

    project_dir = os.path.abspath(args.project_dir)
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    print_header("Import")
    print("project_dir:", project_dir)
    print("epub_path:", os.path.abspath(args.epub_path))
    print("publication_format:", args.publication_format)

    try:
        import core.utils.metadata as metadata_module
        from core.utils.metadata import Metadata
    except Exception:
        print("FEIL: Klarte ikke å importere core.utils.metadata.")
        print("Sjekk at --project-dir peker på mappen som inneholder core/.")
        print(traceback.format_exc())
        return 2

    print("metadata.py importert fra:", metadata_module.__file__)

    # Monkeypatch Epub-symbolet i metadata.py, slik at isinstance(epub, Epub)
    # blir sant for LocalEpub.
    metadata_module.Epub = LocalEpub

    epub = None

    try:
        epub = LocalEpub(args.epub_path)
        detected_identifier = epub.identifier()
        edition_identifier = args.produksjonsnummer or detected_identifier

        print_header("EPUB funnet")
        print("book_path:", epub.book_path)
        print("opf_path:", epub.opf_path())
        print("dc:identifier:", detected_identifier)
        print("test identifier:", edition_identifier)
        print("dc:title:", epub.title())

        print_header("Metadata._read_epub_package_metadata(epub)")
        package_metadata = Metadata._read_epub_package_metadata(epub, report=report)
        print_json(package_metadata)

        required = ["identifier", "title", "language"]
        missing = [key for key in required if not package_metadata or not package_metadata.get(key)]
        if missing:
            print("ADVARSEL: Mangler viktige felter:", ", ".join(missing))
        else:
            print("OK: fant grunnleggende metadatafelter.")

        print_header("Metadata.get_creative_work_from_epub(epub)")
        creative_work = Metadata.get_creative_work_from_epub(
            epub,
            publication_format=args.publication_format,
            report=report,
        )
        print_json(creative_work)

        if not creative_work or not creative_work.get("editions"):
            print("FEIL: get_creative_work_from_epub returnerte ikke editions.")
            return 1

        print_header("Metadata.get_edition_from_epub(..., format='json')")
        edition_json = Metadata.get_edition_from_epub(
            edition_identifier,
            format="json",
            report=report,
            epub=epub,
            publication_format=args.publication_format,
        )
        print_json(edition_json)

        if not edition_json:
            print("FEIL: get_edition_from_epub(format='json') returnerte None.")
            return 1

        print_header("Metadata.get_edition_from_epub(..., format='opf')")
        opf_metadata = Metadata.get_edition_from_epub(
            edition_identifier,
            format="opf",
            report=report,
            epub=epub,
            publication_format=args.publication_format,
        )
        print_text(opf_metadata)
        opf_ok = try_parse_xml("EPUB fallback OPF metadata", opf_metadata)

        print_header("Metadata.get_edition_from_epub(..., format='html')")
        html_head = Metadata.get_edition_from_epub(
            edition_identifier,
            format="html",
            report=report,
            epub=epub,
            publication_format=args.publication_format,
        )
        print_text(html_head)
        html_ok = try_parse_xml("EPUB fallback HTML head", html_head)

        if not opf_ok or not html_ok:
            print("FEIL: OPF/HTML fra EPUB fallback kunne ikke parses som XML.")
            return 1

        # Simuler at eksterne metadata ikke finnes, og test at de nye metodene
        # fortsatt kan levere metadata fra EPUB. Dette er kjernen i siste fallback.
        print_header("Simulert siste fallback: NLB/LMSyn feiler, EPUB brukes")
        print("OK hvis disse tre er ikke-None:")
        print("creative_work:", "OK" if creative_work else "None")
        print("edition_json:", "OK" if edition_json else "None")
        print("opf_metadata:", "OK" if opf_metadata else "None")
        print("html_head:", "OK" if html_head else "None")

        if args.force_insert_smoke_test:
            print_header("Smoke-test av insert_metadata() på midlertidig kopi")

            if Path(args.epub_path).is_file():
                tmpdir = tempfile.TemporaryDirectory(prefix="metadata-insert-test-")
                with zipfile.ZipFile(args.epub_path, "r") as zf:
                    zf.extractall(tmpdir.name)
                insert_epub = LocalEpub(tmpdir.name)
            else:
                tmpdir = tempfile.TemporaryDirectory(prefix="metadata-insert-test-")
                shutil.copytree(args.epub_path, tmpdir.name, dirs_exist_ok=True)
                insert_epub = LocalEpub(tmpdir.name)

            # Tving bort eksterne metadata for å kontrollere siste fallback.
            original_validate = Metadata.validate_metadata
            original_get_creative_work = Metadata.get_creative_work_from_api
            original_get_edition_api = Metadata.get_edition_from_api
            original_get_edition_lmsyn = Metadata.get_edition_from_lmsyn_api

            try:
                Metadata.validate_metadata = staticmethod(lambda *a, **kw: False)
                Metadata.get_creative_work_from_api = staticmethod(lambda *a, **kw: None)
                Metadata.get_edition_from_api = staticmethod(lambda *a, **kw: None)
                Metadata.get_edition_from_lmsyn_api = staticmethod(lambda *a, **kw: None)

                ok = Metadata.insert_metadata(
                    report,
                    insert_epub,
                    publication_format=args.publication_format,
                    report_metadata_errors=False,
                )
                print("insert_metadata returnerte:", ok)

                if not ok:
                    print("FEIL: insert_metadata klarte ikke å bruke EPUB-fallback.")
                    return 1

            finally:
                Metadata.validate_metadata = original_validate
                Metadata.get_creative_work_from_api = original_get_creative_work
                Metadata.get_edition_from_api = original_get_edition_api
                Metadata.get_edition_from_lmsyn_api = original_get_edition_lmsyn
                try:
                    insert_epub.cleanup()
                except Exception:
                    pass
                tmpdir.cleanup()

        print_header("RESULTAT")
        print("OK: EPUB fallback ser ut til å fungere.")
        return 0

    finally:
        if epub is not None:
            epub.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
