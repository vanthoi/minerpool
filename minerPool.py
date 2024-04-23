import threading
import json
import utils.config as config
import asyncio
import websockets
from datetime import datetime, timedelta, date
import time
import sys
from pydantic import BaseModel
from database.mongodb import test_db_connection
from database.database import test_redis_connection
from api.api_client import test_api_connection
import os
import logging
from dotenv import load_dotenv
from utils.userdata import check_active_users, check_wallet_active
import base58
from transactions.updateGradient import clean_job_folder

active_connections = set()
MAX_CONNECTIONS = 1500

dotenv_path = ".env"
load_dotenv(dotenv_path)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)

from jobs.updateJob import update_jobs
from transactions.updateGradient import update_gradient
from transactions.transactionBatch import (
    add_transaction_to_batch,
    process_all_transactions,
)
from jobs.fetchBlock import (
    process_transactions,
    deduct_balance_from_wallet,
    get_balance_from_wallet,
    get_balance_poolowner,
    deduct_balance_from_poolowner,
    get_miner_TransactionsPushed,
)


from fastapi import FastAPI, HTTPException, Query, Request, Depends
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import uvicorn
from fastapi.middleware.cors import CORSMiddleware

minerpool_private_key = os.getenv("PRIVATEKEY")
if minerpool_private_key is None:
    print(
        "Minerpool PRIVATEKEY not found. Please check readme.md to set the PRIVATEKEY in the .env variable."
    )
    exit(0)

minerpool_wallet_address = os.getenv("MINERPOOLWALLETADDRESS")
if minerpool_wallet_address is None:
    print(
        "Minerpool MINERPOOLWALLETADDRESS not found. Please check readme.md to set the MINERPOOLWALLETADDRESS in the .env variable."
    )
    exit(1)

minerpool_reward_address = os.getenv("MINERPOOLREWARDWALLETADDRESS")
if minerpool_reward_address is None:
    print(
        "Minerpool MINERPOOLREWARDWALLETADDRESS not found. Please check readme.md to set the MINERPOOLREWARDWALLETADDRESS in the .env variable."
    )
    exit(2)


class MessageType:
    GRADIENT = "gradient"
    REQUESTFILE = "requestFile"
    REQUESTJOB = "requestJob"


app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_fastapi():
    uvicorn.run(app, host=config.FAST_API_URL, port=config.FAST_API_PORT)


last_request_times = {}


class DeductBalanceRequest(BaseModel):
    wallet_address: str
    amount_to_deduct: float


class DeductBalancePool(BaseModel):
    amount_to_deduct: float


@app.get("/active-miners")
@limiter.limit(config.RATE_LIMIT1)
def get_active_users(request: Request):
    try:
        return {"active_miners": check_active_users()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/check-active/{wallet_address}")
@limiter.limit(config.RATE_LIMIT1)
def get_wallet_active(request: Request, wallet_address: str):
    try:
        return check_wallet_active(wallet_address)
    except Exception as e:
        status_code = 400 if "not found" in str(e).lower() else 500
        raise HTTPException(status_code=status_code, detail=str(e))


@app.get("/get_balance/")
@limiter.limit(config.RATE_LIMIT1)
async def get_balance(request: Request, wallet_address: str):
    if not wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address must be provided")

    balance = get_balance_from_wallet(wallet_address)
    if isinstance(balance, str) and balance.startswith("Error"):

        raise HTTPException(
            status_code=404 if "not found" in balance else 400, detail=balance
        )

    return {"balance": balance}


@app.get("/get_balance_poolowner/")
@limiter.limit(config.RATE_LIMIT1)
async def poolowner_get_balance(request: Request):

    balance = get_balance_poolowner()
    if isinstance(balance, str) and balance.startswith("Error"):

        raise HTTPException(
            status_code=404 if "not found" in balance else 400, detail=balance
        )

    return {"balance": balance}


@app.post("/deduct_balance/")
@limiter.limit(config.RATE_LIMIT2)
async def deduct_balance(
    request: Request,
    deduct_request: DeductBalanceRequest,
):
    result, response = deduct_balance_from_wallet(
        deduct_request.wallet_address, deduct_request.amount_to_deduct
    )
    if result is None:
        raise HTTPException(status_code=400, detail=response)
    else:
        add_transaction_to_batch(
            deduct_request.wallet_address, response, "deduct_balance"
        )
        return {"message": f"Amount deducted successfully: {response}"}


@app.post("/poolowner_deduct_balance/")
@limiter.limit(config.RATE_LIMIT1)
async def poolowner_deduct_balance(
    request: Request,
    deduct_request: DeductBalancePool,
):
    result, response, wallet_address = deduct_balance_from_poolowner(
        deduct_request.amount_to_deduct
    )
    if result is None:
        raise HTTPException(status_code=400, detail=response)
    else:
        add_transaction_to_batch(wallet_address, response, "pool_deduct_balance")
        return {"message": f"Amount deducted successfully: {response}"}


@app.get("/latestwithdraws/")
@limiter.limit(config.RATE_LIMIT1)
async def latest_withdraws(request: Request, wallet_address: str):
    if not wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address must be provided")

    result = get_miner_TransactionsPushed(wallet_address)

    if not result.get("success", False):
        message = result.get("message", "An unexpected error occurred")
        status_code = 404 if "No details found" in message else 500
        raise HTTPException(status_code=status_code, detail=message)
    return result.get("data", {})


async def periodic_process_transactions():
    while True:
        process_transactions()
        await asyncio.sleep(config.CHECK_INTERVAL)


def save_file_chunk_in_job_folder(chunk, folder_name, file_name, is_first_chunk):
    folder_name = os.path.basename(folder_name)

    folder_path = os.path.join("Job", folder_name)
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, file_name)

    with open(file_path, "ab" if not is_first_chunk else "wb") as file:
        file.write(chunk)


def update_balance_periodically():
    try:
        while True:
            process_all_transactions()
            time.sleep(60)
    except Exception as e:
        print(f"Error in update_balance_periodically: {e}")


def is_valid_address(address: str) -> bool:
    try:
        _ = bytes.fromhex(address)
        return len(address) == 128
    except ValueError:
        try:
            decoded_bytes = base58.b58decode(address)
            if len(decoded_bytes) != 33:
                return False
            specifier = decoded_bytes[0]
            if specifier not in [42, 43]:
                return False
            return True
        except ValueError:

            return False
    except Exception as e:
        print(f"Error validating address: {e}")
        return False


async def handle_client(websocket, path):
    global active_connections
    num_active_connections = len(active_connections)
    logging.info(f"active_connections {num_active_connections}")
    if len(active_connections) >= MAX_CONNECTIONS:
        await websocket.close(reason="ERROR: Connection limit reached")
        return
    active_connections.add(websocket)
    try:
        async for message in websocket:
            try:
                parsed_message = json.loads(message)
                message_type = parsed_message.get("type")
                wallet_address = parsed_message.get("wallet_address")

                if wallet_address is not None and not is_valid_address(wallet_address):
                    await websocket.send("ERROR: Invalid wallet address")
                    await websocket.close()
                    active_connections.discard(websocket)
                    continue

                if message_type == "gradient":
                    folder_name = parsed_message.get("folder_name")
                    job_name = parsed_message.get("job_name")
                    wallet_address = parsed_message.get("wallet_address")
                    file_name = parsed_message.get("file_name")
                    just_name = parsed_message.get("just_name")
                    file_chunk = parsed_message.get("file_data").encode("latin1")

                    if file_chunk == b"EOF":
                        # print(f"Completed receiving {file_name}")

                        success, message = update_gradient(
                            job_name, just_name, "1", wallet_address, file_name
                        )
                        if success:
                            await websocket.send("SUCCESS: GRADIENT ACCEPTED")
                            await websocket.close()
                            active_connections.discard(websocket)
                        else:
                            await websocket.send(f"ERROR: {message}")
                            await websocket.close()
                            active_connections.discard(websocket)
                    else:
                        is_first_chunk = parsed_message.get("is_first_chunk", False)
                        save_file_chunk_in_job_folder(
                            file_chunk, folder_name, file_name, is_first_chunk
                        )

                elif message_type == "requestFile":
                    wallet_address = parsed_message.get("wallet_address")

                    # Check if the wallet_address is in cooldown
                    current_time = datetime.utcnow()
                    if wallet_address in last_request_times:
                        last_request_time = last_request_times[wallet_address]
                        if current_time - last_request_time < timedelta(seconds=20):
                            await websocket.send(
                                "ERROR: Cooldown period not yet passed. Please wait."
                            )
                            await websocket.close()
                            active_connections.discard(websocket)
                            continue

                    # Update the last request time
                    last_request_times[wallet_address] = current_time

                    file = update_jobs(wallet_address)
                    if file is None or (file[0] is None and file[1] is None):
                        await websocket.send("ERROR: NO JOB FOUND!")
                        await websocket.close()
                        active_connections.discard(websocket)
                    else:
                        await websocket.send(json.dumps(file))

                elif message_type == "ping":
                    await websocket.send("SUCCESS: ping")

                else:
                    await websocket.send("ERROR: Unknown message type")
                    await websocket.close()
                    active_connections.discard(websocket)

            except json.JSONDecodeError:
                await websocket.send("ERROR: Invalid message format")
                await websocket.close()
                active_connections.discard(websocket)

    except websockets.ConnectionClosed:
        logging.error("Client disconnected")
        active_connections.discard(websocket)
        # Handle disconnection
    finally:
        await websocket.wait_closed()
        # logging.info("WebSocket connection closed by the client.")
        # logging.info(f"Before Client disconnected {len(active_connections)}")
        logging.info("Client disconnected")
        active_connections.discard(websocket)
        # logging.info(f"After Client disconnected {len(active_connections)}")


async def main():
    clean_job_folder()
    logging.info("Requesting Job in MinerPool")
    # create_db("History")
    balance_thread = threading.Thread(target=update_balance_periodically, daemon=True)
    fastapi_thread = threading.Thread(daemon=True, target=run_fastapi)
    fastapi_thread.start()
    balance_thread.start()
    start_server = websockets.serve(handle_client, config.IP, config.PORT)
    await start_server

    # Start the periodic task
    periodic_task = asyncio.create_task(periodic_process_transactions())

    try:
        await asyncio.Future()

    finally:
        logging.info("MinerPool shutdown process starting.")
        periodic_task.cancel()
        await periodic_task
        logging.info("MinerPool shutdown process complete.")


if __name__ == "__main__":
    if not test_db_connection():
        logging.error("Failed to establish MongoDB connection. Exiting...")
        sys.exit(1)
    if not test_redis_connection():
        logging.error("Failed to establish Redis connection. Exiting...")
        sys.exit(2)
    if not test_api_connection(config.API_URL):
        logging.error("Failed to establish API connection. Exiting...")
        sys.exit(3)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down MinerPool due to KeyboardInterrupt.")
