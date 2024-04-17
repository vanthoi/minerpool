import redis
import utils.config as config

r = redis.Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    password=config.REDIS_AUTH,
    decode_responses=True,
)


def test_redis_connection():
    try:
        r = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_AUTH,
            decode_responses=True,
        )
        # Ping the Redis server
        r.ping()
        print("Redis connection established successfully.")
        return True
    except redis.ConnectionError:
        print("Failed to connect to Redis.")
        return False
