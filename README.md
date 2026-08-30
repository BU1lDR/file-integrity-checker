# 🛡️ File Integrity Checker (FIC)

> A lightweight, robust, and secure Python-based **File Integrity Monitoring (FIM)** utility designed to detect unauthorized file changes, deletions, and additions using **SHA-256 cryptographic hashing**.

---

## 🌟 Key Features

* **🔒 Cryptographic Integrity**: Computes unique SHA-256 checksums for every monitored file.
* **🛡️ Self-Defending Baseline**: Generates a `.sha256` sidecar file to detect unauthorized tampering with the baseline manifest itself.
* **⚡ Atomic File Operations**: Prevents corruption during baseline writes using safe temporary files and flush/fsync routines.
* **🚫 Flexible Exclusion Rules**: Supports directory and file exclusions with path-traversal (`..`) and absolute path safety validation.
* **📂 Symlink & Error Resilience**: Automatically bypasses symbolic links to avoid infinite recursion loops and safely reports unreadable files.
* **📊 Visual Console & File Logging**: Outputs clear status indicators (`[UNCHANGED]`, `[MODIFIED]`, `[NEW]`, `[DELETED]`) and maintains log records.

---

## 🧠 Core Concepts & Architecture

```
   ┌──────────────────┐
   │ Monitored Folder │
   └─────────┬────────┘
             │
             ▼
    [SHA-256 Hashing] ───►  Atomic Baseline Write (.tmp ──► .json)
             │                          │
             ▼                          ▼
    [Integrity Check] ◄─── Compare ─── [Self-Verification (.sha256)]
```

### 1. SHA-256 Cryptographic Hashing
Every file inside the monitored directory is read in binary chunks (`4096 bytes`) to generate a unique 64-character hexadecimal digest. If even a single byte inside a file changes, its resulting hash will completely change.

### 2. Self-Verifying Baseline Security
To prevent attackers from modifying the `baseline.json` file to mask unauthorized changes, FIC generates a secondary signature file (`baseline.json.sha256`). Prior to every integrity scan, FIC verifies that the baseline file matches its stored hash.

### 3. Atomic Replacement
To guarantee zero corruption during write operations (e.g., power failure or process interruption), baselines are written to a temporary `.tmp` file, flushed to disk (`fsync`), and atomically swapped using `os.replace()`.

### 4. Path Normalization & Security Rules
All monitored paths are converted into Unix-style relative paths (`/`). FIC enforces security constraints by blocking absolute paths and parent directory traversal attempts (`..`).

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.8+** (Standard Library only; no external package dependencies required)

### Configuration (`config.json`)
Create a `config.json` file in the root directory:

```json
{
  "monitored_folder": "./data",
  "baseline_path": "./baseline.json",
  "log_path": "./logs/fic.log",
  "exclusions": [
    ".git",
    "logs",
    "temp.txt"
  ]
}
```

---

## 💻 Usage & Commands

### 1. Initialize Baseline (`init`)
Scans the monitored directory and creates a new cryptographic baseline manifest.

```bash
python fic.py init
```
*Custom Overrides:*
```bash
python fic.py init --folder ./my_folder --baseline ./my_baseline.json --exclude cache --exclude logs
```

### 2. Run Integrity Check (`check`)
Compares current files against the stored baseline and reports modifications or drift.

```bash
python fic.py check
```

**Sample Output:**
```text
Checking file integrity...

[UNCHANGED] document.pdf
[MODIFIED]  config/settings.env
[NEW]       malicious_script.sh
[DELETED]   important_data.csv

Integrity Check Summary
-----------------------
Unchanged:   1
Modified:    1
New:         1
Deleted:     1
Scan errors: 0
```

### 3. Check System Status (`status`)
Displays the status of the monitored folder, baseline manifest, sidecar hash integrity, and loaded exclusions.

```bash
python fic.py status
```

---

## 🚦 Exit Codes

| Exit Code | Constant | Meaning |
| :---: | :--- | :--- |
| **`0`** | `EXIT_SUCCESS` | Integrity verified / Command executed successfully. |
| **`1`** | `EXIT_INTEGRITY_FAILURE` | File modification, addition, or deletion detected. |
| **`2`** | `EXIT_ERROR` | System error, missing folder, or baseline verification failure. |