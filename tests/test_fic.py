import contextlib
import hashlib
import io
import tempfile
import unittest
import json
from pathlib import Path

import fic


# --------------------------------------------------
# Test calculate_hash()
# --------------------------------------------------

class TestCalculateHash(unittest.TestCase):

    def test_calculate_hash(self):

        content = b"File Integrity Checker"

        expected_hash = hashlib.sha256(
            content
        ).hexdigest()

        with tempfile.TemporaryDirectory() as temp_dir:

            test_file = Path(
                temp_dir
            ) / "test.txt"

            test_file.write_bytes(
                content
            )

            actual_hash = fic.calculate_hash(
                test_file
            )

        self.assertEqual(
            actual_hash,
            expected_hash
        )

    def test_calculate_hash_file_not_found(self):

        missing_file = Path(
            "this_file_does_not_exist.txt"
        )

        result = fic.calculate_hash(
            missing_file
        )

        self.assertIsNone(
            result
        )


# --------------------------------------------------
# Test directory_scanner()
# --------------------------------------------------

class TestDirectoryScanner(unittest.TestCase):

    def test_directory_scanner_finds_files(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            file_one = root / "file1.txt"
            file_two = root / "file2.txt"

            file_one.write_text(
                "Hello",
                encoding="utf-8"
            )

            file_two.write_text(
                "World",
                encoding="utf-8"
            )

            file_hashes, errors, symlinks_skipped = (
                fic.directory_scanner(
                    root
                )
            )

            expected_file_one_hash = hashlib.sha256(
                b"Hello"
            ).hexdigest()

            expected_file_two_hash = hashlib.sha256(
                b"World"
            ).hexdigest()

            self.assertEqual(
                len(file_hashes),
                2
            )

            self.assertEqual(
                errors,
                []
            )

            self.assertEqual(
                symlinks_skipped,
                0
            )

            self.assertEqual(
                file_hashes["file1.txt"],
                expected_file_one_hash
            )

            self.assertEqual(
                file_hashes["file2.txt"],
                expected_file_two_hash
            )

    def test_directory_scanner_excludes_directory(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            included_file = root / "important.txt"

            excluded_directory = root / "cache"

            excluded_file = (
                excluded_directory / "temporary.txt"
            )

            included_file.write_text(
                "Important data",
                encoding="utf-8"
            )

            excluded_directory.mkdir()

            excluded_file.write_text(
                "Temporary data",
                encoding="utf-8"
            )

            file_hashes, errors, symlinks_skipped = (
                fic.directory_scanner(
                    root,
                    ["cache"]
                )
            )

            self.assertIn(
                "important.txt",
                file_hashes
            )

            self.assertNotIn(
                "cache/temporary.txt",
                file_hashes
            )

            self.assertEqual(
                errors,
                []
            )

            self.assertEqual(
                symlinks_skipped,
                0
            )

    def test_directory_scanner_nested_directories(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            root_file = root / "root.txt"

            documents = root / "documents"

            archive = documents / "archive"

            report_file = documents / "report.txt"

            old_file = archive / "old.txt"

            documents.mkdir()

            archive.mkdir()

            root_file.write_text(
                "Root file",
                encoding="utf-8"
            )

            report_file.write_text(
                "Report",
                encoding="utf-8"
            )

            old_file.write_text(
                "Old file",
                encoding="utf-8"
            )

            file_hashes, errors, symlinks_skipped = (
                fic.directory_scanner(
                    root
                )
            )

            self.assertEqual(
                len(file_hashes),
                3
            )

            self.assertEqual(
                errors,
                []
            )

            self.assertEqual(
                symlinks_skipped,
                0
            )

            self.assertIn(
                "root.txt",
                file_hashes
            )

            self.assertIn(
                "documents/report.txt",
                file_hashes
            )

            self.assertIn(
                "documents/archive/old.txt",
                file_hashes
            )

    def test_directory_scanner_multiple_exclusions(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            included_file = root / "important.txt"

            cache_directory = root / "cache"

            logs_directory = root / "logs"

            temporary_directory = root / "temporary"

            cache_file = (
                cache_directory / "cache.txt"
            )

            logs_file = (
                logs_directory / "application.log"
            )

            temporary_file = (
                temporary_directory / "temp.txt"
            )

            included_file.write_text(
                "Important data",
                encoding="utf-8"
            )

            cache_directory.mkdir()

            logs_directory.mkdir()

            temporary_directory.mkdir()

            cache_file.write_text(
                "Cache data",
                encoding="utf-8"
            )

            logs_file.write_text(
                "Log data",
                encoding="utf-8"
            )

            temporary_file.write_text(
                "Temporary data",
                encoding="utf-8"
            )

            file_hashes, errors, symlinks_skipped = (
                fic.directory_scanner(
                    root,
                    [
                        "cache",
                        "logs",
                        "temporary"
                    ]
                )
            )

            self.assertIn(
                "important.txt",
                file_hashes
            )

            self.assertNotIn(
                "cache/cache.txt",
                file_hashes
            )

            self.assertNotIn(
                "logs/application.log",
                file_hashes
            )

            self.assertNotIn(
                "temporary/temp.txt",
                file_hashes
            )

            self.assertEqual(
                len(file_hashes),
                1
            )

            self.assertEqual(
                errors,
                []
            )

            self.assertEqual(
                symlinks_skipped,
                0
            )


# --------------------------------------------------
# Test initialize()
# --------------------------------------------------

class TestInitialize(unittest.TestCase):

    def test_initialize_creates_baseline(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important data",
                encoding="utf-8"
            )

            result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_SUCCESS
            )

            self.assertTrue(
                baseline_path.exists()
            )

            baseline_hash_path = (
                baseline_path.with_suffix(
                    ".sha256"
                )
            )

            self.assertTrue(
                baseline_hash_path.exists()
            )

    def test_initialize_baseline_contains_correct_hash(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            content = b"Important data"

            test_file.write_bytes(
                content
            )

            result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            expected_hash = hashlib.sha256(
                content
            ).hexdigest()

            self.assertIn(
                "important.txt",
                baseline_data["files"]
            )

            self.assertEqual(
                baseline_data["files"]["important.txt"],
                expected_hash
            )

    def test_initialize_missing_monitored_folder(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = (
                root / "does_not_exist"
            )

            baseline_folder = (
                root / "baseline"
            )

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

            self.assertFalse(
                baseline_path.exists()
            )

    def test_initialize_file_as_monitored_path(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_path = (
                root / "not_a_directory.txt"
            )

            baseline_folder = (
                root / "baseline"
            )

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_path.write_text(
                "This is a file, not a directory.",
                encoding="utf-8"
            )

            result = fic.initialize(
                monitored_path,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

            self.assertFalse(
                baseline_path.exists()
            )


# --------------------------------------------------
# Test check_integrity()
# --------------------------------------------------

class TestCheckIntegrity(unittest.TestCase):

    def test_check_integrity_detects_modified_file(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Original content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            test_file.write_text(
                "Modified content",
                encoding="utf-8"
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_INTEGRITY_FAILURE
            )

    def test_check_integrity_detects_new_file(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            original_file = (
                monitored_folder / "important.txt"
            )

            original_file.write_text(
                "Original content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            new_file = (
                monitored_folder / "new_file.txt"
            )

            new_file.write_text(
                "New content",
                encoding="utf-8"
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_INTEGRITY_FAILURE
            )

    def test_check_integrity_detects_deleted_file(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            test_file.unlink()

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_INTEGRITY_FAILURE
            )

    def test_check_integrity_accepts_unchanged_file(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_SUCCESS
            )

    def test_check_integrity_detects_multiple_changes(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            modified_file = (
                monitored_folder / "modified.txt"
            )

            deleted_file = (
                monitored_folder / "deleted.txt"
            )

            unchanged_file = (
                monitored_folder / "unchanged.txt"
            )

            modified_file.write_text(
                "Original content",
                encoding="utf-8"
            )

            deleted_file.write_text(
                "This will be deleted",
                encoding="utf-8"
            )

            unchanged_file.write_text(
                "This will remain unchanged",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            modified_file.write_text(
                "Modified content",
                encoding="utf-8"
            )

            deleted_file.unlink()

            new_file = (
                monitored_folder / "new.txt"
            )

            new_file.write_text(
                "New content",
                encoding="utf-8"
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_INTEGRITY_FAILURE
            )

    def test_check_integrity_rejects_exclusion_mismatch(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            cache_directory = (
                monitored_folder / "cache"
            )

            cache_directory.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            cache_file = (
                cache_directory / "cache.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            cache_file.write_text(
                "Cache content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                ["cache"]
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_missing_baseline(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_detects_corrupted_baseline(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            baseline_path.write_text(
                "This baseline has been modified.",
                encoding="utf-8"
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_missing_baseline_json(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            baseline_path.unlink()

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_invalid_baseline_json(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            baseline_path.write_text(
                "{ this is not valid JSON",
                encoding="utf-8"
            )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_invalid_baseline_structure(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            invalid_baseline = {
                "hello": "world"
            }

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    invalid_baseline,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_unsupported_algorithm(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            baseline_data["algorithm"] = "md5"

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_unsupported_version(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            baseline_data["version"] = 999

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_missing_files_field(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            del baseline_data["files"]

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_invalid_files_type(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            baseline_data["files"] = []

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_invalid_file_hash(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            baseline_data["files"]["important.txt"] = (
                "not-a-real-hash"
            )

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_non_hex_file_hash(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            baseline_data["files"]["important.txt"] = (
                "g" * 64
            )

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_accepts_uppercase_file_hash(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            original_hash = (
                baseline_data["files"]["important.txt"]
            )

            baseline_data["files"]["important.txt"] = (
                original_hash.upper()
            )

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_SUCCESS
            )

    def test_check_integrity_rejects_wrong_length_file_hash(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            baseline_data["files"]["important.txt"] = (
                "abcdef1234567890"
            )

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_non_string_file_hash(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            baseline_data["files"]["important.txt"] = 123456

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_empty_file_path(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            original_hash = (
                baseline_data["files"]["important.txt"]
            )

            baseline_data["files"] = {
                "": original_hash
            }

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_backslash_file_path(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            original_hash = (
                baseline_data["files"]["important.txt"]
            )

            baseline_data["files"] = {
                "folder\\important.txt": original_hash
            }

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_absolute_unix_file_path(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            original_hash = (
                baseline_data["files"]["important.txt"]
            )

            baseline_data["files"] = {
                "/important.txt": original_hash
            }

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_absolute_windows_file_path(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            original_hash = (
                baseline_data["files"]["important.txt"]
            )

            baseline_data["files"] = {
                "C:\\important.txt": original_hash
            }

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_path_traversal(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            original_hash = (
                baseline_data["files"]["important.txt"]
            )

            baseline_data["files"] = {
                "../important.txt": original_hash
            }

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_embedded_path_traversal(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            original_hash = (
                baseline_data["files"]["important.txt"]
            )

            baseline_data["files"] = {
                "folder/../important.txt": original_hash
            }

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_rejects_parent_directory_path(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            original_hash = (
                baseline_data["files"]["important.txt"]
            )

            baseline_data["files"] = {
                "..": original_hash
            }

            with open(
                baseline_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    baseline_data,
                    file
                )

            self.assertTrue(
                fic.save_baseline_hash(
                    baseline_path
                )
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )

    def test_check_integrity_accepts_valid_nested_file_path(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            nested_folder = (
                monitored_folder / "docs"
            )

            nested_folder.mkdir(
                parents=True
            )

            test_file = (
                nested_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            with open(
                baseline_path,
                "r",
                encoding="utf-8"
            ) as file:

                baseline_data = json.load(
                    file
                )

            self.assertIn(
                "docs/important.txt",
                baseline_data["files"]
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                result,
                fic.EXIT_SUCCESS
            )

    def test_check_integrity_rejects_duplicate_exclusions(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_folder = root / "baseline"

            baseline_path = (
                baseline_folder / "baseline.json"
            )

            monitored_folder.mkdir()

            test_file = (
                monitored_folder / "important.txt"
            )

            test_file.write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                ["cache", "cache"]
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )


# --------------------------------------------------
# Validate an exclusion path
# --------------------------------------------------

# validate_exclusion had no tests at all, while the baseline path validator
# above has nine — and the two are supposed to enforce the same rules on the
# same kind of string. The untested one was the weaker one: it asked
# Path(exclusion).is_absolute(), which on Windows says False for "/etc/passwd"
# because there is no drive letter. The same config file was therefore accepted
# on one platform and rejected on the other.
#
# These test the function directly rather than through check_integrity, because
# the question is what the rule is, and there are ten cases of it.

class TestValidateExclusion(unittest.TestCase):

    def test_accepts_relative_paths(self):

        for exclusion in (
            "cache",
            "logs/old",
            "a/b/c",
            "...",
            "..hidden"
        ):

            with self.subTest(exclusion=exclusion):

                self.assertTrue(
                    fic.validate_exclusion(exclusion)
                )

    def test_rejects_absolute_unix_path(self):

        # The case that motivated this class. Path.is_absolute() answers False
        # here on Windows and True on Linux, so this must not depend on it.
        self.assertFalse(
            fic.validate_exclusion("/etc/passwd")
        )

    def test_rejects_drive_qualified_path(self):

        for exclusion in (
            "C:/Windows",
            "C:\\Windows",
            "c:/windows"
        ):

            with self.subTest(exclusion=exclusion):

                self.assertFalse(
                    fic.validate_exclusion(exclusion)
                )

    def test_rejects_drive_relative_path(self):

        # No separator, so nothing above reads this as absolute — but "C:cache"
        # means cache/ inside whatever C:'s current directory happens to be.
        self.assertFalse(
            fic.validate_exclusion("C:cache")
        )

    def test_rejects_backslash_path(self):

        # Rejected because is_excluded() compares against as_posix(): this
        # would match on Windows and match nothing at all on Linux.
        self.assertFalse(
            fic.validate_exclusion("logs\\temp")
        )

    def test_rejects_unc_path(self):

        self.assertFalse(
            fic.validate_exclusion("\\\\server\\share")
        )

    def test_rejects_path_traversal(self):

        for exclusion in (
            "..",
            "../secrets",
            "logs/../../etc",
            "a/.."
        ):

            with self.subTest(exclusion=exclusion):

                self.assertFalse(
                    fic.validate_exclusion(exclusion)
                )

    def test_rejects_empty_path(self):

        for exclusion in ("", "   ", "\t"):

            with self.subTest(exclusion=exclusion):

                self.assertFalse(
                    fic.validate_exclusion(exclusion)
                )


class TestCheckIntegrityExclusionValidation(unittest.TestCase):

    def test_check_integrity_rejects_absolute_unix_exclusion(self):

        # The unit test above proves the rule; this proves the rule is reached
        # and turns into the documented exit code rather than a silent scan.
        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_path = (
                root / "baseline" / "baseline.json"
            )

            monitored_folder.mkdir()

            (monitored_folder / "important.txt").write_text(
                "Important content",
                encoding="utf-8"
            )

            initialize_result = fic.initialize(
                monitored_folder,
                baseline_path,
                []
            )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            result = fic.check_integrity(
                monitored_folder,
                baseline_path,
                ["/etc/passwd"]
            )

            self.assertEqual(
                result,
                fic.EXIT_ERROR
            )


# --------------------------------------------------
# Test show_status()
#
# `status` had no tests at all, which is how it came to print "Baseline
# integrity: FAILED" and exit 0 for as long as it did. The command's whole job is
# reporting on the baseline, and the exit code is the only part of its report that
# anything automated reads. The action that runs it in CI ran it twice, both times
# after `init`, so it was only ever asked about a tree that was fine -- and under
# `set -e` a healthy 0 is indistinguishable from an unconditional one.
#
# So these assert the exit code against the printed lines in each state, rather
# than asserting the lines alone. A disagreement between the two is the defect.
# --------------------------------------------------

class TestShowStatus(unittest.TestCase):

    @contextlib.contextmanager
    def tree(self, exclusions=()):
        """A healthy initialised tree: monitored folder, baseline, sidecar.

        Built by calling initialize() rather than by writing the three files by
        hand, so the sidecar holds the digest fic itself computes. A hand-rolled
        one would only prove that this file and its author agree about the format.
        """

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            monitored_folder = root / "data"

            baseline_path = (
                root / "baseline" / "baseline.json"
            )

            monitored_folder.mkdir()

            (monitored_folder / "important.txt").write_text(
                "Important data",
                encoding="utf-8"
            )

            with contextlib.redirect_stdout(io.StringIO()):

                initialize_result = fic.initialize(
                    monitored_folder,
                    baseline_path,
                    list(exclusions)
                )

            self.assertEqual(
                initialize_result,
                fic.EXIT_SUCCESS
            )

            yield monitored_folder, baseline_path

    def status(self, monitored_folder, baseline_path):

        output = io.StringIO()

        with contextlib.redirect_stdout(output):

            result = fic.show_status(
                monitored_folder,
                baseline_path
            )

        return result, output.getvalue()

    def test_a_healthy_tree_is_ok_and_exits_zero(self):

        # The case CI was already covering, kept because everything below changes
        # the exit code and something has to pin the value it changes it from. The
        # fic-checks action runs `status` after `init` under `set -e`, so a
        # regression here fails that job rather than this test alone.
        with self.tree(exclusions=["temp"]) as (monitored_folder, baseline_path):

            result, output = self.status(
                monitored_folder,
                baseline_path
            )

        self.assertEqual(
            result,
            fic.EXIT_SUCCESS
        )

        self.assertIn(
            "Baseline integrity: OK",
            output
        )

        self.assertIn(
            "Status: OK",
            output
        )

        self.assertNotIn(
            "PROBLEMS FOUND",
            output
        )

    def test_a_tampered_baseline_exits_error_rather_than_success(self):

        # The bug itself. A recorded digest is changed and the sidecar is left
        # alone, which is exactly what the sidecar exists to catch -- and `status`
        # caught it, said so on stdout, and returned EXIT_SUCCESS. Anything reading
        # the documented contract instead of the text was told the tree was fine.
        with self.tree() as (monitored_folder, baseline_path):

            baseline_data = json.loads(
                baseline_path.read_text(encoding="utf-8")
            )

            baseline_data["files"] = {
                name: "0" * 64
                for name in baseline_data["files"]
            }

            baseline_path.write_text(
                json.dumps(baseline_data, indent=4),
                encoding="utf-8"
            )

            result, output = self.status(
                monitored_folder,
                baseline_path
            )

        self.assertEqual(
            result,
            fic.EXIT_ERROR
        )

        self.assertIn(
            "Baseline integrity: FAILED",
            output
        )

        self.assertIn(
            "does not match its sidecar digest",
            output
        )

        # Still loadable, so the exit code came from the integrity check and not
        # from the unreadable-baseline branch further up. Two problems both exiting
        # 2 would make this test pass while testing the wrong one.
        self.assertNotIn(
            "could not be read",
            output
        )

    def test_a_missing_sidecar_is_a_problem_rather_than_a_pass(self):

        # "unavailable" is not "fine". Deleting the sidecar removes the ability to
        # verify, and an exit code that said 0 here would make "we could not look"
        # and "we looked and found nothing" the same answer.
        with self.tree() as (monitored_folder, baseline_path):

            fic.get_baseline_hash_path(
                baseline_path
            ).unlink()

            result, output = self.status(
                monitored_folder,
                baseline_path
            )

        self.assertEqual(
            result,
            fic.EXIT_ERROR
        )

        self.assertIn(
            "Baseline hash: MISSING",
            output
        )

        self.assertIn(
            "Baseline integrity: unavailable",
            output
        )

        self.assertIn(
            "integrity cannot be verified",
            output
        )

    def test_an_unverifiable_state_exits_what_check_exits(self):

        # Asserted against `check` rather than against a literal, because the
        # argument for 2 was that it is what the sibling command already returns on
        # the same tree. If `check` ever moves, this fails and the pair is looked at
        # together instead of drifting apart quietly.
        with self.tree() as (monitored_folder, baseline_path):

            baseline_path.unlink()

            fic.get_baseline_hash_path(
                baseline_path
            ).unlink()

            status_result, output = self.status(
                monitored_folder,
                baseline_path
            )

            with contextlib.redirect_stdout(io.StringIO()):

                check_result = fic.check_integrity(
                    monitored_folder,
                    baseline_path,
                    []
                )

        self.assertEqual(
            status_result,
            check_result
        )

        self.assertEqual(
            status_result,
            fic.EXIT_ERROR
        )

        self.assertIn(
            "there is no baseline to check against",
            output
        )

    def test_a_missing_monitored_folder_is_a_problem_while_integrity_is_fine(self):

        # The state that separates "the baseline is intact" from "the system is
        # healthy". Every baseline line here is OK, integrity verifies, and the
        # thing being watched is gone -- so a status derived from the integrity
        # check alone would report success over a folder that no longer exists.
        with self.tree() as (monitored_folder, baseline_path):

            (monitored_folder / "important.txt").unlink()

            monitored_folder.rmdir()

            result, output = self.status(
                monitored_folder,
                baseline_path
            )

        self.assertEqual(
            result,
            fic.EXIT_ERROR
        )

        self.assertIn(
            "Monitored folder: MISSING",
            output
        )

        self.assertIn(
            "Baseline integrity: OK",
            output
        )

        self.assertIn(
            "the monitored folder does not exist",
            output
        )

    def test_an_unreadable_baseline_with_a_matching_digest_is_still_a_problem(self):

        # Why the unreadable baseline is tracked separately from the sidecar check
        # rather than folded into it: the two can disagree. The file is overwritten
        # with something that is not JSON and the sidecar is recomputed *over the
        # corruption*, so integrity verifies perfectly against a baseline nothing
        # can load. Deriving the exit code from the integrity line would print
        # "unavailable" for the file count and exit 0 in the same breath.
        with self.tree() as (monitored_folder, baseline_path):

            baseline_path.write_text(
                "this is not json at all\n",
                encoding="utf-8"
            )

            with contextlib.redirect_stdout(io.StringIO()):

                fic.save_baseline_hash(
                    baseline_path
                )

            self.assertTrue(
                fic.verify_baseline_hash(baseline_path)
            )

            result, output = self.status(
                monitored_folder,
                baseline_path
            )

        self.assertEqual(
            result,
            fic.EXIT_ERROR
        )

        self.assertIn(
            "Baseline files: unavailable",
            output
        )

        self.assertIn(
            "Baseline integrity: OK",
            output
        )

        self.assertIn(
            "the baseline exists but could not be read",
            output
        )

    def test_every_problem_is_named_and_not_merely_counted(self):

        # A reader holding the output can already see which lines say MISSING. This
        # is for the reader holding only the exit code, which is the one the code
        # exists for -- so each problem is listed by name, and all of them are,
        # rather than the first one found short-circuiting the rest.
        with self.tree() as (monitored_folder, baseline_path):

            (monitored_folder / "important.txt").unlink()

            monitored_folder.rmdir()

            baseline_path.unlink()

            fic.get_baseline_hash_path(
                baseline_path
            ).unlink()

            result, output = self.status(
                monitored_folder,
                baseline_path
            )

        self.assertEqual(
            result,
            fic.EXIT_ERROR
        )

        self.assertIn(
            "Status: PROBLEMS FOUND",
            output
        )

        for problem in (
            "the monitored folder does not exist",
            "there is no baseline to check against",
            "the baseline's sidecar digest is missing",
        ):

            with self.subTest(problem=problem):

                self.assertIn(
                    problem,
                    output
                )


# --------------------------------------------------
# Run tests
# --------------------------------------------------

if __name__ == "__main__":

    unittest.main()