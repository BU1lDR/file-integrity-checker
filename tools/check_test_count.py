"""Assert the test count quoted in README.md and in this repository's GitHub
description is the count discovery actually finds.

CI already proves discovery finds *something*: the fic-checks action fails if
``discover`` collects zero, because a renamed directory or a changed file pattern
would otherwise turn both suite steps green while testing nothing. That guard
answers "is this number greater than zero". It does not answer "is this number the
one the documentation claims", and two places claim it:

    README.md          "48 tests, no fixtures to set up"
    GitHub description "48 unittest cases."

Both are correct as this is written. Neither was checked by anything, and the
sibling project already ran this experiment for us: security-scanner's description
said "353 tests" while its suite was at 396, having survived two increments that
moved every other copy of the figure. It stayed wrong because a repository
description cannot appear in a diff — no commit touches it, so no review sees it,
and it is the first sentence anyone reads.

Adding a test is the most routine change this repo can receive and it falsifies
both numbers at once. That is the whole argument for checking rather than
remembering: a figure that goes stale every time the project improves is a figure
nobody can maintain by intending to.

Run from the repository root: ``python tools/check_test_count.py``. Both copies are
checked on every run, so two stale numbers are one run's output rather than two
round trips, and the exact ``gh repo edit`` command is printed for the one no
commit can fix.

When the GitHub API cannot be reached this says so, in those words, rather than
reporting agreement: "we found nothing" and "we could not look" must not produce
the same output. Under GITHUB_ACTIONS that state also exits non-zero, because a
check that quietly skips itself in CI is a green tick over nothing. Run by hand it
only reports, so a clone with no token still gets the README check instead of a
wall.

Python 3.8 compatible, deliberately. Nothing in CI needs it to be — this runs in
one job on one current interpreter, not in the version matrix — but this repo's
headline claim is 3.8+ and it installs nothing anywhere, so a tool here that
quietly required 3.9 would be a trap for the next person who reaches for it. The
accommodations are two: no str.removesuffix, and socket.timeout is caught
alongside TimeoutError because before 3.10 they are unrelated classes and urllib
raises the former.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
TESTS = ROOT / "tests"

API = "https://api.github.com/repos/{slug}"
TIMEOUT = 15

# The two copies word it differently, so they get a pattern each rather than one
# pattern loose enough to match both. A regex that accepted "tests" or "cases"
# anywhere would also match prose about test cases in general, and this file's
# value depends entirely on it comparing the figure someone actually reads.
README_QUOTED = re.compile(r"\b(\d+) tests\b")           # "48 tests, no fixtures ..."
DESCRIPTION_QUOTED = re.compile(r"\b(\d+) unittest cases\b")  # "... 48 unittest cases."


def discovered_count() -> int:
    """How many tests ``unittest discover`` finds, in process.

    The same call the fic-checks action makes, for the same reason it makes it
    there rather than parsing output: a count read back from a summary line is a
    count you have to trust the formatting of.

    loader.errors is checked because it is the hole in countTestCases(). When a
    test module fails to import, discovery does not raise — it synthesises a
    _FailedTest standing in for the module, and that placeholder *counts*. So a
    broken import can leave the total looking plausible, or even unchanged, and
    this script would compare a number about nothing to the README and agree with
    it. An import failure has to be louder than a mismatch, not quieter.
    """
    # Discovery imports the test modules, which `import fic`. Standing in the root
    # is what normally puts fic.py on sys.path; doing it explicitly means this
    # works when run from anywhere, which matters because the thing it is checking
    # (README.md) documents being run from two different directories.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    loader = unittest.defaultTestLoader
    suite = loader.discover(str(TESTS), top_level_dir=str(ROOT))

    if loader.errors:
        for error in loader.errors:
            sys.stderr.write(str(error) + "\n")
        raise SystemExit(
            "discovery could not load every test module (see above), so its count "
            "is a count of placeholders and means nothing. Fix the import first."
        )

    count = suite.countTestCases()
    if count == 0:
        raise SystemExit(
            "discovery collected no tests, so there is no real number to compare "
            "the documentation against"
        )
    return count


def repo_slug() -> str | None:
    """owner/repo for this checkout, or None if it cannot be established.

    GITHUB_REPOSITORY first: in Actions it is authoritative and costs no
    subprocess. The origin remote is the fallback, so a hand run works and so a
    fork checks its own description rather than asserting against a page its owner
    cannot edit.
    """
    from_env = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if from_env.count("/") == 1:
        return from_env

    proc = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if proc.returncode != 0:
        return None
    url = proc.stdout.strip()
    if url.endswith(".git"):          # str.removesuffix is 3.9+; this repo says 3.8+
        url = url[: -len(".git")]
    if "github.com" not in url:
        return None
    parts = re.split(r"[/:]", url)
    if len(parts) < 2:
        return None
    return "/".join(parts[-2:])


def fetch_description(slug: str) -> tuple[str | None, str | None]:
    """(description, error). Exactly one of the two is None.

    The description comes back whole, not just its number, because the fix for a
    stale one is a replacement string: `gh repo edit` takes the whole sentence.
    Having it here lets the failure message print a command that can be run
    without reading it first.

    The token is not for access — the description is public — but for the rate
    limit. Unauthenticated calls get 60/hour shared across everything leaving that
    runner's IP, which fails for reasons that have nothing to do with the claim.
    """
    request = urllib.request.Request(
        API.format(slug=slug),
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            # The API refuses requests without one.
            "User-Agent": "fic-check-test-count (+https://github.com/{})".format(slug),
        },
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", "Bearer " + token)

    # One retry, and only for failures that are plausibly the network rather than
    # the answer. A 404 or 403 is not retried: repeating a question does not change
    # a refusal, and a rate-limit 403 deserves to be read rather than papered over.
    last = None  # type: str | None
    for attempt in range(2):
        if attempt:
            time.sleep(2)
        try:
            response = urllib.request.urlopen(request, timeout=TIMEOUT)
        except urllib.error.HTTPError as exc:
            last = "HTTP {} from the GitHub API for {}".format(exc.code, slug)
            if exc.code < 500:
                return None, last
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            # socket.timeout only became an alias of TimeoutError in 3.10, and it
            # is what urllib raises on a read timeout before then.
            last = "could not reach the GitHub API for {}: {}".format(
                slug, getattr(exc, "reason", exc)
            )
        else:
            try:
                with response:
                    return json.load(response).get("description") or "", None
            except (json.JSONDecodeError, ValueError) as exc:
                return None, "the GitHub API returned something that is not JSON: {}".format(exc)
    return None, "{} (retried once)".format(last)


def check_readme(actual: int) -> bool:
    text = README.read_text(encoding="utf-8")
    quoted = README_QUOTED.search(text)
    if quoted is None:
        print("no 'N tests' figure found in README.md — did the wording change?")
        return False

    claimed = int(quoted.group(1))
    if claimed == actual:
        print("README.md says {} tests; discovery finds {}. Agreed.".format(claimed, actual))
        return True

    line_no = text[: quoted.start()].count("\n") + 1
    print(
        "README.md:{} claims {} tests; discovery finds {}.\n"
        "Update that line.".format(line_no, claimed, actual)
    )
    return False


def check_description(actual: int) -> bool:
    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"

    slug = repo_slug()
    if slug is None:
        print(
            "could not work out which GitHub repository this checkout is, so the\n"
            "description went unchecked (no GITHUB_REPOSITORY and no github.com\n"
            "origin remote)."
        )
        return not in_ci

    description, error = fetch_description(slug)
    if error is not None:
        print(
            "the repo description went unchecked: {}.\n"
            "README.md was still checked. Re-run with a network, or open\n"
            "https://github.com/{} and compare the sentence under the repo "
            "name.".format(error, slug)
        )
        return not in_ci

    quoted = DESCRIPTION_QUOTED.search(description)
    if quoted is None:
        print(
            "{}'s description quotes no 'N unittest cases' figure, so there is\n"
            "nothing there to go stale. Nothing to do.".format(slug)
        )
        return True

    claimed = int(quoted.group(1))
    if claimed == actual:
        print(
            "{}'s description says {} unittest cases; discovery finds {}. "
            "Agreed.".format(slug, claimed, actual)
        )
        return True

    # count=1 so only the figure that was compared is rewritten. A description
    # that somehow quotes two counts wants a person looking at it, not silent
    # normalisation by a command this script suggested.
    corrected = DESCRIPTION_QUOTED.sub("{} unittest cases".format(actual), description, count=1)
    print(
        "{}'s description claims {} unittest cases; discovery finds {}.\n"
        "It is the first sentence a visitor reads and the one copy no commit can\n"
        "fix. Run:\n"
        "\n"
        "  gh repo edit {} --description {}\n".format(
            slug, claimed, actual, slug, shlex.quote(corrected)
        )
    )
    return False


def main() -> int:
    actual = discovered_count()
    # Both checks run before either verdict is used; `and` would short-circuit the
    # second, and two stale copies should cost one run, not two.
    readme_ok = check_readme(actual)
    description_ok = check_description(actual)
    return 0 if readme_ok and description_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
