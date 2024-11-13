import json
from funcnodes_core import JSONEncoder


def make_progress_message(
    message: str, status: str, progress: float, blocking: bool
) -> dict:
    return {
        "type": "progress",
        "message": message,
        "status": status,
        "progress": progress,
        "blocking": blocking,
    }


def make_progress_message_string(
    message: str, status: str, progress: float, blocking: bool
) -> str:
    return json.dumps(
        make_progress_message(message, status, progress, blocking), cls=JSONEncoder
    )


def worker_event_message(event: str, **kwargs) -> dict:
    return {
        "type": "workerevent",
        "event": event,
        "data": kwargs,
    }


def worker_event_message_string(event: str, **kwargs) -> str:
    return json.dumps(worker_event_message(event, **kwargs), cls=JSONEncoder)
