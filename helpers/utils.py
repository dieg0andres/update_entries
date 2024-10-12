import datetime
import requests
import time

from helpers.setup_logging import setup_logging



logger = setup_logging("utils")


def count_total_entries(pods):
    """
    Counts the total number of entries across all tuples in the pods list.
    
    Args:
        pods (list): A list of tuples where the second element in each tuple is a list of entries (dictionaries).

    Returns:
        int: The total number of entries across all tuples.
    """
    total_entries = 0

    # Iterate over each tuple in pods
    for _, entries in pods:
        total_entries += len(entries)  # Add the number of entries in the current tuple

    return total_entries



def post_request(data_dict, url):
    """
    Sends a POST request with JSON data to the specified URL.

    Parameters:
    - data_dict (dict): The data dictionary to send as JSON.
    - url (str): The target URL for the POST request.

    Returns:
    - response (requests.Response): The response object from the POST request.
    """
    try:
        # Log the start of the request
        logger.info(f"Sending POST request to {url}")

        # Send POST request with JSON data
        response = requests.post(url, json=data_dict)
        
        # Log the successful request
        logger.info(f"POST request to {url} succeeded with status code {response.status_code}")

        # Raise an exception if the request was unsuccessful
        response.raise_for_status()

        # Return the response object if successful
        return response
    except requests.exceptions.RequestException as e:
        # Log the exception
        logger.error(f"An error occurred during POST request to {url}: {e}")
        return response



def convert_time_to_iso(time_struct):
    if isinstance(time_struct, time.struct_time):
        updated_parsed_dt = datetime.datetime(*time_struct[:6])  # Convert to datetime
        updated_parsed_iso = updated_parsed_dt.isoformat()  # Convert to ISO 8601 string
    else:
        updated_parsed_iso = None  # Handle missing or invalid date

    return updated_parsed_iso



def get_channel_dict_for_post(channel):
    return {
    'author': channel['author'],
    'category': channel['category'],
    'description': channel['description'],
    'image': channel['image'],
    'subtitle': channel['subtitle'],
    'summary': channel['summary'],
    'title': channel['title'],
    'updated_parsed': convert_time_to_iso(channel['updated_parsed']),
    'rss_url': channel['rss_url'],
    }
    


def get_entry_dict_for_post(entry, channel_id):
    return {
        'channel': channel_id,
        'author': entry['author'],
        '_id': entry['id'], #_id is the id of the RSS feed entry, not the PODSUM entry id
        'itunes_duration': entry['itunes_duration'],
        'links': entry['links'],
        'published_parsed': convert_time_to_iso(entry['published_parsed']),
        '_summary': entry['summary'],
        'title': entry['title'],
    }



def get_summary_dict_for_post(entry, entry_id):

    summaries = {
        'entry': entry_id,
        'paragraph_summary': entry.get('paragraph_summary', ''),
        'bullet_summary': entry.get('bullet_summary', ''),
    }

    if summaries['paragraph_summary'] == '' or summaries['bullet_summary'] == '':
        return None

    return summaries

def get_transcript_dict_for_post(entry, entry_id):
    return {
        'entry': entry_id,
        'transcript': entry.get('transcript', ''),
    }