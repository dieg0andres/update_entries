from decouple import config

from helpers.pickle_helpers import load_from_pickle
from helpers.setup_logging import setup_logging
from helpers.utils import post_request, count_total_entries, get_entry_dict_for_post, get_summary_dict_for_post, get_transcript_dict_for_post



logger = setup_logging("update_db")

NEW_ENTRIES_WITH_SUMMARIES_PICKLE = config("NEW_ENTRIES_WITH_SUMMARIES_PICKLE")

ENV = config('ENV')

# Set the BASE_URL based on the environment
if ENV == 'DEV':
    BASE_URL = config('BASE_DEV_URL')
elif ENV == 'PROD':
    BASE_URL = config('BASE_PROD_URL')
else:
    logger.error("Invalid environment specified")
    raise ValueError("Invalid environment specified")

API_URL_SECRET_STRING = config('API_URL_SECRET_STRING')

if API_URL_SECRET_STRING == "None":
    API_URL_SECRET_STRING = None



def build_url(api_base_url, table, secret_string=None):
    """
    Constructs a URL for API requests based on the provided parameters.

    This function builds a URL by combining the base API URL, an optional secret string,
    and the table name. It's designed to create URLs for different API endpoints.

    Args:
        api_base_url (str): The base URL of the API.
        table (str): The name of the table or endpoint to be accessed: 'channels', 'entries', 'summaries', or 'transcripts'.
        secret_string (str, optional): A secret string to be included in the URL for authentication purposes.
            Defaults to None.

    Returns:
        str: The constructed URL.
    """
  
    if secret_string is None:
        url = f"{api_base_url}{table}/"
    else:
        url = f"{api_base_url}{secret_string}/{table}/"

    return url



def post_data_for_entry(entry, channel_id):
    """
    Posts data for a single entry to the server, including the entry itself, its summary, and transcript.

    Args:
        entry (dict): A dictionary containing the entry data.
        channel_id (int): The ID of the channel this entry belongs to.

    Returns:
        None

    This function performs three main tasks:
    1. Posts the entry data to the server.
    2. Posts the summary data for the entry.
    3. Posts the transcript data for the entry.

    If any of these operations fail, it logs an error and returns early.
    """

    entry_dict = get_entry_dict_for_post(entry, channel_id)
    url = build_url(BASE_URL, 'entries', API_URL_SECRET_STRING)
    new_entry = post_request(entry_dict, url)

    if new_entry.status_code != 201:
        logger.error(f"FAILED to create entry in the database. Status code: {new_entry.status_code}.  at {url}, for entry: {entry_dict}")
        return

    entry_id = new_entry.json()['id']
    summary_dict = get_summary_dict_for_post(entry, entry_id)

    if summary_dict is not None:
        url = build_url(BASE_URL, 'summaries', API_URL_SECRET_STRING)
        new_summary = post_request(summary_dict, url)

        if new_summary.status_code != 201:
            logger.error(f"FAILED to create summary in the database. Status code: {new_summary.status_code}.  at {url}, for entry: {summary_dict}")
            return
    
    # transcript_dict = get_transcript_dict_for_post(entry, entry_id)
    # url = build_url(BASE_URL, 'transcripts', API_URL_SECRET_STRING)
    # new_transcript = post_request(transcript_dict, url)

    # if new_transcript.status_code != 201:
    #     logger.error(f"FAILED to create transcript in the database. Status code: {new_transcript.status_code}.  at {url}, for entry: {transcript_dict}")
    #     return
    
    logger.info(f"Successfully created entry, summary, and transcript in the database for entry: {entry.get('title', 'No title')}")



def post_data_to_server(pods):
    """
    Posts data for all entries in all channels to the server.

    Args:
        pods (list): A list of tuples, where each tuple contains a channel dictionary
                     and a list of entry dictionaries for that channel.

    Returns:
        None

    This function iterates through all channels and their entries, posting each entry's
    data to the server. It logs the progress and any errors encountered during the process.
    """

    total_entries = count_total_entries(pods)
    for index, (channel, entries) in enumerate(pods):
        logger.info(f"Posting data for channel {channel['title']}")

        channel_id = channel.get('id', None)

        if channel_id is None:
            logger.error(f"Channel ID not found for channel {channel.get('title', 'No title')}")
            return

        for entry in entries:
            logger.info(f"Posting data for entry {index+1} of {total_entries}")

            post_data_for_entry(entry, channel_id)
                    


def update_db():
    """
    Updates the database with new entries and summaries.

    """

    # Load the new entries with summaries from the pickle file
    pods = load_from_pickle(NEW_ENTRIES_WITH_SUMMARIES_PICKLE)

    # Post the loaded data to the server
    post_data_to_server(pods)

    # Log a success message
    logger.info("update_db.py ran successfully")
 

