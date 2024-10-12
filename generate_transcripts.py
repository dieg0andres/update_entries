import os
import requests
import whisper

from decouple import config
from helpers.json_helpers import convert_to_json_and_save
from helpers.pickle_helpers import load_from_pickle, save_to_pickle
from helpers.setup_logging import setup_logging
from helpers.utils import count_total_entries



NEW_ENTRIES_PICKLE = config('NEW_ENTRIES_PICKLE')
NEW_ENTRIES_WITH_TRANSCRIPTS_JSON = config('NEW_ENTRIES_WITH_TRANSCRIPTS_JSON')
NEW_ENTRIES_WITH_TRANSCRIPTS_PICKLE = config('NEW_ENTRIES_WITH_TRANSCRIPTS_PICKLE')
MP3_FILENAME = config('MP3_FILENAME')
WHISPER_MODEL_SIZE = config('WHISPER_MODEL_SIZE')
WHISPER_MODEL_LANGUAGE = config('WHISPER_MODEL_LANGUAGE')
WHISPER_MODEL_VERBOSE = config('WHISPER_MODEL_VERBOSE', cast=bool)


logger = setup_logging("generate_transcripts")



def entry_to_db_format(entry: dict):
    """
    Converts an entry dictionary to a format suitable for the database.

    Args:
        entry (dict): The entry dictionary to convert.

    Returns:
        dict: The converted entry dictionary.
    """

    try:
        return {
            "author": entry.get("author", None),
            "id": entry.get("id", None),
            "itunes_duration": entry.get("itunes_duration", None),
            "links": entry.get("links", None),
            "published_parsed": entry.get("published_parsed", None),
            "summary": entry.get("summary", None),
            "title": entry.get("title", None)
        }
    except Exception as e:
        logger.error(f"Error converting entry to db format: {e}")
        return None



def download_mp3(entry, output_filename):
    """
    Downloads the latest MP3 file for a given entry and saves it as 'output_filename'.
    Args:
        entry (dict): The entry dictionary to download the MP3 for.
        output_filename (str): The filename to save the MP3 as. Default is 'podcast.mp3'.
    Returns:
        bool: True if the download is successful, False otherwise.
    """
   
    # Find the MP3 link in the entry's 'links' field
    mp3_link = None
    for link in entry.get('links', []):
        if link.get('rel') == 'enclosure' and link.get('type') == 'audio/mpeg':
            mp3_link = link['href']
            break
    
    if not mp3_link:
        logger.warning(f"No MP3 file found in entry: {entry.get('author')} - {entry.get('title')}")
        return False

    # Download the MP3 file
    try:
        logger.info(f"Downloading MP3 for {entry.get('author')} - {entry.get('title')}...")
        response = requests.get(mp3_link, stream=True, timeout=10)
        response.raise_for_status()

        with open(output_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"MP3 file saved as {output_filename}.")
        return True
    except requests.RequestException as e:
        logger.error(f"Error downloading MP3 file for {entry.get('author')} - {entry.get('title')}: {e}")
        return False



def get_transcript(mp3_file):
    """
    Generates a transcript from an MP3 file using the specified Whisper model.

    Args:
        mp3_file (str): The path to the MP3 file to transcribe.
        model_name (str): The name of the Whisper model to use for transcription.

    Returns:
        dict or None: A dictionary containing the transcription result with 'text' and 'segments' keys,
                      or None if an error occurs during transcription.

    Raises:
        FileNotFoundError: If the specified MP3 file does not exist.
        Exception: For any other errors that occur during the transcription process.
    """
    
    try:
        # Ensure the podcast file exists
        if not os.path.exists(mp3_file):
            logger.error(f"Podcast file {mp3_file} does not exist.")
            return None

        # Load the Whisper model
        model = whisper.load_model(WHISPER_MODEL_SIZE)

        # Perform the transcription
        result = model.transcribe(mp3_file, verbose=WHISPER_MODEL_VERBOSE, language=WHISPER_MODEL_LANGUAGE)
        
        # Return the result (a dictionary containing 'text' and 'segments')
        logger.info("Transcription completed successfully.")
        return result

    except Exception as e:
        logger.error(f"An error occurred during transcription: {e}")
        return None



def process_pods(pods):
    """
    Process the list of podcast entries by converting them to the required database format
    and generating transcripts.

    Args:
        pods (list): List of tuples with channels and their entries.

    Returns:
        list: A new list of tuples containing channels and their entries with transcripts.
    """
    pods_with_transcripts = []
    
    # Convert entries to database format
    for index, (channel, entries) in enumerate(pods):
        converted_entries = convert_entries(entries)
        pods_with_transcripts.append((channel, converted_entries))

    # Generate transcripts for the converted entries
    total_entries = count_total_entries(pods)
    logger.info(f"Total entries to generate transcripts for: {total_entries}")
    
    return generate_and_attach_transcripts(pods_with_transcripts, total_entries)



def convert_entries(entries):
    """
    Convert podcast entries to the required database format.

    Args:
        entries (list): List of entries for a channel.

    Returns:
        list: Converted entries in the required database format.
    """
    return [entry_to_db_format(entry) for entry in entries]



def generate_and_attach_transcripts(pods_with_transcripts, total_entries):
    """
    Generate and attach transcripts to the entries. If transcript generation fails, 
    the entry is removed.

    Args:
        pods_with_transcripts (list): List of channels and entries (already converted to DB format).
        total_entries (int): Total number of entries to process.

    Returns:
        list: The list of channels and entries with transcripts attached.
    """
    count = 0
    for index, (channel, entries) in enumerate(pods_with_transcripts):
        logger.info(f"Generating transcripts for channel: {channel.get('title')}")
        
        for entry in entries[:]:  # Use slice [:] to safely remove items while iterating
            if download_mp3(entry, MP3_FILENAME):
                logger.info(f"Generating transcript for entry: {entry.get('title')}")
                logger.info(f"Generating transcript {count + 1} out of {total_entries} total")

                transcript = get_transcript(MP3_FILENAME)
                
                if transcript is not None:
                    entry['transcript'] = transcript
                else:
                    entries.remove(entry)  # Safely remove entry if transcript generation fails
                    logger.warning(f"Removed entry '{entry.get('title')}' due to transcript generation failure")

            count += 1

            # if count == 3:
            #     break

        # Save the progress after processing each channel
        save_results(pods_with_transcripts, NEW_ENTRIES_WITH_TRANSCRIPTS_PICKLE, NEW_ENTRIES_WITH_TRANSCRIPTS_JSON)

        # if count == 3:
        #     break
    
    return pods_with_transcripts


def save_results(pods_with_transcripts, pickle_filename, json_filename):
    """
    Save the podcast entries with transcripts to both pickle and JSON files.

    Args:
        pods_with_transcripts (list): List of channels and entries with transcripts attached.
        pickle_filename (str): Filename for the pickle file.
        json_filename (str): Filename for the JSON file.
    """
    save_to_pickle(pods_with_transcripts, pickle_filename)
    convert_to_json_and_save(pods_with_transcripts, json_filename)



def generate_transcripts():
    """
    Main function that coordinates the generation of transcripts for podcast entries.
    """
    # Load the existing pods from pickle
    pods = load_from_pickle(NEW_ENTRIES_PICKLE)
    
    # Convert entries to database format and generate transcripts
    pods_with_transcripts = process_pods(pods)

    # Save results to pickle and JSON
    save_results(pods_with_transcripts, NEW_ENTRIES_WITH_TRANSCRIPTS_PICKLE, NEW_ENTRIES_WITH_TRANSCRIPTS_JSON)
