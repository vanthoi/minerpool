import redis
import json
from datetime import datetime, timedelta

from database.database import r


def parse_datetime(time_str_or_int):
    formats = ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]
    if isinstance(time_str_or_int, int):
        return datetime.fromtimestamp(time_str_or_int)
    for fmt in formats:
        try:
            return datetime.strptime(time_str_or_int, fmt)
        except ValueError:
            continue
    raise ValueError(f"Time data '{time_str_or_int}' does not match any known format")


def check_active_users():
    current_time = datetime.utcnow()
    active_user_count = 0
    try:
        miners_list = r.hgetall("miners_list")
        for _, miner_details in miners_list.items():
            details = json.loads(miner_details)
            last_active_time = parse_datetime(details["last_active_time"])
            if (current_time - last_active_time) < timedelta(minutes=30):
                active_user_count += 1
        return active_user_count
    except Exception as e:
        raise e


def check_wallet_active(wallet_address: str):
    try:
        miner_details = r.hget("miners_list", wallet_address)
        if not miner_details:
            return {"active": False, "message": "Wallet address not found"}
        details = json.loads(miner_details)
        last_active_time = parse_datetime(details["last_active_time"])
        active_status = (datetime.utcnow() - last_active_time) < timedelta(minutes=30)
        return {"active": active_status}
    except Exception as e:
        raise e
