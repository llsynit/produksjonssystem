import logging
import threading
import requests

def send_request(filename, options):
    logging.info("Sending requests...")


# Background worker function
def run():
    logging.info("API worker started...")

# Use start and join to run as a thread
def start():
    """
    Start thread
    """
    global thread
    thread = threading.Thread(target=run, name="api_worker")
    thread.setDaemon(True)
    thread.start()
    logging.info("Started API worker...")
    return thread

def join():
    """
    Stop thread
    """
    global thread
    logging.debug(f"Joining {thread.name}")
    thread.join(timeout=5)

    if thread.is_alive():
        logging.debug("The API worker thread is still running. Ignoring and continuing shutdown…")
