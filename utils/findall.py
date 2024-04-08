from database.database import r, test_redis_connection
import json
import logging
from tabulate import tabulate


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def fetch_and_process_miners():
    try:
        if not test_redis_connection():
            logging.error("Redis connection is not established.")
            return None

        miners_list = r.hgetall("miners_list")
        pool_owner_details = r.hgetall("pool_owner")
    except Exception as e:
        logging.error(f"Error fetching data from Redis: {e}")
        return

    total_balance = 0.0
    table_data = []

    # Process miners
    for wallet_address, miner_details in miners_list.items():
        try:

            wallet_address = (
                wallet_address.decode("utf-8")
                if isinstance(wallet_address, bytes)
                else wallet_address
            )

            miner_details = (
                miner_details.decode("utf-8")
                if isinstance(miner_details, bytes)
                else miner_details
            )
            details = json.loads(miner_details)

            total_balance += details["balance"]
            table_data.append([wallet_address, details["balance"]])
        except json.JSONDecodeError:
            logging.warning(
                f"Error decoding JSON for wallet address {wallet_address}. Skipping..."
            )
        except KeyError:
            logging.warning(
                f"Error: 'balance' key not found in data for wallet address {wallet_address}. Skipping..."
            )
        except Exception as e:
            logging.error(
                f"Unexpected error processing miner details for wallet address {wallet_address}: {e}"
            )

    # Process pool owner
    pool_owner_balance = 0.0
    if pool_owner_details:
        try:
            pool_owner = {
                k.decode("utf-8") if isinstance(k, bytes) else k: (
                    v.decode("utf-8") if isinstance(v, bytes) else v
                )
                for k, v in pool_owner_details.items()
            }
            pool_owner_balance = float(pool_owner.get("amount", 0))
            total_balance += pool_owner_balance
            table_data.append(
                [
                    "Pool Owner (" + pool_owner["wallet_address"] + ")",
                    pool_owner_balance,
                ]
            )
        except Exception as e:
            logging.error(f"Error processing pool owner details: {e}")

    print(tabulate(table_data, headers=["Wallet Address", "Balance"], tablefmt="grid"))
    logging.info(
        f"Total balance of all users (excluding pool owner): {total_balance - pool_owner_balance}"
    )
    logging.info(f"Pool owner balance: {pool_owner_balance}")
    logging.info(f"Combined total balance: {total_balance}")


if __name__ == "__main__":
    fetch_and_process_miners()
