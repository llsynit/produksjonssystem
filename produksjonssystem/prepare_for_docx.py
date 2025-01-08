#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import shutil
import sys
import tempfile

from lxml import etree as ElementTree
from bs4 import BeautifulSoup


from core.pipeline import Pipeline
from core.utils.epub import Epub
from core.utils.xslt import Xslt
from core.utils.filesystem import Filesystem

if sys.version_info[0] != 3 or sys.version_info[1] < 5:
    print("# This script requires Python version 3.5+")
    sys.exit(1)


class PrepareForDocx(Pipeline):
    uid = "prepare-for-docx"
    title = "Klargjør for DOCX"
    labels = ["e-bok", "Statped"]
    publication_format = "XHTML"
    expected_processing_time = 380

    def on_book_deleted(self):
        self.utils.report.info("Slettet bok i mappa: " + self.book['name'])
        self.utils.report.title = self.title + " EPUB slettet: " + self.book['name']
        self.utils.report.should_email = False
        return True

    def on_book_modified(self):
        self.utils.report.info("Endret bok i mappa: " + self.book['name'])
        return self.on_book()

    def on_book_created(self):
        self.utils.report.info("Ny bok i mappa: " + self.book['name'])
        return self.on_book()

    def on_book(self):
        self.utils.report.attachment(None, self.book["source"], "DEBUG")
        epub = Epub(self.utils.report, self.book["source"])

        epubTitle = ""
        try:
            epubTitle = " (" + epub.meta("dc:title") + ") "
        except Exception:
            pass

        # sjekk at dette er en EPUB
        if not epub.isepub():
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎"
            return False

        if not epub.identifier():
            self.utils.report.error(self.book["name"] + ": Klarte ikke å bestemme boknummer basert på dc:identifier.")
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎"
            return False

        # ---------- lag en kopi av EPUBen ----------

        temp_epubdir_obj = tempfile.TemporaryDirectory()
        temp_epubdir = temp_epubdir_obj.name
        Filesystem.copy(self.utils.report, self.book["source"], temp_epubdir)
        temp_epub = Epub(self, temp_epubdir)

        # ---------- gjør tilpasninger i HTML-fila med XSLT ----------

        opf_path = temp_epub.opf_path()
        if not opf_path:
            self.utils.report.error(self.book["name"] + ": Klarte ikke å finne OPF-fila i EPUBen.")
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎" + epubTitle
            return False
        opf_path = os.path.join(temp_epubdir, opf_path)
        opf_xml = ElementTree.parse(opf_path).getroot()

        html_file = opf_xml.xpath("/*/*[local-name()='manifest']/*[@id = /*/*[local-name()='spine']/*[1]/@idref]/@href")
        html_file = html_file[0] if html_file else None
        if not html_file:
            self.utils.report.error(self.book["name"] + ": Klarte ikke å finne HTML-fila i OPFen.")
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎" + epubTitle
            return False
        html_dir = os.path.dirname(opf_path)
        html_file = os.path.join(html_dir, html_file)
        if not os.path.isfile(html_file):
            self.utils.report.error(self.book["name"] + ": Klarte ikke å finne HTML-fila.")
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎" + epubTitle
            return False

        temp_html_obj = tempfile.NamedTemporaryFile()
        temp_html = temp_html_obj.name

        mathml_to_statpedmath = os.path.join(Xslt.xslt_dir, PrepareForDocx.uid, "mathml_to_statpedmath.py")
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xhtml").name
        command = ["python", mathml_to_statpedmath, "-i", temp_html, "-o", output_file]
        # Log the command for debugging
        self.utils.report.debug("Running command: " + " ".join(command))

        # Run the subprocess directly
        try:
            process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, timeout=600, check=True)

            # Check if the process was successful
            success = process.returncode == 0

            # Handle success or failure
            if success:
                self.utils.report.info(f"Conversion successful. Output file created at: {output_file}")
            else:
                self.utils.report.error("Conversion failed. Check the log for details.")
                self.utils.report.error(f"stderr: {process.stderr.decode('utf-8')}")
                self.utils.report.error(f"stdout: {process.stdout.decode('utf-8')}")

        except subprocess.CalledProcessError as e:
            self.utils.report.error("Exception occurred during subprocess execution", exc_info=True)
            self.utils.report.error(f"stderr: {e.stderr.decode('utf-8')}")
            self.utils.report.error(f"stdout: {e.stdout.decode('utf-8')}")
        except Exception as e:
            self.utils.report.error("An unexpected error occurred", exc_info=True)

        xslt = Xslt(self,
                    stylesheet=os.path.join(Xslt.xslt_dir, PrepareForDocx.uid, "prepare-for-docx.xsl"),
                    source=html_file,
                    target=temp_html)
        if not xslt.success:
            self.utils.report.title = self.title + ": " + epub.identifier() + " feilet 😭👎" + epubTitle
            return False
        shutil.copy(temp_html, html_file)

        archived_path, stored = self.utils.filesystem.storeBook(temp_epubdir, epub.identifier())
        self.utils.report.attachment(None, archived_path, "DEBUG")
        self.utils.report.title = self.title + ": " + epub.identifier() + " ble konvertert 👍😄" + epubTitle
        return True


if __name__ == "__main__":
    PrepareForDocx().run()
