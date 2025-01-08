import json
import os
import tempfile


def write_json_secure(data, filepath, cls=None):
    """
    Write JSON data to a file securely to avoid corruption.

    :param data: The data to write (dictionary or list).
    :param filepath: The final JSON file path.
    """
    # Get the directory of the target file
    directory = os.path.dirname(filepath)

    # Create a temporary file in the same directory
    with tempfile.NamedTemporaryFile(
        "w+", dir=directory, delete=False, encoding="utf-8"
    ) as temp_file:
        temp_file_path = temp_file.name
        try:
            # Write the JSON data to the temporary file
            json.dump(data, temp_file, indent=4, cls=cls)
            temp_file.flush()  # Ensure all data is written to disk
            os.fsync(temp_file.fileno())  # Force writing to disk for durability
        except Exception as e:
            # Clean up the temporary file in case of an error
            os.remove(temp_file_path)
            raise e

    # Atomically replace the target file with the temporary file
    os.replace(temp_file_path, filepath)
