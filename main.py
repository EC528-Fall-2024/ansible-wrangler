# The main file to setup all the APIs and code structures

import requests 
from requests.auth import HTTPBasicAuth
import json
import os

# Connect to SerivceNow API
# ServiceNow Instance Profile
instance = 'https://dev265596.service-now.com'
username = 'admin'
password = 'e8*cNsMy6R-N'

endpoint = '/api/now/table/incident'
user_endpoint = '/api/now/table/sys_user'

# Form the complete URL with filters and ordering by number in ascending order
user_name = 'System Administrator'  # desired user name to find the sys_id
url = instance + user_endpoint + "?sysparm_query=name=" + user_name

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))

# This prints out the system_id of the user: 
# could later turn this into a function that returns the system_id
if response.status_code == 200:
    data = response.json()
    if len(data['result']) > 0:
        caller_sys_id = data['result'][0]['sys_id']
        print("Caller sys_id:", caller_sys_id)
    else:
        print("User not found")
else:
    print(f"Error: {response.status_code}, {response.text}")
    

# Updated filter query using the sys_id
filter_query = f"caller_id={caller_sys_id}^active=true^universal_requestISEMPTY"
url = instance + endpoint + "?sysparm_query=" + filter_query

# Continue with making the API request...
response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))

# Check the response status and parse data
# This is for the incidents since now we have the sys_id
if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=4))
else:
    print(f"Error: {response.status_code}, {response.text}")