from database.database import r
import json
from database.leveldatabase import store_in_db, retrieve_from_db
from database.redis_client import set_last_block_height, get_last_block_height
from database.mongodb import minerProcessedTransaction, minerTransactionsPushed
from pymongo.errors import PyMongoError
import utils.config as config
import logging
from datetime import datetime
from api.api_client import fetch_block


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)


def get_balance_from_wallet(wallet_address):
    try:
        miner_data_json = r.hget("miners_list", wallet_address)
        if miner_data_json is None:
            return "Error: Wallet address not found."
        miner_data = json.loads(miner_data_json)

        balance = miner_data.get("balance")
        if balance is not None:
            return balance
        else:
            return "Error: Balance not found for the given wallet address."
    except Exception as e:
        return f"Error: get_balance_from_wallet An unexpected error occurred - {str(e)}"


def get_balance_poolowner():
    try:
        pool_owner_data = r.hgetall("pool_owner")
        if pool_owner_data:
            balance = pool_owner_data.get("amount")
            if balance is not None:
                return balance
            else:
                return "Error: Balance not found for the pool owner."
        else:
            return "Error: Pool owner data not found."
    except Exception as e:
        return f"Error: get_balance_poolowner An unexpected error occurred - {str(e)}"


def deduct_balance_from_wallet(wallet_address, amount_to_deduct):
    try:
        miner_data_json = r.hget("miners_list", wallet_address)
        if miner_data_json is None:
            return None, "Error: Wallet address not found."
        miner_data = json.loads(miner_data_json)
        balance = miner_data.get("balance", 0)
        if balance is None or balance < 0.001:
            return None, "Error: Insufficient balance for deduction."

        if amount_to_deduct < 0.001 or len(str(amount_to_deduct).split(".")[-1]) > 8:
            return (
                None,
                "Error: Invalid deduction amount. Must be at least 0.001 and have no more than 8 decimal places.",
            )
        new_balance = balance - amount_to_deduct
        if new_balance < 0:
            return None, "Error: Deduction amount exceeds current balance."
        miner_data["balance"] = round(new_balance, 8)
        r.hset("miners_list", wallet_address, json.dumps(miner_data))
        return True, round(amount_to_deduct, 8)
    except Exception as e:

        return (
            None,
            f"deduct_balance_from_wallet An unexpected error occurred - {str(e)}",
        )


def deduct_balance_from_poolowner(amount_to_deduct):
    try:
        pool_owner_data = r.hgetall("pool_owner")
        if not pool_owner_data:
            return None, "Error: Pool owner data not found.", None

        current_amount = float(pool_owner_data.get("amount", 0.0))
        wallet_address = pool_owner_data.get("wallet_address", None)

        if wallet_address is None:
            return None, "Error: Wallet address not found.", None

        if amount_to_deduct < 0.001 or len(str(amount_to_deduct).split(".")[-1]) > 8:
            return (
                None,
                "Error: Invalid deduction amount. Must be at least 0.001 and have no more than 8 decimal places.",
                None,
            )

        new_amount = current_amount - amount_to_deduct
        if new_amount < 0:
            return None, "Error: Deduction amount exceeds current balance.", None

        pool_owner_data["amount"] = str(round(new_amount, 8))
        r.hset("pool_owner", mapping=pool_owner_data)

        return True, round(amount_to_deduct, 8), wallet_address
    except Exception as e:
        return (
            None,
            f"deduct_balance_from_poolowner An unexpected error occurred - {str(e)}",
            None,
        )


def get_miner_TransactionsPushed(wallet_address):
    try:
        wallet_details = minerTransactionsPushed.find_one(
            {"wallet_address": wallet_address}
        )
        if wallet_details:
            # Convert ObjectId to string
            wallet_details["_id"] = str(wallet_details["_id"])
            return {"success": True, "data": wallet_details}
        else:
            return {
                "success": False,
                "message": "No details found for the given wallet address.",
            }
    except PyMongoError as e:
        return {
            "success": False,
            "message": "A database error occurred.",
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "message": "An unexpected error occurred.",
            "error": str(e),
        }


def calculate_percentages(total_amount):
    percentages = {"18%": 0, "82%": 0}
    percentages["18%"] = round(total_amount * 0.18, 8)
    percentages["82%"] = round(total_amount * 0.82, 8)
    return percentages


def update_pool_owner(amount):
    try:
        pool_owner_data = r.hgetall("pool_owner")

        if pool_owner_data:
            current_amount = float(pool_owner_data.get("amount", 0.0))
            wallet_address = pool_owner_data.get("wallet_address", None)
        else:
            current_amount = 0.0
            wallet_address = config.MINERPOOL_REWARD_WALLET_ADDRESS

        new_amount = round(current_amount + amount, 8)
        current_time_utc = datetime.utcnow().isoformat()

        r.hset(
            "pool_owner",
            mapping={
                "amount": str(new_amount),
                "last_processed": current_time_utc,
                "wallet_address": wallet_address,
            },
        )

    except Exception as e:
        logging.error(f"update_pool_owner An unexpected error occurred: {e}")


def update_miner_balances(amount, block_range):
    miner_updates = {}
    try:
        miners_data = r.hgetall("miners_list")

        filtered_miners = {}
        total_score = 0

        for miner, data in miners_data.items():
            try:
                miner_data = json.loads(data)
                score = int(miner_data["score"])
                if score > 0:
                    filtered_miners[miner] = miner_data
                    total_score += score
            except (ValueError, json.JSONDecodeError) as e:
                logging.warning(f"Error processing miner {miner}: {e}")

        if total_score == 0:
            raise ValueError("No scores were computed")

        for miner, data in filtered_miners.items():
            try:
                previous_balance = data["balance"]
                score = int(data["score"])
                miner_share = (score / total_score) * amount
                miner_share = round(miner_share, 8)
                data["balance"] = round(data["balance"] + miner_share, 8)
                data["score"] = "0"
                r.hset("miners_list", miner, json.dumps(data))
                miner_updates[miner] = {
                    "previous_balance": previous_balance,
                    "score": score,
                    "added_amount": miner_share,
                    "current_balance": data["balance"],
                }
            except Exception as e:
                logging.error(f"Error updating miner {miner}: {e}")

        store_in_db(block_range, miner_updates)

        retrieve_from_db(block_range)

        logging.info("Balances updated and scores reset.")

    except Exception as e:
        logging.error(f"update_miner_balances An unexpected error occurred: {e}")


def insert_unique_transaction(hash_value):
    try:
        result = minerProcessedTransaction.update_one(
            {"hash": hash_value},
            {"$setOnInsert": {"hash": hash_value}},
            upsert=True,
        )
        if result.upserted_id is not None:
            # logging.info(f"Inserted new transaction with hash: {hash_value}")
            return True
        else:
            logging.info(f"Transaction with hash: {hash_value} already exists.")
            return False
    except PyMongoError as e:
        logging.error(
            f"Failed to insert or check transaction with hash: {hash_value}. Error: {e}"
        )
        return None


def process_all():
    try:
        last_block_height = get_last_block_height()

        if last_block_height is None:
            logging.info("No last block height found in Redis, using hardcoded value.")
            last_block_height = config.TRACK
        else:
            last_block_height += 1

        logging.info(f"Starting processing from block height: {last_block_height}")

        data = fetch_block(
            f"{config.API_URL}/get_blocks_details?offset={last_block_height}&limit=10"
        )

        if data is None or not data["result"]:
            logging.error("No block data retrieved or no new blocks since last check.")
            return None

        total_amount = 0
        first_block_id = data["result"][0]["block"]["id"]
        last_block_idX = data["result"][-1]["block"]["id"]
        last_block_id = None

        for block in data["result"]:
            block_id = block["block"]["id"]
            last_block_id = block_id

            for transaction in block["transactions"]:
                hash_value = transaction["hash"]
                transaction_amount = 0  # Initialize transaction amount

                if transaction.get("transaction_type", "REGULAR") != "REGULAR":
                    continue

                # Collect all input addresses for the current transaction
                input_addresses = [
                    input["address"] for input in transaction.get("inputs", [])
                ]

                # Check if the transaction is relevant and calculate its amount
                for output in transaction["outputs"]:
                    # Check if the output is for the miner pool wallet address, the type is REGULAR, and the output address is not in the transaction's input addresses (not a self-transaction)
                    if (
                        output["address"] == config.MINERPOOL_WALLET_ADDRESS
                        and output["type"] == "REGULAR"
                        and output["address"] not in input_addresses
                    ):
                        transaction_amount += output["amount"]

                # Only proceed if the transaction is relevant and not already processed
                if transaction_amount > 0:
                    if insert_unique_transaction(hash_value):
                        # Add the transaction amount only if it's a new transaction
                        total_amount += transaction_amount
                    else:
                        logging.info(
                            f"Skipping already processed transaction: {hash_value}"
                        )

        if last_block_id is not None:
            set_last_block_height(last_block_id)
        else:
            logging.info("No new blocks to process.")

        if total_amount <= 0:
            logging.info(
                f"No relevant transactions found for {config.MINERPOOL_WALLET_ADDRESS} in the latest blocks."
            )
            return None

        percentages = calculate_percentages(total_amount)
        block_range_str = f"{first_block_id}-{last_block_idX}"

        # print("percentages", percentages, "total_amount", total_amount)

        return percentages, block_range_str

    except Exception as e:
        logging.error(f"An error occurred during process_all: {e}")
        return None


def process_transactions():
    try:
        info = process_all()
        if info is not None:
            percentages, block_range_str = info
            update_miner_balances(percentages["82%"], block_range_str)
            update_pool_owner(percentages["18%"])
        else:
            logging.error("Skipping process_all due to processing error or no data.")
    except ValueError as e:
        logging.error(f"Error fetching block data: {e}")
    except Exception as e:
        logging.error(f"process_transactions An unexpected error occurred: {e}")
