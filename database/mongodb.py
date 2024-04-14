from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import utils.config as config


def test_db_connection():
    try:
        client = MongoClient(config.MONGO_DB, serverSelectionTimeoutMS=5000)

        client.admin.command("ping")
        print("MongoDB connection established successfully.")
        return True
    except ConnectionFailure:
        print("Failed to connect to MongoDB.")
        return False


def get_db_connection():
    client = MongoClient(config.MONGO_DB)
    return client.minerpool


# Initialize the connection
db = get_db_connection()
minerProcessedTransaction = db.minerProcessedTransaction
minerTransactionsCollection = db.minerTransactionsCollection
minerTransactionsPushed = db.minerTransactionsPushed
minerBalanceUpdateData = db.minerBalanceUpdateData
errorTransaction = db.errorTransaction
catchTransaction = db.catchTransaction
pushHistory = db.pushHistory
