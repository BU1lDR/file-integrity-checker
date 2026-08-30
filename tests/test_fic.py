import hashlib
import tempfile
import unittest
from pathlib import Path

import fic


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

if __name__ == "__main__":

    unittest.main()