#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
import sys
import tempfile

from pathlib import Path
import traceback


from lxml import etree
from bs4 import BeautifulSoup

from core.pipeline import Pipeline
from core.utils.daisy_pipeline import DaisyPipelineJob
from core.utils.epub import Epub
from core.utils.xslt import Xslt
from core.utils.metadata import Metadata
from core.utils.filesystem import Filesystem
from nlbpub_to_statpub import apply_requirements

if sys.version_info[0] != 3 or sys.version_info[1] < 5:
    print("# This script requires Python version 3.5+")
    sys.exit(1)


class NordicToNlbpub(Pipeline):
    uid = "nordic-epub-to-nlbpub"
    title = "Nordisk EPUB til NLBPUB"
    labels = ["EPUB", "Lydbok", "Punktskrift", "e-bok", "Statped"]
    publication_format = None
    expected_processing_time = 2000

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
            epubTitle = " (" + epub.meta("dc:title") + ") "
        except Exception:
            pass

        # sjekk at dette er en EPUB
        if not epub.isepub():
            return False

        if not epub.identifier():
            self.utils.report.error(self.book["name"] + ": Klarte ikke å bestemme boknummer basert på dc:identifier.")
            return False

        if epub.identifier() != self.book["name"].split(".")[0]:
            self.utils.report.error(self.book["name"] + ": Filnavn stemmer ikke overens med dc:identifier: {}".format(epub.identifier()))
            return False

        temp_xml_file_obj = tempfile.NamedTemporaryFile()
        temp_xml_file = temp_xml_file_obj.name
        html_dir_obj = tempfile.TemporaryDirectory()
        html_dir = html_dir_obj.name
        meta_name_content = None
        meta_name = None
        # Read the package.opf file to determine the guidelines version
        opf_path = Path(self.book["source"]).parent / epub.identifier() / "EPUB" / "package.opf"
        try:

            if not opf_path.exists():
                self.utils.report.error(f"Error: OPF file not found at {opf_path}")
                return False
            xml_content = opf_path.read_text(encoding='utf-8')
            soup = BeautifulSoup(xml_content, 'xml')  # Use 'xml' parser

            # Extract content with property 'nordic:guidelines'
            meta_property = soup.find("meta", property="nordic:guidelines")
            meta_property_content = meta_property.text if meta_property else None
            self.utils.report.info("Content of meta with property 'nordic:guidelines':", meta_property_content)

            # Extract single content with name 'nordic:guidelines'
            meta_name = soup.find("meta", attrs={"name": "nordic:guidelines"})
            meta_name_content = meta_name['content'] if meta_name and "content" in meta_name.attrs else None
            self.utils.report.info("Content of meta with name 'nordic:guidelines':", meta_name_content)

        except Exception as e:
            self.utils.report.error(f"Error reading {opf_path}: {e}")
        #TODO:        # refactor to use the same mechanism to save the files.
        if (meta_property_content is not None and meta_property_content=="2020-1") or (meta_name_content is not None and meta_name_content=="2020-1"):
            self.utils.report.info("EPUB har nordic guidelines 2020-1.")
            self.utils.report.info("Konverterer fra Nordisk EPUB 3 til NLBPUB med python skript...")
            success = False
            try:
                command = ["src/run.py", self.book["source"], html_dir, "--add-header-element=false"]

                epub_to_html_home = os.getenv("EPUB_TO_HTML_HOME")
                if not epub_to_html_home:
                    self.utils.report.warning("EPUB_TO_HTML_HOME is not set. Using default value: /opt/nordic-epub3-dtbook-migrator")
                    epub_to_html_home = "/opt/nordic-epub3-dtbook-migrator"

                process = Filesystem.run_static(command, epub_to_html_home, self.utils.report)
                success = process.returncode == 0

            except subprocess.TimeoutExpired:
                self.utils.report.error("Epubcheck for {} took too long and were therefore stopped.".format(os.path.basename(self.book["source"])))

            except Exception:
                self.utils.report.debug(traceback.format_exc(), preformatted=True)
                self.utils.report.error("An error occured while running EPUB to HTML (for " + str(self.book["source"]) + ")")

            if not success:
                self.utils.report.error("Klarte ikke å konvertere boken")
                return False

            self.utils.report.debug("Output directory contains: " + str(os.listdir(html_dir)))
            html_dir = os.path.join(html_dir, epub.identifier())

            if not os.path.isdir(html_dir):
                self.utils.report.error("Finner ikke den konverterte boken: {}".format(html_dir))
                return False

            self.utils.report.info("Boken ble konvertert. Kopierer til NLBPUB-arkiv.")
            archived_path, _ = self.utils.filesystem.storeBook(html_dir, epub.identifier(), overwrite=self.overwrite)
            self.utils.report.attachment(None, archived_path, "DEBUG")
            self.utils.report.title = self.title + ": " + epub.identifier() + " ble konvertert 👍😄" + epubTitle
            return True

        else:
            self.utils.report.info("EPUB har nordic guidelines 2015-1.")
            self.utils.report.info("Lager en kopi av EPUBen")
            temp_epubdir_withimages_obj = tempfile.TemporaryDirectory()
            temp_epubdir_withimages = temp_epubdir_withimages_obj.name
            Filesystem.copy(self.utils.report, self.book["source"], temp_epubdir_withimages)

            self.utils.report.info("Lager en kopi av EPUBen med tomme bildefiler")
            temp_epubdir_obj = tempfile.TemporaryDirectory()
            temp_epubdir = temp_epubdir_obj.name

            Filesystem.copy(self.utils.report, temp_epubdir_withimages, temp_epubdir)
            for root, dirs, files in os.walk(os.path.join(temp_epubdir, "EPUB", "images")):
                for file in files:
                    fullpath = os.path.join(root, file)
                    os.remove(fullpath)
                    Path(fullpath).touch()
            temp_epub = Epub(self.utils.report, temp_epubdir)

            self.utils.report.info("Rydder opp i nordisk EPUB nav.xhtml")
            nav_path = os.path.join(temp_epubdir, temp_epub.nav_path())
            xslt = Xslt(self,
                        stylesheet=os.path.join(Xslt.xslt_dir, NordicToNlbpub.uid, "nordic-cleanup-nav.xsl"),
                        source=nav_path,
                        target=temp_xml_file,
                        parameters={
                            "cover": " ".join([item["href"] for item in temp_epub.spine()]),
                            "base": os.path.dirname(os.path.join(temp_epubdir, temp_epub.opf_path())) + "/"
                        })
            if not xslt.success:
                return False
            shutil.copy(temp_xml_file, nav_path)

            self.utils.report.info("Rydder opp i nordisk EPUB package.opf")
            opf_path = os.path.join(temp_epubdir, temp_epub.opf_path())
            xslt = Xslt(self,
                        stylesheet=os.path.join(Xslt.xslt_dir, NordicToNlbpub.uid, "nordic-cleanup-opf.xsl"),
                        source=opf_path,
                        target=temp_xml_file)
            if not xslt.success:
                return False
            shutil.copy(temp_xml_file, opf_path)

            html_dir_obj = tempfile.TemporaryDirectory()
            html_dir = html_dir_obj.name
            html_file = os.path.join(html_dir, epub.identifier() + ".xhtml")

            self.utils.report.info("Finner ut hvilket bibliotek boka tilhører…")
            edition_metadata = Metadata.get_edition_from_api(epub.identifier(), report=self.utils.report)
            library = None
            if edition_metadata is not None and edition_metadata["library"] is not None:
                library = edition_metadata["library"]
            else:
                library = Metadata.get_library_from_identifier(epub.identifier(), self.utils.report)
            self.utils.report.info(f"Boka tilhører '{library}'")

            self.utils.report.info("Zipper oppdatert versjon av EPUBen...")
            temp_epub.asFile(rebuild=True)

            self.utils.report.info("Konverterer fra Nordisk EPUB 3 til Nordisk HTML 5...")
            epub_file = temp_epub.asFile()
            with DaisyPipelineJob(self,
                                "nordic-epub3-to-html",
                                {"epub": os.path.basename(epub_file), "fail-on-error": "false"},
                                pipeline_and_script_version=[
                                    ("1.13.6", "1.4.6"),
                                    ("1.13.4", "1.4.5"),
                                    ("1.12.1", "1.4.2"),
                                    ("1.11.1-SNAPSHOT", "1.3.0"),
                                ],
                                context={
                                    os.path.basename(epub_file): epub_file
                                }) as dp2_job_convert:
                convert_status = "SUCCESS" if dp2_job_convert.status == "SUCCESS" else "ERROR"

                if convert_status != "SUCCESS":
                    self.utils.report.error("Klarte ikke å konvertere boken")
                    return False

                dp2_html_dir = os.path.join(dp2_job_convert.dir_output, "output-dir", epub.identifier())
                dp2_html_file = os.path.join(dp2_job_convert.dir_output, "output-dir", epub.identifier(), epub.identifier() + ".xhtml")

                if not os.path.isdir(dp2_html_dir):
                    self.utils.report.error("Finner ikke den konverterte boken: {}".format(dp2_html_dir))
                    return False

                if not os.path.isfile(dp2_html_file):
                    self.utils.report.error("Finner ikke den konverterte boken: {}".format(dp2_html_file))
                    self.utils.report.info("Kanskje filnavnet er forskjellig fra IDen?")
                    return False

                Filesystem.copy(self.utils.report, dp2_html_dir, html_dir)

            self.utils.report.info("Rydder opp i nordisk HTML")
            xslt = Xslt(self, stylesheet=os.path.join(Xslt.xslt_dir, NordicToNlbpub.uid, "nordic-cleanup.xsl"),
                        source=html_file,
                        target=temp_xml_file)
            if not xslt.success:
                return False
            shutil.copy(temp_xml_file, html_file)

            self.utils.report.info("Rydder opp i ns0 i page-normal")
            xslt = Xslt(self, stylesheet=os.path.join(Xslt.xslt_dir, NordicToNlbpub.uid, "ns0-cleanup.xsl"),
                        source=html_file,
                        target=temp_xml_file)
            if not xslt.success:
                return False
            shutil.copy(temp_xml_file, html_file)

            self.utils.report.info("Rydder opp i innholdsfortegnelsen")
            xslt = Xslt(self, stylesheet=os.path.join(Xslt.xslt_dir, NordicToNlbpub.uid, "fix-toc-span.xsl"),
                        source=html_file,
                        target=temp_xml_file)
            if not xslt.success:
                return False
            #shutil.copy(temp_xml_file, html_file)

            with open(temp_xml_file, "r") as f:
                soup = BeautifulSoup(f, 'xml')

            with open(temp_xml_file, "w") as f:
                f.write(str(apply_requirements(soup, self.utils.report)))


            shutil.copy(temp_xml_file, html_file)

            self.utils.report.info("Legger til EPUB-filer (OPF, NAV, container.xml, mediatype)...")
            nlbpub_tempdir_obj = tempfile.TemporaryDirectory()
            nlbpub_tempdir = nlbpub_tempdir_obj.name

            nlbpub = Epub.from_html(self, html_dir, nlbpub_tempdir)
            if nlbpub is None:
                return False

            self.utils.report.info("Erstatter tomme bildefiler med faktiske bildefiler")
            for root, dirs, files in os.walk(os.path.join(nlbpub_tempdir, "EPUB", "images")):
                for file in files:
                    fullpath = os.path.join(root, file)
                    relpath = os.path.relpath(fullpath, nlbpub_tempdir)
                    os.remove(fullpath)
                    Filesystem.copy(self.utils.report, os.path.join(temp_epubdir_withimages, relpath), fullpath)
            temp_epub = Epub(self.utils.report, temp_epubdir)


            nlbpub.update_prefixes()

            self.utils.report.info("Boken ble konvertert. Kopierer til NLBPUB-arkiv.")
            archived_path, stored = self.utils.filesystem.storeBook(nlbpub.asDir(), temp_epub.identifier(), overwrite=self.overwrite)
            self.utils.report.attachment(None, archived_path, "DEBUG")
            self.utils.report.title = self.title + ": " + epub.identifier() + " ble konvertert 👍😄" + epubTitle
            return True


if __name__ == "__main__":
    NordicToNlbpub().run()
