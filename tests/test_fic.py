import hashlib
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
# Run tests
# --------------------------------------------------

if __name__ == "__main__":

    unittest.main()