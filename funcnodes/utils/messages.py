import json


def make_progress_message(message, status, progress, blocking):
    return {
        "type": "progress",
        "message": message,
        "status": status,
        "progress": progress,
        "blocking": blocking,
    }


def make_progress_message_string(message, status, progress, blocking):
    return json.dumps(make_progress_message(message, status, progress, blocking))
