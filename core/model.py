import torch
import os
import torch
import torch.nn as nn
import torch.optim as optim
import json
from database.database import r
import logging
import redis

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s - %(message)s"
)


class SimpleModel(nn.Module):
    def __init__(self):
        super(SimpleModel, self).__init__()
        self.fc = nn.Linear(10, 1)

    def forward(self, x):
        return self.fc(x)


def load_model_from_pth(model_path):
    try:
        model = SimpleModel()
        model.load_state_dict(torch.load(model_path))
        model.eval()
        return model
    except Exception as e:
        logging.error(f"Error loading model from {model_path}: {e}")
        return None  # Return None if loading fails


def get_pth_files(job, jobname):
    try:
        job_folder_path = os.path.join(job, jobname)

        full_path = os.path.join(os.getcwd(), job_folder_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"The folder '{jobname}' does not exist.")

        folder_contents = os.listdir(full_path)
        pth_files = [item for item in folder_contents if item.endswith(".pth")]

        if not pth_files:
            raise FileNotFoundError(f"No .pth files found in the folder '{jobname}'.")

        pth_file_paths = [os.path.join(job_folder_path, file) for file in pth_files]

        return pth_file_paths

    except FileNotFoundError as e:
        print(e)
        return []
    except Exception as e:
        logging.error(f"get_pth_files An error occurred: {e}")
        return []


def update_model_record(model_name, new_percentage, validator_wallet):
    try:
        key = "models"

        existing_value = r.hget(key, model_name)
        if existing_value is None:
            logging.warning(f"No record found for model {model_name}")
            return f"No record found for model {model_name}"

        data = json.loads(existing_value)

        if not isinstance(data.get("validators"), list):
            data["validators"] = []

        if validator_wallet in data["validators"]:
            logging.warning(
                f"Validator {validator_wallet} already exists for model {model_name}"
            )
            return f"Validator {validator_wallet} already exists for model {model_name}"

        data["percentage"] += new_percentage
        data["validators"].append(validator_wallet)

        r.hset(key, model_name, json.dumps(data))

        logging.info(f"Model {model_name} record updated successfully.")
        return f"Model {model_name} record updated successfully."
    except Exception as e:
        logging.error(f"update_model_record An error occurred: {e}")
        return f"An error occurred: {e}"


def check_model_record(model_name, validator_wallet):
    try:
        key = "models"

        existing_value = r.hget(key, model_name)
        if existing_value is None:
            return False

        data = json.loads(existing_value)

        if not isinstance(data.get("validators"), list):
            return False

        return validator_wallet in data["validators"]

    except Exception as e:
        logging.error(f"check_model_record An error occurred: {e}")
        return False


def create_model_record(model_name, percentage, validators):
    key = "models"
    try:
        value = json.dumps(
            {"percentage": percentage, "last_active_time": 0, "validators": validators}
        )
    except Exception as e:
        logging.error(f"Error serializing model record data for {model_name}: {e}")
        return f"Error serializing model record data: {e}"

    try:
        # Ensure the Redis operation is executed
        result = r.hset(key, model_name, value)
        if result is not None:
            logging.info(f"Model {model_name} record created/updated successfully.")
            return f"Model {model_name} record created/updated successfully."
        else:
            # If result is None, it indicates an unexpected outcome from the hset operation
            logging.error(
                f"Failed to create/update model record for {model_name}. No exception, but the operation did not succeed."
            )
            return "Operation failed without an exception."
    except redis.RedisError as e:
        # Catching specific Redis errors
        logging.error(
            f"Redis error occurred while creating/updating model record for {model_name}: {e}"
        )
        return f"Redis error: {e}"
    except Exception as e:
        # Catching any other exceptions
        logging.error(
            f"An unexpected error occurred while creating/updating model record for {model_name}: {e}"
        )
        return f"An unexpected error occurred: {e}"


def model_exe(job, job_folder_path):
    try:
        pth_files = get_pth_files(job, job_folder_path)
    except Exception as e:
        logging.error(f"Error in fetching .pth files: {e}")
        return

    models = []
    for model_path in pth_files:
        model = load_model_from_pth(model_path)
        if model is not None:  # Check if the model is loaded successfully
            models.append(model)
        else:
            logging.warning(
                f"Skipped loading corrupted or incompatible model from {model_path}"
            )

    if not models:
        logging.info("No models loaded.")
        return

    # logging.info(f"Loaded models: {models}")

    final_folder = "./Models"
    combined_model = SimpleModel()

    for model in models:
        try:
            combined_model.load_state_dict(model.state_dict(), strict=False)
        except Exception as e:
            logging.error(f"Error combining model states: {e}")
            return

    try:
        os.makedirs(final_folder, exist_ok=True)
        combined_model_save_path = os.path.join(final_folder, f"{job_folder_path}.pth")
        torch.save(combined_model.state_dict(), combined_model_save_path)
        logging.info(f"Combined model saved to {combined_model_save_path}")
        create_model_record(job_folder_path, 0, [])
        return True, combined_model_save_path
    except Exception as e:
        logging.error(f"Error saving combined model: {e}")
