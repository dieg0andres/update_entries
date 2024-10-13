"""
This script queries the PODSUM db for a list of channels/entries, compares that with RSS data (obtained using feedparser)
Generates a list of entries that need to be updated
Saves that list in "new_entries.json"
Logs to: get_entries.log
"""
import feedparser
import requests
import time

from decouple import config
from helpers.json_helpers import convert_to_json_and_save
from helpers.setup_logging import setup_logging
from helpers.pickle_helpers import save_to_pickle



ENV = config('ENV')
API_URL_SECRET_STRING = config('API_URL_SECRET_STRING')
NEW_ENTRIES_PICKLE = config('NEW_ENTRIES_PICKLE')
NEW_ENTRIES_JSON = config('NEW_ENTRIES_JSON')

logger = setup_logging("get_entries")

if ENV == 'DEV':
    BASE_URL = config('BASE_DEV_URL')
elif ENV == 'PROD':
    BASE_URL = config('BASE_PROD_URL')
else:
    logger.error("Invalid environment specified")
    raise ValueError("Invalid environment specified")

if API_URL_SECRET_STRING == "None":
    API_URL_SECRET_STRING = None



def get_latest_entry(api_base_url, channel_id, secret_string=None):
    """
    Sends a GET request to retrieve the latest entry for a specific channel_id.

    :param api_base_url: The base URL of the API (e.g., 'https://api.example.com')
    :param channel_id: The channel_id for which the latest entry is to be retrieved
    :return: A dict of the latest entry data if available, None if not
    """
    if secret_string is None:
        url = f"{api_base_url}entries/latest-entry/{channel_id}/"
    else:
        url = f"{api_base_url}{secret_string}/entries/latest-entry/{channel_id}/"

    try:
        # Send GET request to the API
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            logger.info(f"Successfully retrieved the latest entry from the PODSUM API for channel_id {channel_id}")
            return response.json()  # Return the response data as a dictionary (parsed from JSON)
        elif response.status_code == 404:
            detail = response.json().get('detail')
            logger.warning(f"{detail}: for channel_id {channel_id}")
            return None
        else:
            logger.error(f"Failed to retrieve latest entry. Status code: {response.status_code}, Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error occurred while sending GET request: {e}")
        return None
    


def get_channels(api_base_url, secret_string=None):
    """
    Sends a GET request to retrieve the channels.

    :param api_base_url: The base URL of the API (e.g., 'https://api.example.com')
    :return: A list of dicts (limited fields) of the channels data if available, None if not
    """
    if secret_string is None:
        url = f"{api_base_url}channels/limited-fields/"
    else:
        url = f"{api_base_url}{secret_string}/channels/limited-fields/"

    try:
        # Send GET request to the API
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            logger.info(f"Successfully retrieved the channels from the PODSUM API")
            return response.json() 
        
        else:
            logger.error(f"Failed to retrieve channels. Status code: {response.status_code}, Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error occurred while sending GET request: {e}")
        return None



def get_all_channels_and_their_last_entries(api_base_url, secret_string=None):
    """
    Retrieves all channels and their latest entries from the PODSUM API.

    Args:
        api_base_url (str): The base URL of the API.
        secret_string (str, optional): A secret string for API authentication. Defaults to None.

    Returns:
        list: A list of tuples, where each tuple contains a channel (dict) and its latest entry (dict).
               Returns an empty list if no channels or entries are found.

    Note:
        - This function first fetches all channels using the get_channels() function.
        - For each channel, it then retrieves the latest entry using get_latest_entry().
        - Channels or entries that return None are not included in the final list.
    """
    pods = []

    channels = get_channels(api_base_url, secret_string)

    if channels is not None:
        for channel in channels:
            latest_entry = get_latest_entry(api_base_url, channel['id'], secret_string)

            if latest_entry is not None:
                pods.append((channel, latest_entry))

    return pods



def get_new_entries(existing_pods):
    """
    Retrieves new entries for each podcast channel by comparing the existing entries with the RSS feed.

    Args:
        existing_pods (list): A list of tuples, where each tuple contains a channel dictionary and its last entry.

    Returns:
        list: A list of tuples, where each tuple contains a channel dictionary and a list of new entries.
    """
    new_pods = []

    for i, (channel, last_entry) in enumerate(existing_pods):
        try:
            # Parse the last known entry date from the database
            last_date_from_db = last_entry.get('published_parsed')
            if not last_date_from_db:
                logger.warning(f"No published date found for the last entry of channel {channel['id']}")
                continue

            last_date_from_db = time.strptime(last_date_from_db, '%Y-%m-%dT%H:%M:%SZ')
            last_date_from_db = (last_date_from_db.tm_year, last_date_from_db.tm_mon, last_date_from_db.tm_mday)

            # Fetch the RSS feed for the channel
            logger.info(f"Retrieving the RSS feed for channel {channel['id']} - {channel['title']}")
            feed = feedparser.parse(channel['rss_url'])

            if feed.bozo:
                logger.error(f"Error parsing RSS feed for channel {channel['id']} - {channel['rss_url']}")
                continue

            feed_entries = feed.entries
            if not feed_entries:
                logger.warning(f"No entries found in the RSS feed for channel {channel['id']}")
                continue

            # Collect new entries
            new_entries = []
            for entry in feed_entries:
                try:
                    # Extract and compare the date from the feed entry
                    date_from_feed = entry.get('published_parsed')
                    if not date_from_feed:
                        logger.warning(f"Missing published date for an entry in channel {channel['id']}")
                        continue

                    date_from_feed = (date_from_feed.tm_year, date_from_feed.tm_mon, date_from_feed.tm_mday)

                    # Stop collecting entries once we reach an entry that matches or predates the last known entry
                    if last_date_from_db >= date_from_feed or last_entry['_id'] == entry['id']:
                        break

                    # Add new entry to the list
                    new_entries.append(entry)

                except Exception as e:
                    logger.error(f"Error processing entry in channel {channel['id']}: {e}")
                    continue

            # Only append channels with new entries
            if new_entries:
                new_pods.append((channel, new_entries))

            logger.info(f"Found {len(new_entries)} new entries for channel {channel['id']} - {channel['title']}")

        except Exception as e:
            logger.error(f"Error processing channel {channel['id']}: {e}")
            continue

    return new_pods



def get_entries():
    # From the PODSUM API, get all channels and their last entries.  
    # existing_pods is a list of tuples, where each tuple is a channel (dict) and its last entry (dict).
    existing_pods = get_all_channels_and_their_last_entries(BASE_URL, API_URL_SECRET_STRING)

    # Get new entries for each channel from the RSS feed.
    # new_pods is a list of tuples, where each tuple is a channel (dict) and a list of new entries (list of dicts).
    new_pods = get_new_entries(existing_pods)

    # If there are new entries, save them to a JSON and pickle file
    if len(new_pods) > 0:  
        convert_to_json_and_save(new_pods, NEW_ENTRIES_JSON)
        save_to_pickle(new_pods, NEW_ENTRIES_PICKLE)

        return True
    
    return False


# TODO: Bug, if the PODSUM db doesn't have any entries for a channel, 
# this script skips that channel and doesn't try to get new entries from RSS



# def some_function():
#     logger.debug("This is a debug message from module1")
#     logger.info("This is an info message from module1")
#     logger.warning("This is a warning message from module1")
#     logger.error("This is an error message from module1")
#     logger.critical("This is a critical message from module1")