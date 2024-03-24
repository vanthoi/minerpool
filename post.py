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


class MessageType:
    VALIDATEMODEL = "validateModel"
    UPDATEMODEL = "updateModel"


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)

logging.getLogger("websockets").setLevel(logging.INFO)


from utils.pick import pick_model_for_processing

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


def model_processing_thread(queue, interval=60):
    logging.info("Model processing thread started")
    while True:
        model_data = pick_model_for_processing()
        if model_data:
            logging.debug(f"Model data received: {model_data}")
            queue.put_nowait(model_data)
            logging.debug(f"Model data queued: {model_data}")
        time.sleep(interval)


async def connect_to_server(uri, queue, wallet_address):
    should_reconnect = True
    while should_reconnect:
        try:
            async with websockets.connect(uri) as websocket:
                websockets_dict[uri] = websocket
                logging.info(f"Connected to {uri}")

                async def send_messages():
                    nonlocal should_reconnect

                    while True:
                        try:
                            job_id = await asyncio.wait_for(queue.get(), timeout=30)
                        except asyncio.TimeoutError:
                            logging.warning(f"No job was received for {uri}")
                            continue

                        if job_id is None:
                            should_reconnect = False
                            break

                        message = json.dumps(
                            {
                                "job_id": job_id,
                                "miner_pool_wallet": config.MINERPOOL_WALLET_ADDRESS,
                                "validator_wallet": "none",
                                "job_details": "Job completed",
                                "type": MessageType.VALIDATEMODEL,
                            }
                        )

                        ws = websockets_dict.get(uri)
                        if ws and ws.open:
                            try:
                                if not check_model_record(job_id, wallet_address):
                                    await ws.send(message)
                                    logging.debug(f"Sent JSON message to {uri}")
                            except Exception as e:
                                logging.error(f"Error in sending to {uri}: {e}")
                                websockets_dict.pop(uri, None)
                                break
                        else:
                            logging.error("WebSocket not found in websockets_dict")
                            websockets_dict.pop(uri, None)
                            break

                async def receive_messages():
                    while True:
                        try:
                            if websocket.open:
                                incoming_message = await websocket.recv()
                                logging.info(
                                    f"Received message from server: {incoming_message}"
                                )
                                parsed_message = json.loads(incoming_message)
                                message_type = parsed_message.get("type")

                                if message_type == MessageType.UPDATEMODEL:
                                    job_id = parsed_message.get("job_id")
                                    validator_wallet = parsed_message.get(
                                        "validator_wallet"
                                    )
                                    percentage = read_wallet(validator_wallet)

                                    update = update_model_record(
                                        job_id, percentage, validator_wallet
                                    )
                                    print(
                                        "percentage",
                                        percentage,
                                        job_id,
                                        validator_wallet,
                                    )

                        except websockets.ConnectionClosed:
                            break

                send_task = asyncio.create_task(send_messages())
                receive_task = asyncio.create_task(receive_messages())
                await asyncio.gather(send_task, receive_task)

        except Exception as e:
            logging.error(
                f"connect_to_server Error with WebSocket connection to {uri}: {e}"
            )
            websockets_dict.pop(uri, None)

        if should_reconnect:
            await asyncio.sleep(10)
        else:
            logging.info("Exiting without reconnecting as job_id is None")


def start_connection(uri, queue, wallet_address):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Now, run the async connection function in this new event loop
    loop.run_until_complete(connect_to_server(uri, queue, wallet_address))
    loop.close()


def fetch_peer_periodically(peers_queue, interval=20):
    while True:
        logging.info("Fetching peers...")
        # vals = fetch_validators(config.INODE_VALIDATOR_LIST)
        # save_valid_peers_to_json(vals)
        peers = read_peers("peers.json")
        print("peers", peers)
        if peers:
            peers_queue.put(peers)
        time.sleep(interval)


def main():
    try:
        message_queue = asyncio.Queue()
        peers_queue = queue.Queue()
        active_connections = {}

        peer_thread = threading.Thread(
            target=fetch_peer_periodically, args=(peers_queue,), daemon=True
        )
        peer_thread.start()

        model_thread = threading.Thread(
            target=model_processing_thread, args=(message_queue,), daemon=True
        )
        model_thread.start()

        while True:
            try:
                try:
                    new_peers = peers_queue.get(timeout=10)
                except queue.Empty:
                    continue

                for wallet_address, uri in new_peers:
                    if uri not in active_connections:

                        thread = threading.Thread(
                            target=start_connection,
                            daemon=True,
                            args=(uri, message_queue, wallet_address),
                        )
                        thread.start()
                        active_connections[uri] = thread
                        logging.info(f"Started new connection thread for {uri}")

            except KeyboardInterrupt:
                logging.info("Shutting down...")
                sys.exit(0)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

    # finally:
    #     peer_thread.join()
    #     model_thread.join()
    #     for thread in active_connections.values():
    #         thread.join()


if __name__ == "__main__":
    if not test_api_connection(config.INODE_VALIDATOR_LIST):
        logging.error("Failed to establish API connection. Exiting...")
        sys.exit(1)
    if not test_redis_connection():
        logging.error("Failed to establish Redis connection. Exiting...")
        sys.exit(2)
    try:
        asyncio.new_event_loop().run_until_complete(main())
    except:
        logging.info("Shutting down Connect.py due to KeyboardInterrupt.")
