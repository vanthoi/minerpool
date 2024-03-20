import json
import datetime
from database.database import r


def pick_model_for_processing():
    try:
        all_models = r.hgetall("models")

        # print("all_models", all_models)

        oldest_last_active_time = datetime.datetime.max
        model_with_oldest_time = None
        model_with_no_last_active = None

        models_to_delete = []

        for model_name, model_data in all_models.items():
            if isinstance(model_data, bytes):
                model_data = model_data.decode("utf-8")

            model_info = json.loads(model_data)

            if float(model_info.get("percentage", 0)) >= 51:
                models_to_delete.append(model_name)
                continue

            last_active_time_str = model_info.get("last_active_time")
            if last_active_time_str == 0 or last_active_time_str == "0":
                model_with_no_last_active = model_name
                break

            if float(model_info.get("percentage", 100)) < 51 and isinstance(
                last_active_time_str, str
            ):
                last_active_time = datetime.datetime.fromisoformat(last_active_time_str)
                if last_active_time < oldest_last_active_time:
                    oldest_last_active_time = last_active_time
                    model_with_oldest_time = model_name

        for model in models_to_delete:
            r.hdel("models", model)

        selected_model = model_with_no_last_active or model_with_oldest_time

        if selected_model:
            if isinstance(selected_model, bytes):
                selected_model = selected_model.decode("utf-8")

            model_info = json.loads(r.hget("models", selected_model))
            model_info["last_active_time"] = datetime.datetime.utcnow().isoformat()
            r.hset("models", selected_model, json.dumps(model_info))

            return selected_model

        return None
    except Exception as e:
        print(f"pick_model_for_processing An error occurred: {e}")
        return None
