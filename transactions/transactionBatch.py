import redis
import uuid
from database.database import r
import logging
import json
from datetime import datetime
import utils.config as config
import asyncio
from database.mongodb import (
    minerTransactionsCollection,
    minerTransactionsPushed,
    errorTransaction,
    catchTransaction,
    pushHistory,
)
from api.push import send_transaction
from decimal import Decimal, ROUND_DOWN
from api.api_client import test_api_connection


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)


async def sign_and_push_transactions(transactions):
    try:
        for transaction in transactions:
            private_key = config.PRIVATEKEY
            wallet_address = transaction.get("wallet_address")
            transaction_type = transaction.get("type")
            id = transaction.get("id")
            # print("id", id)
            new_balance = transaction.get("new_balance")
            amounts = "{:.8f}".format(float(new_balance))

            message = ""
            try:
                pushHistory.update_one(
                    {"wallet_address": wallet_address},
                    {
                        "$push": {
                            "transactions": {
                                "id": id,
                                "transaction_type": transaction_type,
                                "amount": amounts,
                                "timestamp": datetime.utcnow(),
                            }
                        }
                    },
                    upsert=True,
                )
                transaction_hash = await send_transaction(
                    private_key, wallet_address, amounts, message
                )
                if transaction_hash:
                    logging.info(f"transaction_hash: {transaction_hash}")
                    minerTransactionsPushed.update_one(
                        {"wallet_address": wallet_address},
                        {
                            "$push": {
                                "transactions": {
                                    "id": id,
                                    "hash": transaction_hash,
                                    "amount": amounts,
                                    "timestamp": datetime.utcnow(),
                                    "transaction_type": transaction_type,
                                }
                            }
                        },
                        upsert=True,
                    )
                else:
                    logging.error(
                        f"Transaction failed for wallet address {wallet_address}. No hash was returned."
                    )
                    errorTransaction.update_one(
                        {"wallet_address": wallet_address},
                        {
                            "$push": {
                                "transactions": {
                                    "id": id,
                                    "error": transaction_hash,
                                    "amount": amounts,
                                    "timestamp": datetime.utcnow(),
                                }
                            }
                        },
                        upsert=True,
                    )
            except Exception as e:
                logging.error(f"Caught exception: {str(e)}")
                error_message = str(e)
                if "You can spend max 255 inputs" in error_message:
                    num_inputs = int(error_message.split("not ")[-1])
                    max_inputs = 255
                    num_splits = -(-num_inputs // max_inputs)  # Ceiling division
                    split_amount = float(amounts) / num_splits
                    logging.info(
                        f"Splitting transaction for {wallet_address} into {num_splits} parts due to UTXO limit."
                    )
                    for _ in range(num_splits):
                        add_transaction_to_batch(
                            wallet_address,
                            split_amount,
                            f"utxos_split_{transaction_type}",
                        )

                    # Remove the original transaction that exceeded the input limit
                    minerTransactionsCollection.delete_one({"id": id})
                elif "URI Too Long for url:" in error_message:
                    split_amount = float(amounts) / 2
                    logging.info(
                        f"Splitting transaction for {wallet_address} into 2 parts due to URI length limit."
                    )
                    for _ in range(2):
                        add_transaction_to_batch(
                            wallet_address,
                            split_amount,
                            f"url_split_{transaction_type}",
                        )

                    minerTransactionsCollection.delete_one({"id": id})
                elif "Request-URI Too Large for url:" in error_message:
                    split_amount = float(amounts) / 2
                    logging.info(
                        f"Splitting transaction for {wallet_address} into 2 parts due to URI length limit."
                    )
                    for _ in range(2):
                        add_transaction_to_batch(
                            wallet_address,
                            split_amount,
                            f"Request-URI{transaction_type}",
                        )

                    minerTransactionsCollection.delete_one({"id": id})
                elif (
                    "HTTPConnectionPool" in error_message
                    or "HTTPSConnectionPool" in error_message
                ):
                    logging.info(
                        f"Failed to connect with blockchain so adding transaction for reprocessing {wallet_address} ."
                    )
                    add_transaction_to_batch(
                        wallet_address, amounts, f"retry_HTTPConnectionPool"
                    )
                    minerTransactionsCollection.delete_one({"id": id})
                else:
                    logging.error(
                        f"Error during transaction processing for {wallet_address}: {error_message}"
                    )
                    catchTransaction.update_one(
                        {"wallet_address": wallet_address},
                        {
                            "$push": {
                                "transactions": {
                                    "id": id,
                                    "error": error_message,
                                    "amount": amounts,
                                    "timestamp": datetime.utcnow(),
                                }
                            }
                        },
                        upsert=True,
                    )
                    add_transaction_to_batch(
                        wallet_address, amounts, f"CatchError_{id}"
                    )
                    minerTransactionsCollection.delete_one({"id": id})

        # Remove successfully processed transactions from the MongoDB collection
        if transactions:
            transactions_ids = [t.get("id") for t in transactions]
            minerTransactionsCollection.delete_many({"id": {"$in": transactions_ids}})
    except Exception as e:
        logging.error(f"Error during signing and pushing transactions: {e}")


def process_all_transactions():
    if not test_api_connection(config.API_URL):
        logging.warning("Blockchain may be down, no transactions pushed.")
        return
    try:
        # Fetch all transactions and sort them by timestamp
        all_transactions = list(minerTransactionsCollection.find().sort("timestamp", 1))

        # Deduplicate transactions, keeping only the latest for each wallet address
        unique_transactions = {}
        for transaction in all_transactions:
            wallet_address = transaction["wallet_address"]
            unique_transactions[wallet_address] = transaction

        # Get the first 5 unique transactions based on the sorted order by timestamp
        pending_transactions = list(unique_transactions.values())[:15]

        if pending_transactions:
            # Since sign_and_push_transactions is an async function,
            # we need to run it inside an event loop
            asyncio.run(sign_and_push_transactions(pending_transactions))

        else:
            print("No pending transactions to process.")
    except Exception as e:
        print(f"Error during process_all_transactions_mongodb: {e}")


def add_transaction_to_batch(wallet_address, tokens_to_distribute, rewardType):
    try:

        # Create the transaction document
        transaction_document = {
            "id": str(uuid.uuid4()),
            "wallet_address": str(wallet_address),
            "new_balance": float(tokens_to_distribute),
            "timestamp": datetime.utcnow(),
            "type": rewardType,
        }

        # Insert the document into the collection
        minerTransactionsCollection.insert_one(transaction_document)

    except Exception as e:
        print(f"Error add_transaction_to_batch: {e}")
