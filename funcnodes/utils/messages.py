import json


def make_progress_message(message: str, status: str, progress: float, blocking: bool):
    return {
        "type": "progress",
        "message": message,
        "status": status,
        "progress": progress,
        "blocking": blocking,
    }


def make_progress_message_string(
    message: str, status: str, progress: float, blocking: bool
):
    return json.dumps(make_progress_message(message, status, progress, blocking))
