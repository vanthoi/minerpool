import socket
import utils.config as config
import requests
import io
import csv
import json
import logging
from jobs.createJob import create_job
from mining.activeMinig import active_mining, mining_status


import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)


class MessageType:
    GRADIENT = "gradient"
    REQUESTFILE = "requestFile"
    REQUESTJOB = "requestJob"


def read_csv_and_parse(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        file_like_object = io.StringIO(response.text)
        csv_reader = csv.reader(file_like_object)

        next(csv_reader, None)

        file_hashes = {}
        for row in csv_reader:
            if len(row) == 2:
                file_url, sha256_hash = row
                file_hashes[sha256_hash] = {
                    "wallet": 0,
                    "downloaded": 0,
                    "last_active": 0,
                    "gradient": 0,
                    "location": 0,
                    "url": file_url,
                }
            else:
                logging.info(f"Skipping invalid row: {row}")

        return file_hashes

    except requests.HTTPError as e:
        print(f"HTTP request error: {e}")
        return None
    except Exception as e:
        print(f"read_csv_and_parse An error occurred: {e}")
        return None


def request_job(wallet_id, message_type):
    try:
        if message_type != MessageType.REQUESTJOB:
            raise ValueError("Invalid message type")

        data = {
            "type": message_type,
            "content": {
                "wallet_id": wallet_id,
            },
        }

        serialized_data = json.dumps(data)

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        client.settimeout(10)
        client.connect((config.INODE_IP, config.INODE_PORT))

        client.sendall(serialized_data.encode("utf-8"))

        response = client.recv(config.BUFFER_SIZE)

        if not response:
            logging.info("Received an empty response from the server")
            return None

        decoded_response = response.decode("utf-8")

        response_data = json.loads(decoded_response)

        hash_url = response_data.get("hash")

        if not hash_url:
            raise ValueError("Received invalid hash URL")

        file_hashes = read_csv_and_parse(hash_url)

        if file_hashes:
            job_id = response_data.get("jobname")
            value = create_job(job_id, file_hashes)
            if value:
                result = active_mining(value)
                status = mining_status(True)
                print("result", result, status)
            else:
                raise RuntimeError("Failed to create job")
            return response_data
        else:
            raise RuntimeError("Failed to create job due to empty file hashes")

    except socket.timeout:
        logging.info(f"Connection timed out")
    except socket.error as e:
        logging.info(f"Socket error: {e}")
    except json.JSONDecodeError:
        logging.info("Error decoding JSON")
    except ValueError as ve:
        logging.info(ve)
    except Exception as e:
        logging.info(f"request_job An unexpected error occurred: {e}")
    finally:
        if "client" in locals():
            client.close()

    return None
