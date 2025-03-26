import os
import base64
import logging
from pathlib import Path
from os import path
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import requests

class ApiWorker:
    @staticmethod
    def get_metadata_from_api(production_number):
        url = "https://api.nlb.no/v1/editions/{}/metadata?format=opf".format(
            production_number)
        response = requests.get(url)
        status_code = response.status_code
        if response is not None and status_code == 200:
            soup = BeautifulSoup(response.text, "xml")

            """"
            # Extract all dc: and meta tags
            for tag in soup.find_all():
                if tag.name.startswith("dc:"):
                    metadata[tag.name] = tag.text.strip()
                elif tag.name == "meta" and tag.has_attr("property"):
                    metadata[tag["property"]] = tag.text.strip()

            return metadata """
            # if response.status_code == 200:
            # soup = BeautifulSoup(response.text, "xml")
            metadata_tag = soup.find("metadata")

            if metadata_tag:
                metadata = {}

                # Extract all dc: and other tags
                for tag in metadata_tag.find_all():
                    print("tag.name--"+tag.name)
                    if tag.name not in ["meta"]:
                        if tag.name == "creator":
                            print("tag.text.strip()--"+tag.text.strip())
                            # Ensure 'dc:creator' is a list, and append the creator text
                            if "creator" not in metadata:
                                metadata["creator"] = []
                            metadata["creator"].append(tag.text.strip())
                        else:
                            metadata[tag.name] = tag.text.strip()

                # Extract all <meta> tags with property attributes
                for meta in metadata_tag.find_all("meta"):
                    property_name = meta.get("property")
                    if property_name:
                        metadata[property_name] = meta.text.strip()

                return metadata

    def get_cover_image(pathf):
        """Returns the cover image of the book
        Args:
            path (str): file path
        """
        encoded_img_data = ''
        if not path.exists(pathf):
            pathf = 'dummy.png'
        with open(pathf, 'rb') as binary_file:
            binary_file_data = binary_file.read()
            base64_encoded_data = base64.b64encode(binary_file_data)
            encoded_img_data = base64_encoded_data.decode('utf-8')
            return encoded_img_data


    def validate_identifier(produnumber, identifier):
        if str(produnumber)[:4] == str(identifier)[:4]:
            return True
        return False


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


    def format_creators(creator_list):
        # Join the creator names with a comma and a space, after replacing the comma in each creator name
        return ', '.join([creator.replace(",", "") for creator in creator_list])
    @staticmethod
    def send_request(task_type, productionnumber, options, archived_time):
        logging.info(f"Received task type {task_type} for {productionnumber} with options: {options}")
        logging.info("Sending requests...")
        logging.info(archived_time)
        metadata = ApiWorker.get_metadata_from_api(productionnumber)
        logging.info("Metadata:-----", metadata)