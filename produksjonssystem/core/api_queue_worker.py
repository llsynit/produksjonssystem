import logging
import threading
import queue
import os
import requests
from core.api_worker import ApiWorker

task_queue = queue.Queue()

API_BASE_URL = os.environ.get('API_BASE_URL')
SERVER_NAME = os.environ.get('SERVER_NAME')
book_archive_dirs = os.getenv("BOOK_ARCHIVE_DIRS", "")
entries = book_archive_dirs.split()
dir_map = dict(entry.split("=", 1) for entry in entries)
master = dir_map.get("master")
logging.info(f"master: {master}")

headers = {
    "Content-Type": "application/json",
    "Authorization": os.environ.get('API_KEY')
}

def get_directories():
    logging.info(f"master: {master}")
    return {
        #innkommendenordisk
        'NORDISK': {
            "folder": os.path.join(master, "innkommende/nordisk"),
            "edition_type": ["nordiskepub"],
            "stage": "innkommendenordisk",
            "uid": "initial-nordisk-registration"
        },
        #master
        'NLBPUB': {
            "folder": os.path.join(master, "master/NLBPUB"),
            "edition_type": ["masternlbpub"],
            "stage": "masternlbpub",
            "uid": "initial-nlbpub-registration"

        },
        # lyd
        'UTGAVE_INN_LYDBOK': {
            "folder": os.path.join(master, "utgave-inn/lydbok"),
            "edition_type": ["daisy202"],
            "stage": "utgaveinnlydbok",
            "uid": "initial-utgaveinnlydbok-registration"
        },
        'EPUB_TIL_INNLESING': {
            "folder": os.path.join(master, "utgave-klargjort/EPUB-til-innlesing"),
            "edition_type": ["daisy202"],
            "stage": "utgaveklargjorttilinnlesing",
            "uid": "initial-epub-til-innlesing-registration"

        },

        #felles for docx og html
        'UTGAVE_INN_ETEKST': {
            "folder": os.path.join(master, "utgave-inn/e-tekst"),
            "edition_type": ["html", "docx"],
            "stage": "utgaveinnetekst",
            "uid": "initial-utgaveinnetekst-registration"
        },

        #docx
        'UTGAVE_KLARGJORT_DOCX': {
            "folder": os.path.join(master, "utgave-klargjort/DOCX"),
            "edition_type": ["docx"],
            "stage": "utgaveklargjortdocx",
            "uid": "initial-utgaveklargjortdocx-registration"
        },

        'UTGAVE_UT_DOCX': {
            "folder": os.path.join(master, "utgave-ut/DOCX"),
            "edition_type": ["docx"],
            "stage": "utgaveutdocx",
            "uid": "initial-docx-registration"
        },
        #html
        'UTGAVE_KLARGJORT_EBOK': {
            "folder": os.path.join(master, "utgave-klargjort/e-bok"),
            "edition_type": ["html"],
            "stage": "utgaveklargjortebok",
            "uid": "initial-utgaveklargjortebok-registration"
        },
        'UTGAVE_UT_HTML': {
            "folder": os.path.join(master, "utgave-ut/HTML"),
            "edition_type": ["html"],
            "stage": "utgaveuthtml",
            "uid": "initial-html-registration"
        },
        #punktskrift
         'UTGAVE_INN_PUNKTSKRIFT': {
            "folder": os.path.join(master, "utgave-inn/punktskrift"),
            "edition_type": ["pef"],
            "stage": "utgaveinnpunktskrift",
            "uid": "initial-utgaveinnpunktskrift-registration"
        },
        'UTGAVE_KLARGJORT_PUNKTSKRIFT': {
            "folder": os.path.join(master, "utgave-klargjort/punktskrift"),
            "edition_type": ["pef"],
            "stage": "utgaveklargjortpunktskrift",
            "uid": "initial-utgaveklargjortpunktskrift-registration"
        },
        'UTGAVE_UT_PEF': {
            "folder": os.path.join(master, "utgave-ut/PEF"),
            "edition_type":[ "pef"],
            "stage": "utgaveutpef",
            "uid": "initial-pef-registration"
        },
    }


def register_nlbpub(folder, edition, stage, uid):
    print(edition + "----------------------------------------")
    logging.info("getting production numbers from the database ....")
    production_numbers = [str(pn) for pn in ApiWorker.get_all_master_production_numbers()]
    logging.info(f"Master production numbers: {production_numbers}")

    fv_production_numbers = [str(pn) for pn in ApiWorker.get_all_fileversion_production_numbers(stage, SERVER_NAME)]
    logging.info(f"Server {SERVER_NAME} File version stage {stage} production numbers: {fv_production_numbers}")

    for directory in os.listdir(folder):
        if os.path.isdir(os.path.join(folder, directory)):
            production_number = directory
            path = os.path.join(folder, production_number, "EPUB", production_number + ".xhtml")
            logging.info("Checking " + production_number + " in master " + str(production_numbers))
            if str(production_number) in production_numbers:
                logging.info(f"Production number {production_number} already exists in master {production_numbers}. Skipping...")
            else:
                logging.info(f"Production number {production_number} does not exist in master. Registering it ...")
                guidelines = ApiWorker.get_guidelines_from_opf(production_number)
                attributes = {
                    "production_number": production_number,
                    "edition": edition,
                    "stage": stage,
                    "guidelines": guidelines if guidelines else "",

                }
                add_task(uid, production_number, attributes)
            logging.info("Checking  " + str(production_number) + " in fileversion " + str(fv_production_numbers))
            if str(production_number) in fv_production_numbers:
                logging.info(f"Production number {production_number} already exists in file version {fv_production_numbers}. Skipping...")
            else:
                logging.info(f"Production number {production_number} does not exist in versions. Registering it ...")
                date_modified = ApiWorker.get_date_modified(path)
                logging.info(f"Date modified for {production_number} is : {date_modified}")
                attributes = {
                    "production_number": production_number,
                    "edition": edition,
                    "stage": stage,
                    "date_modified": date_modified
                }
                add_task(uid, production_number, attributes)

def add_task(uid, production_number, attributes):
    """
    Add a file processing task to the queue.
    """
    task_queue.put((uid, production_number, attributes))
    logging.info(f"api-queue Task type {uid} added: {production_number} with attributes: {attributes}")

def process_tasks():
    """
    Continuously processes tasks from the queue.
    """
    logging.info("Queue worker started...")
    while True:
        task = None
        try:
            task = task_queue.get()
            if len(task) == 3:
                uid, production_number, attributes  = task
            else:
                raise ValueError(f"Invalid task format: {task}")

            logging.info(f"Processing task from process {uid}: {production_number} with attributes: {attributes}")
            ApiWorker.send_request(uid, production_number, attributes)

        except Exception as e:
            logging.error(f"Error processing task: {task}. Error: {e}")
        finally:
            task_queue.task_done()
def check_folders_for_unregistered_files():
    """
    Check folders for unregistered files.
    """
    logging.info("Checking folders for unregistered files...")
    logging.info(os.environ.get("BOOK_ARCHIVE_DIRS"))
    logging.info("-----------***-----------------")
    directories = get_directories()
    for key, value in directories.items():

        uid = value.get("uid", "")
        folder = value["folder"]
        stage = value["stage"]
        edition_types = value["edition_type"]
        uid = value["uid"]
        directory = os.environ.get(key)
        # If the directory exists (is not None or empty)
        if folder:
            #if key == "NLBPUB" or key == "UTGAVE_INN_PUNKTSKRIFT" or key == "UTGAVE_INN_LYDBOK" or key == "UTGAVE_INN_ETEKST":
                # pass
            if key == "NLBPUB" or key =="UTGAVE_INN_ETEKST":
                for edition in edition_types:
                    logging.info(f"Registering for {edition} in {key}")
                    print(f"Registering -------******@-- for {edition} in {key}")
                    register_nlbpub(folder, edition, stage, uid)

            print("Others---")
            """elif key == "UTGAVE_INN_PUNKTSKRIFT":
                # pass
                register_utgave_inn_punkt_og_utformater(folder, edition, stage)
            elif key == "UTGAVE_INN_LYDBOK":
                register_lydbok(folder, edition, stage)
            else:
                register_other_intermidiate_formats(key,
                                                    folder, edition, stage)"""


# Start queue worker thread
def start():
    """start forder checking thread"""
    threading.Thread(target=check_folders_for_unregistered_files, name="initial_scan_worker", daemon=True).start()

    """
    Start thread for queue processing.
    """
    global thread
    thread = threading.Thread(target=process_tasks, name="queue_worker")
    thread.setDaemon(True)
    thread.start()
    logging.info("Started API queue worker...")
    return thread

def join():
    """
    Stop thread.
    """
    global thread
    logging.debug(f"Joining {thread.name}")
    thread.join(timeout=5)

    if thread.is_alive():
        logging.debug("The queue worker thread is still running. Ignoring and continuing shutdown…")
