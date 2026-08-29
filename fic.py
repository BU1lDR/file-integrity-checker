import hashlib
import json
import sys
import logging
import re
from pathlib import Path

# --------------------------------------------------
# Configuration
# --------------------------------------------------

MONITORED_FOLDER = Path("test_data")
BASELINE_PATH = Path("baseline/baseline.json")
BASELINE_HASH_PATH = Path("baseline/baseline.sha256")
LOG_PATH = Path("logs/fic.log")


# --------------------------------------------------
# Configure LOGGING
# --------------------------------------------------

def setup_logging():

    LOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )



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
        logging.error(f"Could not read {file_path}: {error}")
        return None
    
    return hasher.hexdigest()



# --------------------------------------------------
# Scan a directory and calculate hashes
# --------------------------------------------------

def directory_scanner(folder):

    logging.info(f"Scanning directory: {folder}")


    file_hashes = {}
    errors = []

    for i in folder.rglob("*"):

        if i.is_file():

            file_hash = calculate_hash(i)

            relative_path = i.relative_to(folder)
            normalized_path = relative_path.as_posix()

            if file_hash is not None:
                file_hashes[normalized_path] = file_hash
            else:
                errors.append(normalized_path)

    logging.info(
        f"Scan completed. " 
        f"Files succesfully hashed: {len(file_hashes)}"
    )

    return file_hashes, errors



# --------------------------------------------------
# Save baseline to JSON
# --------------------------------------------------

def save_baseline(file_hashes, baseline_path):

    logging.info(f"Saving baseline to: {baseline_path}")

    baseline_data = {
        "version": 1,
        "algorithm": "sha256",
        "files": file_hashes
    }

    baseline_path.parent.mkdir(
        parents = True, 
        exist_ok = True
    )

    with open(baseline_path, "w") as file:
        json.dump(baseline_data, file, indent = 4)

    logging.info(f"Baseline saved successfully: {baseline_path}")



# --------------------------------------------------
# Loading + validating baseline from JSON
# --------------------------------------------------

def load_baseline(baseline_path):

    logging.info(f"Loading baseline: {baseline_path}")


    try:
        with open(baseline_path, "r") as file:
            baseline_data = json.load(file)


    except FileNotFoundError:
        print("[ERROR] Baseline file not found.")

        logging.error(f"Baseline file not found: {baseline_path}")
        return None


    except json.JSONDecodeError:
        print("[ERROR] Baseline file contains invalid JSON.")

        logging.error(f"Invalid JSON in baseline: {baseline_path}")
        return None

    
    if not validate_baseline(baseline_data):
        print("[ERROR] Baseline validation failed.")
        return None


    logging.info(
        "Baseline loaded successfully. "
        f"Files: {len(baseline_data['files'])}"
    )

    return baseline_data["files"]

# --------------------------------------------------
# Hash Validator
# --------------------------------------------------

def isValid_sha256(value):

    if not isinstance(value, str):
        return False

    return bool(
        re.fullmatch(
            r"[0-9a-fA-F]{64}",
            value
        )
    )


# --------------------------------------------------
# Complete validator (root_obj + version + algorithm + file + file_path + hash)
# --------------------------------------------------

def validate_baseline(baseline_data):

    if not isinstance(baseline_data, dict):

        logging.error(
            "Baseline root is not a JSON object."
        )

        return False

    version = baseline_data.get("version")

    if not isinstance(version, int) or isinstance(version, bool):

        logging.error(
            "Baseline version is not an integer."
        )

        return False

    if version != 1:

        logging.error(
            f"Unsupported baseline version: {version}"
        )

        return False

    algorithm = baseline_data.get("algorithm")

    if not isinstance(algorithm, str):

        logging.error(
            "Baseline algorithm is not a string."
        )

        return False

    if algorithm.lower() != "sha256":

        logging.error(
            f"Unsupported hashing algorithm: {algorithm}"
        )

        return False

    files = baseline_data.get("files")

    if not isinstance(files, dict):

        logging.error(
            "Baseline file data is not an object."
        )

        return False

    for file_path, file_hash in files.items():

        if not isinstance(file_path, str):

            logging.error(
                "Baseline contains a non-string file path."
            )

            return False

        if not file_path:

            logging.error(
                "Baseline contains an empty file path."
            )

            return False

        if "\\" in file_path:

            logging.error(
                f"Baseline contains non-normalized path: "
                f"{file_path}"
            )

            return False

        if file_path.startswith("/"):

            logging.error(
                f"Baseline contains absolute path: "
                f"{file_path}"
            )

            return False

        if len(file_path) >= 2 and file_path[1] == ":":

            logging.error(
                f"Baseline contains absolute path: "
                f"{file_path}"
            )

            return False

        if not isValid_sha256(file_hash):

            logging.error(
                f"Invalid SHA-256 hash for: "
                f"{file_path}"
            )

            return False

    return True



# --------------------------------------------------
# Saving the baseline hash
# --------------------------------------------------

def save_baseline_hash():

    baseline_hash = calculate_hash(BASELINE_PATH)

    if baseline_hash is None:

        logging.error("Could not calculate baseline hash.")
        return False

    try:
        with open(BASELINE_HASH_PATH, "w") as file:
            file.write(baseline_hash)

    except OSError as error:

        logging.error(f"Could not save baseline hash: {error}")
        return False

    logging.info("Baseline hash saved successfully")

    return True



# --------------------------------------------------
# Verifying the baseline hash
# --------------------------------------------------

def verify_baseline_hash():

    if not BASELINE_HASH_PATH.exists():
        print("[ERROR] Baseline hash file not found.")

        logging.error("Baseline hash file not found.")
        return False

    try:
        with open(BASELINE_HASH_PATH, "r") as file:
            expected_hash = file.read().strip()

    except OSError as error:
        print("[ERROR] Could not read baseline hash.")

        logging.error(
            f"Could not read baseline hash: {error}"
        )
        return False


    if not isValid_sha256(expected_hash):
        print("[ERROR] Baseline hash file is invalid.")

        logging.error("Baseline hash file contains an invalid SHA-256 hash.")
        return False


    actual_hash = calculate_hash(BASELINE_PATH)

    if actual_hash is None:
        print("[ERROR] Could not calculate baseline hash.")
        return False

    if actual_hash != expected_hash:
        print("[ALERT] Baseline has been modified!")

        logging.critical("Baseline integrity verification failed.")
        return False

    logging.info("Baseline integrity verified successfully.")

    return True



# --------------------------------------------------
# Compare baseline with current scan
# --------------------------------------------------

def compare_files(baseline, current, scan_errors):

    results = {
        "unchanged": [],
        "modified": [],
        "new": [],
        "deleted": [],
        "scan_error": []
    }

    scan_error_set = set(scan_errors)

    # Record scan errors
    for file_path in scan_errors:
        results["scan_error"].append(file_path)

        logging.error(
            f"File could not be scanned: {file_path}"
        )


    # Check current files against baseline
    for file_path, current_hash in current.items():

        if file_path in baseline:

            if baseline[file_path] == current_hash:
                results["unchanged"].append(file_path)
            else:
                results["modified"].append(file_path)

                logging.warning(f"File modified: {file_path}")

    
        else:
            results["new"].append(file_path)

            logging.warning(f"New file detected: {file_path}")


    # Check baseline files against current scan
    for file_path in baseline:

        if file_path not in current:

            if file_path in scan_error_set:
                continue

            results["deleted"].append(file_path)

            logging.warning(f"File deleted: {file_path}")


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

    for file_path in results["scan_error"]:
        print(f"[SCAN ERROR] {file_path}")

    print()
    print("Integrity Check Summary")
    print("-----------------------")

    print(f"Unchanged:   {len(results['unchanged'])}")
    print(f"Modified:    {len(results['modified'])}")
    print(f"New:         {len(results['new'])}")
    print(f"Deleted:     {len(results['deleted'])}")
    print(f"Scan errors: {len(results['scan_error'])}")



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

    logging.info("Baseline creation started.")

    print("Creating baseline...")
    print()

    file_hashes, scan_errors = directory_scanner(MONITORED_FOLDER)

    if scan_errors:
        print()
        print("[ERROR] Baseline was not created because some files could not be scanned.")
        logging.error(
        "Baseline creation aborted because "
        "some files could not be scanned."
        )

        display_scan_errors(scan_errors)

        return

    save_baseline(file_hashes, BASELINE_PATH) #baseline is only created when the scan is complete.

    if not save_baseline_hash():
        print("[ERROR] Baseline protection failed.")

        logging.error("Baseline protection failed.")
        return

    
    print()
    print(
        f"Baseline created for "
        f"{len(file_hashes)} files."
    )
    logging.info(
        f"Baseline created for "
        f"{len(file_hashes)} files."
    )

# --------------------------------------------------
# Check current files against baseline
# --------------------------------------------------

def check_integrity():

    logging.info("Integrity check started.")

    print("Checking file integrity...")
    print()

    if not verify_baseline_hash():
        print()
        print("Integrity check aborted.")
        return

    baseline = load_baseline(BASELINE_PATH)

    if baseline is None:
        print()
        print("Create a baseline first with:")
        print("    python fic.py init")

        logging.error("Integrity check aborted because baseline could not be loaded.")

        return

    current, scan_errors = directory_scanner(MONITORED_FOLDER)

    results = compare_files(baseline, current, scan_errors)

    display_results(results)

    display_scan_errors(scan_errors)

    logging.info(
        "Integrity check completed. "
        f"Unchanged={len(results['unchanged'])}, "
        f"Modified={len(results['modified'])}, "
        f"New={len(results['new'])}, "
        f"Deleted={len(results['deleted'])}, "
        f"ScanErrors={len(results['scan_error'])}"
    )


# --------------------------------------------------
# ************** Main program **************
# --------------------------------------------------

def main():

    setup_logging()

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