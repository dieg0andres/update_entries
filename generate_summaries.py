import time

from decouple import config
from helpers.json_helpers import convert_to_json_and_save
from helpers.pickle_helpers import load_from_pickle, save_to_pickle
from helpers.setup_logging import setup_logging
from helpers.utils import count_total_entries
from openai import OpenAI




logger = setup_logging("generate_summaries")


NEW_ENTRIES_WITH_TRANSCRIPTS_PICKLE = config("NEW_ENTRIES_WITH_TRANSCRIPTS_PICKLE")
NEW_ENTRIES_WITH_SUMMARIES_JSON = config("NEW_ENTRIES_WITH_SUMMARIES_JSON")
NEW_ENTRIES_WITH_SUMMARIES_PICKLE = config("NEW_ENTRIES_WITH_SUMMARIES_PICKLE")
GPT_MODEL_NAME = config("GPT_MODEL_NAME")
OPENAI_API_KEY = config("OPENAI_API_KEY")
PROMPT = config("PROMPT")
TPM = config("TPM", cast=int)





def construct_prompt(channel, entry, summary_format):
    """
    Constructs the prompt for generating the summary.
    Args:
        channel (dict): The channel to process.
        entry (dict): The entry to process.
        summary_format (str): The format of the summary to generate.
    Returns:
        str: The constructed prompt.
    """

    show = channel.get('title', '')
    episode_title = entry.get('title', '')
    episode_context = entry.get('summary', '')

    try:
        transcript_text = entry['transcript']['text']
    except Exception as e:
        logger.error(f"Error getting transcript for {entry.get('title', 'unknown')}: {e}")
        transcript_text = ""

    if summary_format == "paragraph_summary":
        summary_format = "paragraph"
    elif summary_format == "bullet_summary":
        summary_format = "bullet points"

    prompt = (
        f"Below is a transcript from the {show} podcast. The title of this episode is {episode_title}. "
        f"Here is some information on the context of this episode: {episode_context}. "
        f"Write a summary of the transcript in past tense and {summary_format} form, which should take 10 minutes to read. "
        "Write as if Brett Cooper were talking directly to a high school reader describing the episode, in the first person "
        "with an expressive yet simple writing style. Use quotes from the transcript to make the summary more interesting. "
        "Include details that support main points and insights from the transcript. Ignore content about sponsors "
        "or ads, and do not mention Brett Cooper or high school. Transcript: "
        f"{transcript_text}"
    )
    return prompt



def summarize_entry(entry, prompt, summary_format):
    """
    Summarizes the 'text' field of an entry['transcript'] using OpenAI's API.

    Args:
        channel (dict): The channel to process.
        entry (dict): The entry to process.
        summary_type (str): The type of summary to generate.

    Returns:
        dict: The entry with an added 'summary' field.
    """

    messages = [
        {"role": "system", "content": "You are an expert writer."},
        {"role": "user", "content": prompt}
    ]
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        chat_completion = client.chat.completions.create(
            model=GPT_MODEL_NAME,
            messages=messages,
            # max_tokens=100,
            # temperature=0.7
        )
        summary = chat_completion.choices[0].message.content
        entry[summary_format] = summary
        total_tokens = chat_completion.usage.total_tokens
        SLEEP_TIME = int( 60.0 / ( TPM * 1.0 / total_tokens ) ) - 1
        logger.info(f"Sleeping for {SLEEP_TIME} seconds")
        time.sleep(SLEEP_TIME)
        # TODO: improve algorightm for calculating sleep time due to TPM limit
        # TODO: High prioriy: figure out BATCH API to save money

    except Exception as e:
        logger.error(f"Error creating {summary_format} for {entry.get('title', 'unknown')}: {e}")
        return None

    logger.info(f"Created {summary_format} for {entry.get('title', 'unknown')}")
    logger.info(f"Total tokens: {total_tokens}")
    return entry



def process_podcasts(podcasts, summary_format):
    """
    Processes all entries in the list of podcasts.

    Args:
        podcasts (list): List of podcasts (channel_dict, entries_list).
        prompt_template (str): The prompt template for the summary.

    Returns:
        list: Updated list of podcasts with summaries added to entries.
        If sussesful, each entry will have a "paragrph_summary" and "bullet_summary" key (as assigned by summary_format)
    """
    counter = 0
    total_entries = count_total_entries(podcasts)
    logger.info(f"Total entries needing summaries: {total_entries}")

    for channel, entries in podcasts:
        for entry in entries:

            counter += 1
            logger.info(f"Processing entry {counter} of {total_entries}")

            prompt = construct_prompt(channel, entry, summary_format)

            if prompt is not None:

                logger.info(f"Generating {summary_format} for {channel.get('title', 'unknown')} - {entry.get('title', 'unknown')}")
                summarized_entry = summarize_entry(entry, prompt, summary_format)

                # Remove entries that failed to generate a summary
                if summarized_entry is None:
                    logger.warning(f"Removing {entry.get('title', 'unknown')} from {channel.get('title', 'unknown')} because summary could not be generated")
                    entries.remove(entry)

            else:
                logger.warning(f"Prompt is None for {channel.get('title', 'unknown')} - {entry.get('title', 'unknown')}.  Did not generate summary.  Removed entry from list of entries.")
                entries.remove(entry)

        save_results(podcasts, NEW_ENTRIES_WITH_SUMMARIES_PICKLE, NEW_ENTRIES_WITH_SUMMARIES_JSON)

        #     if counter == 0:
        #         break
        # if counter == 0:
        #     break
    return podcasts


def save_results(pods_with_summaries, pickle_filename, json_filename):
    """
    Save the podcast entries with transcripts to both pickle and JSON files.

    Args:
        pods_with_summaries (list): List of channels and entries with summaries attached.
        pickle_filename (str): Filename for the pickle file.
        json_filename (str): Filename for the JSON file.
    """
    save_to_pickle(pods_with_summaries, pickle_filename)
    convert_to_json_and_save(pods_with_summaries, json_filename)



def generate_summaries():

    # Step 1: Read podcasts from pickle file
    pods = load_from_pickle(NEW_ENTRIES_WITH_TRANSCRIPTS_PICKLE)

    # Step 2 & 3: Process each Entry and save the response in the Entry
    pods_with_summaries = process_podcasts(pods, "paragraph_summary")
    pods_with_summaries = process_podcasts(pods_with_summaries, "bullet_summary")

    # Save results to pickle and JSON
    save_results(pods_with_summaries, NEW_ENTRIES_WITH_SUMMARIES_PICKLE, NEW_ENTRIES_WITH_SUMMARIES_JSON)

