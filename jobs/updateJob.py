import redis
import json
import datetime
import utils.config as config
import logging
from database.database import r
from mining.activeMinig import mining_status
from jobs.requestJob import request_job


import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)


class MessageType:
    DOWNLOADFILE = "downloadFile"
    REQUESTJOB = "requestJob"


def update_jobs(new_wallet_address):
    # print("Inside of update_jobs")
    try:
        current_time = datetime.datetime.utcnow()

        ten_minutes_ago = current_time - datetime.timedelta(minutes=1)

        active_mining_status = r.get("mining_status")

        if active_mining_status in [None, False, "False"]:
            logging.info("No active mining")
            request_job(config.MINERPOOL_WALLET_ADDRESS, MessageType.REQUESTJOB)
            logging.info("New Job was requested from the Inode")
            return None, None

        active_mining_value = r.get("active_mining")

        if not active_mining_value:
            logging.info("Error: 'active_mining' not found in Redis.")
            return None, None

        file_hashes = r.hgetall(active_mining_value)
        if not file_hashes:
            logging.error(f"Error: No job found with ID {active_mining_value}.")
            return None, None

        all_have_gradient = True

        for file_hash, json_data in file_hashes.items():
            try:
                data = json.loads(json_data)
                # print("DATA OF JOBS", data)
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON data for {file_hash}.")
                continue

            if "gradient" not in data or not data["gradient"]:
                # print("Inside of if and else  gradient")
                gradient_value = str(data.get("gradient"))
                if gradient_value != "1":
                    # print("gradient_value != 1 ? ", gradient_value)
                    all_have_gradient = False

                updated = False

                try:
                    last_active_time = datetime.datetime.fromisoformat(
                        data.get("last_active")
                    )

                except TypeError:
                    last_active_time = datetime.datetime.min

                if "wallet" in data and last_active_time < ten_minutes_ago:
                    data["wallet"] = new_wallet_address
                    data["last_active"] = current_time.isoformat()
                    data["downloaded"] = "1"
                    updated = True
                elif "wallet" not in data:
                    data["wallet"] = new_wallet_address
                    data["last_active"] = current_time.isoformat()
                    data["downloaded"] = "1"
                    updated = True

                if updated:
                    json_data = json.dumps(data)
                    r.hset(active_mining_value, file_hash, json_data)
                    return json.dumps(
                        {
                            "file_hash": file_hash,
                            "url": data["url"],
                            "active_mining_value": active_mining_value,
                            "message_type": MessageType.DOWNLOADFILE,
                        }
                    )

        if all_have_gradient:
            logging.warning("All jobs were processed successfully")
            mining_status(False)

        return None, None

    except redis.RedisError as e:
        logging.error(f"Redis error: {e}")
        return None, None
    except Exception as e:
        logging.error(f"update_jobs An error occurred: {e}")
        return None, None
