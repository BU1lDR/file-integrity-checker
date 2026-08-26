import hashlib
import json
import sys
from pathlib import Path

# --------------------------------------------------
# Configuration
# --------------------------------------------------

MONITORED_FOLDER = Path("test_data")
BASELINE_PATH = Path("baseline/baseline.json")


# --------------------------------------------------
# Calculate SHA-256 hash of a file
# --------------------------------------------------

def calculate_hash(file_path):
    hasher = hashlib.sha256()

    try:
        with open(file_path, "rb") as file:
            while chunk := file.read(4096):
                hasher.update(chunk)

    except (FileNotFoundError, PermissionError) as error:
        print(f"[ERROR] Could not read {file_path}: {error}")
        return None
    
    return hasher.hexdigest()


# --------------------------------------------------
# Scan a directory and calculate hashes
# --------------------------------------------------

def directory_scanner(folder):
    file_hashes = {}
    errors = []

    for i in folder.rglob("*"):

        if i.is_file():

            file_hash = calculate_hash(i)

            if file_hash is not None:
                file_hashes[str(i)] = file_hash
            else:
                errors.append(str(i))

    return file_hashes, errors


# --------------------------------------------------
# Save baseline to JSON
# --------------------------------------------------

def save_baseline(file_hashes, baseline_path):

    baseline_path.parent.mkdir(parents = True, exist_ok = True)

    with open(baseline_path, "w") as file:
        json.dump(file_hashes, file, indent = 4)


# --------------------------------------------------
# Load baseline from JSON
# --------------------------------------------------

def load_baseline(baseline_path):

    try:
        with open(baseline_path, "r") as file:
            return json.load(file)

    except FileNotFoundError:
        print("[ERROR] Baseline file not found.")
        return None

    except json.JSONDecodeError:
        print("[ERROR] Baseline file contained invalid JSON.")
        return None


# --------------------------------------------------
# Compare baseline with current scan
# --------------------------------------------------

def compare_files(baseline, current):

    results = {
        "unchanged": [],
        "modified": [],
        "new": [],
        "deleted": []
    }

    # Check current files against baseline
    for file_path, current_hash in current.items():

        if file_path in baseline:

            if baseline[file_path] == current_hash:
                results["unchanged"].append(file_path)
            else:
                results["modified"].append(file_path)
    
        else:
            results["new"].append(file_path)

    # Check baseline files against current scan
    for file_path in baseline:

        if file_path not in current:
            results["deleted"].append(file_path)

    return results


# --------------------------------------------------
# Display comparison results
# --------------------------------------------------

def display_results(results):

    print()

    for file_path in results["unchanged"]:
        print(f"[UNCHANGED] {file_path}")
        
    for file_path in results["modified"]:
        print(f"[MODIFIED]  {file_path}")
        
    for file_path in results["new"]:
        print(f"[NEW]       {file_path}")
        
    for file_path in results["deleted"]:
        print(f"[DELETED]   {file_path}")

    print()
    print("Integrity Check Summary")
    print("-----------------------")

    print(f"Unchanged: {len(results['unchanged'])}")
    print(f"Modified:  {len(results['modified'])}")
    print(f"New:       {len(results['new'])}")
    print(f"Deleted:   {len(results['deleted'])}")

# --------------------------------------------------
# Display scan errors
# --------------------------------------------------

def display_scan_errors(errors):

    if not errors:
        return

    print()
    print("Files that could not be scanned")
    print("-------------------------------")

    for file_path in errors:
        print(f"[ERROR] {file_path}")


# --------------------------------------------------
# Initialize a new baseline
# --------------------------------------------------

def initialize():

    print("Creating baseline...")
    print()

    file_hashes, scan_errors = directory_scanner(MONITORED_FOLDER)

    save_baseline(file_hashes, BASELINE_PATH)

    print()
    print(f"Baseline created for {len(file_hashes)} files.")

    display_scan_errors(scan_errors)


# --------------------------------------------------
# Check current files against baseline
# --------------------------------------------------

def check_integrity():

    print("Checking file integrity...")
    print()

    baseline = load_baseline(BASELINE_PATH)

    if baseline is None:
        print()
        print("Create a baseline first with:")
        print("    python fic.py init")
        return

    current, scan_errors = directory_scanner(MONITORED_FOLDER)

    results = compare_files(baseline, current)

    display_results(results)

    display_scan_errors(scan_errors)


# --------------------------------------------------
# ************** Main program **************
# --------------------------------------------------

def main():

    if len(sys.argv) < 2:

        print("File Integrity Checker")
        print()
        print("Usage:")
        print("    python fic.py init")
        print("    python fic.py check")

        return


    command = sys.argv[1].lower()

    if command == "init":
        initialize()

    elif command == "check":
        check_integrity()

    else:
        print(f"[ERROR] Unknown command: {command}")
        print()
        print("Usage:")
        print("    python fic.py init")
        print("    python fic.py check")


if __name__ == "__main__":
    main()