# 🛡️ File Integrity Checker (FIC)

> **Lightweight, cryptographically secure file monitoring for Python.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Security: SHA-256](https://img.shields.io/badge/Security-SHA--256-green.svg)](https://en.wikipedia.org/wiki/SHA-2)
[![Platform: Cross--Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](#)

---

## 📌 Overview

**File Integrity Checker (FIC)** is a CLI security utility designed to safeguard critical files from unauthorized tampering, silent corruption, and unmonitored updates [cite: 1]. 

By creating a cryptographic snapshot (baseline) of your target directory using **SHA-256 digests**, FIC lets you detect file modifications, additions, and deletions instantly [cite: 1].

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
| **🔒 Cryptographic Precision** | Employs collision-resistant **SHA-256** hashing for absolute data verification [cite: 1]. |
| **🛡️ Self-Protecting Baseline** | Generates a standalone `.sha256` signature to detect local baseline tampering. |
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
   - **`init`**: Writes `baseline.json` and locks it with a `<baseline>.sha256` digest.
   - **`check`**: Validates `baseline.json` health and flags `[MODIFIED]`, `[NEW]`, `[DELETED]`, or `[SCAN ERROR]` files.

---

## 📋 Requirements

- **Python**: `3.8` or higher
- **Dependencies**: **Zero third-party libraries required!** Built entirely on standard library modules (`argparse`, `hashlib`, `json`, `logging`, `os`, `re`, `sys`, `time`, `pathlib`).

---

## 🚀 Quick Start & Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/file-integrity-checker.git
cd file-integrity-checker

# 2. Verify Python version
python3 --version
```

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

> ⚠️ **Security Rule**: Relative paths only for `exclusions`. Absolute paths and parent traversal patterns (`..`) are strictly prohibited and rejected during config parsing.

---

## 💻 Usage

FIC features three straightforward commands:

### 1. Create a Baseline (`init`)
Creates a fresh snapshot of your monitored directory.

```bash
python fic.py init
```

*CLI Overrides:*
```bash
python fic.py init --folder ./target_folder --baseline ./baseline.json --exclude temp
```

---

### 2. Verify File Integrity (`check`)
Compares current files against your saved baseline.

```bash
python fic.py check
```

---

### 3. Inspect System Status (`status`)
Verifies health of monitored folders, baseline files, and signature digests.

```bash
python fic.py status
```

---

## Example Output

### Running `python fic.py check` (Changes Detected)

```text
Checking file integrity...

[UNCHANGED] config.py
[MODIFIED]  data/database.sqlite
[NEW]       temp_notes.txt
[DELETED]   old_config.json

Integrity Check Summary
-----------------------
Unchanged:   1
Modified:    1
New:         1
Deleted:     1
Scan errors: 0

Symbolic links skipped: 0
```

---

### Running `python fic.py status`

```text
File Integrity Checker Status
-----------------------------
Monitored folder: OK (target_folder)
Baseline: OK (baseline.json)
Baseline hash: OK (baseline.sha256)
Baseline files: 4
Exclusions: 2
  - temp
  - cache/logs
Baseline integrity: OK
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

- **Tamper-Proof Baselines**: FIC pairs `baseline.json` with a separate `.sha256` signature digest file. If a bad actor alters the baseline directly, execution immediately halts with an integrity error.
- **Traversal Defense**: All relative paths are normalized using standard POSIX forward slashes (`/`), preventing platform-specific path manipulation.
- **Safe Persistence**: Writes data to a temporary file (`.tmp`) before calling `os.replace` to protect against partial baseline writes during crashes or file locks.

---

## 🧪 Running Tests

To run the unit test suite:

```bash
python -m unittest discover -s tests
```

---

## 📁 Project Structure

```text
file-integrity-checker/
│
├──  config.json          # Default configuration file
├──  fic.py               # Main CLI tool & core scanner engine
├──  README.md            # Project documentation
│
└──  tests/               # Unit testing modules
```

---

## ⚠️ Limitations

- **Polling-Based Monitor**: FIC performs point-in-time checks when executed rather than real-time OS event listening (`inotify`/`watchdog`).
- **Content Focus**: Tracks SHA-256 hash changes in file contents [cite: 1]. Metadata attributes (e.g., `chmod` permissions, timestamps) are not recorded.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
