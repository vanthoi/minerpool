import redis

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def test_redis_connection():
    try:
        r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
        # Ping the Redis server
        r.ping()
        print("Redis connection established successfully.")
        return True
    except redis.ConnectionError:
        print("Failed to connect to Redis.")
        return False
