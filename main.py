from get_entries import get_entries
from generate_transcripts import generate_transcripts
from generate_summaries import generate_summaries
from update_db import update_db

from helpers.setup_logging import setup_logging


logger = setup_logging("main")

def main():
    """
    Main function to run the update_entries script.
    """
    logger.info("Starting the update_entries script")

    # 1. Get new entries
    if get_entries():
        logger.info("New entries found")

        # 2. Generate transcripts
        generate_transcripts()
        logger.info("Transcripts generated")
        
        # 3. Generate summaries
        generate_summaries()
        logger.info("Summaries generated")
        
        # 4. Update the db
        update_db()
        logger.info("database updated")


    else:
        logger.info("No new entries found.  Nothing updated to the database.")

    logger.info("update_entries script completed")


if __name__ == "__main__":
    main()
