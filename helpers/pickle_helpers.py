import os
import pickle

from helpers.setup_logging import setup_logging
from pickle import PicklingError


logger = setup_logging("pickle_helpers")


def save_to_pickle(data, filename: str, overwrite: bool = True):
    """
    Saves data to a pickle file with the highest available protocol.
    
    Args:
        data: Data to be saved.
        filename (str): The name of the file to save data to.
        overwrite (bool): Whether to overwrite the file if it exists. Default is True.

    Returns:
        bool: True if data was successfully saved, False otherwise.
    """
    # Check if file exists and handle overwriting
    if os.path.exists(filename) and not overwrite:
        logger.error(f"File '{filename}' already exists. Set overwrite=True to overwrite.")
        return False

    try:
        # Use a temporary file to ensure data integrity in case of failure
        temp_filename = filename + ".tmp"
        
        # Save data to a temporary file
        with open(temp_filename, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Rename the temporary file to the target file
        os.replace(temp_filename, filename)
        logger.info(f"Data successfully saved to {filename}.")
        return True

    except (OSError, PicklingError) as e:
        logger.error(f"Failed to save data to {filename}: {e}")
        return False

    except Exception as e:
        logger.error(f"An unexpected error occurred while saving to {filename}: {e}")
        return False




def load_from_pickle(filename: str):
    """
    Loads data from a pickle file.
    
    Args:
        filename (str): The name of the pickle file to load data from.

    Returns:
        The data loaded from the pickle file, or None if an error occurs.
    """
    if not os.path.exists(filename):
        logger.error(f"File '{filename}' does not exist.")
        return None

    try:
        # Open the pickle file and load the data
        with open(filename, 'rb') as f:
            data = pickle.load(f)
        logger.info(f"Data successfully loaded from {filename}.")
        return data

    except (OSError, pickle.UnpicklingError) as e:
        logger.error(f"Failed to load data from {filename}: {e}")
        return None

    except Exception as e:
        logger.error(f"An unexpected error occurred while loading from {filename}: {e}")
        return None
