import json
import datetime
from database.database import r


def pick_model_for_processing():
    try:
        all_models = r.hgetall("models")

        # Initialize variables to store models' info
        models_to_consider = []
        models_to_delete = []

        # Process each model to determine its eligibility
        for model_name, model_data in all_models.items():
            if isinstance(model_data, bytes):
                model_data = model_data.decode("utf-8")
            model_info = json.loads(model_data)

            # Check if the model should be deleted
            if float(model_info.get("percentage", 0)) >= 91:
                models_to_delete.append(model_name)
                continue

            # Prepare model info for sorting
            last_active_time = model_info.get("last_active_time")
            if last_active_time == 0 or last_active_time == "0":
                # Use a default old date for models with no last active time
                last_active_time = datetime.datetime.min.isoformat()
            models_to_consider.append((model_name, model_info, last_active_time))

        # Delete models that are over the threshold
        for model in models_to_delete:
            r.hdel("models", model)

        # Sort models first by percentage, then by last active time
        models_to_consider.sort(
            key=lambda x: (
                float(x[1]["percentage"]),
                datetime.datetime.fromisoformat(x[2]),
            )
        )

        # Select the model to process
        if models_to_consider:
            selected_model, model_info, _ = models_to_consider[0]

            # Update the selected model's last active time
            model_info["last_active_time"] = datetime.datetime.utcnow().isoformat()
            r.hset("models", selected_model, json.dumps(model_info))

            return {"key": selected_model, "value": model_info}

        return None
    except Exception as e:
        print(f"pick_model_for_processing An error occurred: {e}")
        return None
