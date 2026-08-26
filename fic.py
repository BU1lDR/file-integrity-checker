import hashlib
from pathlib import Path

def calculate_hash(file_path):
    hasher = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(4096):
            hasher.update(chunk)

    return hasher.hexdigest()


folder = Path("test_data")

for i in folder.rglob("*"):
    if i.is_file():
        file_hash = calculate_hash(i)

        print("File:", i)
        print("Hash:", file_hash)