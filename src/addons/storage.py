from datetime import datetime, timedelta
import json
import os
from typing import Optional, Dict, Any

TOKEN_FILE_PATH = "tokens.json"
STATE_FILE_PATH = "states.json"


from datetime import datetime, timedelta
import json
import os
from typing import Optional, Dict, Any



def save_tokens_to_json(tokens: Dict[str, Any], crm_name: str):
    if "expires_in" in tokens and "expires_at" not in tokens:
        expires_at = datetime.now() + timedelta(seconds=tokens["expires_in"])
        tokens["expires_at"] = expires_at.isoformat()

    all_tokens = {}
    if os.path.exists(TOKEN_FILE_PATH):
        with open(TOKEN_FILE_PATH, "r") as file:
            all_tokens = json.load(file)

    # Add a timestamp for last authentication
    tokens["last_authenticated"] = datetime.now().isoformat()

    all_tokens[crm_name] = {
        "status": "success",
        **tokens
    }

    with open(TOKEN_FILE_PATH, "w") as file:
        json.dump(all_tokens, file, indent=4)

    print(f"Tokens saved under '{crm_name}' in {TOKEN_FILE_PATH}")
    
def get_stored_tokens(crm_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve stored tokens for a specific CRM (or the most recently used CRM if none specified)."""
    if not os.path.exists(TOKEN_FILE_PATH):
        print("No token file found")
        return None

    try:
        with open(TOKEN_FILE_PATH, "r") as file:
            all_tokens = json.load(file)

        # If CRM is specified, return its tokens
        if crm_name:
            crm_name = crm_name.lower()
            if crm_name not in all_tokens:
                print(f"No tokens found for {crm_name}")
                return None
            token_data = all_tokens[crm_name]
            token_data["crm_name"] = crm_name
            return token_data

        # If no CRM specified, find the most recently authenticated one
        latest_token = None
        latest_auth_time = None

        for name, token_data in all_tokens.items():
            if not token_data:
                continue

            auth_time_str = token_data.get("last_authenticated")
            if not auth_time_str:
                continue  # Skip if no auth time recorded

            auth_time = datetime.fromisoformat(auth_time_str)

            if latest_auth_time is None or auth_time > latest_auth_time:
                latest_auth_time = auth_time
                latest_token = token_data
                latest_token["crm_name"] = name

        return latest_token

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


# New functions for state management (without clearing)
def save_state(state: str, crm_name: str) -> None:
    """Save the state parameter for OAuth CSRF protection"""
    all_states = {}
    if os.path.exists(STATE_FILE_PATH):
        with open(STATE_FILE_PATH, "r") as file:
            all_states = json.load(file)
    
    # Store state with timestamp for expiration checking
    all_states[crm_name] = {
        "state": state,
        "created_at": datetime.now().isoformat()
    }
    
    with open(STATE_FILE_PATH, "w") as file:
        json.dump(all_states, file, indent=4)
    
    print(f"State saved for {crm_name}")


def get_state(crm_name: str) -> Optional[str]:
    """
    Retrieve the stored state for the specified CRM.
    Returns None if state doesn't exist or is expired (10 min limit).
    """
    if not os.path.exists(STATE_FILE_PATH):
        print("No state file found")
        return None
    
    try:
        with open(STATE_FILE_PATH, "r") as file:
            all_states = json.load(file)
        
        if crm_name not in all_states:
            print(f"No state found for {crm_name}")
            return None
        
        state_data = all_states[crm_name]
        created_at = datetime.fromisoformat(state_data["created_at"])
        
        # Check if state has expired (10 minutes)
        if datetime.now() - created_at > timedelta(minutes=10):
            print(f"State for {crm_name} has expired")
            return None
        
        return state_data["state"]
    
    except Exception as e:
        print(f"Error retrieving state: {e}")
        return None