from database.database import r
import json
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)


def update_miner(wallet, score, last_active_time):
    try:
        if not r.exists("miners_list"):
            r.hset(
                "miners_list",
                wallet,
                json.dumps(
                    {"balance": 0, "score": score, "last_active_time": last_active_time}
                ),
            )
            return True, "Miner data added successfully."
        else:
            miner_data = r.hget("miners_list", wallet)
            if miner_data:
                miner_data = json.loads(miner_data)
                miner_data["score"] = str(int(miner_data["score"]) + int(score))
                miner_data["last_active_time"] = last_active_time
                r.hset("miners_list", wallet, json.dumps(miner_data))
                return True, "Miner updated successfully."
            else:
                r.hset(
                    "miners_list",
                    wallet,
                    json.dumps(
                        {
                            "balance": 0,
                            "score": score,
                            "last_active_time": last_active_time,
                        }
                    ),
                )
                return True, "Miner score updated successfully."
    except json.JSONDecodeError:
        logging.error("Error in processing JSON data.")
        return False, "Failed to process JSON data."
    except ValueError as e:
        logging.error(f"Value error: {e}")
        return False, f"Value error: {e}"
    except Exception as e:
        logging.error(f"update_miner An unexpected error occurred: {e}")
        return False, f"An unexpected error occurred: {e}"
