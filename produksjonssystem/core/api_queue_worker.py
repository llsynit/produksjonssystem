import logging
import threading
import queue

from core.api_worker import send_request

task_queue = queue.Queue()

def add_task(task_type, filename, options):
    """
    Add a file processing task to the queue.
    """
    task_queue.put(( filename, options))
    logging.info(f"Task type {task_type} added: {filename} with options: {options}")

def process_tasks():
    """
    Continuously processes tasks from the queue.
    """
    logging.info("Queue worker started...")
    while True:
        try:
            task_type, filename, options = task_queue.get()
            logging.info(f"Processing task: {filename} with options: {options}")
            # Process file
            send_request(task_type, filename, options)

        except Exception as e:
            logging.error(f"Error processing task: {filename}, options: {options}. Error: {e}")
        finally:
            task_queue.task_done()



# Start queue worker thread
def start():
    """
    Start thread for queue processing.
    """
    global thread
    thread = threading.Thread(target=process_tasks, name="queue_worker", daemon=True)
    thread.start()
    logging.info("Started queue worker...")
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
