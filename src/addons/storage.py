import json

class FileStoragePlugin:
    def __init__(self, path="contacts.json"):
        self.path = path

    def save(self, data):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=4)
