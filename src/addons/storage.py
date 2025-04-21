import json

def save_contacts_to_json(contacts: dict, filename: str = "contacts.json"):
    contacts_list = contacts.get("parties", [])

    if not contacts_list:
        print("No contacts to save.")
        return

    with open(filename, mode='w', encoding='utf-8') as file:
        json.dump(contacts_list, file, indent=4, ensure_ascii=False)

    print(f"Saved {len(contacts_list)} contacts to {filename}")
