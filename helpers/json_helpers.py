import json
import os

from helpers.setup_logging import setup_logging

logger = setup_logging("json_helpers")


def convert_to_json_and_save(new_pods, file_name='./data/test.json', encoding='utf-8', overwrite=True):
    """
    Converts a list of tuples (Channel, Entries) into a JSON format and saves it to a file.

    Args:
        new_pods (list): A list of tuples where each tuple is (Channel dict, Entries list).
        file_name (str): The name of the JSON file to save the data.
        encoding (str): The encoding to use for the JSON file (default: utf-8).
        overwrite (bool): Whether to overwrite the file if it exists (default: False).

    Returns:
        bool: True if the file is successfully written, False otherwise.
    """
    
    # Validate the data structure
    if not isinstance(new_pods, list):
        logger.error("Invalid data: new_pods must be a list of tuples.")
        return False

    try:
        # Convert the list of tuples (Channel, Entries) into a serializable format
        serializable_pods = [{"Channel": channel, "Entries": entries} for channel, entries in new_pods]

        # Check if the file already exists and handle overwrite
        if os.path.exists(file_name) and not overwrite:
            logger.error(f"File '{file_name}' already exists. Set overwrite=True to overwrite the file.")
            return False

        # Write the converted data to a .json file
        with open(file_name, 'w', encoding=encoding) as json_file:
            json.dump(serializable_pods, json_file, indent=4, ensure_ascii=False)

        logger.info(f"Data successfully written to {file_name}")
        return True

    except (IOError, OSError) as file_error:
        logger.error(f"Error writing to file {file_name}: {file_error}")
        return False

    except (TypeError, ValueError) as serialization_error:
        logger.error(f"Error serializing data to JSON: {serialization_error}")
        return False
