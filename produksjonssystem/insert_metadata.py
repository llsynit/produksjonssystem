#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import tempfile
import datetime
from pathlib import Path
from bs4 import BeautifulSoup

from core.pipeline import DummyPipeline, Pipeline
from core.utils.epub import Epub
from core.utils.metadata import Metadata
from core.utils.filesystem import Filesystem
from core.api_queue_worker import add_task
from core.api_worker import ApiWorker


class InsertMetadata(Pipeline):
    # Ikke instansier denne klassen; bruk heller InsertMetadataBraille osv.
    uid = "insert-metadata"
    # gid = "insert-metadata"
    title = "Sett inn metadata"
    # group_title = "Sett inn metadata"
    labels = ["Statped"]
    publication_format = None
    expected_processing_time = 500
    attributes = {}

    logPipeline = None

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
        def check_metadata_inserted( xhtml_file_path):
            """
            Check if <meta name="nlbprod:metadata.inserted" content="true" /> exists in the XHTML file.
            """
            if not os.path.exists(xhtml_file_path):
                self.utils.report.info("File does not exist: " + xhtml_file_path)
                return False

            try:
                with open(xhtml_file_path, 'r', encoding='utf-8') as file:
                    soup = BeautifulSoup(file, 'xml')  # Use 'xml' parser for XHTML files

                # Check if the <meta name="nlbprod:metadata.inserted" content="true" /> exists
                inserted_meta = soup.find("meta", attrs={"name": "nlbprod:metadata.inserted"})
                if inserted_meta and inserted_meta.get("content") == "true":
                    self.utils.report.info("Metadata inserted flag is 'true'.")
                    return True
                else:
                    self.utils.report.info("Metadata inserted flag is not 'true' or not found.")
                    return False

            except Exception as e:
                self.utils.report.info(f"Error processing XHTML file: {e}")
                return False


        def update_dc_identifier( xhtml_file_path, format_type):
            """
            Update the <meta name="dc:identifier" /> tag content based on the format type.
            """
            if not os.path.exists(xhtml_file_path):
                self.utils.report.info("File does not exist: " + xhtml_file_path)
                return False

            try:
                with open(xhtml_file_path, 'r', encoding='utf-8') as file:
                    soup = BeautifulSoup(file, 'xml')  # Use 'xml' parser for XHTML files

                # Determine which meta tag to read based on the format
                format_map = {
                    "XHTML": "nlbprod:identifier.ebook",
                    "DAISY 2.02": "nlbprod:identifier.daisy202",
                    "Braille": "nlbprod:identifier.braille"
                }

                meta_name_to_read = format_map.get(format_type)
                if not meta_name_to_read:
                    self.utils.report.info(f"Unsupported format: {format_type}")
                    return False

                # Find the relevant identifier meta tag
                source_meta = soup.find("meta", attrs={"name": meta_name_to_read})
                if not source_meta or "content" not in source_meta.attrs:
                    self.utils.report.info(f"Source metadata '{meta_name_to_read}' not found.")
                    return False

                new_value = source_meta["content"]

                # Find and update the <meta name="dc:identifier" />
                dc_identifier_meta = soup.find("meta", attrs={"name": "dc:identifier"})
                if dc_identifier_meta:
                    dc_identifier_meta["content"] = new_value
                    self.utils.report.info(f"Updated dc:identifier content to: {new_value}")

                    # Write the modified content back to the file
                    with open(xhtml_file_path, 'w', encoding='utf-8') as file:
                        file.write(str(soup))

                    self.utils.report.info("Metadata successfully updated.")
                    return True
                else:
                    self.utils.report.info("dc:identifier meta tag not found.")
                    return False

            except Exception as e:
                self.utils.report.info(f"Error processing XHTML file: {e}")
                return False



        self.utils.report.attachment(None, self.book["source"], "DEBUG")
        epub = Epub(self.utils.report, self.book["source"])

        epubTitle = ""
        try:
            epubTitle = " (" + epub.meta("dc:title") + ") "
        except Exception:
            pass

        # check that this is an EPUB (we only insert metadata into EPUBs)
        if not epub.isepub():
            return False

        if not epub.identifier():
            self.utils.report.error(self.book["name"] + ": Klarte ikke å bestemme boknummer basert på dc:identifier.")
            return False

        if epub.identifier() != self.book["name"].split(".")[0]:
            self.utils.report.error(self.book["name"] + ": Filnavn stemmer ikke overens med dc:identifier: {}".format(epub.identifier()))
            return False

        should_produce, metadata_valid = Metadata.should_produce(epub.identifier(), self.publication_format, report=self.utils.report)
        if not metadata_valid:
            self.utils.report.info("{} har feil i metadata for {}. Avbryter.".format(epub.identifier(), self.publication_format))
            self.utils.report.title = "{}: {} har feil i metadata for {} 😭👎 {}".format(self.title, epub.identifier(), self.publication_format, epubTitle)
            message = "{}: {} har feil i metadata for {} 😭👎 {}".format(self.title, epub.identifier(), self.publication_format, epubTitle)
            ApiWorker.notify(epub.identifier(), "fail", message)
            return False
        if not should_produce:
            self.utils.report.info("{} skal ikke produseres som {}. Avbryter.".format(epub.identifier(), self.publication_format))
            self.utils.report.title = "{}: {} Skal ikke produseres som {} 🤷 {}".format(self.title, epub.identifier(), self.publication_format, epubTitle)
            return True

        self.utils.report.info("Lager en kopi av EPUBen")
        temp_epubdir_obj = tempfile.TemporaryDirectory()
        temp_epubdir = temp_epubdir_obj.name
        Filesystem.copy(self.utils.report, self.book["source"], temp_epubdir)
        temp_epub = Epub(self.utils.report, temp_epubdir)
        ##test
        xhtml_file = epub.identifier() + ".xhtml"
        xhtml_file_path = os.path.normpath(os.path.join(os.path.join(temp_epubdir, "EPUB",xhtml_file)))

        metadata_inserted_status = check_metadata_inserted(xhtml_file_path)
        if metadata_inserted_status:
            self.utils.report.info("Metadata er allerede satt inn i XHTML-filen.")
            update_dc_identifier( xhtml_file_path, self.publication_format)

        else:
            is_valid = Metadata.insert_metadata(self.utils.report, temp_epub, publication_format=self.publication_format, report_metadata_errors=False)
            if not is_valid:
                self.utils.report.error("Bibliofil-metadata var ikke valide. Avbryter.")
                return False

        self.utils.report.info("Boken ble oppdatert med format-spesifikk metadata. Kopierer til {}-arkiv.".format(self.publication_format))

        archived_path, stored = self.utils.filesystem.storeBook(temp_epub.asDir(), epub.identifier())
        self.utils.report.attachment(None, archived_path, "DEBUG")
        date_modified = datetime.datetime.now().timestamp()  # Get the current timestamp

        self.utils.report.title = "{}: {} har fått {}-spesifikk metadata og er klar til å produseres 👍😄 {}".format(
            self.title, epub.identifier(), self.publication_format, temp_epub.meta("dc:title"))
        dt_m = datetime.datetime.fromtimestamp(date_modified)  # Convert the timestamp to a datetime object
        archived_time = dt_m.isoformat()

        self.attributes["date_modified"] = archived_time
        add_task(self.uid,epub.identifier(), self.attributes)
        message = "{}: {} har fått {}-spesifikk metadata og er klar til å produseres 👍😄 {}".format(
            self.title, epub.identifier(), self.publication_format, temp_epub.meta("dc:title"))
        ApiWorker.notify(epub.identifier(), "success", message)
        return True


class InsertMetadataDaisy202(InsertMetadata):
    uid = "insert-metadata-daisy202"
    title = "Sett inn metadata for lydbok"
    labels = ["Lydbok", "Metadata", "Statped"]
    publication_format = "DAISY 2.02"
    expected_processing_time = 500
    attributes = {
            "edition": "daisy202",
            "stage": "utgaveinnlydbok",
        }

class InsertMetadataXhtml(InsertMetadata):
    uid = "insert-metadata-xhtml"
    title = "Sett inn metadata for e-bok"
    labels = ["e-bok", "Metadata", "Statped"]
    publication_format = "XHTML"
    expected_processing_time = 500
    attributes = {
            "edition": "html",
            "stage": "utgaveinnetekst",
        }


class InsertMetadataBraille(InsertMetadata):
    uid = "insert-metadata-braille"
    title = "Sett inn metadata for punktskrift"
    labels = ["Punktskrift", "Metadata", "Statped"]
    publication_format = "Braille"
    expected_processing_time = 500
    attributes = {
            "edition": "pef",
            "stage": "utgaveinnpunktskrift",
        }
