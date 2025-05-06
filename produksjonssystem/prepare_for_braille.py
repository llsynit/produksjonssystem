#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import shutil
import sys
import tempfile
import datetime

from lxml import etree as ElementTree
from lxml import etree
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


from core.pipeline import Pipeline
from core.utils.epub import Epub
from core.utils.xslt import Xslt
from core.utils.filesystem import Filesystem
from core.api_queue_worker import add_task
from core.api_worker import ApiWorker


if sys.version_info[0] != 3 or sys.version_info[1] < 5:
    print("# This script requires Python version 3.5+")
    sys.exit(1)


class PrepareForBraille(Pipeline):
    uid = "prepare-for-braille"
    title = "Klargjør for punktskrift"
    labels = ["Punktskrift", "Statped"]
    publication_format = "Braille"
    expected_processing_time = 450


    attributes = {
            "edition": "pef",
            "stage": "utgaveklargjortpunktskrift",
        }
    message =""
    def on_book_deleted(self):
        self.utils.report.info("Slettet bok i mappa: " + self.book['name'])
        self.utils.report.title = self.title + " EPUB master slettet: " + self.book['name']
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
            epubTitle = " (" + epub.meta("dc:title") + ") "  # type: ignore
        except Exception:
            pass

        # sjekk at dette er en EPUB
        if not epub.isepub():
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎"
            message = self.title + ": " + self.book["name"] + " feilet 😭👎"
            ApiWorker.notify(epub.identifier(), "fail", message)
            return

        if not epub.identifier():
            self.utils.report.error(self.book["name"] + ": Klarte ikke å bestemme boknummer basert på dc:identifier.")
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎"
            ApiWorker.notify(epub.identifier(), "fail", message)
            return False

        # ---------- lag en kopi av EPUBen ----------

        temp_epubdir_obj = tempfile.TemporaryDirectory()
        temp_epubdir = temp_epubdir_obj.name
        Filesystem.copy(self.utils.report, self.book["source"], temp_epubdir)
        temp_epub = Epub(self.utils.report, temp_epubdir)

        # ---------- gjør tilpasninger i HTML-fila med XSLT ----------

        opf_path = temp_epub.opf_path()
        if not opf_path:
            self.utils.report.error(self.book["name"] + ": Klarte ikke å finne OPF-fila i EPUBen.")
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎" + epubTitle
            ApiWorker.notify(epub.identifier(), "fail", message)
            return False
        opf_path = os.path.join(temp_epubdir, opf_path)
        xml_parser = ElementTree.XMLParser(encoding="utf-8")
        opf_xml = ElementTree.parse(opf_path, parser=xml_parser).getroot()

        html_file = opf_xml.xpath("/*/*[local-name()='manifest']/*[@id = /*/*[local-name()='spine']/*[1]/@idref]/@href")
        html_file = html_file[0] if html_file else None
        if not html_file:
            self.utils.report.error(self.book["name"] + ": Klarte ikke å finne HTML-fila i OPFen.")
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎" + epubTitle
            ApiWorker.notify(epub.identifier(), "fail", message)
            return False
        html_file = os.path.join(os.path.dirname(opf_path), html_file)
        if not os.path.isfile(html_file):
            self.utils.report.error(self.book["name"] + ": Klarte ikke å finne HTML-fila.")
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎" + epubTitle
            ApiWorker.notify(epub.identifier(), "fail", message)
            return False

        temp_html_obj = tempfile.NamedTemporaryFile()
        temp_html = temp_html_obj.name

        self.utils.report.info("Tilpasser innhold for punktskrift…")
        xslt = Xslt(self,
                    stylesheet=os.path.join(Xslt.xslt_dir, PrepareForBraille.uid, "prepare-for-braille.xsl"),
                    source=html_file,
                    target=temp_html,
                    report=self.utils.report)
        if not xslt.success:
            report_title = self.title + ": " + str(epub.identifier()) + " feilet 😭👎" + str(epubTitle)
            ApiWorker.notify(epub.identifier(), "fail", message)
            self.utils.report.title = report_title
            return False
        shutil.copy(temp_html, html_file)

        self.utils.report.info("Bedre hefteinndeling, fjern tittelside og innholdsfortegnelse, flytte kolofon og opphavsrettside til slutten av boka…")
        xslt = Xslt(self,
                    stylesheet=os.path.join(Xslt.xslt_dir, PrepareForBraille.uid, "pre-processing.xsl"),
                    source=html_file,
                    target=temp_html,
                    report=self.utils.report)
        if not xslt.success:
            report_title = self.title + ": " + str(epub.identifier() or "") + " feilet 😭👎" + str(epubTitle)
            ApiWorker.notify(epub.identifier(), "fail", message)
            self.utils.report.title = report_title
            return False
        shutil.copy(temp_html, html_file)

        self.utils.report.info("Bedre håndtering av tabeller…")
        xslt = Xslt(self,
                    stylesheet=os.path.join(Xslt.xslt_dir, PrepareForBraille.uid, "add-table-classes.xsl"),
                    source=html_file,
                    target=temp_html,
                    report=self.utils.report)
        if not xslt.success:
            self.utils.report.title = self.title + ": " + str(epub.identifier() or "") + " feilet 😭👎" + epubTitle
            ApiWorker.notify(epub.identifier(), "fail", message)
            return False
        shutil.copy(temp_html, html_file)

        self.utils.report.info("Lag ny tittelside og bokinformasjon…")
        xslt = Xslt(self,
                    stylesheet=os.path.join(Xslt.xslt_dir, PrepareForBraille.uid, "insert-boilerplate.xsl"),
                    source=html_file,
                    target=temp_html,
                    report=self.utils.report)
        if not xslt.success:
            self.utils.report.title = self.title + ": " + str(epub.identifier() or "") + " feilet 😭👎" + epubTitle
            ApiWorker.notify(epub.identifier(), "fail", message)
            return False
        shutil.copy(temp_html, html_file)

        # ---------- hent nytt boknummer fra /html/head/meta[@name='dc:identifier'] og bruk som filnavn ----------

        xml_parser = ElementTree.XMLParser(encoding="utf-8")
        html_xml = ElementTree.parse(temp_html, parser=xml_parser).getroot()
        result_identifier = html_xml.xpath("/*/*[local-name()='head']/*[@name='dc:identifier']")
        result_identifier = result_identifier[0].attrib["content"] if result_identifier and "content" in result_identifier[0].attrib else None
        if not result_identifier:
            self.utils.report.error(self.book["name"] + ": Klarte ikke å finne boknummer i ny HTML-fil.")
            self.utils.report.title = self.title + ": " + self.book["name"] + " feilet 😭👎" + epubTitle
            ApiWorker.notify(epub.identifier(), "fail", message)
            return False

        shutil.copy(html_file, temp_html)
        os.remove(html_file)
        html_file = os.path.join(os.path.dirname(html_file), result_identifier + ".html")  # Bruk html istedenfor xhtml når det ikke er en EPUB
        shutil.copy(temp_html, html_file)
         #-----remove pef-about and replace with epub:frontmatter--
        #--- Temporary solution to make the merknad to appear after the toc in pef files
        # find sections with class pef-about and  remove that class and replace it with epub:type="frontmatter"
        self.utils.report.info("Endrer klasse pef-about til epub:type='frontmatter'")
        soup = BeautifulSoup(open(html_file), "html.parser")
        for section in soup.find_all("section", class_="pef-about"):
            section["epub:type"] = "frontmatter"
            del section["class"]
        with open(html_file, "w") as file:
            file.write(str(soup))

        # ---------- slett EPUB-spesifikke filer ----------

        items = opf_xml.xpath("/*/*[local-name()='manifest']/*")
        for item in items:
            delete = False

            if "properties" in item.attrib and "nav" in re.split(r'\s+', item.attrib["properties"]):
                delete = True

            if "media-type" in item.attrib:
                if item.attrib["media-type"].startswith("audio/"):
                    delete = True
                elif item.attrib["media-type"] == "application/smil+xml":
                    delete = True

            if not delete or "href" not in item.attrib:
                continue

            fullpath = os.path.join(os.path.dirname(opf_path), item.attrib["href"])
            os.remove(fullpath)
        os.remove(opf_path)

        # ---------- lagre HTML-filsett ----------

        html_dir = os.path.dirname(opf_path)

        self.utils.report.info("Boken ble konvertert. Kopierer til arkiv for punkt-klare HTML-filer.")

        archived_path, stored = self.utils.filesystem.storeBook(html_dir, self.book["name"])
        date_modified = datetime.datetime.now().timestamp()
        self.utils.report.attachment(None, archived_path, "DEBUG")
        self.utils.report.title = self.title + ": " + self.book["name"] + " ble konvertert 👍😄" + epubTitle
        dt_m = datetime.datetime.fromtimestamp(date_modified)
        archived_time = dt_m.isoformat()
        self.attributes["date_modified"] = archived_time
        add_task(self.uid,epub.identifier(), self.attributes)
        message = self.title + ": " + self.book["name"] + " ble konvertert 👍😄" + epubTitle
        ApiWorker.notify(epub.identifier(), "success", message)
        return True


if __name__ == "__main__":
    PrepareForBraille().run()
