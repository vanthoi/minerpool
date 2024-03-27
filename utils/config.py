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

# Inode Connect Configuration settings
INODE_IP = "152.53.3.235"
INODE_PORT = 65432
BUFFER_SIZE = 1024


# MinerPool Configuration settings
IP = "0.0.0.0"
PORT = 5501
CHECK_INTERVAL = 60
MINERPOOL_WALLET_ADDRESS = env.MINERPOOLWALLETADDRESS
MINERPOOL_REWARD_WALLET_ADDRESS = env.MINERPOOLREWARDWALLETADDRESS
INODE_VALIDATOR_LIST = "http://152.53.3.235:8000/validators"
CORE_URL = "https://api.upow.ai"
PRIVATEKEY = env.PRIVATEKEY
API_URL = "https://api.upow.ai"
TRACK = 15616
FAST_API_URL = "0.0.0.0"
FAST_API_PORT = 8003
