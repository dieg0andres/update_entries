# Objective:

Update the entries in the PODSUM database with new data from the podcast RSS feed.

<br>

# Implementation (high level steps):

+ The whole process is carried out by 5 scripts (steps) in the following order:
+ Whole script carried out by cron job on Mac Mini, every 24 hours
+ Each script has its own log file, which is saved in the "logs" folder
+ Each script has its own .json file, .pkl file, which is saved in the "data" folder

### [1. get_entries.py](#1-about-get_entriespy)
+ Queries the PODSUM db for a list of channels/entries, compares that with RSS data
+ Generates a list of entries that need to be updated
+ Saves that list in `new_entries.json` and `new_entries.pkl` in the data folder
+ `new_entries.pkl` is a list of tuples, where each tuple is a channel and a list of entries.
    + Channel is a dict with keys: `id`, `title`, `rss_url`
    + Entry is a dict with keys: `id`, `title`, `description`, `published`, `link`, `enclosure_url`, `enclosure_length`, `enclosure_type`
+ Logs to: `get_entries.log` in the logs folder

### [2. generate_transcripts.py](#2-about-generate_transcriptspy)
+ Reads the `new_entries.pkl` file from step 1 above
+ For each entry, it uses OpenAI Whisper to generate a transcript, locally (uses temporary file `podcast.mp3`)
+ Saves the transcript in `new_entries_with_transcripts.json` and `new_entries_with_transcripts.pkl`
+ Logs to: `generate_transcripts.log`

### [3. generate_summaries.py](#3-about-generate_summariespy)
+ Reads the `new_entries_with_transcripts.pkl` file from step 2 above
+ For each entry, it uses OpenAI GPT-4 to generate summaries.  Those summaries are added to each entry, in two formats: `paragraph_summary` and `bullet_summary`
+ Summaries are accessed by `entry["paragraph_summary"]` and `entry["bullet_summary"]`
+ Saves the summary in `new_entries_with_summaries.json` and `new_entries_with_summaries.pkl`
+ Logs to: `generate_summaries.log`

### [4. update_db.py](#4-about-update_dbpy)
+ Reads the "new_entries_with_summaries.json" file
+ For each entry, it updates the PODSUM db
+ Logs to: update_db.log

### [5. main.py](#5-about-mainpy)
+ This is the entry point for the update_entries script.
+ It calls all the other scripts in the correct order
+ Logs to: main.log

<br>

# Implementation details:

+ There is a "helpers" folder, which contains shared code between the scripts

## 1. About get_entries.py:

### Summary of `get_entries.py`

This script retrieves podcast channels and their latest entries from the PODSUM API, checks RSS feeds for new entries, and saves the results in both JSON and pickle formats. Below is a detailed explanation of the key components and how the script operates.

---

#### `get_entries()`

**Purpose**:  
This is the main function that coordinates the entire process of fetching channels, checking for new entries via RSS, and saving those entries to a JSON and pickle file.

- **Existing Entries Retrieval**:  
  Retrieves all channels and their latest entries from the PODSUM API via the `get_all_channels_and_their_last_entries()` function.

- **New Entries Check**:  
  Calls `get_new_entries()` to compare the RSS feed entries with the latest known entries from the API.

- **Saving Results**:  
  If new entries are found, it saves the new data using `convert_to_json_and_save()` to create a JSON file and `save_to_pickle()` to create a pickle file for future use.

---

#### Key Functions

##### `get_all_channels_and_their_last_entries()`

**Purpose**:  
Fetches all channels from the PODSUM API and retrieves the latest entry for each channel.

- **Channel Retrieval**:  
  Uses `get_channels()` to fetch a list of available channels from the API.
  
- **Latest Entry Retrieval**:  
  For each channel, `get_latest_entry()` is used to fetch the most recent entry, ensuring that channels without new entries are excluded from the result.

**Usage**:  
This function returns a list of tuples, where each tuple contains:
- A dictionary representing a channel
- A dictionary representing the latest entry for that channel.

---

##### `get_new_entries()`

**Purpose**:  
Compares the latest entries in the RSS feed against the stored entries from the PODSUM API and retrieves new entries.

- **Date Comparison**:  
  Parses and compares the `published_parsed` field from the stored data and the RSS feed to determine whether each entry is new.
  
- **Error Handling**:  
  Catches errors for malformed RSS feeds or missing data, ensuring the script continues processing other channels.

**Usage**:  
This function takes `existing_pods` (the current list of channels and their latest entries) and returns a list of channels and their newly discovered entries.


---

#### API Interaction Functions

##### `get_channels()`

**Purpose**:  
Sends a `GET` request to retrieve a list of available channels from the PODSUM API.

- **Secret String Authentication**:  
  If a secret string is provided, it appends the string to the API URL for authentication.

**Usage**:  
Returns a list of channels with limited fields (e.g., `id`, `title`, `rss_url`).

---

##### `get_latest_entry()`

**Purpose**:  
Fetches the latest entry for a specific channel from the PODSUM API.

- **Error Handling**:  
  Catches network errors and logs appropriate messages for failed requests.

**Usage**:  
Returns the latest entry for a given channel as a dictionary.

---

#### How to Use

1. Ensure environment variables (`ENV`, `API_URL_SECRET_STRING`, `BASE_DEV_URL`, `BASE_PROD_URL`) are configured using `decouple`.
2. Run the `get_entries()` function to automatically:
   - Fetch the latest entries from the PODSUM API.
   - Compare them with the RSS feed entries.
   - Save new entries (if any) to both JSON and pickle files called `new_entries.json` and `new_entries.pkl` in the `data` folder.

<br>

## 2. About generate_transcripts.py:
### Summary of `generate_transcripts.py`

This script processes podcast entries by downloading MP3 files, generating transcripts using the OpenAI Whisper model, and saving the results into both JSON and Pickle formats. It uses helper functions to manage file downloads, transcription, and data formatting for storing results.

#### Purpose of `generate_transcripts()` function

The `generate_transcripts()` function is the main orchestrator. It loads podcast entries from a Pickle file, processes them by downloading MP3 files, generating transcripts, and saving the results into both JSON and Pickle formats.

---

#### Key Functions Overview

#### `entry_to_db_format()`

**Purpose**:  
The `entry_to_db_format()` function converts a podcast entry dictionary into a format that is suitable for storing in a database. It extracts key fields like `author`, `id`, `itunes_duration`, `links`, `published_parsed`, `summary`, and `title` from the entry dictionary. If any field is missing, it assigns a default value of `None`. If an error occurs during the conversion, the function logs the error and returns `None`.

**Usage**:
```python
entry = {
    "author": "John Doe",
    "id": "1234",
    "itunes_duration": "12:30",
    "links": [{"rel": "enclosure", "href": "http://example.com/audio.mp3"}],
    "published_parsed": "2023-09-01T10:00:00Z",
    "summary": "This is a podcast episode.",
    "title": "Episode 1"
}

converted_entry = entry_to_db_format(entry)
```
---
#### `download_mp3`

**Purpose**:  
Downloads the latest MP3 file for a given podcast entry using the provided link in the entry's `links` field and saves it locally as `output_filename`. It returns `True` if the download is successful, otherwise `False`.

**Usage**:
```python
download_success = download_mp3(entry, MP3_FILENAME)
```

---

#### `get_transcript`

**Purpose**:  
Generates a transcript from an MP3 file using the Whisper model specified in the environment variables. The function returns a dictionary with transcription results containing `text` and `segments` keys, or `None` if an error occurs during transcription.

**Usage**:
```python
transcript = get_transcript(MP3_FILENAME)
```

---

#### `process_pods`

**Purpose**:  
Processes the list of podcast entries by converting them to the required database format and generating transcripts for each entry. The function returns a new list of tuples containing channels and their entries with transcripts.

**Usage**:
```python
pods_with_transcripts = process_pods(pods)
```

---

#### `convert_entries`

**Purpose**:  
Converts a list of podcast entries into the required database format by applying the `entry_to_db_format()` function to each entry.

**Usage**:
```python
converted_entries = convert_entries(entries)
```

---

#### `generate_and_attach_transcripts`

**Purpose**:  
Generates and attaches transcripts to the podcast entries. If the transcript generation fails, the entry is removed from the list. The function processes each entry, downloads the MP3 file, generates the transcript, and returns the updated list of channels and entries with transcripts.

**Usage**:
```python
updated_pods = generate_and_attach_transcripts(pods_with_transcripts, total_entries)
```

---

#### `save_results`

**Purpose**:  
Saves the podcast entries with transcripts to both Pickle and JSON files. This ensures that the processed data is persisted in two formats for later use.

**Usage**:
```python
save_results(pods_with_transcripts, NEW_ENTRIES_WITH_TRANSCRIPTS_PICKLE, NEW_ENTRIES_WITH_TRANSCRIPTS_JSON)
```

---


## 3. About generate_summaries.py:
+ asdf

## 4. About update_db.py:
+ asdf

## 5. About main.py:
+ asdf

