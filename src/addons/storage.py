from datetime import datetime, timedelta
import json
import os
from typing import Optional, Dict, Any

TOKEN_FILE_PATH = "tokens.json"

def save_tokens_to_json(tokens: Dict[str, Any]) -> None:
    """Save tokens to JSON file with proper expiration time."""
    # Ensure we have an expiration time
    if 'expires_in' in tokens and 'expires_at' not in tokens:
        expires_at = datetime.now() + timedelta(seconds=tokens['expires_in'])
        tokens['expires_at'] = expires_at.isoformat()
    
    # Save all token data
    with open(TOKEN_FILE_PATH, 'w') as file:
        json.dump({"access_token_response": tokens}, file, indent=4)
    print(f"Tokens saved to {TOKEN_FILE_PATH}")

def get_stored_tokens() -> Optional[Dict[str, Any]]:
    """Retrieve stored tokens, automatically refresh if expired."""
    if not os.path.exists(TOKEN_FILE_PATH):
        print("No token file found")
        return None

    try:
        with open(TOKEN_FILE_PATH, 'r') as file:
            data = json.load(file)
            token_data = data.get("access_token_response", {})
            
            if not token_data:
                print("No token data found in file")
                return None

            # Check if token is expired
            expires_at = token_data.get("expires_at")
            if expires_at:
                expiration_time = datetime.fromisoformat(expires_at)
                if datetime.now() < expiration_time:
                    print("Valid token found")
                    return token_data
                else:
                    print("Token expired")

            # Try to refresh if we have a refresh token
            refresh_token = token_data.get("refresh_token")
            if refresh_token:
                print("Attempting to refresh token...")
                from addons.integration.plugins.capsule import refresh_access_token
                new_tokens = refresh_access_token(refresh_token)
                if new_tokens:
                    save_tokens_to_json(new_tokens)
                    return new_tokens
                else:
                    print("Failed to refresh token")
            else:
                print("No refresh token available")

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


def clear_tokens() -> bool:
    """Remove the token file if it exists"""
    try:
        if os.path.exists(TOKEN_FILE_PATH):
            os.remove(TOKEN_FILE_PATH)
            return True
        return False
    except Exception as e:
        print(f"Error removing token file: {e}")
        return False