import redis
import json
import datetime
import os
import logging
import redis
from database.database import r
from mining.updateMiner import update_miner
from core.model import load_model_from_pth, model_exe
from mining.activeMinig import mining_status


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)


def delete_job(job_id):
    try:
        if not delete_job_folder(job_id):
            logging.warning(f"Failed to delete folder for job {job_id}.")

        if not r.exists(job_id):
            logging.warning(f"Job {job_id} does not exist.")
            return False

        r.delete(job_id)
        logging.info(f"Job {job_id} deleted successfully.")
        return True

    except redis.RedisError as e:
        logging.error(f"Redis error: {e}")
        return False
    except Exception as e:
        logging.error(f"delete_job error occurred: {e}")
        return False


def delete_job_folder(jobname):
    job_folder_path = os.path.join(".", "Job", jobname)

    try:
        if os.path.exists(job_folder_path):
            for root, dirs, files in os.walk(job_folder_path, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    os.remove(file_path)
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    os.rmdir(dir_path)
            os.rmdir(job_folder_path)
            return True
        else:
            raise FileNotFoundError(f"No such directory: '{job_folder_path}'")
    except Exception as e:
        print(f"delete_job_folder Error: {e}")
        return False


def delete_file_on_error(jobname, file_name):
    job_folder_path = os.path.join("..", "Job", jobname)
    file_path = os.path.join(job_folder_path, file_name)

    if not os.path.exists(file_path):
        return False, f"File {file_name} not found in {jobname}."

    try:
        os.remove(file_path)
        # Removing the job folder if it's empty, using os.rmdir instead of shutil.rmtree
        if not os.listdir(job_folder_path):
            os.rmdir(job_folder_path)
        return True, f"File {file_name} successfully deleted from {jobname}."
    except Exception as e:
        return False, f"Error deleting file: {e}"


def update_gradient(jobname, hash_value, new_gradient, wallet_address, file_name):
    try:
        if not r.exists(jobname):
            return False, f"Job {jobname} not found in the database."

        job_data = r.hget(jobname, hash_value)
        if not job_data:
            return False, f"Hash {hash_value} not found in job {jobname}."

        try:
            data = json.loads(job_data)

        except json.JSONDecodeError:
            delete_file_on_error(jobname, file_name)  # Delete file on JSON decode error
            return (
                False,
                f"Error decoding JSON data for hash {hash_value} in job {jobname}.",
            )

        if data.get("gradient", 0) != 0:
            delete_file_on_error(jobname, file_name)
            return (
                False,
                f"Gradient already exists for hash {hash_value} in job {jobname}.",
            )

        if data.get("downloaded", 0) == 0:
            delete_file_on_error(jobname, file_name)
            return False, f"This job {hash_value} wasn't downloaded."

        try:
            model_path = f"Job/{jobname}/{file_name}"
            # print("model_path", model_path)

            models = []
            model = load_model_from_pth(model_path)
            models.append(model)

        except FileNotFoundError:
            logging.error(f"File not found: {model_path}")
        except IOError:
            logging.error(
                f"IO error occurred while loading the model from {model_path}"
            )

        except Exception as e:
            logging.error(f"Error loading model from {model_path}: {e}")

            delete_file_on_error(jobname, file_name)
            return False, f"This job {hash_value} was corrupted."

        data["gradient"] = new_gradient
        updated_data = json.dumps(data)
        r.hset(jobname, hash_value, updated_data)

        current_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        success, message = update_miner(wallet_address, "1", current_time)
        if not success:
            delete_file_on_error(jobname, file_name)
            return False, message

        file_hashes = r.hgetall(jobname)
        if not file_hashes:
            print(f"Error: No job found with ID {jobname}.")
            return None, None

        gradient_missing = False

        for key, value in file_hashes.items():
            if isinstance(value, bytes):
                value = value.decode("utf-8")

            try:
                data = json.loads(value)  # Load JSON data
            except json.JSONDecodeError:
                logging.error("Error decoding")
                continue

            if "gradient" not in data or int(data["gradient"]) == 0:
                logging.info("Inside of Missing Gradients")
                gradient_missing = True
                break

        if gradient_missing:
            logging.info("Waiting for more gradients to be uploaded")
        else:
            output = model_exe("Job", jobname)
            if output:
                logging.info("Model execution successful")
                result = delete_job(jobname)
                if result:
                    print(f"Job {jobname} deleted successfully.")
                else:
                    print(f"Failed to delete job {jobname}.")

                mining_status(False)
            else:
                logging.error("Model execution failed")

        return True, "Gradient updated successfully."

    except redis.RedisError as e:
        delete_file_on_error(jobname, file_name)
        return False, f"Redis error: {e}"
    except Exception as e:
        delete_file_on_error(jobname, file_name)
        return False, f"update_gradient An error occurred: {e}"


def clean_job_folder():
    try:
        active_mining_value = r.get("active_mining")
        if not active_mining_value:
            print("No active mining job specified. Aborting clean-up.")
            return

        job_root_path = os.path.join(".", "Job")

        for folder_name in os.listdir(job_root_path):
            folder_path = os.path.join(job_root_path, folder_name)

            if folder_name == active_mining_value:
                continue

            if os.path.isdir(folder_path):
                for root, dirs, files in os.walk(folder_path, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(folder_path)

        print(f"Cleaned up all folders except '{active_mining_value}'.")
    except redis.exceptions.RedisError as re:
        print(f"Redis error: {re}")
    except FileNotFoundError as fnf:
        print(f"File not found error: {fnf}")
    except Exception as e:
        print(f"Unexpected error: {e}")
