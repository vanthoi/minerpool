# Upow MinerPool

MinerPool serves as a crucial intermediary between inodes and individual Ai-miners within a distributed computing environment. Its primary function is to procure computational Main-jobs from inodes and efficiently distribute sub-jobs among participating miners. This enables miners to securely engage in training or processing these jobs, contributing to the network's overall computational power and integrity.

## Configuration

Before diving into the MinerPool setup, it's essential to configure the system correctly. The `config.py` file contains several critical settings that need to be adjusted according to your network setup and preferences.

## Enable port for accepting connections (Ubuntu)

```bash
  sudo ufw allow 5503
```

## Installing Redis

To ensure Redis is installed and properly configured on your system, you can use the `install_redis.sh` script. Follow these steps for your operating system:

### macOS and Ubuntu

1. **Make the Script Executable:**

   - Open a terminal and navigate to the directory containing the `install_redis.sh` script.
   - Run the command `chmod +x install_redis.sh` to make the script executable.

2. **Run the Script:**
   - Execute the script by running `./install_redis.sh` in the terminal.
   - If necessary, the script will ask for your password to grant permission for installation steps that require superuser access.

The script will check if Redis is already installed on your system and proceed with the installation if it is not. It also ensures that Redis is set to start on boot.

## Installing Mongodb

To Install Mongodb on Ubuntu you can use the `install_mongodb.sh` script.

### Ubuntu

1. **Make the Script Executable:**

   - Open a terminal and navigate to the directory containing the `install_mongodb.sh` script.
   - Run the command `chmod +x install_mongodb.sh` to make the script executable.

2. **Run the Script:**
   - Execute the script by running `./install_mongodb.sh` in the terminal.
   - If necessary, the script will ask for your password to grant permission for installation steps that require superuser access.

### Inode Connect Configuration

- `INODE_IP`: The IP address of the inode server.
- `INODE_PORT`: The port on which the inode server is running.
- `BUFFER_SIZE`: The buffer size for network communication.

### MinerPool Configuration

- `IP`: The IP address on which this MinerPool server will run.
- `PORT`: The port on which this MinerPool server will listen.
- `CHECK_INTERVAL`: The interval (in seconds) for processing blocks.
- `MINERPOOL_WALLET_ADDRESS`: The wallet address for this MinerPool.
- `MINERPOOL_REWARD_WALLET_ADDRESS`: The wallet address for distributing MinerPool Fee. (18%)
- `INODE_VALIDATOR_LIST`: URL to fetch the list of validators from the inode server.
- `CORE_URL`: The URL of the node for blockchain interactions.
- `PRIVATEKEY`: The private key for the MinerPool's wallet. This is crucial for transactions.
- `API_URL`: The URL for API interactions, typically with the blockchain node.
- `TRACK`: The starting block height for tracking blockchain transactions.
- `FAST_API_URL`: The URL for the FastAPI server.
- `FAST_API_PORT`: The port for the FastAPI server.

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
   pip3 install -r requirements.txt
   ```

4. **Configure Settings**: Adjust the settings in `config.py` as per your setup.
5. **Configure MongoDB and Redis:**
   - Ensure MongoDB and Redis are running on your system.
   - Update the MongoDB connection URL and database details in `database/mongodb.py` if necessary.
6. **Set Up Environment Variables:**
   - Set up environment variables for configuration parameters.
   - Set from which block height you want minerpool to start tracking rewards given by iNode (TRACKBLOCK).
   - Open `.env` file in your project root directory you can use command `nano .env`
   - Add the following lines to your `.env` file,`PRIVATEKEY=YOUR_POOL_WALLET_PRIVATEKEY` you check envExample for reference
     ```
      PRIVATEKEY=key
      MINERPOOLWALLETADDRESS=pool_address
      MINERPOOLREWARDWALLETADDRESS=reward_address
      TRACKBLOCK=10000
      INODEIP=192.99.7.175
      INODEVALIDATORLIST=http://192.99.7.175:8000/validators
      REDISHOST=localhost
      REDISPORT=6379
      REDISDB=0
     ```
7. **Prepare Your Development Environment**

   Depending on your operating system, you may need to install additional tools to ensure the `fastecdsa` Python package and other dependencies compile correctly:

   - **Ubuntu Users:**

     Install the necessary libraries by running:

     ```bash
     sudo apt-get update
     sudo apt-get install libgmp3-dev
     sudo apt-get install build-essential libssl-dev libffi-dev python3-dev
     ```

   - **Windows Users:**

     Install Visual Studio, which includes the necessary C++ build tools. Download it from [https://visualstudio.microsoft.com/vs/preview/](https://visualstudio.microsoft.com/vs/preview/) and ensure to select the C++ workload during installation.
     [wikihow Install Clang on Windows](https://www.wikihow.com/Install-Clang-on-Windows)

   - **macOS Users:**

     Install Xcode or the standalone Command Line Tools for Xcode, which include `clang`. This can be done by installing Xcode from the Mac App Store or by running the following command in the terminal:

     ```bash
     xcode-select --install
     ```

     For users who prefer not to install Xcode, downloading Command Line Tools for Xcode from [Apple Developer Downloads](https://developer.apple.com/download/more/) is an alternative.
     [https://ics.uci.edu/~pattis/common/handouts/macclion/clang.html](https://ics.uci.edu/~pattis/common/handouts/macclion/clang.html)

   Please ensure these tools are correctly installed and configured on your system before proceeding with the installation of the Python package dependencies.

8. **Run MinerPool**: Start the MinerPool server by running the main script. For example, `python3 minerPool.py`.
9. **Connect with Validators**: Start by running `python3 connect.py`.

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
