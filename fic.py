import hashlib
import json
import sys
import logging
import re
import os
import argparse
from pathlib import Path

# --------------------------------------------------
# Configuration
# --------------------------------------------------

MONITORED_FOLDER = Path("test_data")
BASELINE_PATH = Path("baseline/baseline.json")
LOG_PATH = Path("logs/fic.log")

#---------------------------------------------------
# Defining exit codes
# --------------------------------------------------

EXIT_SUCCESS = 0
EXIT_INTEGRITY_FAILURE = 1
EXIT_ERROR = 2
# 0- PASS
# 1- VIOLATION
# 2- ERROR



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
# Exclusion path validation
# --------------------------------------------------

def validate_exclusion(exclusion):

    path = Path(exclusion)

    #Absolute-paths not allowed
    if path.is_absolute():
        return False

    #Parent-directory traversal not allowed
    for part in path.parts:

        if part == "..":
            return False

    return True


# --------------------------------------------------
# All exclusions validation
# --------------------------------------------------

def validate_exclusions(exclusions):

    for exclusion in exclusions:

        if not validate_exclusion(exclusion):
            print(
                f"[ERROR] Invalid "
                f"exclusion: {exclusion}"
            )

            logging.error(
                f"Invalid exclusion: "
                f"{exclusion}"
            )

            return False

    return True



# --------------------------------------------------
#  Relative path normalization
# --------------------------------------------------

def normalize_relative_path(file_path,root_folder):

    relative_path = file_path.relative_to(root_folder)
    return relative_path.as_posix()



# --------------------------------------------------
# Determination of whether a path is excluded or not?
# --------------------------------------------------

def is_excluded(file_path, root_folder, exclusions):

    relative_path = (file_path.relative_to(root_folder))

    normalized_path = (relative_path.as_posix())


    for exclusion in exclusions:

        exclusion_path = (Path(exclusion))

        #EXACT MATCH
        if normalized_path == (exclusion_path.as_posix()):
            return True

        #DIRECTORY MATCH
        if normalized_path.startswith(exclusion_path.as_posix() + "/"):
            return True


    return False



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

def directory_scanner(folder, exclusions = None):

    if exclusions is None:
        exclusions = []

    logging.info(f"Scanning directory: {folder}")

    logging.info(f"Exclusions: {exclusions}")


    file_hashes = {}
    errors = []
    symlinks_skipped = 0

    for root, directories, files  in os.walk(
        folder,
        topdown = True,
        followlinks  = False
    ):
        root_path = Path(root)

    #*HANDLING DIRECTORIES*
        #REMOVING EXCLUDED DIRECTORIES
        directories_to_remove = []

        for directory in directories:
            directory_path = (
                root_path / directory
            )

            #Skipping symbolic-link directories
            if directory_path.is_symlink():
                directories_to_remove.append(directory)

                symlinks_skipped += 1

                logging.info(
                    f"Skipping symbolic "
                    f"directory link: "
                    f"{directory_path}"
                )

                continue

            #Skipping exclude directories
            if is_excluded(
                directory_path,
                folder,
                exclusions
            ):
                directories_to_remove.append(directory)

                logging.info(
                    f"Skipping excluded "
                    f"directory: "
                    f"{directory_path}"
                )


        for directory in directories_to_remove:

            directory_path = (root_path / directory)

            directories.remove(directory)

            logging.info(
                f"Skipping excluded "
                f"directory: "
                f"{root_path / directory}"
            )

        #PROCESS FILES
        for file_name in files:
            file_path = (root_path / file_name)

            #Skipping symbolic links
            if file_path.is_symlink():
                symlinks_skipped += 1

                logging.info(
                    "Skipping symbolic link: "
                    f"{file_path}"
                )

                continue

            #Check exclusions
            if is_excluded(file_path, folder, exclusions):
                continue

            #Confirm regular file
            if not file_path.is_file():
                continue

            #Calculate hash
            file_hash = calculate_hash(file_path)

            normalized_path = normalize_relative_path(file_path, folder)

            if file_hash is not None:
                file_hashes[normalized_path] = file_hash
            else:
                errors.append(normalized_path)

    logging.info(
        f"Scan completed. "
        f"Files successfully hashed: "
        f"{len(file_hashes)}, "
        f"Symlinks skipped: "
        f"{symlinks_skipped}, "
        f"Errors: "
        f"{len(errors)}"
    )

    return ( 
        file_hashes,
        errors,
        symlinks_skipped
    )



# --------------------------------------------------
# Save baseline to JSON
# --------------------------------------------------

def save_baseline(file_hashes, baseline_path, exclusions):

    logging.info(f"Saving baseline to: {baseline_path}")

    baseline_data = {
        "version": 2,
        "algorithm": "sha256",
        "exclusions": exclusions,
        "files": file_hashes
    }

    baseline_path.parent.mkdir(
        parents = True, 
        exist_ok = True
    )

    temporary_path = (
        baseline_path.with_suffix(
            baseline_path.suffix + ".tmp"
        )
    )

    try:
        #Writing the new baseline to a temporary file
        with open(temporary_path, "w", encoding  = "utf-8") as file:
            json.dump(baseline_data, file, indent = 4)
            file.flush()
            os.fsync(file.fileno())

            #automatically replace the old baseline
            os.replace(temporary_path, baseline_path)

    except OSError as error:

        logging.error(f"Could not save baseline: {error}")

        #Removing temporary files(if they remain)
        try:
            if temporary_path.exists():
                temporary_path.unlink()

        except OSError as cleanup_error:

            logging.error(
                f"Could not remove temporary baseline file: {cleanup_error}"
            )

        return False

    except (TypeError, ValueError) as error:

        logging.error(f"Could not serialize baseline: {error}")

        try:
            if temporary_path.exists():
                temporary_path.unlink()

        except OSError as cleanup_error:

            logging.error(
                f"Could not remove temporary baseline file: {cleanup_error}"
                )

        return False

    logging.info(f"Baseline saved successfully: {baseline_path}")

    return True



# --------------------------------------------------
# SHA-256 Hash Validator
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

    #ROOT OBJECT VALIDATOR
    if not isinstance(baseline_data, dict):

        logging.error(
            "Baseline root is not a JSON object."
        )

        return False

    #VERSION VALIDATOR
    version = baseline_data.get("version")

    if not isinstance(version, int) or isinstance(version, bool):

        logging.error(
            "Baseline version is not an integer."
        )

        return False

    if version != 2:

        logging.error(
            f"Unsupported baseline version: {version}"
        )

        return False

    #ALGORITHM VALIDATOR
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

    exclusions = baseline_data.get("exclusions")

    if not isinstance(exclusions,list):
        logging.error(
            "Baseline exclusions are "
            "not a list."
        )

        return False

    for exclusion in exclusions:

        if not isinstance(
            exclusion,
            str
        ):

            logging.error(
                "Baseline contains a "
                "non-string exclusion."
            )

            return False


        if not exclusion:

            logging.error(
                "Baseline contains an "
                "empty exclusion."
            )

            return False


        if not validate_exclusion(
            exclusion
        ):

            logging.error(
                f"Invalid baseline "
                f"exclusion: {exclusion}"
            )

            return False

    #FILE OBJECT VALIDATOR
    files = baseline_data.get("files")

    if not isinstance(files, dict):

        logging.error(
            "Baseline file data is not an object."
        )

        return False

    #FILE ENTRY VALIDATOR
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
# Loading baseline from JSON
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

    #VALIDATING STRUCTURE
    if not validate_baseline(baseline_data):
        print("[ERROR] Baseline validation failed.")
        return None


    logging.info(
        "Baseline loaded successfully. "
        f"Files: {len(baseline_data['files'])}"
    )

    return (
        baseline_data["files"],
        baseline_data["exclusions"]
    )



# --------------------------------------------------
# Baseline hash path (HELPER)
# --------------------------------------------------

def get_baseline_hash_path(baseline_path):

    return baseline_path.with_suffix(".sha256")



# --------------------------------------------------
# Saving the baseline hash
# --------------------------------------------------

def save_baseline_hash(baseline_path):

    baseline_hash_path = (get_baseline_hash_path(baseline_path))

    baseline_hash = calculate_hash(baseline_path)

    if baseline_hash is None:

        logging.error("Could not calculate baseline hash.")
        return False

    try:
        baseline_hash_path.parent.mkdir(
            parents = True,
            exist_ok = True
        )

        with open(baseline_hash_path, "w") as file:
            file.write(baseline_hash)

    except OSError as error:

        logging.error(f"Could not save baseline hash: {error}")
        return False

    logging.info(
        f"Baseline hash saved successfully: "
        f"{baseline_hash_path}"
    )

    return True



# --------------------------------------------------
# Verifying the baseline hash
# --------------------------------------------------

def verify_baseline_hash(baseline_path):

    baseline_hash_path = (get_baseline_hash_path(baseline_path))

    if not baseline_hash_path.exists():
        print("[ERROR] Baseline hash file not found.")

        logging.error("Baseline hash file not found.")
        return False

    try:
        with open(baseline_hash_path, "r") as file:
            expected_hash = file.read().strip()

    except OSError as error:
        print("[ERROR] Could not read baseline hash.")

        logging.error(
            f"Could not read baseline hash: {error}"
        )
        return False

    #VALIDATING STORED HASH
    if not isValid_sha256(expected_hash):
        print("[ERROR] Baseline hash file is invalid.")

        logging.error("Baseline hash file contains an invalid SHA-256 hash.")
        return False

    #CALCULATING CURRENT HASH
    actual_hash = calculate_hash(baseline_path)

    if actual_hash is None:
        print("[ERROR] Could not calculate baseline hash.")
        return False

    #COMPARING HASHES
    if actual_hash != expected_hash:
        print("[ALERT] Baseline has been modified!")

        logging.critical("Baseline integrity verification failed.")
        return False

    logging.info("Baseline integrity verified successfully.")

    return True



# --------------------------------------------------
# Compare exclusions
# --------------------------------------------------

def exclusions_match(expected,supplied):

    expected_set = set(expected)

    supplied_set = set(supplied)

    return (expected_set == supplied_set)



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
# Display integrity results
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
# Initialize a new baseline (INIT)
# --------------------------------------------------

def initialize(monitored_folder, baseline_path, exclusions):

    logging.info(
        f"Baseline creation started. "
        f"Folder={monitored_folder}, "
        f"Baseline={baseline_path}, "
        f"Exclusions={exclusions}"
    )

    print("Creating baseline...")
    print()

    #Validate exclusions
    if not validate_exclusions(exclusions):
        return EXIT_ERROR

    #Verify monitored folder
    if not monitored_folder.exists():
        print(
            f"[ERROR] Monitored folder "
            f"does not exist: "
            f"{monitored_folder}"
        )

        logging.error(
            f"Monitored folder does "
            f"not exist: "
            f"{monitored_folder}"
        )

        return EXIT_ERROR

    if not monitored_folder.is_dir():
        print(
            f"[ERROR] Monitored path "
            f"is not a directory: "
            f"{monitored_folder}"
        )

        logging.error(
            f"Monitored path is not "
            f"a directory: "
            f"{monitored_folder}"
        )

        return EXIT_ERROR

    #Scan directory
    (file_hashes, scan_errors, symlinks_skipped) = directory_scanner(monitored_folder, exclusions)

    #Abort if scan was incomplete
    if scan_errors:
        print()
        print("[ERROR] Baseline was not created because some files could not be scanned.")

        logging.error(
        "Baseline creation aborted because "
        "some files could not be scanned."
        )

        display_scan_errors(scan_errors)

        return EXIT_ERROR

    #Save baseline
    save_baseline(file_hashes, baseline_path, exclusions) 

    #Protect baseline
    if not save_baseline_hash(baseline_path):
        print("[ERROR] Baseline protection failed.")

        logging.error("Baseline protection failed.")
        return EXIT_ERROR

    
    print()
    print(
        f"Baseline created for "
        f"{len(file_hashes)} files."
    )
    print(
        f"Symbolic links skipped: "
        f"{symlinks_skipped}"
    )

    logging.info(
        f"Baseline created for "
        f"{len(file_hashes)} files."
    )

    return EXIT_SUCCESS



# --------------------------------------------------
# Check Integrity (CHECK)
# --------------------------------------------------

def check_integrity(monitored_folder, baseline_path, exclusions):

    logging.info(
        f"Integrity check started. "
        f"Folder={monitored_folder}, "
        f"Baseline={baseline_path}"
        f"Exclusions={exclusions}"
    )

    print("Checking file integrity...")
    print()

    #Validate exclusions
    if not validate_exclusions(exclusions):
        return EXIT_ERROR

    #Verify monitored folder
    if not monitored_folder.exists():
        print(
            f"[ERROR] Monitored folder "
            f"does not exist: "
            f"{monitored_folder}"
        )

        logging.error(
            f"Monitored folder does "
            f"not exist: "
            f"{monitored_folder}"
        )

        return EXIT_ERROR

    if not monitored_folder.is_dir():
        print(
            f"[ERROR] Monitored path "
            f"is not a directory: "
            f"{monitored_folder}"
        )

        logging.error(
            f"Monitored path is not "
            f"a directory: "
            f"{monitored_folder}"
        )

        return EXIT_ERROR

    #Verify baseline protection, before trusting the data.
    if not verify_baseline_hash(baseline_path):
        print()
        print("Integrity check aborted.")
        return EXIT_ERROR

    #Load baseline
    baseline_data = load_baseline(baseline_path)

    if baseline is None:
        print()
        print("Create a baseline first with:")
        print("    python fic.py init")
    
        logging.error("Integrity check aborted because baseline could not be loaded.")
    
        return EXIT_ERROR
    
    baseline, baseline_exclusions = (baseline_data)

    #Verify exclusion config
    if not exclusions_match(baseline_exclusions, exclusions):
        print(
            "[ERROR] Exclusion "
            "configuration does not "
            "match the baseline."
        )

        print(
            f"Baseline exclusions: "
            f"{baseline_exclusions}"
        )

        print(
            f"Supplied exclusions: "
            f"{exclusions}"
        )

        logging.error(
            "Exclusion configuration "
            "does not match baseline."
        )

        return EXIT_ERROR

    #Scan current directory
    (current, scan_errors, symlinks_skipped) = directory_scanner(monitored_folder, exclusions)

    #Compare files
    results = compare_files(baseline, current, scan_errors)

    #Display results
    display_results(results)
    display_scan_errors(scan_errors)

    print()
    print(
        f"Symbolic links skipped: "
        f"{symlinks_skipped}"
    )

    #Log summary
    logging.info(
        "Integrity check completed. "
        f"Unchanged={len(results['unchanged'])}, "
        f"Modified={len(results['modified'])}, "
        f"New={len(results['new'])}, "
        f"Deleted={len(results['deleted'])}, "
        f"ScanErrors={len(results['scan_error'])}, "
        f"SymlinksSkipped={symlinks_skipped}"
    )


    #Incomplete scan
    if scan_errors:
        return EXIT_ERROR

    #Integrity violation
    if (
        results["modified"]
        or results["new"]
        or results["deleted"]
    ):
        return EXIT_INTEGRITY_FAILURE

    #if everything matches:
    return EXIT_SUCCESS



# --------------------------------------------------
# Show checker status (STATUS)
# --------------------------------------------------

def show_status(monitored_folder, baseline_path):

    baseline_hash_path = (get_baseline_hash_path(baseline_path))

    print("File Integrity Checker Status")
    print("-----------------------------")

    #FIRST STATUS CHECK(MONITORED FOLDER)
    if monitored_folder.exists():
        print(
            f"Monitored folder: OK "
            f"({monitored_folder})"
        )

    else:
        print(
            f"Monitored folder: MISSING "
            f"({monitored_folder})"
        )

    #CHECK BASELINE
    if baseline_path.exists():
        print(
            f"Baseline: OK "
            f"({baseline_path})"
        )

    else:
        print(
            f"Baseline: MISSING "
            f"({baseline_path})"
        )

    #CHECK BASELINE HASH
    if baseline_hash_path.exists():
        print(
            f"Baseline hash: OK "
            f"({baseline_hash_path})"
        )

    else:
        print(
            f"Baseline hash: MISSING "
            f"({baseline_hash_path})"
        )

    #COUNT BASELINE FILES
    if baseline_path.exists():

        baseline, exclusions = load_baseline(baseline_path)
        print(
            f"Exclusions: "
            f"{len(exclusions)}"
        )
        for exclusion in exclusions:
            print(f"  - {exclusion}")

        if baseline is not None:
            print(
                f"Baseline files: {len(baseline)}"
            )

        else:
            print(
                "Baseline files: unavailable"
            )

    else:
        print(
            "Baseline files: unavailable"
        )

    #VERIFY THE BASELINE
    if baseline_path.exists() and baseline_hash_path.exists():

        if verify_baseline_hash(baseline_path):
            print(
                "Baseline integrity: OK"
            )

        else:
            print(
                "Baseline integrity: FAILED"
            )

    else:
        print(
            "Baseline integrity: unavailable"
        )

    return EXIT_SUCCESS

    

# --------------------------------------------------
# CLI parser
# --------------------------------------------------

def create_parser():

    parser = argparse.ArgumentParser(
        description=(
            "File Integrity Checker - "
            "detect unauthorized file changes."
        )
    )

#SUBCOMMANDS:
    subparsers = parser.add_subparsers(
        dest="command"
    )

    #INIT
    init_parser = subparsers.add_parser(
        "init",
        help="Create a new baseline."
    )

    init_parser.add_argument(
        "--folder",
        type=Path,
        default=MONITORED_FOLDER,
        help="Folder to monitor."
    )

    init_parser.add_argument(
	    "--baseline",
	    type=Path,
	    default=BASELINE_PATH,
	    help="Path to the baseline file."
	)

    init_parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help=(
            "Path to exclude from monitoring. "
            "Can be specified multiple times."
        )
    )


    #CHECK
    check_parser = subparsers.add_parser(
        "check",
        help="Check file integrity."
    )

    check_parser.add_argument(
        "--folder",
        type=Path,
        default=MONITORED_FOLDER,
        help="Folder to check."
    )

    check_parser.add_argument(
	    "--baseline",
	    type=Path,
	    default=BASELINE_PATH,
	    help="Path to the baseline file."
	)

    check_parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help=(
            "Path to exclude from monitoring. "
            "Can be specified multiple times."
        )
    )


    #STATUS
    status_parser = subparsers.add_parser(
        "status",
        help="Show checker status."
    )

    status_parser.add_argument(
            "--folder",
            type=Path,
            default=MONITORED_FOLDER,
            help="Folder to check."
    )

    status_parser.add_argument(
        "--baseline",
        type=Path,
        default=BASELINE_PATH,
        help="Path to the baseline file."
    )

    return parser



# --------------------------------------------------
# ************** Main program **************
# --------------------------------------------------

def main():

    setup_logging()

    parser = create_parser()

    args = parser.parse_args()

    #No command
    if args.command is None:
        parser.print_help()
        return EXIT_ERROR

    #'Initialize' baseline
    if args.command == "init":
        return initialize(
            args.folder,
            args.baseline,
            args.exclude
        )

    #'check' integrity
    elif args.command == "check":
        return check_integrity(
            args.folder,
            args.baseline,
            args.exclude
        )

    #Show 'status'
    elif args.command == "status":
        return show_status(
            args.folder,
            args.baseline
        )

    return EXIT_ERROR

#---------------**PROGRAM ENTRY POINT**--------------
if __name__ == "__main__":
    sys.exit(
        main()
    )