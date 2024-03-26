import asyncio
import websockets
import threading
import json
import time
import logging
import utils.config as config
import requests
from datetime import datetime, timedelta
import sys
import queue
from core.model import update_model_record, check_model_record
from api.api_client import test_api_connection
from database.database import test_redis_connection
from utils.pick2 import pick_model_for_processing


class MessageType:
    VALIDATEMODEL = "validateModel"
    UPDATEMODEL = "updateModel"


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)

logging.getLogger("websockets").setLevel(logging.INFO)


websockets_dict = {}


def read_peers(file_path):
    valid_peers = []
    try:
        with open(file_path, "r") as file:
            data = json.load(file)

            for wallet_address, details in data.items():
                ip = details.get("IP")
                port = details.get("Port")

                if ip and port:
                    uri = f"ws://{ip}:{port}"
                    # Append a tuple of (wallet_address, uri)
                    valid_peers.append((wallet_address, uri))
                else:
                    logging.error(f"Missing IP or Port for wallet {wallet_address}")

    except json.JSONDecodeError:
        logging.error("read_peers Error decoding JSON from the file")
    except FileNotFoundError:
        logging.error(f"read_peers File not found: {file_path}")

    return valid_peers


def read_wallet(wallet_address):
    try:
        with open("peers.json", "r") as file:
            data = json.load(file)

            for address, details in data.items():
                if address == wallet_address:
                    percentage = details.get("Percentage")
                    if percentage is not None:
                        logging.info(
                            f"Wallet: {wallet_address}, Percentage: {percentage}%"
                        )
                        return percentage
                    else:
                        logging.error(f"Percentage missing for wallet {wallet_address}")
                        return None

        logging.error(f"Wallet address {wallet_address} not found.")
        return None

    except json.JSONDecodeError:
        logging.error("read_wallet Error decoding JSON from the file")
        return None
    except FileNotFoundError:
        logging.error("read_wallet File not found: peer.json")
        return None


def save_valid_peers_to_json(vals):
    current_time = datetime.utcnow()
    four_hours_ago = current_time - timedelta(hours=4)
    valid_peers = {}

    for wallet_address, details in vals.items():
        try:
            details_dict = json.loads(details)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON for wallet {wallet_address}: {e}")
            continue

        percentage = details_dict.get("percentage", 0)
        ping_time = details_dict.get("ping")

        if percentage >= 1:
            if ping_time and ping_time != "0":
                try:
                    ping_datetime = datetime.fromisoformat(ping_time)
                    if ping_datetime >= four_hours_ago:
                        valid_peers[wallet_address] = {
                            "Percentage": percentage,
                            "IP": details_dict["ip"],
                            "Port": details_dict["port"],
                        }
                    else:
                        logging.info(
                            f"Wallet {wallet_address} ping time is older than four hours. Ping time: {ping_time}"
                        )
                except ValueError:
                    logging.error(
                        f"Invalid date format for wallet {wallet_address}. Ping time: {ping_time}"
                    )
            else:
                logging.info(
                    f"Wallet {wallet_address} has no valid ping time (found: '{ping_time}')."
                )
        else:
            logging.debug(
                f"Wallet {wallet_address} has a percentage lower than 1% (found: {percentage})."
            )

    with open("peers.json", "w") as file:
        json.dump(valid_peers, file, indent=4)
        logging.info("Valid peers have been saved to peers.json.")


def fetch_validators(validators):
    try:
        response = requests.get(validators)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as errh:
        logging.error(f"Http Error:", {errh})
    except requests.exceptions.ConnectionError as errc:
        logging.error(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        logging.error(f"Timeout Error:", {errt})
    except requests.exceptions.RequestException as err:
        logging.error(f"OOps: Something Else", {err})
    return []


def fetch_peer_periodically(interval=600):
    while True:

        vals = fetch_validators(config.INODE_VALIDATOR_LIST)
        save_valid_peers_to_json(vals)

        time.sleep(interval)


async def send_message_to_validator(validator_info, message):
    uri = validator_info
    try:
        async with websockets.connect(uri) as websocket:
            print("Now connected with", uri)
            await websocket.send(message)
            response = await asyncio.wait_for(websocket.recv(), timeout=20)
            await websocket.close()
            return response
    except asyncio.TimeoutError:
        print(f"Timeout when sending message to {uri}")
    except Exception as e:
        print(f"Error when sending message to {uri}: {e}")
    return None


async def main():
    while True:
        try:
            if not test_api_connection(config.INODE_VALIDATOR_LIST):
                logging.error("Failed to establish API connection. Exiting...")
                break

            model = pick_model_for_processing()
            if not model:
                print("No model found for processing. Retrying...")
                await asyncio.sleep(60)
                continue

            peers = read_peers("peers.json")
            if not peers:
                print("No peers found or error reading peers. Retrying...")
                await asyncio.sleep(60)
                continue

            temp_peers = [
                (validator_id, validator_info)
                for validator_id, validator_info in peers
                if validator_id not in model["value"].get("validators", [])
            ]
            processed_validators = set()

            for validator_info in temp_peers[:]:
                validator_id, validator_uri = validator_info
                logging.info(
                    f"Processing validator {validator_id} with URI {validator_uri}"
                )
                if validator_id in processed_validators:
                    continue

                message = json.dumps(
                    {
                        "job_id": model["key"],
                        "miner_pool_wallet": config.MINERPOOL_WALLET_ADDRESS,
                        "validator_wallet": "none",
                        "job_details": "Job completed",
                        "type": MessageType.VALIDATEMODEL,
                    }
                )

                try:
                    response = await send_message_to_validator(validator_uri, message)
                    if response in [
                        "Invalid message format",
                        "Error processing message",
                    ]:
                        logging.error(
                            f"Validator {validator_id} responded with error: {response}"
                        )
                        continue

                    parsed_message = json.loads(response)
                    message_type = parsed_message.get("type")

                    if message_type == MessageType.UPDATEMODEL:
                        job_id = parsed_message.get("job_id")
                        validator_wallet = parsed_message.get("validator_wallet")
                        percentage = read_wallet(validator_wallet)

                        update = update_model_record(
                            job_id, percentage, validator_wallet
                        )
                        if update:
                            print(
                                f"Model updated successfully for validator {validator_wallet}."
                            )
                        else:
                            print(
                                f"Failed to update model for validator {validator_wallet}."
                            )
                    processed_validators.add(validator_id)
                    temp_peers.remove(validator_info)

                    temp_peers = [
                        peer
                        for peer in temp_peers
                        if peer[0] not in processed_validators
                    ]

                except json.JSONDecodeError:
                    logging.error(
                        f"Failed to parse JSON response from validator {validator_id}."
                    )
                except Exception as e:
                    logging.error(
                        f"An error occurred while processing validator {validator_id}: {str(e)}"
                    )

                if not temp_peers:
                    break

            await asyncio.sleep(120)

        except Exception as e:
            logging.error(f"An unexpected error occurred: {str(e)}")
            await asyncio.sleep(190)


if __name__ == "__main__":
    balance_thread = threading.Thread(target=fetch_peer_periodically, daemon=True)
    balance_thread.start()
    if not test_redis_connection():
        logging.error("Failed to establish Redis connection. Exiting...")
        sys.exit(0)

    try:
        asyncio.run(main())
    except Exception as e:
        print("Unexpected error:", e)
    except KeyboardInterrupt:
        logging.info("Shutting down due to KeyboardInterrupt.")
