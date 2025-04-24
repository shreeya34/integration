from datetime import datetime, timedelta
import json
import os
from typing import Optional, Dict, Any

TOKEN_FILE_PATH = "tokens.json"


def save_tokens_to_json(tokens: Dict[str, Any], crm_name: str):
    if "expires_in" in tokens and "expires_at" not in tokens:
        expires_at = datetime.now() + timedelta(seconds=tokens["expires_in"])
        tokens["expires_at"] = expires_at.isoformat()

    # Load existing tokens if the file exists
    all_tokens = {}
    if os.path.exists(TOKEN_FILE_PATH):
        with open(TOKEN_FILE_PATH, "r") as file:
            all_tokens = json.load(file)

    # Save tokens under the CRM name
    all_tokens[crm_name] = {
        "status": "success",
        **tokens
    }

    with open(TOKEN_FILE_PATH, "w") as file:
        json.dump(all_tokens, file, indent=4)

    print(f"Tokens saved under '{crm_name}' in {TOKEN_FILE_PATH}")

def get_stored_tokens() -> Optional[Dict[str, Any]]:
    """Retrieve stored tokens, auto-refresh if expired."""
    if not os.path.exists(TOKEN_FILE_PATH):
        print("No token file found")
        return None

    try:
        with open(TOKEN_FILE_PATH, "r") as file:
            data = json.load(file)

            # We assume only one CRM is stored at a time.
            for crm_name, token_data in data.items():
                if not token_data:
                    continue

                # Check expiry
                expires_at = token_data.get("expires_at")
                if expires_at and datetime.now() < datetime.fromisoformat(expires_at):
                    print(f"Valid token found for {crm_name}")
                    token_data["crm_name"] = crm_name
                    return token_data
                else:
                    print("Token expired")

                refresh_token = token_data.get("refresh_token")
                if refresh_token:
                    print(f"Refreshing token for {crm_name}...")
                    from addons.integration.plugins.capsule import refresh_access_token
                    new_tokens = refresh_access_token(refresh_token)
                    if new_tokens:
                        save_tokens_to_json(new_tokens, crm_name)
                        new_tokens["crm_name"] = crm_name
                        return new_tokens
                    else:
                        print("Failed to refresh token")
            print("No valid token found")
            return None

    except Exception as e:
        print(f"Error reading token file: {e}")
        return None



def save_contacts_to_json(contacts: dict, filename: str = "contacts.json"):
    contacts_list = contacts.get("parties", [])
    if not contacts_list:
        print("No contacts to save.")
        return
    with open(filename, mode="w", encoding="utf-8") as file:
        json.dump(contacts_list, file, indent=4, ensure_ascii=False)
    print(f"Saved {len(contacts_list)} contacts to {filename}")


def clear_tokens(crm_name: Optional[str] = None) -> bool:
    try:
        if os.path.exists(TOKEN_FILE_PATH):
            if crm_name:
                with open(TOKEN_FILE_PATH, "r") as file:
                    data = json.load(file)
                if crm_name in data:
                    del data[crm_name]
                    with open(TOKEN_FILE_PATH, "w") as file:
                        json.dump(data, file, indent=4)
                    print(f"Token for '{crm_name}' removed")
                    return True
                print(f"No token found for '{crm_name}' to remove")
                return False
            else:
                os.remove(TOKEN_FILE_PATH)
                print("All tokens cleared")
                return True
        return False
    except Exception as e:
        print(f"Error removing token(s): {e}")
        return False
