import os
from dotenv import load_dotenv

dotenv_path = ".env"
load_dotenv(dotenv_path)


class Env:
    def __init__(self):
        for key, value in os.environ.items():
            setattr(self, key, value)


env = Env()

# Inode Connect Configuration settings
INODE_IP = "127.0.0.1"
INODE_PORT = 65432
BUFFER_SIZE = 1024


# MinerPool Configuration settings
IP = "127.0.0.1"
PORT = 5501
CHECK_INTERVAL = 60
MINERPOOL_WALLET_ADDRESS = "DhWyMUj2pna2UYbvrqULyLf6dEo2MNzPHA7Uh4kBrJGFY"
MINERPOOL_REWARD_WALLET_ADDRESS = "Djxhpx8ogGwpfe1tHxuBLVuxXZEhrS7spstDuXUugJ32i"
INODE_VALIDATOR_LIST = "http://0.0.0.0:8000/validators"
CORE_URL = "http://127.0.0.1:3006"
PRIVATEKEY = env.PRIVATEKEY
API_URL = "http://127.0.0.1:3006"
TRACK = 500
FAST_API_URL = "0.0.0.0"
FAST_API_PORT = 8003
