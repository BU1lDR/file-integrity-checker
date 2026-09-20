# 🛡️ File Integrity Checker (FIC)

> **Lightweight, hash-based file integrity monitoring for Python.**

[![CI](https://github.com/BU1lDR/file-integrity-checker/actions/workflows/file-integrity-checker.yml/badge.svg)](https://github.com/BU1lDR/file-integrity-checker/actions/workflows/file-integrity-checker.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Security: SHA-256](https://img.shields.io/badge/Security-SHA--256-green.svg)](https://en.wikipedia.org/wiki/SHA-2)
[![Platform: Cross--Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](#)

---

- Brief: <https://roadmap.sh/projects/file-integrity-checker>
- Submission: <[https://roadmap.sh/projects/file-integrity-checker/solutions?u=6a6b956333d15c831089876f](https://roadmap.sh/projects/file-integrity-checker)>

---

## 📌 Overview

**File Integrity Checker (FIC)** is a CLI utility that tells you when files under a directory
have changed behind your back — edited, replaced, added, or deleted.

It takes a snapshot (baseline) of your target directory as **SHA-256 digests**, then compares the
directory against that snapshot whenever you ask it to. FIC detects changes; it does not prevent
them, and it only looks when you run it.

```text
┌──────────────────┐      📸 Snapshot     ┌─────────────────┐ 
│ Monitored Folder │ ───────────────────> │  baseline.json  │
└──────────────────┘                      └─────────────────┘
         │                                          │
         │     🔍 Compare Current vs Baseline       |
         └──────────────────────────────────────────┘
                               │
                               ▼
            🚨 [MODIFIED]  ✨ [NEW]  ❌ [DELETED]
```

---

## ✨ Features

| Feature | Description |
| :--- | :--- |
| **🔒 SHA-256 Digests** | Hashes file contents with collision-resistant **SHA-256**, so a change of a single byte shows up. |
| **🔎 Baseline Sidecar Digest** | Writes the baseline's own SHA-256 to a `.sha256` file beside it, so a corrupted or hand-edited baseline is caught instead of trusted. |
| **⚡ Atomic Write Safety** | Uses `os.replace` with retry backoff to prevent baseline corruption during unexpected interruptions. |
| **🎯 Granular Filtering** | Excludes specific files or nested directories using normalized relative path rules. |
| **🔗 Symlink Defense** | Bypasses symbolic links automatically to block infinite loops and out-of-scope traversal. |
| **📊 Clear Reporting** | Displays formatted terminal output while logging detailed events to disk. |

---

## ⚙️ How It Works

FIC executes in **four main stages**:

```text
  1. LOAD CONFIG       2. DIRECTORY SCAN       3. BASELINE / CHECK       4. VERIFY & REPORT
┌──────────────────┐   ┌────────────────────┐   ┌──────────────────────┐   ┌───────────────────┐
│ Read config.json │ ─>│ Traverse directory │ ─>│ Hash files (4KB)     │ ─>│ Output summary to │
│ & validate keys  │   │ & check exclusions │   │ Save/Verify snapshot │   │ stdout & fic.log  │
└──────────────────┘   └────────────────────┘   └──────────────────────┘   └───────────────────┘
```

1. **Configuration**: Parses and validates `config.json` parameters (`monitored_folder`, `baseline_path`, `log_path`, `exclusions`).
2. **Directory Walk**: Scans target folders recursively while honoring exclusion lists and skipping symlinks.
3. **Hashing Engine**: Computes SHA-256 digests in efficient 4 KB chunks.
4. **Integrity Match**:
   - **`init`**: Writes `baseline.json` and records its own SHA-256 in a `<baseline>.sha256` sidecar.
   - **`check`**: Validates `baseline.json` health and flags `[MODIFIED]`, `[NEW]`, `[DELETED]`, or `[SCAN ERROR]` files.

---

## 📋 Requirements

- **Python**: `3.8` or higher
- **Dependencies**: **Zero third-party libraries required!** Built entirely on standard library modules (`argparse`, `hashlib`, `json`, `logging`, `os`, `re`, `sys`, `time`, `pathlib`).

---

## 🚀 Quick Start & Installation

```bash
# 1. Clone the repository.
git clone https://github.com/BU1lDR/file-integrity-checker.git
cd file-integrity-checker

# 2. Verify Python version (3.8+). Use `python3` if `python` is not on your PATH.
python --version

# 3. Take a baseline. The repo ships a sample target_folder/, which is what the
#    default config.json monitors, so this works on a fresh clone.
python fic.py init

# 4. Nothing has changed yet, so this reports every file as [UNCHANGED].
python fic.py check
```

There is nothing to install — FIC is standard library only. `init` writes
`baseline.json`, `baseline.sha256`, and `logs/fic.log` next to `config.json`; all
three are gitignored.

To point FIC at something of your own, edit `monitored_folder` in `config.json`
(or pass `--folder`). If that folder does not exist, `init` stops with
`[ERROR] Monitored folder does not exist` rather than creating it — FIC will not
invent the thing it is supposed to be watching.

---

## 🔧 Configuration

Setup your monitoring scope in **`config.json`**:

```json
{
    "monitored_folder": "target_folder",
    "baseline_path": "baseline.json",
    "log_path": "logs/fic.log",
    "exclusions": [
        "temp",
        "cache/logs",
        "ignored_file.txt"
    ]
}
```

> ⚠️ **Security Rule**: Relative, forward-slash paths only for `exclusions`. Rejected during config
> parsing: anything starting with `/`, anything carrying a drive letter (`C:/logs`, `C:\logs`, and the
> drive-relative `C:logs`), anything containing a backslash, and any path with a `..` segment. The rule
> is the same one applied to the paths inside the baseline, and it is deliberately spelled out as string
> rules rather than delegated to `Path.is_absolute()` — that method calls `/etc/passwd` relative on
> Windows and absolute on Linux, so it cannot decide this for a config file meant to be portable.

**Where relative paths point.** Every relative path in `config.json` is resolved against the
directory `config.json` lives in — not against whatever directory you ran the command from. So
`python fic.py check` from the repo root and `python /path/to/file-integrity-checker/fic.py check`
from some unrelated directory monitor the same folder and write the same baseline. Paths you type on
the command line (`--folder`, `--baseline`, `--config`) are relative to your shell, which is what you
would expect from something you just typed.

Use `--config` to keep a config somewhere else:

```bash
python fic.py check --config /etc/fic/production.json
```

---

## 💻 Usage

FIC features three straightforward commands. Run them from anywhere — `fic.py` finds its own
`config.json`, so `python /path/to/file-integrity-checker/fic.py check` from an unrelated directory
does the same thing as `python fic.py check` from the repo root.

### 1. Create a Baseline (`init`)
Creates a fresh snapshot of your monitored directory.

```bash
python fic.py init
```

*CLI Overrides:*
```bash
python fic.py init --folder ./target_folder --baseline ./baseline.json --exclude temp
```

> Passing `--exclude` **replaces** the config's exclusion list rather than adding to it, and `check`
> refuses to run if its exclusions do not match the ones recorded in the baseline. Override on `init`
> and you have to pass the same `--exclude` flags to `check`.

---

### 2. Verify File Integrity (`check`)
Compares current files against your saved baseline.

```bash
python fic.py check
```

---

### 3. Inspect System Status (`status`)
Reports whether the monitored folder, the baseline, and its sidecar digest are present and agree.

```bash
python fic.py status
```

`status` exits `0` only when all three are present and the baseline matches its sidecar digest, and `2`
otherwise — including when the baseline or the sidecar is *missing*, because then integrity was not
verified rather than verified and fine. It names each problem it found on the way out, so the exit code
and the report cannot disagree. It printed `Baseline integrity: FAILED` and exited `0` until this was
fixed, which meant anything reading the documented contract instead of the text was told a tampered
baseline was healthy.

---

## Example Output

This is the shipped `target_folder/` after `init`, one file edited, one added, one deleted — so you
can reproduce it rather than take its word for it.

### Running `python fic.py check` (Changes Detected)

```text
Checking file integrity...


[MODIFIED]  notes.txt
[NEW]       scratch.txt
[DELETED]   data/records.csv

Integrity Check Summary
-----------------------
Unchanged:   0
Modified:    1
New:         1
Deleted:     1
Scan errors: 0

Symbolic links skipped: 0
```

Paths are relative to the monitored folder, not to the baseline. `ignored_file.txt` was edited too
and is absent from the report, because it is in the exclusion list.

---

### Running `python fic.py status`

```text
File Integrity Checker Status
-----------------------------
Monitored folder: OK (.../file-integrity-checker/target_folder)
Baseline: OK (.../file-integrity-checker/baseline.json)
Baseline hash: OK (.../file-integrity-checker/baseline.sha256)
Baseline files: 2
Exclusions: 3
  - temp
  - cache/logs
  - ignored_file.txt
Baseline integrity: OK

Status: OK
```

The paths print in full so there is no doubt which folder is being watched — `status` run from two
different directories should name the same one. On a tree with something wrong, the last line reads
`Status: PROBLEMS FOUND` and is followed by one line per problem:

```text
Baseline integrity: FAILED

Status: PROBLEMS FOUND
  - the baseline does not match its sidecar digest
```

---

## 🚦 Exit Codes

Integrate FIC seamlessly into **CI/CD pipelines**, **cron jobs**, or **automation scripts**:

| Exit Code | Symbol | Status | Meaning |
| :---: | :---: | :--- | :--- |
| **`0`** | ✅ | `EXIT_SUCCESS` | Execution successful. No file integrity violations found during `check`. |
| **`1`** | 🚨 | `EXIT_INTEGRITY_FAILURE` | Integrity check detected modified, new, or deleted files. |
| **`2`** | ❌ | `EXIT_ERROR` | Command failed due to invalid configuration, missing files, or baseline tampering. |

---

## 🔐 Security Considerations

- **Baseline Sidecar Digest — and what it is not**: FIC pairs `baseline.json` with a `.sha256` file
  holding the baseline's own digest, and refuses to run `check` if the two disagree. That digest is
  **unkeyed** and it lives in the same directory as the file it covers, so it is not a signature and
  the baseline is not tamper-proof: anyone who can write `baseline.json` can recompute the sidecar
  and overwrite it too. What the sidecar does catch is a baseline that was truncated, corrupted, or
  edited by something that did not know to update the digest — which is the common case, not the
  adversarial one.
- **If you need the baseline to survive an attacker**, the digest has to sit somewhere the attacker
  cannot reach: keep the baseline on read-only or append-only storage, or copy the `.sha256` off the
  host and compare it out of band. FIC does not do either for you.
- **Traversal Defense**: Config exclusions and baseline paths are rejected if they are absolute, carry
  a drive letter, contain a backslash, or contain `..`, and all relative paths are normalized to POSIX
  forward slashes (`/`) so the same baseline reads the same way on Windows and Linux. Both checks are
  written as string rules; the exclusion one used `Path.is_absolute()` until it was noticed that the
  answer differs by platform, which meant a config rejected on Linux was accepted on Windows.
- **Safe Persistence**: Writes data to a temporary file (`.tmp`) before calling `os.replace` to protect against partial baseline writes during crashes or file locks.

---

## 🧪 Running Tests

From the repository root:

```bash
python -m unittest discover -s tests
```

Unlike `fic.py`, this one does care where you stand — the tests `import fic`, so `fic.py` has to be
on `sys.path`. Above, what puts it there is `python -m` adding the current directory, which is the
repo root, which is where `fic.py` lives. From outside the clone, name the top-level directory
explicitly instead:

```bash
python -m unittest discover -s file-integrity-checker/tests -t file-integrity-checker
```

The two differ only in what puts `fic.py` on `sys.path` — `python -m` in the first, `-t` in the
second. Drop the `-t` and discovery still finds the test files and then fails to import the module
they test, which is exactly the kind of thing that works one way and not the other. CI runs both.

78 tests, no fixtures to set up; they build their own directories under `tempfile` and clean up
after themselves, so the suite never touches your real baseline. Some of them are about
`tools/check_test_count.py` rather than about `fic.py`: the guard that keeps this very number
honest had nothing checking *it*, which is how a fix for its network handling came to be written
twice and to land once. How many of them those are is deliberately not written here: it would be
a second count, in a sentence the guard above checks only for the first, which is the problem
this paragraph is about.

The `status` ones were added the same way and for the same reason. That command had no tests at all,
and CI only ever ran it immediately after `init` — on a tree that was healthy, under `set -e`, where a
correct `0` and an unconditional `0` look identical. Each one now asserts the exit code against the
lines printed beside it, because a status report whose text and exit code disagree is the defect.

**What CI covers.** Both commands run on every push to `main` and every pull request, on Linux,
macOS and Windows, on Python 3.8 through 3.14 — the two badges at the top of this file are claims, and this is what checks them.
CI also runs the quickstart and the three commands end to end through a shell, because the tests
`import fic` and call it in-process: they cannot catch a `python fic.py` that no longer starts, a
path that resolves against the wrong directory, or a wrong exit code. Those three are asserted
separately, since they are the documented interface. Nothing is installed in any of those jobs,
which is how the standard-library-only claim is tested rather than just stated.

A third job checks the suite's size wherever it is quoted: the sentence above, and this
repository's GitHub description. Both are claims about the suite that adding a single test
falsifies — and the description is a copy no commit can touch, so no diff and no review was ever
going to catch it drifting. `tools/check_test_count.py` compares both to what discovery actually
finds. It runs on `python:3.8`, the floor the badge claims, so the script's own claim to work there
is proven rather than stated.

This paragraph quoted the number too, in its first version, and that is why the check reads *every*
figure in this file rather than the first one. Explaining a guard beside the thing it guards is how
you end up with a second copy four lines below the copy it corrects.

---

## 📁 Project Structure

```text
file-integrity-checker/
│
├──  .github/             # CI workflow and the shared check set two of its three jobs run
├──  .gitignore           # Covers baseline.json, baseline.sha256, logs/, __pycache__/
├──  config.json          # Default configuration file
├──  fic.py               # Main CLI tool & core scanner engine
├──  requirements.txt     # Standard library only — nothing to install
├──  README.md            # Project documentation
├──  LICENSE              # MIT
│
├──  target_folder/       # Sample tree the default config monitors, so a fresh clone works
├──  tests/               # Unit testing modules
└──  tools/               # Checks the test count quoted here and in the repo description
```

---

## ⚠️ Limitations

- **Polling-Based Monitor**: FIC performs point-in-time checks when executed rather than real-time OS event listening (`inotify`/`watchdog`).
- **Content Focus**: Tracks SHA-256 hash changes in file contents. Metadata attributes (e.g., `chmod` permissions, timestamps) are not recorded, so a permission change alone is invisible to FIC.
- **Unkeyed Baseline Digest**: The `.sha256` sidecar detects corruption and careless edits, not a determined attacker — see [Security Considerations](#-security-considerations).

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
