import redis
from database.database import r


def active_mining(value):
    try:
        r.set("active_mining", value)
        return True

    except redis.RedisError as e:
        print(f"Redis error: {e}")
        return False
    except Exception as e:
        print(f"active_mining An unexpected error occurred: {e}")
        return False


def mining_status(value):
    try:
        r.set("mining_status", str(value))
        return True

    except redis.RedisError as e:
        print(f"Redis error: {e}")
        return False
    except Exception as e:
        print(f"mining_status An unexpected error occurred: {e}")
        return False
