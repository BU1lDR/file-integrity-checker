import hashlib
import json
from pathlib import Path

def calculate_hash(file_path):
    hasher = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(4096):
            hasher.update(chunk)

    return hasher.hexdigest()


def directory_scanner(folder):
    file_count = 0 # File counter initilization
    file_hashes = {} # dictionary initialization
    for i in folder.rglob("*"):
        if i.is_file():

            file_count += 1 # File counter increment

            file_hashes[str(i)] = file_hash

            file_hash = calculate_hash(i)

            print(f"[FILE] {i}")
            print(f"       SHA-256: {file_hash}")
            print(f"       Size: {i.stat().st_size} bytes") # File metadata(size)
            print()

    print(f"{file_count} files scanned")

    return file_hashes

folder = Path("test_data")
baseline = directory_scanner(folder)