import requests

# Base URL of the API
url_template = "http://localhost:8000/api/entries/{id}/"

# Loop through entry IDs 204 to 345
for entry_id in range(204, 346):
    # Format the URL with the current entry ID
    url = url_template.format(id=entry_id)
    
    # Send the DELETE request
    response = requests.delete(url)
    
    # Check if the request was successful
    if response.status_code == 204:
        print(f"Entry {entry_id} deleted successfully.")
    else:
        print(f"Failed to delete entry {entry_id}: {response.status_code} - {response.reason}")
