import hashlib
import json
import sys
from pathlib import Path

def calculate_hash(file_path):
    hasher = hashlib.sha256()

    # perform operation, if the operation is a succes -> continue ; error -> handle error
    try:
        with open(file_path, "rb") as file:
            while chunk := file.read(4096):
                hasher.update(chunk)

    except (FileNotFoundError, PermissionError) as error:
        print(f"[ERROR] Could not read {file_path}: {error}")
        return None
    
    return hasher.hexdigest()


def directory_scanner(folder):
    file_count = 0 # File counter initilization
    file_hashes = {} # dictionary initialization

    for i in folder.rglob("*"):
        if i.is_file():

            file_count += 1 # File counter increment

            file_hash = calculate_hash(i)

            if file_hash is not None:
                file_hashes[str(i)] = file_hash

            print(f"[FILE] {i}")
            print(f"       SHA-256: {file_hash}")
            print(f"       Size: {i.stat().st_size} bytes") # File metadata(size)
            print()

    print(f"{file_count} files scanned")

    return file_hashes


def save_baseline(file_hashes, baseline_path):
    with open(baseline_path, "w") as file:
        json.dump(file_hashes, file, indent = 4)


def load_baseline(baseline_path):
    with open(baseline_path, "r") as file:
        return json.load(file)


def compare_files(baseline, current):

    results = {
        "unchanged": [],
        "modified": [],
        "new": [],
        "deleted": []
    }

    for file_path, current_hash in current.items():

        if file_path in baseline:

            if baseline[file_path] == current_hash:
                results["unchanged"].append(file_path)
            else:
                results["modified"].append(file_path)
    
        else:
            results["new"].append(file_path)

    for file_path in baseline:

        if file_path not in current:
            results["deleted"].append(file_path)

    return results


def display_results(results):
    
    for file_path in results["unchanged"]:
        print(f"[UNCHANGED] {file_path}")
        
    for file_path in results["modified"]:
        print(f"[MODIFIED]  {file_path}")
        
    for file_path in results["new"]:
        print(f"[NEW]       {file_path}")
        
    for file_path in results["deleted"]:
        print(f"[DELETED]   {file_path}")


folder = Path("test_data")
baseline_path = Path("baseline/baseline.json")


if len(sys.argv) < 2:
    print("Usage: python fic.py [init|check]")
    sys.exit(1)

command = sys.argv[1]

if command == "init":
    print("Creating baseline...")

    file_hashes = directory_scanner(folder)

    save_baseline(file_hashes, baseline_path)

    print("Baseline created.")


elif command == "check":
    print("Checking file integrity...")

    baseline = load_baseline(baseline_path)

    current = directory_scanner(folder)

    compare_files(baseline, current)


else:
    print("Unknown command.")
    print("Usage: python fic.py [init|check]")