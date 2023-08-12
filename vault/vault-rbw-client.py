#!/usr/bin/env python3

# A handy script to load secrets from the local rbw (BitWarden) client.
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# (c) 2023, Ryszard Knop <rk@dragonic.eu>
#
# You can use this script with ansible-vault's `--vault-id id@vault-rbw-client.py`
# argument, for example `prod@vault-rbw-client.py` to run `rbw get ansible-vault-prod`.
# Make sure this script is executable first.
#
# The Vault ID passed to the script will replace {VAULT_ID} in the RBW_CREDENTIAL.
# You can optionally set the RBW_FOLDER for `rbw get --folder ...`.
# With no arguments, this runs `rbw get ansible-vault-default`.
#
# You can either edit the variables below directly, pass them as arguments,
# or set environment variables to configure this script.

import os
import sys
import argparse
import subprocess

RBW_DEFAULT_VAULT_ID = os.environ.get("RBW_DEFAULT_VAULT_ID", "default")
RBW_CREDENTIAL = os.environ.get("RBW_CREDENTIAL", "ansible-vault-{VAULT_ID}")
RBW_FOLDER = os.environ.get("RBW_FOLDER", None)
RBW_TRY_UNLOCK = os.environ.get("RBW_TRY_UNLOCK", True)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gets Ansible Vault credentials from the rbw Bitwarden client.",
    )

    parser.add_argument(
        "--vault-id",
        default=RBW_DEFAULT_VAULT_ID,
        help="Ansible Vault ID to look up (replaces {VAULT_ID} in the credential).",
    )
    parser.add_argument(
        "--credential",
        default=RBW_CREDENTIAL,
        help="Bitwarden credential to look up with rbw.",
    )
    parser.add_argument(
        "--folder",
        default=RBW_FOLDER,
        help="Bitwarden folder to look up credentials in.",
    )

    return parser.parse_args()


def try_unlock_vault() -> None:
    if isinstance(RBW_TRY_UNLOCK, str):
        can_unlock = RBW_TRY_UNLOCK.lower() in ("y", "yes", "t", "true", "on", "1")
    else:
        can_unlock = bool(RBW_TRY_UNLOCK)

    if can_unlock:
        try:
            subprocess.run(["rbw", "unlock"], check=True)
            return
        except subprocess.CalledProcessError:
            sys.exit(1)

    sys.exit(1)  # Locked, can't do anything about it, bye!


def get_credentials(vault_id, credential, folder):
    try:
        subprocess.run(["rbw", "unlocked"], check=True)
    except subprocess.CalledProcessError:
        try_unlock_vault()

    try:
        folder_args = [] if not folder else ["--folder", folder]
        rbw = subprocess.run(
            ["rbw", "get", *folder_args, credential.replace("{VAULT_ID}", vault_id)],
            check=True,
        )
    except subprocess.CalledProcessError:
        sys.exit(1)


if __name__ == "__main__":
    args = parse_args()
    get_credentials(args.vault_id, args.credential, args.folder)
