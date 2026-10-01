import os
import time
import requests
import json

# Setup parameters
CUBE_URL = "http://ekanite.tch.harvard.edu:32223/api/v1"
TOKEN = os.environ["CUBE_TOKEN"]  # never commit a live token
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# The target MPRAGE folder path discovered in CUBE
# e.g. "SERVICES/PACS/PACSDCM/<MRN>-<PATIENT_NAME>-<DOB>/<STUDY>-<ACCESSION>-<STUDY_DATE>/<SERIES>-SAGT1_MPRAGE"
TARGET_DIR = os.environ["CUBE_TARGET_DIR"]

def get_plugin_id_and_url(plugin_name):
    print(f"Searching for plugin: {plugin_name}...")
    url = f"{CUBE_URL}/plugins/search/?name_exact={plugin_name}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    items = resp.json()["collection"]["items"]
    if not items:
        raise ValueError(f"Plugin {plugin_name} not found!")
    
    plugin_data = items[0]["data"]
    plugin_id = next(x["value"] for x in plugin_data if x["name"] == "id")
    plugin_href = items[0]["href"]
    
    # We also need instances url
    links = items[0]["links"]
    instances_url = next(x["href"] for x in links if x["rel"] == "instances")
    
    print(f"Found {plugin_name}: ID={plugin_id}, instances_url={instances_url}")
    return plugin_id, instances_url

def poll_instance_status(instance_url):
    print(f"Polling instance status: {instance_url}")
    while True:
        resp = requests.get(instance_url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()["collection"]["items"][0]["data"]
        status = next(x["value"] for x in data if x["name"] == "status")
        print(f"Current status: {status}")
        if status in ["finishedSuccessfully", "errored", "cancelled"]:
            return status
        time.sleep(10)

def main():
    # 1. Locate plugins
    dircopy_id, dircopy_instances_url = get_plugin_id_and_url("pl-dircopy")
    fshack_id, fshack_instances_url = get_plugin_id_and_url("pl-fshack")
    
    # 2. Launch pl-dircopy to copy the directory and create the feed
    print("\n--- Step 1: Launching pl-dircopy ---")
    payload = {
        "template": {
            "data": [
                {"name": "dir", "value": TARGET_DIR},
                {"name": "title", "value": "MPRAGE_input_feed"},
                {"name": "compute_resource_name", "value": "argentum"}
            ]
        }
    }
    
    # Collection+JSON post
    resp = requests.post(dircopy_instances_url, headers=HEADERS, json=payload)
    if resp.status_code != 201:
        print(f"Error launching pl-dircopy: {resp.text}")
        resp.raise_for_status()
        
    dircopy_inst = resp.json()["collection"]["items"][0]
    dircopy_inst_id = next(x["value"] for x in dircopy_inst["data"] if x["name"] == "id")
    dircopy_inst_href = dircopy_inst["href"]
    print(f"Successfully launched pl-dircopy! Instance ID: {dircopy_inst_id}")
    
    # 3. Poll pl-dircopy
    status = poll_instance_status(dircopy_inst_href)
    if status != "finishedSuccessfully":
        print(f"pl-dircopy failed with status: {status}")
        return
        
    # 4. Launch pl-fshack
    print("\n--- Step 2: Launching pl-fshack ---")
    fshack_payload = {
        "template": {
            "data": [
                {"name": "previous_id", "value": str(dircopy_inst_id)},
                {"name": "title", "value": "FreeSurfer_Volumetrics"},
                {"name": "compute_resource_name", "value": "argentum"},
                {"name": "exec", "value": "recon-all"},
                {"name": "args", "value": "ARGS: -all -notalairach"},
                {"name": "inputFile", "value": ".dcm"},
                {"name": "outputFile", "value": "recon-output"},
                {"name": "threads", "value": 3},
                {"name": "no_fail", "value": False}
            ]
        }
    }
    
    resp = requests.post(fshack_instances_url, headers=HEADERS, json=fshack_payload)
    if resp.status_code != 201:
        print(f"Error launching pl-fshack: {resp.text}")
        resp.raise_for_status()
        
    fshack_inst = resp.json()["collection"]["items"][0]
    fshack_inst_id = next(x["value"] for x in fshack_inst["data"] if x["name"] == "id")
    fshack_inst_href = fshack_inst["href"]
    print(f"Successfully launched pl-fshack! Instance ID: {fshack_inst_id}")
    
    # 5. Poll pl-fshack status (it will take a while, but this script demonstrates the full loop)
    print("For a full FreeSurfer run, polling can take hours. Script will poll status once:")
    poll_instance_status(fshack_inst_href)

if __name__ == "__main__":
    main()
