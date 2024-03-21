# Upow MinerPool

MinerPool serves as a crucial intermediary between inodes and individual Ai-miners within a distributed computing environment. Its primary function is to procure computational Main-jobs from inodes and efficiently distribute sub-jobs among participating miners. This enables miners to securely engage in training or processing these jobs, contributing to the network's overall computational power and integrity.

## Configuration

Before diving into the MinerPool setup, it's essential to configure the system correctly. The `config.py` file contains several critical settings that need to be adjusted according to your network setup and preferences.

### Inode Connect Configuration

- `INODE_IP`: The IP address of the inode server. Default is `127.0.0.1`.
- `INODE_PORT`: The port on which the inode server is running. Default is `65432`.
- `BUFFER_SIZE`: The buffer size for network communication. Default is `1024`.

### MinerPool Configuration

- `IP`: The IP address on which this MinerPool server will run. Default is `127.0.0.1`.
- `PORT`: The port on which this MinerPool server will listen. Default is `5501`.
- `CHECK_INTERVAL`: The interval (in seconds) for processing blocks. Default is `600`.
- `MINERPOOL_WALLET_ADDRESS`: The wallet address for this MinerPool.
- `MINERPOOL_REWARD_WALLET_ADDRESS`: The wallet address for distributing MinerPool Fee. (18%)
- `INODE_VALIDATOR_LIST`: URL to fetch the list of validators from the inode server.
- `CORE_URL`: The URL of the node for blockchain interactions.
- `PRIVATEKEY`: The private key for the MinerPool's wallet. This is crucial for transactions.
- `API_URL`: The URL for API interactions, typically with the blockchain node.
- `TRACK`: The starting block height for tracking blockchain transactions.
- `FAST_API_URL`: The URL for the FastAPI server (if different from the default IP).
- `FAST_API_PORT`: The port for the FastAPI server. Default is `8003`.

## Getting Started

To get started with MinerPool, ensure that Python 3.6+ is installed on your system. Follow these steps:

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/upowai/minerpool.git
   ```

2. **Navigate to the Project Directory:**

   ```bash
   cd minerpool
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Settings**: Adjust the settings in `config.py` as per your setup.
5. **Configure MongoDB and Redis:**
   - Ensure MongoDB and Redis are running on your system.
   - Update the MongoDB connection URL and database details in `database/mongodb.py` if necessary.
6. **Set Up Environment Variables:**
   - Optionally, set up environment variables for configuration parameters.
7. **Run MinerPool**: Start the MinerPool server by running the main script. For example, `python minerPool.py`.
8. **Connect with Validators**: Start by running `python connect.py`.

## API Endpoints

MinerPool offers a set of RESTful API endpoints through its FastAPI server, allowing for various operations related to wallet balance management and transaction processing. Below are the available endpoints:

### Wallet Balance

- **GET `/get_balance/`**: Retrieve the current balance of a specified miner's wallet address.

  - **Parameters**:
    - `wallet_address`: The wallet address of the miner.
  - **Returns**: The balance of the specified wallet address.

- **GET `/get_balance_poolowner/`**: Fetch the balance of the pool owner's wallet.
  - **Returns**: The balance of the pool owner's wallet.

### Balance Deduction

- **POST `/deduct_balance/`**: Deduct a specified amount from a miner's wallet balance.

  - **Body**:
    - `wallet_address`: The wallet address from which the balance will be deducted.
    - `amount_to_deduct`: The amount to be deducted from the wallet balance.
  - **Returns**: A message indicating the successful deduction of the specified amount.

- **POST `/poolowner_deduct_balance/`**: Deduct a specified amount from the pool owner's wallet balance.
  - **Body**:
    - `amount_to_deduct`: The amount to be deducted from the pool owner's wallet balance.
  - **Returns**: A message indicating the successful deduction of the specified amount.

### Sample API Call using `curl`

To test the `/get_balance/` endpoint to retrieve the balance of a specific wallet address, you can use the following `curl` command:

```bash
curl -X 'GET' \
  'http://<FAST_API_URL>:<FAST_API_PORT>/get_balance/?wallet_address=DhWyMUj2pna2UYbvrqULyLf6dEo2MNzPHA7Uh4kBrJGFY' \
  -H 'accept: application/json'
```

Replace `<FAST_API_URL>` and `<FAST_API_PORT>` with the actual URL and port where your FastAPI server is running. This command sends a GET request to the `/get_balance/` endpoint with a query parameter for the `wallet_address`. The server should respond with the balance of the specified wallet address in JSON format.

## Features

- **Job Distribution**: Efficiently allocates computational jobs among miners.
- **Security**: Ensures secure processing and training of jobs by miners.
- **Reward Distribution**: Manages the distribution of rewards to miners based on their contribution.
- **Real-Time Communication**: Utilizes WebSockets for real-time communication between the pool and miners.
- **Scalability**: Designed to scale with the network, accommodating an increasing number of miners and jobs.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
