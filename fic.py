import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from pathlib import Path


# --------------------------------------------------
# Configuration
# --------------------------------------------------

MONITORED_FOLDER = Path("test_data")
BASELINE_PATH = Path("baseline/baseline.json")
LOG_PATH = Path("logs/fic.log")


# --------------------------------------------------
# Exit codes
# --------------------------------------------------

EXIT_SUCCESS = 0
EXIT_INTEGRITY_FAILURE = 1
EXIT_ERROR = 2


# --------------------------------------------------
# Configure logging
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
# Validate an exclusion path
# --------------------------------------------------

def validate_exclusion(
    exclusion
):

    path = Path(exclusion)

    # Absolute paths are not allowed

    if path.is_absolute():
        return False

    # Parent-directory traversal is not allowed

    for part in path.parts:

        if part == "..":
            return False

    return True


# --------------------------------------------------
# Validate all exclusions
# --------------------------------------------------

def validate_exclusions(
    exclusions
):

    for exclusion in exclusions:

        if not validate_exclusion(
            exclusion
        ):
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
# Normalize a relative path
# --------------------------------------------------

def normalize_relative_path(
    file_path,
    root_folder
):

    relative_path = (
        file_path.relative_to(
            root_folder
        )
    )

    return relative_path.as_posix()


# --------------------------------------------------
# Determine whether a path is excluded
# --------------------------------------------------

def is_excluded(
    file_path,
    root_folder,
    exclusions
):

    relative_path = (
        file_path.relative_to(
            root_folder
        )
    )

    normalized_path = (
        relative_path.as_posix()
    )

    for exclusion in exclusions:

        exclusion_path = Path(
            exclusion
        )

        normalized_exclusion = (
            exclusion_path.as_posix()
        )

        # Exact match

        if normalized_path == (
            normalized_exclusion
        ):
            return True

        # Directory match

        if normalized_path.startswith(
            normalized_exclusion + "/"
        ):
            return True

    return False


# --------------------------------------------------
# Calculate SHA-256 hash of a file
# --------------------------------------------------

def calculate_hash(
    file_path
):

    hasher = hashlib.sha256()

    try:
        with open(
            file_path,
            "rb"
        ) as file:
            while chunk := file.read(
                4096
            ):
                hasher.update(
                    chunk
                )

    except (
        FileNotFoundError,
        PermissionError
    ) as error:
        print(
            f"[ERROR] Could not read "
            f"{file_path}: {error}"
        )

        logging.error(
            f"Could not read "
            f"{file_path}: {error}"
        )

        return None

    return hasher.hexdigest()


# --------------------------------------------------
# Scan a directory
# --------------------------------------------------

def directory_scanner(
    folder,
    exclusions=None
):

    if exclusions is None:

        exclusions = []

    logging.info(
        f"Scanning directory: {folder}"
    )

    logging.info(
        f"Exclusions: {exclusions}"
    )

    file_hashes = {}

    errors = []

    symlinks_skipped = 0

    for root, directories, files in os.walk(
        folder,
        topdown=True,
        followlinks=False
    ):

        root_path = Path(root)

        # --------------------------------------------------
        # Handle directories
        # --------------------------------------------------

        directories_to_remove = []

        for directory in directories:
            directory_path = (
                root_path / directory
            )

            # Skip symbolic-link directories

            if directory_path.is_symlink():
                directories_to_remove.append(
                    directory
                )

                symlinks_skipped += 1

                logging.info(
                    f"Skipping symbolic "
                    f"directory link: "
                    f"{directory_path}"
                )
                continue

            # Skip excluded directories

            if is_excluded(
                directory_path,
                folder,
                exclusions
            ):
                directories_to_remove.append(
                    directory
                )

                logging.info(
                    f"Skipping excluded "
                    f"directory: "
                    f"{directory_path}"
                )

        # Remove directories before
        # os.walk descends into them

        for directory in directories_to_remove:
            directories.remove(
                directory
            )

        # --------------------------------------------------
        # Process files
        # --------------------------------------------------

        for file_name in files:
            file_path = (
                root_path / file_name
            )

            # --------------------------------------------------
            # Skip symbolic links
            # --------------------------------------------------

            if file_path.is_symlink():
                symlinks_skipped += 1

                logging.info(
                    f"Skipping symbolic "
                    f"link: {file_path}"
                )
                continue

            # --------------------------------------------------
            # Check exclusions
            # --------------------------------------------------

            if is_excluded(
                file_path,
                folder,
                exclusions
            ):
                continue

            # --------------------------------------------------
            # Confirm regular file
            # --------------------------------------------------

            if not file_path.is_file():
                continue

            # --------------------------------------------------
            # Calculate hash
            # --------------------------------------------------

            file_hash = calculate_hash(
                file_path
            )

            normalized_path = (
                normalize_relative_path(
                    file_path,
                    folder
                )
            )

            if file_hash is not None:
                file_hashes[
                    normalized_path
                ] = file_hash

            else:
                errors.append(
                    normalized_path
                )

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
# Atomically replace a file with retries
# --------------------------------------------------

def atomic_replace(
    source,
    destination,
    retries=5,
    delay=0.5
):

    for attempt in range(
        1,
        retries + 1
    ):

        try:
            os.replace(
                source,
                destination
            )

            logging.info(
                f"Atomic replacement "
                f"succeeded on attempt "
                f"{attempt}."
            )

            return True

        except PermissionError as error:
            print(
                f"[WARNING] File is locked. "
                f"Replacement attempt "
                f"{attempt}/{retries}."
            )

            logging.warning(
                f"Replacement attempt "
                f"{attempt}/{retries} failed: "
                f"{error}"
            )

            if attempt < retries:
                time.sleep(
                    delay
                )

        except OSError as error:

            print(
                f"[ERROR] Atomic replacement "
                f"failed: {error}"
            )

            logging.error(
                f"Atomic replacement failed: "
                f"{error}"
            )

            return False

    print(
        "[ERROR] Could not replace "
        f"{destination} because the file "
        "remained locked."
    )

    return False


# --------------------------------------------------
# Save baseline
# --------------------------------------------------

def save_baseline(
    file_hashes,
    baseline_path,
    exclusions
):

    logging.info(
        f"Saving baseline to: "
        f"{baseline_path}"
    )

    baseline_data = {
        "version": 2,
        "algorithm": "sha256",
        "exclusions": exclusions,
        "files": file_hashes
    }

    baseline_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary_path = (
        baseline_path.with_suffix(
            baseline_path.suffix + ".tmp"
        )
    )

    try:

        # --------------------------------------------------
        # Write temporary baseline
        # --------------------------------------------------

        with open(
            temporary_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                baseline_data,
                file,
                indent=4
            )
            file.flush()
            os.fsync(
                file.fileno()
            )

        logging.info(
            f"Temporary baseline created: "
            f"{temporary_path}"
        )

        # --------------------------------------------------
        # Atomically replace baseline
        # --------------------------------------------------

        if not atomic_replace(
            temporary_path,
            baseline_path
        ):
            return False

    except (
        OSError,
        TypeError,
        ValueError
    ) as error:
        print(
            f"[ERROR] Could not save baseline: "
            f"{error}"
        )

        logging.error(
            f"Could not save baseline: "
            f"{error}"
        )

        # --------------------------------------------------
        # Clean up temporary file
        # --------------------------------------------------

        try:

            if temporary_path.exists():

                temporary_path.unlink()

        except OSError as cleanup_error:

            logging.error(
                f"Could not remove temporary "
                f"baseline file: "
                f"{cleanup_error}"
            )

        return False

    logging.info(
        f"Baseline saved successfully: "
        f"{baseline_path}"
    )

    return True


# --------------------------------------------------
# Validate SHA-256 hash
# --------------------------------------------------

def isValid_sha256(
    value
):

    if not isinstance(
        value,
        str
    ):

        return False

    return bool(
        re.fullmatch(
            r"[0-9a-fA-F]{64}",
            value
        )
    )


# --------------------------------------------------
# Validate baseline structure
# --------------------------------------------------

def validate_baseline(
    baseline_data
):

    # --------------------------------------------------
    # Validate root object
    # --------------------------------------------------

    if not isinstance(
        baseline_data,
        dict
    ):

        logging.error(
            "Baseline root is not "
            "a JSON object."
        )

        return False

    # --------------------------------------------------
    # Validate version
    # --------------------------------------------------

    version = baseline_data.get(
        "version"
    )

    if (
        not isinstance(
            version,
            int
        )
        or isinstance(
            version,
            bool
        )
    ):

        logging.error(
            "Baseline version is "
            "not an integer."
        )

        return False

    if version != 2:

        logging.error(
            f"Unsupported baseline "
            f"version: {version}"
        )

        return False

    # --------------------------------------------------
    # Validate algorithm
    # --------------------------------------------------

    algorithm = baseline_data.get(
        "algorithm"
    )

    if not isinstance(
        algorithm,
        str
    ):

        logging.error(
            "Baseline algorithm is "
            "not a string."
        )

        return False

    if algorithm.lower() != "sha256":

        logging.error(
            f"Unsupported hashing "
            f"algorithm: {algorithm}"
        )

        return False

    # --------------------------------------------------
    # Validate exclusions
    # --------------------------------------------------

    exclusions = baseline_data.get(
        "exclusions"
    )

    if not isinstance(
        exclusions,
        list
    ):

        logging.error(
            "Baseline exclusions "
            "are not a list."
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

    # --------------------------------------------------
    # Validate files object
    # --------------------------------------------------

    files = baseline_data.get(
        "files"
    )

    if not isinstance(
        files,
        dict
    ):

        logging.error(
            "Baseline file data "
            "is not an object."
        )

        return False

    # --------------------------------------------------
    # Validate every file
    # --------------------------------------------------

    for (
        file_path,
        file_hash
    ) in files.items():

        # File path must be a string

        if not isinstance(
            file_path,
            str
        ):

            logging.error(
                "Baseline contains a "
                "non-string file path."
            )

            return False

        # File path cannot be empty

        if not file_path:

            logging.error(
                "Baseline contains an "
                "empty file path."
            )

            return False

        # Backslashes are not allowed

        if "\\" in file_path:

            logging.error(
                "Baseline contains "
                f"non-normalized path: "
                f"{file_path}"
            )

            return False

        # Absolute Unix-style path

        if file_path.startswith(
            "/"
        ):

            logging.error(
                "Baseline contains "
                f"absolute path: "
                f"{file_path}"
            )

            return False

        # Absolute Windows-style path

        if (
            len(file_path) >= 2
            and file_path[1] == ":"
        ):

            logging.error(
                "Baseline contains "
                f"absolute path: "
                f"{file_path}"
            )

            return False

        # Parent traversal

        if ".." in Path(
            file_path
        ).parts:

            logging.error(
                "Baseline contains "
                f"path traversal: "
                f"{file_path}"
            )

            return False

        # Validate hash

        if not isValid_sha256(
            file_hash
        ):

            logging.error(
                "Invalid SHA-256 hash "
                f"for: {file_path}"
            )

            return False

    return True


# --------------------------------------------------
# Load baseline
# --------------------------------------------------

def load_baseline(
    baseline_path
):

    logging.info(
        f"Loading baseline: "
        f"{baseline_path}"
    )

    try:
        with open(
            baseline_path,
            "r",
            encoding="utf-8"
        ) as file:

            baseline_data = json.load(
                file
            )

    except FileNotFoundError:
        print(
            "[ERROR] Baseline file "
            "not found."
        )

        logging.error(
            f"Baseline file not found: "
            f"{baseline_path}"
        )

        return None

    except json.JSONDecodeError:
        print(
            "[ERROR] Baseline file "
            "contains invalid JSON."
        )

        logging.error(
            f"Invalid JSON in baseline: "
            f"{baseline_path}"
        )

        return None

    except OSError as error:
        print(
            "[ERROR] Could not read "
            "baseline file."
        )

        logging.error(
            f"Could not read baseline: "
            f"{error}"
        )

        return None

    # Validate baseline

    if not validate_baseline(
        baseline_data
    ):
        print(
            "[ERROR] Baseline "
            "validation failed."
        )

        return None

    logging.info(
        "Baseline loaded successfully. "
        f"Files: "
        f"{len(baseline_data['files'])}"
    )

    return (
        baseline_data["files"],
        baseline_data["exclusions"]
    )


# --------------------------------------------------
# Get baseline hash path
# --------------------------------------------------

def get_baseline_hash_path(
    baseline_path
):
    return baseline_path.with_suffix(
        ".sha256"
    )


# --------------------------------------------------
# Save baseline hash
# --------------------------------------------------

def save_baseline_hash(
    baseline_path
):

    baseline_hash_path = (
        get_baseline_hash_path(
            baseline_path
        )
    )

    temporary_hash_path = (
        baseline_hash_path.with_name(
            baseline_hash_path.name
            + ".tmp"
        )
    )

    baseline_hash = calculate_hash(
        baseline_path
    )

    if baseline_hash is None:

        logging.error(
            "Could not calculate "
            "baseline hash."
        )

        return False

    try:
        baseline_hash_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # --------------------------------------------------
        # Remove stale temporary file
        # --------------------------------------------------

        if temporary_hash_path.exists():

            try:
                temporary_hash_path.unlink()

            except OSError as error:

                logging.warning(
                    f"Could not remove stale "
                    f"temporary hash file: "
                    f"{error}"
                )

        # --------------------------------------------------
        # Create temporary hash file
        # --------------------------------------------------

        with open(
            temporary_hash_path,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(
                baseline_hash
            )
            file.flush()
            os.fsync(
                file.fileno()
            )

        logging.info(
            f"Temporary baseline hash "
            f"created: {temporary_hash_path}"
        )

        # --------------------------------------------------
        # Verify temporary file exists
        # --------------------------------------------------

        if not temporary_hash_path.exists():
            print(
                "[ERROR] Temporary baseline "
                "hash file disappeared before "
                "replacement."
            )

            logging.error(
                "Temporary baseline hash "
                "file disappeared before "
                "replacement."
            )

            return False

        # --------------------------------------------------
        # Atomically replace hash
        # --------------------------------------------------

        if not atomic_replace(
            temporary_hash_path,
            baseline_hash_path
        ):
            return False

    except (
        OSError,
        TypeError,
        ValueError
    ) as error:
        print(
            f"[ERROR] Could not save "
            f"baseline hash: {error}"
        )

        logging.error(
            f"Could not save baseline "
            f"hash: {error}"
        )

        # --------------------------------------------------
        # Clean up temporary file
        # --------------------------------------------------

        try:
            if temporary_hash_path.exists():

                temporary_hash_path.unlink()

        except OSError as cleanup_error:
            logging.error(
                f"Could not remove "
                f"temporary hash file: "
                f"{cleanup_error}"
            )

        return False

    logging.info(
        f"Baseline hash saved: "
        f"{baseline_hash_path}"
    )

    return True


# --------------------------------------------------
# Verify baseline hash
# --------------------------------------------------

def verify_baseline_hash(
    baseline_path
):

    baseline_hash_path = (
        get_baseline_hash_path(
            baseline_path
        )
    )

    if not baseline_hash_path.exists():
        print(
            "[ERROR] Baseline hash "
            "file not found."
        )

        logging.error(
            "Baseline hash file "
            "not found."
        )

        return False

    try:
        with open(
            baseline_hash_path,
            "r",
            encoding="utf-8"
        ) as file:
            expected_hash = (
                file.read().strip()
            )

    except OSError as error:
        print(
            "[ERROR] Could not read "
            "baseline hash."
        )

        logging.error(
            f"Could not read "
            f"baseline hash: {error}"
        )

        return False

    # Validate stored hash

    if not isValid_sha256(
        expected_hash
    ):
        print(
            "[ERROR] Baseline hash "
            "file is invalid."
        )

        logging.error(
            "Baseline hash file "
            "contains an invalid "
            "SHA-256 hash."
        )

        return False

    # Calculate current hash

    actual_hash = calculate_hash(
        baseline_path
    )

    if actual_hash is None:
        print(
            "[ERROR] Could not calculate "
            "baseline hash."
        )

        return False

    # Compare hashes

    if actual_hash != expected_hash:
        print(
            "[ALERT] Baseline has "
            "been modified!"
        )

        logging.critical(
            "Baseline integrity "
            "verification failed."
        )

        return False

    logging.info(
        "Baseline integrity "
        "verified successfully."
    )

    return True


# --------------------------------------------------
# Compare exclusions
# --------------------------------------------------

def exclusions_match(
    expected,
    supplied
):
    expected_set = set(
        expected
    )

    supplied_set = set(
        supplied
    )

    return (
        expected_set
        == supplied_set
    )


# --------------------------------------------------
# Compare baseline and current files
# --------------------------------------------------

def compare_files(
    baseline,
    current,
    scan_errors
):

    results = {
        "unchanged": [],
        "modified": [],
        "new": [],
        "deleted": [],
        "scan_error": []
    }

    scan_error_set = set(
        scan_errors
    )

    # --------------------------------------------------
    # Record scan errors
    # --------------------------------------------------

    for file_path in scan_errors:
        results[
            "scan_error"
        ].append(
            file_path
        )

        logging.error(
            f"File could not be "
            f"scanned: {file_path}"
        )

    # --------------------------------------------------
    # Check current files
    # --------------------------------------------------

    for (
        file_path,
        current_hash
    ) in current.items():

        if file_path in baseline:

            if (
                baseline[file_path]
                == current_hash
            ):
                results[
                    "unchanged"
                ].append(
                    file_path
                )

            else:
                results[
                    "modified"
                ].append(
                    file_path
                )

                logging.warning(
                    f"File modified: "
                    f"{file_path}"
                )

        else:
            results[
                "new"
            ].append(
                file_path
            )

            logging.warning(
                f"New file detected: "
                f"{file_path}"
            )

    # --------------------------------------------------
    # Check for deleted files
    # --------------------------------------------------

    for file_path in baseline:

        if file_path not in current:

            # Do not report as deleted
            # if the file could not be scanned.
            if file_path in scan_error_set:
                continue

            results[
                "deleted"
            ].append(
                file_path
            )

            logging.warning(
                f"File deleted: "
                f"{file_path}"
            )

    return results


# --------------------------------------------------
# Display integrity results
# --------------------------------------------------

def display_results(
    results
):

    print()

    for file_path in results[
        "unchanged"
    ]:
        print(
            f"[UNCHANGED] {file_path}"
        )

    for file_path in results[
        "modified"
    ]:
        print(
            f"[MODIFIED]  {file_path}"
        )

    for file_path in results[
        "new"
    ]:
        print(
            f"[NEW]       {file_path}"
        )

    for file_path in results[
        "deleted"
    ]:
        print(
            f"[DELETED]   {file_path}"
        )

    for file_path in results[
        "scan_error"
    ]:
        print(
            f"[SCAN ERROR] {file_path}"
        )

    print()
    print(
        "Integrity Check Summary"
    )
    print(
        "-----------------------"
    )
    print(
        f"Unchanged:   "
        f"{len(results['unchanged'])}"
    )
    print(
        f"Modified:    "
        f"{len(results['modified'])}"
    )
    print(
        f"New:         "
        f"{len(results['new'])}"
    )
    print(
        f"Deleted:     "
        f"{len(results['deleted'])}"
    )
    print(
        f"Scan errors: "
        f"{len(results['scan_error'])}"
    )


# --------------------------------------------------
# Display scan errors
# --------------------------------------------------

def display_scan_errors(
    errors
):

    if not errors:
        return

    print()
    print(
        "Files that could not "
        "be scanned"
    )
    print(
        "-----------------------"
    )

    for file_path in errors:
        print(
            f"[ERROR] {file_path}"
        )


# --------------------------------------------------
# Initialize baseline
# --------------------------------------------------

def initialize(
    monitored_folder,
    baseline_path,
    exclusions
):

    logging.info(
        f"Baseline creation started. "
        f"Folder={monitored_folder}, "
        f"Baseline={baseline_path}, "
        f"Exclusions={exclusions}"
    )

    print(
        "Creating baseline..."
    )
    print()

    # --------------------------------------------------
    # Validate exclusions
    # --------------------------------------------------

    if not validate_exclusions(
        exclusions
    ):
        return EXIT_ERROR

    # --------------------------------------------------
    # Verify monitored folder
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Scan directory
    # --------------------------------------------------

    (
        file_hashes,
        scan_errors,
        symlinks_skipped
    ) = directory_scanner(
        monitored_folder,
        exclusions
    )

    # --------------------------------------------------
    # Abort if scan was incomplete
    # --------------------------------------------------

    if scan_errors:
        print()
        print(
            "[ERROR] Baseline was not "
            "created because some "
            "files could not be scanned."
        )

        logging.error(
            "Baseline creation "
            "aborted because some "
            "files could not be scanned."
        )

        display_scan_errors(
            scan_errors
        )

        return EXIT_ERROR

    # --------------------------------------------------
    # Save baseline
    # --------------------------------------------------

    if not save_baseline(
        file_hashes,
        baseline_path,
        exclusions
    ):
        print(
            "[ERROR] Could not save baseline."
        )

        logging.error(
            "Baseline creation failed."
        )

        return EXIT_ERROR

    # --------------------------------------------------
    # Protect baseline
    # --------------------------------------------------

    if not save_baseline_hash(
        baseline_path
    ):
        print(
            "[ERROR] Baseline "
            "protection failed."
        )

        logging.error(
            "Baseline protection "
            "failed."
        )

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
# Check integrity
# --------------------------------------------------

def check_integrity(
    monitored_folder,
    baseline_path,
    exclusions
):

    logging.info(
        f"Integrity check started. "
        f"Folder={monitored_folder}, "
        f"Baseline={baseline_path}, "
        f"Exclusions={exclusions}"
    )

    print(
        "Checking file integrity..."
    )
    print()

    # --------------------------------------------------
    # Validate exclusions
    # --------------------------------------------------

    if not validate_exclusions(
        exclusions
    ):
        return EXIT_ERROR

    # --------------------------------------------------
    # Verify monitored folder
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Verify baseline integrity
    # --------------------------------------------------

    if not verify_baseline_hash(
        baseline_path
    ):
        print()
        print(
            "Integrity check aborted."
        )

        return EXIT_ERROR

    # --------------------------------------------------
    # Load baseline
    # --------------------------------------------------

    baseline_data = load_baseline(
        baseline_path
    )

    if baseline_data is None:
        print()
        print(
            "Create a baseline first "
            "with:"
        )
        print(
            "    python fic.py init"
        )

        logging.error(
            "Integrity check aborted "
            "because baseline could "
            "not be loaded."
        )

        return EXIT_ERROR

    baseline, baseline_exclusions = (
        baseline_data
    )

    # --------------------------------------------------
    # Verify exclusion configuration
    # --------------------------------------------------

    if not exclusions_match(
        baseline_exclusions,
        exclusions
    ):

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

    # --------------------------------------------------
    # Scan current directory
    # --------------------------------------------------

    (
        current,
        scan_errors,
        symlinks_skipped
    ) = directory_scanner(
        monitored_folder,
        exclusions
    )

    # --------------------------------------------------
    # Compare files
    # --------------------------------------------------

    results = compare_files(
        baseline,
        current,
        scan_errors
    )

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    display_results(
        results
    )

    display_scan_errors(
        scan_errors
    )

    print()
    print(
        f"Symbolic links skipped: "
        f"{symlinks_skipped}"
    )

    # --------------------------------------------------
    # Log summary
    # --------------------------------------------------

    logging.info(
        "Integrity check completed. "
        f"Unchanged="
        f"{len(results['unchanged'])}, "
        f"Modified="
        f"{len(results['modified'])}, "
        f"New="
        f"{len(results['new'])}, "
        f"Deleted="
        f"{len(results['deleted'])}, "
        f"ScanErrors="
        f"{len(results['scan_error'])}, "
        f"SymlinksSkipped="
        f"{symlinks_skipped}"
    )

    # --------------------------------------------------
    # Incomplete scan
    # --------------------------------------------------

    if scan_errors:
        return EXIT_ERROR

    # --------------------------------------------------
    # Integrity violation
    # --------------------------------------------------

    if (
        results["modified"]
        or results["new"]
        or results["deleted"]
    ):
        return EXIT_INTEGRITY_FAILURE

    # --------------------------------------------------
    # Everything matches
    # --------------------------------------------------

    return EXIT_SUCCESS


# --------------------------------------------------
# Show status
# --------------------------------------------------

def show_status(
    monitored_folder,
    baseline_path
):

    baseline_hash_path = (
        get_baseline_hash_path(
            baseline_path
        )
    )

    print(
        "File Integrity Checker Status"
    )
    print(
        "-----------------------------"
    )

    # --------------------------------------------------
    # Monitored folder
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Baseline
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Baseline hash
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Baseline information
    # --------------------------------------------------

    if baseline_path.exists():
        baseline_data = load_baseline(
            baseline_path
        )

        if baseline_data is not None:
            baseline, exclusions = (
                baseline_data
            )

            print(
                f"Baseline files: "
                f"{len(baseline)}"
            )

            print(
                f"Exclusions: "
                f"{len(exclusions)}"
            )

            for exclusion in exclusions:
                print(
                    f"  - {exclusion}"
                )

        else:
            print(
                "Baseline files: "
                "unavailable"
            )

    else:
        print(
            "Baseline files: "
            "unavailable"
        )

    # --------------------------------------------------
    # Baseline integrity
    # --------------------------------------------------

    if (
        baseline_path.exists()
        and baseline_hash_path.exists()
    ):

        if verify_baseline_hash(
            baseline_path
        ):
            print(
                "Baseline integrity: OK"
            )

        else:
            print(
                "Baseline integrity: FAILED"
            )

    else:
        print(
            "Baseline integrity: "
            "unavailable"
        )

    return EXIT_SUCCESS


# --------------------------------------------------
# Create command-line parser
# --------------------------------------------------

def create_parser():

    parser = argparse.ArgumentParser(

        description=(
            "File Integrity Checker - "
            "detect unauthorized file "
            "changes."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    # ==================================================
    # INIT COMMAND
    # ==================================================

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
            "Path to exclude from "
            "monitoring. Can be "
            "specified multiple times."
        )
    )

    # ==================================================
    # CHECK COMMAND
    # ==================================================

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
            "Path to exclude from "
            "monitoring. Can be "
            "specified multiple times."
        )
    )

    # ==================================================
    # STATUS COMMAND
    # ==================================================

    status_parser = subparsers.add_parser(
        "status",
        help="Show checker status."
    )

    status_parser.add_argument(
        "--folder",
        type=Path,
        default=MONITORED_FOLDER,
        help="Folder to inspect."
    )

    status_parser.add_argument(
        "--baseline",
        type=Path,
        default=BASELINE_PATH,
        help="Path to the baseline file."
    )

    return parser


# --------------------------------------------------
# Main program
# --------------------------------------------------

def main():

    setup_logging()

    parser = create_parser()

    args = parser.parse_args()

    # --------------------------------------------------
    # No command
    # --------------------------------------------------

    if args.command is None:
        parser.print_help()
        return EXIT_ERROR

    # --------------------------------------------------
    # Initialize
    # --------------------------------------------------

    if args.command == "init":
        return initialize(
            args.folder,
            args.baseline,
            args.exclude
        )

    # --------------------------------------------------
    # Check
    # --------------------------------------------------

    elif args.command == "check":
        return check_integrity(
            args.folder,
            args.baseline,
            args.exclude
        )

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    elif args.command == "status":
        return show_status(
            args.folder,
            args.baseline
        )

    return EXIT_ERROR


# --------------------------------------------------
# Program entry point
# --------------------------------------------------

if __name__ == "__main__":

    sys.exit(
        main()
    )