import redis
import json
from database.database import r

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)


def create_job(job_id, file_hashes):
    try:
        for file_hash, data in file_hashes.items():
            try:
                json_data = json.dumps(data)
                r.hset(job_id, file_hash, json_data)
            except TypeError as e:
                logging.error(f"Error serializing data for file_hash {file_hash}: {e}")
        logging.info(f"Job {job_id} created successfully.")
        return job_id
    except redis.RedisError as e:
        logging.error(f"Redis error: {e}")
        return None
    except Exception as e:
        logging.error(f"create_job An unexpected error occurred: {e}")
        return None
