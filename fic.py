import hashlib
from pathlib import Path

def calculate_hash(file_path):
    hasher = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(4096):
            hasher.update(chunk)

    return hasher.hexdigest()


folder = Path("test_data")

file_count = 0
for i in folder.rglob("*"):
    if i.is_file():

        file_count += 1 # A file counter

        file_hash = calculate_hash(i)

        print(f"[FILE] {i}")
        print(f"       SHA-256: {file_hash}")
        print()

print(f"{file_count} files scanned")