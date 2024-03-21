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
INODE_IP = "152.53.3.235"
INODE_PORT = 65432
BUFFER_SIZE = 1024


# MinerPool Configuration settings
IP = "0.0.0.0"
PORT = 5501
CHECK_INTERVAL = 600
MINERPOOL_WALLET_ADDRESS = "DhWyMUj2pna2UYbvrqULyLf6dEo2MNzPHA7Uh4kBrJGFY"
MINERPOOL_REWARD_WALLET_ADDRESS = "Djxhpx8ogGwpfe1tHxuBLVuxXZEhrS7spstDuXUugJ32i"
INODE_VALIDATOR_LIST = "http://152.53.3.235:8000/validators"
CORE_URL = "https://api.upow.ai"
PRIVATEKEY = env.PRIVATEKEY
API_URL = "https://api.upow.ai"
TRACK = 15616
FAST_API_URL = "0.0.0.0"
FAST_API_PORT = 8003
