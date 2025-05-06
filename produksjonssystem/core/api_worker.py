import os
import base64
import logging
from pathlib import Path
from os import path
from datetime import datetime
import logging
from bs4 import BeautifulSoup
from lxml import etree
import requests

API_BASE_URL = os.environ.get('API_BASE_URL')
SERVER_NAME = os.environ.get('SERVER_NAME')
book_archive_dirs = os.getenv("BOOK_ARCHIVE_DIRS", "")
entries = book_archive_dirs.split()
dir_map = dict(entry.split("=", 1) for entry in entries)
master = dir_map.get("master")
logging.info(f"master: {master}")



class ApiWorker:
    @staticmethod
    def get_date_modified(path):
        """Get permission of file or directory in octal
        Args:
            path (str): file path
        """
        path_obj = Path(path)
        if path_obj.exists():
            date_modified = os.path.getmtime(path_obj)
            logging.debug(f"----date_modified: {date_modified}")
            # date_modified = os.path.getmtime(path)
            dt_m = datetime.fromtimestamp(date_modified)
            logging.debug(f"****@@date_modified: {dt_m}")
            # return dt_m
            # Convert datetime to an ISO 8601 string --to handle JSON serializable issue
            return dt_m.isoformat()
        return None

    @staticmethod
    def get_guidelines_from_opf(productionnumber):
        path = os.path.join(master,"master","NLBPUB", productionnumber, "EPUB", "package.opf")

        try:
            if not os.path.exists(path):
                logging.error(f"Error: OPF file not found at {path}")
                return False

            with open(path, encoding='utf-8') as f:
                xml_content = f.read()

            soup = BeautifulSoup(xml_content, 'xml')  # Use 'xml' parser

            # Extract content with property 'nordic:guidelines'
            meta_property = soup.find("meta", property="nordic:guidelines")
            if meta_property:
                logging.info("Found 'meta' with property 'nordic:guidelines'")
                return None

            # Extract single content with name 'nordic:guidelines'
            meta_name = soup.find("meta", attrs={"name": "nordic:guidelines"})
            if meta_name and "content" in meta_name.attrs:
                logging.info("Found 'meta' with name 'nordic:guidelines'")
                return None

            return True  # Return True if neither was found

        except Exception as e:
            logging.error(f"Error reading {path}: {e}")

    def get_cover_image(productionnumber):
        """Returns the cover image of the book
        Args:
            path (str): file path
        """
        path = os.path.join(master,"master","NLBPUB", productionnumber, "EPUB", "images", "cover.jpg")
        encoded_img_data = ''
        if not path.exists(path):
            return None
        with open(path, 'rb') as binary_file:
            binary_file_data = binary_file.read()
            base64_encoded_data = base64.b64encode(binary_file_data)
            encoded_img_data = base64_encoded_data.decode('utf-8')
            return encoded_img_data


    def validate_identifier(produnumber, identifier):
        if str(produnumber)[:4] == str(identifier)[:4]:
            return True
        return False




    def format_creators(creator_list):
        # Join the creator names with a comma and a space, after replacing the comma in each creator name
        return ', '.join([creator.replace(",", "") for creator in creator_list])
    @staticmethod
    def notify(production_number, status, message):
        url = f"{API_BASE_URL}users/notifications/update/"
        headers = {
            "Content-Type": "application/json",
            "Authorization": os.environ.get('API_KEY')
        }
        payload = {
            "production_number": production_number,
            "message": message,
            "server_name": SERVER_NAME,
            "status": status

        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logging.info(f"Notification sent successfully: {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Failed to send notification: {e}")
            return False
        return True

    @staticmethod
    def get_all_master_production_numbers():
        url = f"{API_BASE_URL}books/list/masterproductionnumbers/"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            #production_numbers = [item['production_number'] for item in data]
            return data.get("production_numbers", [])
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return []
    @staticmethod
    def get_all_fileversion_production_numbers(stage, server_name):
        logging.info(f"Getting all file version production numbers for stage: {stage} and server name: {server_name}")
        url = f"{API_BASE_URL}books/list/fileversionproductionnumbers/{server_name}/{stage}/"
        try:
            response = requests.get(url, params={ "server_name": server_name})
            response.raise_for_status()
            data = response.json()
            logging.info(f"Response data: {data}")
            #production_numbers = [item['production_number'] for item in data]
            return data.get("production_numbers", [])
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return []
    @staticmethod
    def check_master_exists(production_number: int) -> bool:
        url = f"{API_BASE_URL}books/check/master/{production_number}/"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json().get("exists", False)
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return False
    @staticmethod
    def check_fileversion_exists( server_name, production_number, stage) -> bool:
        url = f"{API_BASE_URL}books/check/version/{server_name}/{stage}/{production_number}/"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json().get("exists", False)
        except requests.RequestException as e:
            print("-----")
            print(f"Request failed: {e}")
            return False



    @staticmethod
    def register_api(production_number, payload, enpoint):
        logging.info(f"Registering book {production_number} with payload: {payload}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": os.environ.get('API_KEY')
        }
        if enpoint == "master":
            register_url = f"{API_BASE_URL}books/register/master/"
        else:
            register_url = f"{API_BASE_URL}books/register/fileversion/"
        #logging.info(f"URL {register_url}")
        #logging.info(f"KEY {os.environ.get('API_KEY')}")

        register_response = requests.post(
            register_url, json=payload, headers=headers)

        if register_response.status_code == 201:
            logging.info(f"Successfully registered book {production_number} in {enpoint}")
        else:
            logging.error(
                f"Failed to register book {production_number}: {register_response.text}")


    @staticmethod
    def get_metadata_from_api(production_number):
        other_formats_prodnumbers = {}
        metadata = {}
        try:
            # Define the API URL using the production_number
            api_url = f"https://api.nlb.no/v1/editions/{production_number}/metadata?format=opf"
            response = requests.get(api_url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            soup = BeautifulSoup(response.content, 'lxml-xml')
            title = soup.find("dc:title").text
            author = soup.find("dc:creator").text
            year = soup.find("meta", {"property": "dc:date.issued"}).text
            isbn = soup.find("meta", {"property": "schema:isbn"}).text
            production_number = soup.find("dc:identifier", {"id": "pub-id"}).text
            cover_image = "path"  # Assuming a placeholder path for the cover image
            other_formats_prodnumbers = {}  # Default empty dictionary for other formats' production numbers
            daisy202=soup.find("meta", {"property": "nlbprod:identifier.daisy202"}).text
            braille=soup.find("meta", {"property": "nlbprod:identifier.braille"}).text
            ebook=soup.find("meta", {"property": "nlbprod:identifier.ebook"}).text
            other_formats_prodnumbers = {
            "masternlbpub": production_number,
            "lyd": daisy202,
            "pef": braille,
            "html":ebook,
            "docx":ebook

            }
            print("other_formats_prodnumbers" + str(other_formats_prodnumbers))
            # Create the final book data dictionary
            metadata = {
                "title": title,
                "author": author,
                "year": year,
                "isbn": isbn,
                "cover_image": cover_image,
                "production_number": production_number,
                "other_formats_prodnumbers": other_formats_prodnumbers
            }

            return metadata

        except requests.exceptions.RequestException as e:
            # Handle any request-related errors
            logging.error(f"Error fetching data from API: {e}")
            return None

        except Exception as e:
            # Handle any other errors
            logging.error(f"Error: {e}")
            return None


    def send_request(uid, productionnumber, attributes):
        if uid == "nordic-epub-to-nlbpub" or uid == "initial-nlbpub-registration":
            if ApiWorker.check_master_exists(productionnumber):
                logging.info(f"Production number {productionnumber} already exists in master. Skipping...")
            else:
                metadata = ApiWorker.get_metadata_from_api(productionnumber)
                if metadata is None:
                    logging.error(f"Failed to fetch metadata for {productionnumber}")
                    return

                guidelines = attributes.get("guidelines") or ApiWorker.get_guidelines_from_opf(productionnumber)
                if guidelines:
                    metadata["guidelines"] = guidelines

                ApiWorker.register_api(productionnumber, metadata, "master")

            if ApiWorker.check_fileversion_exists(SERVER_NAME, productionnumber, attributes["stage"]):
                logging.info(f"Main -- Production number {productionnumber} already exists in file version. Skipping...")
            else:
                payload = {
                    "production_number": productionnumber,
                    "edition_type": attributes["edition"],
                    "stage": attributes["stage"],
                    "server_name": SERVER_NAME,
                    "date_modified": attributes["date_modified"],
                }
                ApiWorker.register_api(productionnumber, payload, "fileversion")
                return  # ✅ Prevents falling into the else block

        else:
            if ApiWorker.check_fileversion_exists(SERVER_NAME, productionnumber, attributes["stage"]):
                logging.info(f"Else -- Production number {productionnumber} already exists in file version. Skipping...")

            payload = {
                "production_number": productionnumber,
                "edition_type": attributes["edition"],
                "stage": attributes["stage"],
                "server_name": SERVER_NAME,
                "date_modified": attributes["date_modified"],
            }
            ApiWorker.register_api(productionnumber, payload, "fileversion")