from database.database import r, test_redis_connection
import json
import logging
from tabulate import tabulate
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def parse_datetime(time_str_or_int):
    formats = ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]
    if isinstance(time_str_or_int, int):
        # Assume it's a timestamp
        return datetime.fromtimestamp(time_str_or_int)
    for fmt in formats:
        try:
            return datetime.strptime(time_str_or_int, fmt)
        except ValueError:
            continue
    raise ValueError(f"Time data '{time_str_or_int}' does not match any known format")


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
    active_user_count = 0
    current_time = datetime.utcnow()
    table_data = []

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
            last_active_time = parse_datetime(details["last_active_time"])
            active_status = (
                "Yes"
                if (current_time - last_active_time) < timedelta(minutes=30)
                else "No"
            )
            if active_status == "Yes":
                active_user_count += 1

            table_data.append([wallet_address, details["balance"], active_status])
        except json.JSONDecodeError:
            logging.warning(
                f"Error decoding JSON for wallet address {wallet_address}. Skipping..."
            )
        except KeyError:
            logging.warning(
                f"Missing key in data for wallet address {wallet_address}. Skipping..."
            )
        except ValueError as e:
            logging.error(
                f"Error parsing date for wallet address {wallet_address}: {e}"
            )
        except Exception as e:
            logging.error(f"Unexpected error for wallet address {wallet_address}: {e}")

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
                    "N/A",
                ]
            )
        except Exception as e:
            logging.error(f"Error processing pool owner details: {e}")

    print(
        tabulate(
            table_data,
            headers=["Wallet Address", "Balance", "Active in Last 30min"],
            tablefmt="grid",
        )
    )
    logging.info(
        f"Total balance of all users (excluding pool owner): {total_balance - pool_owner_balance}"
    )
    logging.info(f"Pool owner balance: {pool_owner_balance}")
    logging.info(f"Combined total balance: {total_balance}")
    logging.info(f"Total active users in the last 30 minutes: {active_user_count}")


if __name__ == "__main__":
    fetch_and_process_miners()
