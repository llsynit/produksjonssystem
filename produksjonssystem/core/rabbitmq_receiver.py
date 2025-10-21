import pika
import logging
import threading
import requests

braille_arguements_from_rbmq = {}

def check_braille_filename_in_queues(filename):
    filename_prefix = filename.split('.')
    filename = filename_prefix[0]
    print(braille_arguements_from_rbmq)
    if filename in braille_arguements_from_rbmq:
        options = braille_arguements_from_rbmq[filename]
        del braille_arguements_from_rbmq[filename]
        return options
    else:
        return None

# Callback function to handle received file and options
def process_file(ch, method, properties, body):
    logging.info("Received something-------******************************@...")
    filename, options = body.decode().split(',')
    print("Received file:", filename)
    print("Received options:", options)
    # Implement file processing logic here
    # remove filename from the braille_arguements_from_rbmq if it exists
    if filename in braille_arguements_from_rbmq:
        logging.warning(f"{filename} exist int dict from before. Removing it before adding new options")
        del braille_arguements_from_rbmq[filename]

    braille_arguements_from_rbmq[filename] = options
      # Acknowledge the message
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Consume file and options from the queue



# Start consuming messages
def run():
    logging.info("Trying to connect to rabbitmq...")
    try:
        # Connect to RabbitMQ server
        connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq', 5672))
        channel = connection.channel()
        logging.info("Connection to rabbitmq successful...")
        # Declare a queue
        logging.info("Declaring file_processing_queue queue...")
        channel.queue_declare(queue='file_processing_queue')
        channel.start_consuming()
        logging.info("Waiting for files and processing options...")
        channel.basic_consume(queue='file_processing_queue', on_message_callback=process_file)
    except Exception as e:
        logging.error(f"Error while connecting to RabbitMQ: {e}")





# Use start and join to run as a thread
def start():
    """
    Start thread
    """

    global thread, base_url
    thread = threading.Thread(target=run, name="rabbitmq_receiver")
    thread.setDaemon(True)
    thread.start()
    logging.info("Started Rabbitmq receiver.... ")
    return thread


def join():
    """
    Stop thread
    """

    global thread


    logging.debug("joining {}".format(thread.name))
    thread.join(timeout=5)

    if thread.is_alive():
        logging.debug("The Rabbitmq thread is still running. Let's ignore it and continue shutdown…")
