import os
from dotenv import load_dotenv

dotenv_path = ".env"
load_dotenv(dotenv_path)


class Env:
    def __init__(self):
        for key, value in os.environ.items():
            setattr(self, key, value)


env = Env()

minerpool_private_key = os.getenv("PRIVATEKEY")
if minerpool_private_key is None:
    print(
        "Minerpool PRIVATEKEY not found. Please check readme.md to set the PRIVATEKEY in the .env variable."
    )
    exit(0)

minerpool_wallet_address = os.getenv("MINERPOOLWALLETADDRESS")
if minerpool_wallet_address is None:
    print(
        "Minerpool MINERPOOLWALLETADDRESS not found. Please check readme.md to set the MINERPOOLWALLETADDRESS in the .env variable."
    )
    exit(1)

minerpool_reward_address = os.getenv("MINERPOOLREWARDWALLETADDRESS")
if minerpool_reward_address is None:
    print(
        "Minerpool MINERPOOLREWARDWALLETADDRESS not found. Please check readme.md to set the MINERPOOLREWARDWALLETADDRESS in the .env variable."
    )
    exit(2)

minerpool_track_block = os.getenv("TRACKBLOCK")
if minerpool_track_block is None:
    print(
        "Minerpool TRACKBLOCK not found. Please check readme.md to set the TRACKBLOCK in the .env variable."
    )
    exit(3)

minerpool_inode_ip = os.getenv("INODEIP")
if minerpool_inode_ip is None:
    print(
        "Minerpool INODEIP not found. Please check readme.md to set the INODEIP in the .env variable."
    )
    exit(4)

minerpool_indoe_val_list = os.getenv("INODEVALIDATORLIST")
if minerpool_indoe_val_list is None:
    print(
        "Minerpool INODEVALIDATORLIST not found. Please check readme.md to set the INODEVALIDATORLIST in the .env variable."
    )
    exit(5)


minerpool_redishost = os.getenv("REDISHOST")
if minerpool_redishost is None:
    print(
        "Minerpool REDISHOST not found. Please check readme.md to set the REDISHOST in the .env variable."
    )
    exit(6)


minerpool_redisport = os.getenv("REDISPORT")
if minerpool_redisport is None:
    print(
        "Minerpool REDISPORT not found. Please check readme.md to set the REDISPORT in the .env variable."
    )
    exit(7)


minerpool_redisdb = os.getenv("REDISDB")
if minerpool_redisdb is None:
    print(
        "Minerpool REDISDB not found. Please check readme.md to set the REDISDB in the .env variable."
    )
    exit(8)


minerpool_redisauth = os.getenv("REDISAUTH")
if minerpool_redisauth is None:
    print(
        "Minerpool REDISAUTH not found. Please check readme.md to set the REDISAUTH in the .env variable."
    )
    exit(12)

minerpool_mongodburi = os.getenv("MONGODB")
if minerpool_mongodburi is None:
    print(
        "Minerpool MONGODB not found. Please check readme.md to set the MONGODB in the .env variable."
    )
    exit(9)

minerpool_ratelimit1 = os.getenv("RATELIMIT1")
if minerpool_ratelimit1 is None:
    print(
        "Minerpool RATELIMIT1 not found. Please check readme.md to set the RATELIMIT1 in the .env variable."
    )
    exit(10)

minerpool_ratelimit2 = os.getenv("RATELIMIT2")
if minerpool_ratelimit2 is None:
    print(
        "Minerpool RATELIMIT2 not found. Please check readme.md to set the RATELIMIT2 in the .env variable."
    )
    exit(11)

# Inode Connect Configuration settings
INODE_IP = env.INODEIP
INODE_PORT = 65432
BUFFER_SIZE = 1024


# MinerPool Configuration settings
IP = "0.0.0.0"
PORT = 5501
CHECK_INTERVAL = 60
MINERPOOL_WALLET_ADDRESS = env.MINERPOOLWALLETADDRESS
MINERPOOL_REWARD_WALLET_ADDRESS = env.MINERPOOLREWARDWALLETADDRESS
INODE_VALIDATOR_LIST = env.INODEVALIDATORLIST
CORE_URL = "https://api.upow.ai"
PRIVATEKEY = env.PRIVATEKEY
API_URL = "https://api.upow.ai"
TRACK = env.TRACKBLOCK
FAST_API_URL = "0.0.0.0"
FAST_API_PORT = 8003
RATE_LIMIT1 = env.RATELIMIT1
RATE_LIMIT2 = env.RATELIMIT2

# redus database configurations
REDIS_HOST = env.REDISHOST
REDIS_PORT = env.REDISPORT
REDIS_DB = env.REDISDB
REDIS_AUTH = env.REDISAUTH

# Mongodb
MONGO_DB = env.MONGODB
