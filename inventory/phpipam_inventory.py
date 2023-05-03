#!/usr/bin/env python

# Copyright (C) 2023  Ben Hart <ben.hart@jamf.com>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# The purpose behind this was as a custom inventory script to pull address:ip info from
# phpipam. On the Phpipam side it requires at least one custom_field named `custom_managed`
# with a value of `Yes`. We used a second custom_field comprised of a drop-down to define `Role`
# i.e. routers, switches, firewalls, etc. If present that field will create Host Groups.

import requests
import yaml
import json
import os
import argparse

# The ENV variables are set under the credential in AAP/Tower.

# Set the query variables, customize the filter_by and filter_value values to match your custom_fields.
# You can remove the custom_field below if you are querying for just one custom_field key:value pair

# the app_id is the 'name' of your API key
app_id = os.environ.get("IPAM_ID")
controller = "addresses"
action = "get"
filter_by = "custom_fields"
custom_field = "custom_managed"
filter_value = "Yes"
# Get the inventory file path from an environment variable, used when outputting inventory to
# a static file.
# inventory_file_path = os.environ.get('IPAMDEV_FILEPATH')


# ENV lookup for the query URL, for example
# "https://ipam.domain.com/api/?app_id={}&controller={}&action={}&filter_by={}&filter_by={}&filter_value={}"
# This URL makes use of PhpIpam's API filters; filter_by, and filter_value. This is how I query for
# custom_fields
url = os.environ.get("IPAM_QUERY").format(app_id, controller, action, filter_by, custom_field, filter_value)

# Set the headers to include the API key, the key type I use is a static key. Therefor it doesn't
# need to be requested each time, nor does it expire. Best used for testing and development, not prod.
api_key = os.environ.get("IPAM_TOKEN")
headers = {
    "token": api_key,
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)
print("*********************************************")
# Uncomment the below two lines to help when troublshooting to dump the contents of the API call to the console.

# response_dict = response.json()
# print(json.dumps(response_dict, indent=4))

if response.status_code != 200:
    raise ValueError(f"Failed to retrieve addresses: {response.content}")

response_dict = response.json()
addresses = response_dict["data"]

all_hosts = {}
custom_roles = {}

for address in addresses:
    ip_address = address["ip"]
    hostname = address.get("hostname", None)
    custom_role = address["custom_fields"].get("custom_role", None)
    custom_managed = address["custom_fields"].get("custom_managed", None)

    if hostname is None or hostname.strip() == "":
        hostname = ip_address

    if custom_role is not None and custom_role.strip() != "":
       if custom_role not in custom_roles:
            custom_roles[custom_role] = {"hosts": {}}
        custom_roles[custom_role]["hosts"][hostname] = {"ansible_host": ip_address}

    if custom_managed == "Yes":
        all_hosts[hostname] = {"ansible_host": ip_address}

inventory = {"all": {"hosts": all_hosts, "children": custom_roles}}

# Define the command-line arguments using argparse
parser = argparse.ArgumentParser(description="Generate Ansible inventory from PhpIpam")
parser.add_argument("--list", action="store_true", help="List all groups and hosts")
parser.add_argument("--host", help="Get all information about a specific host")
args = parser.parse_args()

if not args.list and not args.host:
    args.list = True

if args.host:
    # If --host is provided, return the details for that host
    if args.host in all_hosts:
        print(json.dumps(all_hosts[args.host], indent=2))
    else:
        print(f"No matching host found for {args.host}")
else:
    # If no arguments are passed, return the entire inventory
    print(json.dumps(inventory, indent=2))
