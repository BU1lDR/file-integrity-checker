import contextlib
import http.client
import importlib.util
import io
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


# --------------------------------------------------
# tools/check_test_count.py
#
# The guard that compares README.md and the GitHub description against what
# `unittest discover` actually finds. It had no tests, and that is not an
# incidental gap: a fix for the mid-read crash below was written, reported as
# landed in this repository and in security-scanner's copy, and had in fact only
# landed in one of them. Nothing could tell the two apart, because neither copy
# was executed by anything except the workflow that runs it against the live API.
#
# Loaded by path. tools/ is not a package and is not on sys.path -- the script is
# run as `python tools/check_test_count.py`, and it finds the repository root from
# its own __file__ rather than from being imported.
# --------------------------------------------------

TOOL = Path(__file__).resolve().parent.parent / "tools" / "check_test_count.py"


def load_tool():

    spec = importlib.util.spec_from_file_location(
        "check_test_count_under_test",
        TOOL
    )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module


class ToolCase(unittest.TestCase):
    """Loads the tool, and puts back everything it borrows.

    load_tool() returns a fresh module object, so assigning to *its* attributes is
    per-test. Its `os`, `time`, `urllib` and `unittest` attributes are not: those
    are the one shared module object each, and setting an attribute on one of them
    changes it for the whole process. The first version of this file did exactly
    that -- `self.tool.os.environ = {}` left os.environ a plain dict for every test
    that ran afterwards -- so each borrow now goes through patch() and is handed
    back, and sys.path is restored because discovery inserts into it.
    """

    def setUp(self):

        self.tool = load_tool()

        self.addCleanup(
            sys.path.__setitem__,
            slice(None),
            list(sys.path)
        )

    def borrow(self, target, attribute, replacement):

        patcher = mock.patch.object(target, attribute, replacement)

        patcher.start()

        self.addCleanup(patcher.stop)

    def no_sleeping(self):

        self.borrow(self.tool.time, "sleep", lambda seconds: None)

    def serve_with(self, urlopen):

        self.borrow(self.tool.urllib.request, "urlopen", urlopen)


class Body:
    """A urlopen return value whose *body* misbehaves.

    The distinction this class exists for: urlopen has already succeeded. It is
    read() that fails, which is the failure urllib does not wrap and the one the
    handler's own comment promises to retry.
    """

    def __init__(self, error=None, data=b""):

        self.error = error

        self.data = data

    def __enter__(self):

        return self

    def __exit__(self, *exc_info):

        return False

    def read(self, *args):

        if self.error is not None:
            raise self.error

        return self.data

    def readinto(self, buffer):

        if self.error is not None:
            raise self.error

        buffer[:len(self.data)] = self.data

        return len(self.data)


# --------------------------------------------------
# Test fetch_description() -- the network edge it used to crash on
# --------------------------------------------------

class TestFetchDescriptionMidReadFailures(ToolCase):

    def setUp(self):

        super().setUp()

        # No real two-second wait for the retry this whole class is about.
        self.no_sleeping()

        self.attempts = []

    def serve(self, body):

        def urlopen(*args, **kwargs):

            self.attempts.append(1)

            return body

        self.serve_with(urlopen)

    def test_incomplete_read_is_reported_not_raised(self):

        # http.client.IncompleteRead is an HTTPException and not an OSError, so it
        # is the case the second handler names HTTPException for. Before the body
        # read moved inside the try, it escaped as a traceback from a tool whose
        # documented behaviour on a network failure is to say so and carry on.
        self.serve(
            Body(http.client.IncompleteRead(b'{"descr'))
        )

        description, error = self.tool.fetch_description("BU1lDR/x")

        self.assertIsNone(description)

        self.assertIn("could not reach the GitHub API", error)

        self.assertIn("IncompleteRead", error)

        self.assertIn("retried once", error)

    def test_connection_reset_mid_read_is_reported_not_raised(self):

        self.serve(
            Body(ConnectionResetError(104, "Connection reset by peer"))
        )

        description, error = self.tool.fetch_description("BU1lDR/x")

        self.assertIsNone(description)

        self.assertIn("could not reach the GitHub API", error)

        self.assertIn("retried once", error)

    def test_a_mid_read_failure_is_retried_exactly_once(self):

        self.serve(
            Body(ConnectionResetError(104, "Connection reset by peer"))
        )

        self.tool.fetch_description("BU1lDR/x")

        self.assertEqual(
            len(self.attempts),
            2
        )


# --------------------------------------------------
# Test fetch_description() -- the answers that are answers
# --------------------------------------------------

class TestFetchDescriptionResponses(ToolCase):

    def setUp(self):

        super().setUp()

        self.no_sleeping()

        self.attempts = []

    def serve_status(self, code):

        def urlopen(*args, **kwargs):

            self.attempts.append(code)

            error = urllib.error.HTTPError(
                "https://api.github.com/repos/BU1lDR/x",
                code,
                "message",
                {},
                None
            )

            # HTTPError reaches _TemporaryFileWrapper through addinfourl, and its
            # __del__ emits a ResourceWarning unless close() was called -- passing
            # fp=None does not help, because .fp is created on demand. Closing them
            # keeps the suite's output clean, and warning noise in a CI log is how
            # real warnings stop being read.
            self.addCleanup(error.close)

            raise error

        self.serve_with(urlopen)

    def test_a_description_comes_back_whole(self):

        # Whole, not just its number: the fix for a stale count is a replacement
        # string, and the failure message prints a `gh repo edit` that can be run
        # without being read first.
        self.serve_with(lambda *a, **k: Body(
            data=b'{"description": "Tamper detection ... 48 unittest cases."}'
        ))

        description, error = self.tool.fetch_description("BU1lDR/x")

        self.assertIsNone(error)

        self.assertEqual(
            description,
            "Tamper detection ... 48 unittest cases."
        )

    def test_a_null_description_is_an_empty_string_not_none(self):

        # A repository with no description at all. None here would be read by the
        # caller as a failure to look, which it is not.
        self.serve_with(lambda *a, **k: Body(
            data=b'{"description": null}'
        ))

        description, error = self.tool.fetch_description("BU1lDR/x")

        self.assertIsNone(error)

        self.assertEqual(
            description,
            ""
        )

    def test_a_body_that_is_not_json_is_not_retried(self):

        # A malformed body is an answer. Asking again gets the same one, and
        # reporting it as a network failure would send somebody to look at the
        # wrong thing.
        attempts = []

        def urlopen(*args, **kwargs):

            attempts.append(1)

            return Body(data=b"<html>rate limited</html>")

        self.serve_with(urlopen)

        description, error = self.tool.fetch_description("BU1lDR/x")

        self.assertIsNone(description)

        self.assertIn("not JSON", error)

        self.assertNotIn("retried", error)

        self.assertEqual(
            len(attempts),
            1
        )

    def test_a_404_is_not_retried(self):

        self.serve_status(404)

        description, error = self.tool.fetch_description("BU1lDR/x")

        self.assertIsNone(description)

        self.assertEqual(
            error,
            "HTTP 404 from the GitHub API for BU1lDR/x"
        )

        self.assertEqual(
            len(self.attempts),
            1
        )

    def test_a_rate_limit_403_is_reported_rather_than_papered_over(self):

        self.serve_status(403)

        description, error = self.tool.fetch_description("BU1lDR/x")

        self.assertIn("HTTP 403", error)

        self.assertEqual(
            len(self.attempts),
            1
        )

    def test_a_server_error_is_retried_once(self):

        # HTTPError is a URLError is an OSError, so this also pins the handler
        # order: if the OSError clause came first it would swallow every status
        # code as a network failure and this message would read differently.
        self.serve_status(502)

        description, error = self.tool.fetch_description("BU1lDR/x")

        self.assertIn("HTTP 502", error)

        self.assertIn("retried once", error)

        self.assertEqual(
            len(self.attempts),
            2
        )


# --------------------------------------------------
# Test check_readme()
# --------------------------------------------------

class TestCheckReadme(ToolCase):

    @contextlib.contextmanager
    def readme(self, text):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = Path(temp_dir) / "README.md"

            path.write_text(
                text,
                encoding="utf-8"
            )

            self.tool.README = path

            yield

    def run_check(self, text, actual):

        output = io.StringIO()

        with self.readme(text):

            with contextlib.redirect_stdout(output):

                result = self.tool.check_readme(actual)

        return result, output.getvalue()

    def test_every_quoted_copy_is_checked_not_just_the_first(self):

        # finditer, not search. A loop that stopped at the first match would
        # correct one copy and certify the rest as fine in the same breath -- and
        # the paragraph in README.md explaining this check quotes the count again,
        # so there genuinely is more than one.
        result, output = self.run_check(
            "It ships 48 tests, no fixtures.\n"
            "The workflow asserts 48 tests still pass.\n"
            "The description says 12 unittest cases.\n",
            48
        )

        self.assertFalse(result)

        self.assertIn("README.md:3", output)

        self.assertIn("12", output)

    def test_both_wordings_are_recognised(self):

        # README.md is free to quote the description's phrasing as well as its own,
        # and a copy it holds can go stale whichever way it is worded.
        result, output = self.run_check(
            "It ships 48 tests.\nThe description says 48 unittest cases.\n",
            48
        )

        self.assertTrue(result)

        self.assertIn("in 2 places", output)

    def test_a_readme_with_no_figure_fails_rather_than_passing_by_not_looking(self):

        # The failure mode worth more than all the others put together: the
        # sentence is reworded or deleted, the pattern matches nothing, and a check
        # that found no disagreement reports success.
        result, output = self.run_check(
            "It ships a comprehensive test suite.\n",
            48
        )

        self.assertFalse(result)

        self.assertIn("passes by not looking", output)

    def test_agreement_names_the_line_it_agreed_on(self):

        result, output = self.run_check(
            "# fic\n\nIt ships 48 tests, no fixtures.\n",
            48
        )

        self.assertTrue(result)

        self.assertIn("line 3", output)

    def test_a_count_inside_a_larger_number_is_not_matched(self):

        # \b on both sides. "148 tests" is not a claim of 48.
        result, output = self.run_check(
            "It ships 148 tests.\n",
            48
        )

        self.assertFalse(result)

        self.assertIn("148", output)


# --------------------------------------------------
# Test check_description()
# --------------------------------------------------

class TestCheckDescription(ToolCase):

    def setUp(self):

        super().setUp()

        self.tool.repo_slug = lambda: "BU1lDR/file-integrity-checker"

        # patch.dict, not a replacement: os.environ is the process's, and handing
        # back a plain dict in its place is not handing it back. It also has to be
        # patched at all rather than read as-is, because a real GITHUB_ACTIONS in
        # the environment would silently flip the two-way test below.
        patcher = mock.patch.dict(
            self.tool.os.environ,
            {},
            clear=True
        )

        patcher.start()

        self.addCleanup(patcher.stop)

    def in_ci(self):

        self.tool.os.environ["GITHUB_ACTIONS"] = "true"

    def run_check(self, actual):

        output = io.StringIO()

        with contextlib.redirect_stdout(output):

            result = self.tool.check_description(actual)

        return result, output.getvalue()

    def serve(self, description, error=None):

        self.tool.fetch_description = lambda slug: (description, error)

    def test_a_stale_description_fails_and_prints_a_runnable_fix(self):

        self.serve("Tamper detection with 12 unittest cases.")

        result, output = self.run_check(48)

        self.assertFalse(result)

        self.assertIn("gh repo edit", output)

        self.assertIn("48 unittest cases", output)

    def test_only_the_compared_figure_is_rewritten(self):

        # count=1. A description quoting two counts wants a person looking at it,
        # not silent normalisation by a command this script suggested.
        self.serve("12 unittest cases, and once 12 unittest cases fewer.")

        result, output = self.run_check(48)

        self.assertFalse(result)

        self.assertIn("48 unittest cases, and once 12 unittest cases fewer.", output)

    def test_an_agreeing_description_passes(self):

        self.serve("Tamper detection with 48 unittest cases.")

        result, output = self.run_check(48)

        self.assertTrue(result)

        self.assertIn("Agreed", output)

    def test_a_description_quoting_no_figure_has_nothing_to_go_stale(self):

        self.serve("Tamper detection for a monitored folder.")

        result, output = self.run_check(48)

        self.assertTrue(result)

        self.assertIn("nothing there to go stale", output)

    def test_an_unreachable_api_passes_by_hand_and_fails_in_ci(self):

        # The deliberate asymmetry, and the behaviour the traceback discarded: by
        # hand, a missing network must not block work on the README, so it reports
        # and passes. In CI a green tick is a positive claim that the description
        # was compared, so there it has to fail.
        self.serve(None, error="could not reach the GitHub API for x: timed out")

        result, output = self.run_check(48)

        self.assertTrue(result)

        self.assertIn("went unchecked", output)

        self.in_ci()

        result, output = self.run_check(48)

        self.assertFalse(result)

    def test_an_unidentifiable_repository_passes_by_hand_and_fails_in_ci(self):

        self.tool.repo_slug = lambda: None

        result, output = self.run_check(48)

        self.assertTrue(result)

        self.assertIn("went unchecked", output)

        self.in_ci()

        result, output = self.run_check(48)

        self.assertFalse(result)


# --------------------------------------------------
# Test discovered_count()
# --------------------------------------------------

class TestDiscoveredCount(ToolCase):

    def setUp(self):

        super().setUp()

        # A loader of its own. defaultTestLoader is a shared global and the run
        # executing this test is holding it, so this is borrowed and handed back
        # rather than assigned over.
        self.borrow(
            self.tool.unittest,
            "defaultTestLoader",
            unittest.TestLoader()
        )

    @contextlib.contextmanager
    def tree(self, package, filename, source):

        # A package name of its own per test, never "tests". Calling the temporary
        # directory `tests` makes discovery import `tests.<module>`, and this
        # repository's real `tests` package is already in sys.modules -- so every
        # import inside the fixture failed, and the broken-import test below passed
        # for a reason that had nothing to do with the broken import.
        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(temp_dir)

            tests = root / package

            tests.mkdir()

            (tests / "__init__.py").write_text(
                "",
                encoding="utf-8"
            )

            (tests / filename).write_text(
                source,
                encoding="utf-8"
            )

            self.tool.ROOT = root

            self.tool.TESTS = tests

            yield

    def test_a_module_that_cannot_be_imported_is_louder_than_a_mismatch(self):

        # The hole in countTestCases(): discovery does not raise on a failed
        # import, it synthesises a _FailedTest standing in for the module -- and
        # that placeholder counts. So a broken import can leave the total looking
        # plausible, and comparing it to the README would agree about nothing.
        with self.tree(
            "tpkg_broken",
            "test_broken.py",
            "import a_module_that_does_not_exist\n"
        ):

            with self.assertRaises(SystemExit) as raised:

                with contextlib.redirect_stderr(io.StringIO()):

                    self.tool.discovered_count()

        self.assertIn(
            "count of placeholders",
            str(raised.exception)
        )

    def test_discovering_nothing_is_an_error_not_a_zero(self):

        # Zero is not a number to compare the documentation against; it is the
        # absence of one. Returning it would make the README's figure "wrong" for
        # a reason that has nothing to do with the README.
        with self.tree(
            "tpkg_empty",
            "not_a_test_module.py",
            "x = 1\n"
        ):

            with self.assertRaises(SystemExit) as raised:

                self.tool.discovered_count()

        self.assertIn(
            "collected no tests",
            str(raised.exception)
        )

    def test_a_real_count_is_returned(self):

        source = (
            "import unittest\n"
            "\n"
            "\n"
            "class T(unittest.TestCase):\n"
            "    def test_one(self):\n"
            "        pass\n"
            "    def test_two(self):\n"
            "        pass\n"
        )

        with self.tree("tpkg_counted", "test_two_of_them.py", source):

            self.assertEqual(
                self.tool.discovered_count(),
                2
            )


# --------------------------------------------------
# Run tests
# --------------------------------------------------

if __name__ == "__main__":

    unittest.main()
