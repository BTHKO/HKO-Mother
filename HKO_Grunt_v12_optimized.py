# ==============================================================
#   HKO GRUNT v12 — Desktop Maintenance Agent (Optimized Edition)
#   Fully optimized, thread-safe, production-ready
#   New features: Progress tracking, cancellation, duplicate management,
#   file organization, AI prep, robust error handling
# ==============================================================

import os
import sys
import json
import hashlib
import shutil
import threading
import queue
import time
import mimetypes
from pathlib import Path
from datetime import datetime
from tkinter import *
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import List, Tuple, Dict, Optional

# --------------------------------------------------------------
# SAFE PATH HANDLING (works in EXE + Python)
# --------------------------------------------------------------

HOME = Path(os.path.expanduser("~"))
DESKTOP = HOME / "Desktop"

# HKO METAVERSE root (auto-created)
METAVERSE = DESKTOP / "HKO_METAVERSE"
METAVERSE.mkdir(exist_ok=True)

LOGS_PATH = METAVERSE / "LOGS"
LOGS_PATH.mkdir(exist_ok=True)

LIBRARY = METAVERSE / "METAVERSE_LIBRARY"
LIBRARY.mkdir(exist_ok=True)

CODE_REPO = LIBRARY / "Code_Repository"
CODE_REPO.mkdir(exist_ok=True)

ORGANIZED = METAVERSE / "ORGANIZED"
ORGANIZED.mkdir(exist_ok=True)

QUARANTINE = METAVERSE / "QUARANTINE"
QUARANTINE.mkdir(exist_ok=True)

CONFIG_PATH = LIBRARY / "grunt_config.json"

# --------------------------------------------------------------
# CONFIG LOADING
# --------------------------------------------------------------

DEFAULT_CONFIG = {
    "quarantine": str(QUARANTINE),
    "scan_mode": "both",
    "hash_algorithm": "sha256",
    "min_file_size_kb": 10,
    "code_extensions": [".py", ".html", ".js", ".json", ".txt", ".css", ".md", ".java", ".cpp", ".c", ".h", ".sh", ".bat"]
}

def load_config() -> Dict:
    """Load configuration with error handling"""
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            # Merge with defaults for any missing keys
            return {**DEFAULT_CONFIG, **config}
        except Exception as e:
            print(f"Config load error: {e}, using defaults")
            return DEFAULT_CONFIG.copy()
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict):
    """Save configuration with error handling"""
    try:
        CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Config save error: {e}")

CONFIG = load_config()

# --------------------------------------------------------------
# LOGGING UTIL (Optimized with append mode)
# --------------------------------------------------------------

class Logger:
    """Thread-safe logger with rotation support"""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)
        self.lock = threading.Lock()

    def log(self, msg: str, level: str = "INFO"):
        """Write log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {msg}\n"

        with self.lock:
            try:
                logfile = self.log_dir / "grunt_log.txt"
                # Append mode - much more efficient
                with open(logfile, "a", encoding="utf-8") as f:
                    f.write(log_entry)
                print(log_entry.strip())
            except Exception as e:
                print(f"Logging error: {e}")

    def rotate_if_needed(self, max_size_mb: int = 10):
        """Rotate log file if it exceeds size limit"""
        try:
            logfile = self.log_dir / "grunt_log.txt"
            if logfile.exists() and logfile.stat().st_size > max_size_mb * 1024 * 1024:
                backup = self.log_dir / f"grunt_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                shutil.move(str(logfile), str(backup))
                self.log("Log rotated", "SYSTEM")
        except Exception as e:
            print(f"Log rotation error: {e}")

logger = Logger(LOGS_PATH)

# --------------------------------------------------------------
# CANCELLATION SUPPORT
# --------------------------------------------------------------

class CancellationToken:
    """Allow long-running operations to be cancelled"""

    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def is_cancelled(self) -> bool:
        return self.cancelled

# --------------------------------------------------------------
# FILE HASHING (Optimized with SHA256)
# --------------------------------------------------------------

def file_hash(path: Path, algorithm: str = "sha256") -> Optional[str]:
    """
    Calculate file hash with specified algorithm.
    Returns None on error.
    """
    try:
        if algorithm == "sha256":
            h = hashlib.sha256()
        elif algorithm == "md5":
            h = hashlib.md5()
        else:
            h = hashlib.sha256()

        with open(path, "rb") as f:
            # Read in 64KB chunks for better performance
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except (IOError, OSError) as e:
        logger.log(f"Hash error for {path}: {e}", "ERROR")
        return None

# --------------------------------------------------------------
# DUPLICATE LOGIC (Optimized with size pre-filtering)
# --------------------------------------------------------------

def find_duplicates(
    root_paths: List[Path],
    token: CancellationToken,
    progress_callback=None,
    min_size_kb: int = 10
) -> List[Tuple[Path, Path]]:
    """
    Find duplicate files with size pre-filtering.
    Only hashes files larger than min_size_kb.
    """
    size_groups = {}  # Group files by size first
    total_files = 0
    processed_files = 0

    # First pass: Group by size
    logger.log(f"Scanning for files (min size: {min_size_kb}KB)...")
    for root in root_paths:
        if token.is_cancelled():
            return []

        root = Path(root)
        if not root.exists():
            continue

        try:
            for file in root.rglob("*"):
                if token.is_cancelled():
                    return []

                if file.is_file():
                    try:
                        size = file.stat().st_size
                        # Only consider files larger than min_size_kb
                        if size >= min_size_kb * 1024:
                            if size not in size_groups:
                                size_groups[size] = []
                            size_groups[size].append(file)
                            total_files += 1
                    except (OSError, IOError):
                        continue
        except (PermissionError, OSError) as e:
            logger.log(f"Access error for {root}: {e}", "WARNING")
            continue

    # Second pass: Hash only files with same size
    logger.log(f"Found {total_files} files, checking for duplicates...")
    seen = {}
    duplicates = []

    for size, files in size_groups.items():
        if token.is_cancelled():
            return []

        # Only hash if there are multiple files of the same size
        if len(files) > 1:
            for file in files:
                if token.is_cancelled():
                    return []

                h = file_hash(file, CONFIG["hash_algorithm"])
                processed_files += 1

                if progress_callback:
                    progress_callback(processed_files, total_files)

                if h:
                    if h in seen:
                        duplicates.append((file, seen[h]))
                    else:
                        seen[h] = file

    logger.log(f"Found {len(duplicates)} duplicate pairs")
    return duplicates

# --------------------------------------------------------------
# FILE ORGANIZATION LOGIC
# --------------------------------------------------------------

FILE_CATEGORIES = {
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xlsx", ".xls", ".pptx", ".ppt"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico", ".webp"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".h", ".sh", ".bat", ".json", ".xml"],
    "Executables": [".exe", ".dll", ".so", ".app", ".msi"],
}

def categorize_file(file: Path) -> str:
    """Determine file category based on extension"""
    ext = file.suffix.lower()

    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category

    return "Other"

def organize_files(
    folders: List[Path],
    token: CancellationToken,
    progress_callback=None,
    move: bool = False
) -> Dict[str, int]:
    """
    Organize files into categories.
    Returns dict with category counts.
    """
    stats = {cat: 0 for cat in FILE_CATEGORIES.keys()}
    stats["Other"] = 0
    total_files = 0
    processed = 0

    # Count total files
    for folder in folders:
        folder = Path(folder)
        if folder.exists():
            total_files += sum(1 for _ in folder.rglob("*") if _.is_file())

    logger.log(f"Organizing {total_files} files...")

    for folder in folders:
        if token.is_cancelled():
            return stats

        folder = Path(folder)
        if not folder.exists():
            continue

        try:
            for file in folder.rglob("*"):
                if token.is_cancelled():
                    return stats

                if file.is_file():
                    try:
                        category = categorize_file(file)
                        target_dir = ORGANIZED / category
                        target_dir.mkdir(exist_ok=True)

                        # Handle name conflicts
                        target_file = target_dir / file.name
                        counter = 1
                        while target_file.exists():
                            stem = file.stem
                            suffix = file.suffix
                            target_file = target_dir / f"{stem}_{counter}{suffix}"
                            counter += 1

                        # Move or copy
                        if move:
                            shutil.move(str(file), str(target_file))
                        else:
                            shutil.copy2(str(file), str(target_file))

                        stats[category] += 1
                        processed += 1

                        if progress_callback:
                            progress_callback(processed, total_files)

                    except (OSError, IOError) as e:
                        logger.log(f"Error organizing {file}: {e}", "ERROR")
                        continue
        except (PermissionError, OSError) as e:
            logger.log(f"Access error for {folder}: {e}", "WARNING")
            continue

    logger.log(f"Organization complete: {stats}")
    return stats

# --------------------------------------------------------------
# CODE EXTRACTION LOGIC (Optimized with conflict resolution)
# --------------------------------------------------------------

def extract_code_from_folder(
    folder: Path,
    token: CancellationToken,
    progress_callback=None
) -> List[str]:
    """
    Extract code files with conflict resolution.
    Creates subdirectories to preserve structure.
    """
    folder = Path(folder)
    extracted = []
    files_found = []

    # Collect all code files
    code_extensions = CONFIG.get("code_extensions", DEFAULT_CONFIG["code_extensions"])
    for file in folder.rglob("*"):
        if file.suffix.lower() in code_extensions:
            files_found.append(file)

    total = len(files_found)
    logger.log(f"Extracting {total} code files...")

    for idx, file in enumerate(files_found):
        if token.is_cancelled():
            return extracted

        try:
            # Preserve directory structure
            rel_path = file.relative_to(folder)
            target = CODE_REPO / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)

            # Handle conflicts
            if target.exists():
                stem = target.stem
                suffix = target.suffix
                counter = 1
                while target.exists():
                    target = target.parent / f"{stem}_{counter}{suffix}"
                    counter += 1

            shutil.copy2(str(file), str(target))
            extracted.append(str(rel_path))

            if progress_callback:
                progress_callback(idx + 1, total)

        except (OSError, IOError) as e:
            logger.log(f"Error extracting {file}: {e}", "ERROR")
            continue

    logger.log(f"Extracted {len(extracted)} code files")
    return extracted

# --------------------------------------------------------------
# AI PREP LOGIC
# --------------------------------------------------------------

def prepare_for_ai(
    folder: Path,
    token: CancellationToken,
    progress_callback=None
) -> str:
    """
    Prepare codebase for AI analysis.
    Creates a consolidated file with all code.
    """
    folder = Path(folder)
    output = []
    files_found = []

    code_extensions = CONFIG.get("code_extensions", DEFAULT_CONFIG["code_extensions"])

    for file in folder.rglob("*"):
        if file.suffix.lower() in code_extensions:
            files_found.append(file)

    total = len(files_found)
    logger.log(f"Preparing {total} files for AI...")

    for idx, file in enumerate(files_found):
        if token.is_cancelled():
            return ""

        try:
            rel_path = file.relative_to(folder)
            output.append(f"\n{'='*60}\n")
            output.append(f"File: {rel_path}\n")
            output.append(f"{'='*60}\n\n")

            content = file.read_text(encoding="utf-8", errors="ignore")
            output.append(content)
            output.append("\n")

            if progress_callback:
                progress_callback(idx + 1, total)

        except Exception as e:
            logger.log(f"Error reading {file}: {e}", "ERROR")
            continue

    result = "".join(output)

    # Save to file
    ai_output = LIBRARY / f"AI_PREP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        ai_output.write_text(result, encoding="utf-8")
        logger.log(f"AI prep saved to {ai_output}")
    except Exception as e:
        logger.log(f"Error saving AI prep: {e}", "ERROR")

    return result

# --------------------------------------------------------------
# TKINTER UI (Thread-safe with queue)
# --------------------------------------------------------------

class GruntApp(Tk):
    def __init__(self):
        super().__init__()
        self.title("HKO Grunt v12 — Desktop Maintenance Agent (Optimized)")
        self.geometry("1400x800")

        # Thread-safe queue for UI updates
        self.ui_queue = queue.Queue()

        # Active cancellation tokens
        self.active_tokens = []

        self.build_ui()
        self.process_ui_queue()

    def process_ui_queue(self):
        """Process UI updates from background threads"""
        try:
            while True:
                callback = self.ui_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_ui_queue)

    def queue_ui_update(self, callback):
        """Schedule a UI update from a background thread"""
        self.ui_queue.put(callback)

    # ----------------------------------------------------------
    def build_ui(self):
        # Menu bar
        menubar = Menu(self)
        self.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Rotate Logs", command=self.rotate_logs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        # Tabs
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab_org = Frame(self.tabs)
        self.tab_dup = Frame(self.tabs)
        self.tab_code = Frame(self.tabs)
        self.tab_ai = Frame(self.tabs)
        self.tab_settings = Frame(self.tabs)

        self.tabs.add(self.tab_org, text="📁 Organize")
        self.tabs.add(self.tab_dup, text="🔍 Duplicates")
        self.tabs.add(self.tab_code, text="💻 Code Catalog")
        self.tabs.add(self.tab_ai, text="🤖 AI Prep")
        self.tabs.add(self.tab_settings, text="⚙️ Settings")

        self.build_org_tab()
        self.build_dup_tab()
        self.build_code_tab()
        self.build_ai_tab()
        self.build_settings_tab()

    # ----------------------------------------------------------
    # ORGANIZE TAB
    # ----------------------------------------------------------
    def build_org_tab(self):
        # Top frame
        top_frame = Frame(self.tab_org)
        top_frame.pack(fill="x", padx=10, pady=10)

        Label(top_frame, text="📂 Folder Selection:", font=("Arial", 11, "bold")).pack(anchor="w")

        btn_frame = Frame(top_frame)
        btn_frame.pack(anchor="w", pady=5)

        Button(btn_frame, text="Add Folder", command=self.select_org_folders).pack(side=LEFT, padx=2)
        Button(btn_frame, text="Clear List", command=lambda: self.org_list.delete(0, END)).pack(side=LEFT, padx=2)

        # List frame
        list_frame = Frame(self.tab_org)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scroll = Scrollbar(list_frame)
        scroll.pack(side=RIGHT, fill=Y)

        self.org_list = Listbox(list_frame, height=10, yscrollcommand=scroll.set)
        self.org_list.pack(side=LEFT, fill="both", expand=True)
        scroll.config(command=self.org_list.yview)

        # Options frame
        opt_frame = Frame(self.tab_org)
        opt_frame.pack(fill="x", padx=10, pady=5)

        self.org_move_var = BooleanVar(value=False)
        Checkbutton(opt_frame, text="Move files (instead of copy)", variable=self.org_move_var).pack(anchor="w")

        # Progress frame
        prog_frame = Frame(self.tab_org)
        prog_frame.pack(fill="x", padx=10, pady=5)

        self.org_progress = ttk.Progressbar(prog_frame, mode='determinate')
        self.org_progress.pack(fill="x")

        self.org_status = Label(prog_frame, text="Ready", anchor="w")
        self.org_status.pack(fill="x")

        # Action frame
        action_frame = Frame(self.tab_org)
        action_frame.pack(fill="x", padx=10, pady=10)

        self.org_run_btn = Button(action_frame, text="🚀 Run Organization", command=self.run_organize_threaded,
                                   bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.org_run_btn.pack(side=LEFT, padx=5)

        self.org_cancel_btn = Button(action_frame, text="❌ Cancel", command=self.cancel_org, state=DISABLED)
        self.org_cancel_btn.pack(side=LEFT, padx=5)

    def select_org_folders(self):
        folder = filedialog.askdirectory()
        if folder:
            self.org_list.insert(END, folder)

    def run_organize_threaded(self):
        folders = list(self.org_list.get(0, END))
        if not folders:
            messagebox.showerror("Error", "No folders selected.")
            return

        self.org_run_btn.config(state=DISABLED)
        self.org_cancel_btn.config(state=NORMAL)
        self.org_progress['value'] = 0

        token = CancellationToken()
        self.active_tokens.append(token)

        def progress_callback(current, total):
            def update():
                if total > 0:
                    self.org_progress['value'] = (current / total) * 100
                    self.org_status.config(text=f"Processing: {current}/{total}")
            self.queue_ui_update(update)

        def task():
            try:
                stats = organize_files(folders, token, progress_callback, self.org_move_var.get())

                def done():
                    self.org_run_btn.config(state=NORMAL)
                    self.org_cancel_btn.config(state=DISABLED)
                    self.org_progress['value'] = 100
                    self.org_status.config(text="Complete!")

                    if token.is_cancelled():
                        messagebox.showinfo("Cancelled", "Organization cancelled by user.")
                    else:
                        msg = "Organization complete!\n\n"
                        for cat, count in stats.items():
                            if count > 0:
                                msg += f"{cat}: {count} files\n"
                        messagebox.showinfo("Done", msg)

                    self.active_tokens.remove(token)

                self.queue_ui_update(done)

            except Exception as e:
                logger.log(f"Organization error: {e}", "ERROR")
                def error():
                    self.org_run_btn.config(state=NORMAL)
                    self.org_cancel_btn.config(state=DISABLED)
                    messagebox.showerror("Error", f"Organization failed: {e}")
                    if token in self.active_tokens:
                        self.active_tokens.remove(token)
                self.queue_ui_update(error)

        threading.Thread(target=task, daemon=True).start()

    def cancel_org(self):
        if self.active_tokens:
            self.active_tokens[-1].cancel()

    # ----------------------------------------------------------
    # DUPLICATES TAB
    # ----------------------------------------------------------
    def build_dup_tab(self):
        # Top frame
        top_frame = Frame(self.tab_dup)
        top_frame.pack(fill="x", padx=10, pady=10)

        Label(top_frame, text="🔍 Duplicate File Scanner", font=("Arial", 11, "bold")).pack(anchor="w")

        # Options
        opt_frame = Frame(top_frame)
        opt_frame.pack(fill="x", pady=5)

        Label(opt_frame, text="Min file size (KB):").pack(side=LEFT)
        self.dup_min_size = Spinbox(opt_frame, from_=1, to=10000, width=10)
        self.dup_min_size.delete(0, END)
        self.dup_min_size.insert(0, str(CONFIG.get("min_file_size_kb", 10)))
        self.dup_min_size.pack(side=LEFT, padx=5)

        # Progress
        prog_frame = Frame(top_frame)
        prog_frame.pack(fill="x", pady=5)

        self.dup_progress = ttk.Progressbar(prog_frame, mode='determinate')
        self.dup_progress.pack(fill="x")

        self.dup_status = Label(prog_frame, text="Ready", anchor="w")
        self.dup_status.pack(fill="x")

        # Actions
        btn_frame = Frame(top_frame)
        btn_frame.pack(fill="x", pady=5)

        self.dup_scan_btn = Button(btn_frame, text="🚀 Scan for Duplicates", command=self.run_dup_scan,
                                    bg="#2196F3", fg="white", font=("Arial", 10, "bold"))
        self.dup_scan_btn.pack(side=LEFT, padx=5)

        self.dup_cancel_btn = Button(btn_frame, text="❌ Cancel", command=self.cancel_dup, state=DISABLED)
        self.dup_cancel_btn.pack(side=LEFT, padx=5)

        Button(btn_frame, text="🗑️ Delete Selected", command=self.delete_duplicates).pack(side=LEFT, padx=5)

        # List frame
        list_frame = Frame(self.tab_dup)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scroll = Scrollbar(list_frame)
        scroll.pack(side=RIGHT, fill=Y)

        self.dup_list = Listbox(list_frame, yscrollcommand=scroll.set, selectmode=MULTIPLE)
        self.dup_list.pack(side=LEFT, fill="both", expand=True)
        scroll.config(command=self.dup_list.yview)

        # Store duplicate data
        self.duplicate_data = []

    def run_dup_scan(self):
        self.dup_scan_btn.config(state=DISABLED)
        self.dup_cancel_btn.config(state=NORMAL)
        self.dup_progress['value'] = 0
        self.dup_list.delete(0, END)
        self.duplicate_data = []

        token = CancellationToken()
        self.active_tokens.append(token)

        min_size = int(self.dup_min_size.get())

        def progress_callback(current, total):
            def update():
                if total > 0:
                    self.dup_progress['value'] = (current / total) * 100
                    self.dup_status.config(text=f"Hashing: {current}/{total}")
            self.queue_ui_update(update)

        def task():
            try:
                roots = [DESKTOP, HOME / "Downloads"]
                dups = find_duplicates(roots, token, progress_callback, min_size)

                def done():
                    self.duplicate_data = dups
                    self.dup_list.delete(0, END)

                    for f1, f2 in dups:
                        size = f1.stat().st_size if f1.exists() else 0
                        size_mb = size / (1024 * 1024)
                        self.dup_list.insert(END, f"[{size_mb:.2f} MB] {f1.name}")
                        self.dup_list.insert(END, f"         → {f1}")
                        self.dup_list.insert(END, f"         → {f2}")
                        self.dup_list.insert(END, "")

                    self.dup_scan_btn.config(state=NORMAL)
                    self.dup_cancel_btn.config(state=DISABLED)
                    self.dup_progress['value'] = 100
                    self.dup_status.config(text=f"Found {len(dups)} duplicate pairs")

                    if token.is_cancelled():
                        messagebox.showinfo("Cancelled", "Scan cancelled by user.")
                    else:
                        messagebox.showinfo("Done", f"Found {len(dups)} duplicate file pairs.")

                    self.active_tokens.remove(token)

                self.queue_ui_update(done)

            except Exception as e:
                logger.log(f"Duplicate scan error: {e}", "ERROR")
                def error():
                    self.dup_scan_btn.config(state=NORMAL)
                    self.dup_cancel_btn.config(state=DISABLED)
                    messagebox.showerror("Error", f"Scan failed: {e}")
                    if token in self.active_tokens:
                        self.active_tokens.remove(token)
                self.queue_ui_update(error)

        threading.Thread(target=task, daemon=True).start()

    def cancel_dup(self):
        if self.active_tokens:
            self.active_tokens[-1].cancel()

    def delete_duplicates(self):
        if not self.duplicate_data:
            messagebox.showinfo("Info", "No duplicates found yet. Run a scan first.")
            return

        result = messagebox.askyesno("Confirm Delete",
                                     f"Delete {len(self.duplicate_data)} duplicate files?\n"
                                     "(Keeps first occurrence, deletes second)")
        if result:
            deleted = 0
            for f1, f2 in self.duplicate_data:
                try:
                    # Delete the second file (keep first)
                    if f2.exists():
                        f2.unlink()
                        deleted += 1
                        logger.log(f"Deleted duplicate: {f2}")
                except Exception as e:
                    logger.log(f"Error deleting {f2}: {e}", "ERROR")

            messagebox.showinfo("Complete", f"Deleted {deleted} duplicate files.")
            self.run_dup_scan()  # Re-scan

    # ----------------------------------------------------------
    # CODE CATALOG TAB
    # ----------------------------------------------------------
    def build_code_tab(self):
        # Top frame
        top_frame = Frame(self.tab_code)
        top_frame.pack(fill="x", padx=10, pady=10)

        Label(top_frame, text="💻 Code File Extractor", font=("Arial", 11, "bold")).pack(anchor="w")

        # Progress
        prog_frame = Frame(top_frame)
        prog_frame.pack(fill="x", pady=5)

        self.code_progress = ttk.Progressbar(prog_frame, mode='determinate')
        self.code_progress.pack(fill="x")

        self.code_status = Label(prog_frame, text="Ready", anchor="w")
        self.code_status.pack(fill="x")

        # Actions
        btn_frame = Frame(top_frame)
        btn_frame.pack(fill="x", pady=5)

        self.code_extract_btn = Button(btn_frame, text="📂 Select Folder & Extract", command=self.run_code_extract,
                                        bg="#9C27B0", fg="white", font=("Arial", 10, "bold"))
        self.code_extract_btn.pack(side=LEFT, padx=5)

        self.code_cancel_btn = Button(btn_frame, text="❌ Cancel", command=self.cancel_code, state=DISABLED)
        self.code_cancel_btn.pack(side=LEFT, padx=5)

        Button(btn_frame, text="📁 Open Repository", command=lambda: os.startfile(CODE_REPO) if os.name == 'nt' else os.system(f'xdg-open "{CODE_REPO}"')).pack(side=LEFT, padx=5)

        # List frame
        list_frame = Frame(self.tab_code)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scroll = Scrollbar(list_frame)
        scroll.pack(side=RIGHT, fill=Y)

        self.code_list = Listbox(list_frame, yscrollcommand=scroll.set)
        self.code_list.pack(side=LEFT, fill="both", expand=True)
        scroll.config(command=self.code_list.yview)

    def run_code_extract(self):
        folder = filedialog.askdirectory(title="Select folder to extract code from")
        if not folder:
            return

        self.code_extract_btn.config(state=DISABLED)
        self.code_cancel_btn.config(state=NORMAL)
        self.code_progress['value'] = 0
        self.code_list.delete(0, END)

        token = CancellationToken()
        self.active_tokens.append(token)

        def progress_callback(current, total):
            def update():
                if total > 0:
                    self.code_progress['value'] = (current / total) * 100
                    self.code_status.config(text=f"Extracting: {current}/{total}")
            self.queue_ui_update(update)

        def task():
            try:
                extracted = extract_code_from_folder(Path(folder), token, progress_callback)

                def done():
                    self.code_list.delete(0, END)
                    for e in extracted:
                        self.code_list.insert(END, e)

                    self.code_extract_btn.config(state=NORMAL)
                    self.code_cancel_btn.config(state=DISABLED)
                    self.code_progress['value'] = 100
                    self.code_status.config(text=f"Extracted {len(extracted)} files")

                    if token.is_cancelled():
                        messagebox.showinfo("Cancelled", "Extraction cancelled by user.")
                    else:
                        messagebox.showinfo("Done", f"Extracted {len(extracted)} code files to:\n{CODE_REPO}")

                    self.active_tokens.remove(token)

                self.queue_ui_update(done)

            except Exception as e:
                logger.log(f"Code extraction error: {e}", "ERROR")
                def error():
                    self.code_extract_btn.config(state=NORMAL)
                    self.code_cancel_btn.config(state=DISABLED)
                    messagebox.showerror("Error", f"Extraction failed: {e}")
                    if token in self.active_tokens:
                        self.active_tokens.remove(token)
                self.queue_ui_update(error)

        threading.Thread(target=task, daemon=True).start()

    def cancel_code(self):
        if self.active_tokens:
            self.active_tokens[-1].cancel()

    # ----------------------------------------------------------
    # AI PREP TAB
    # ----------------------------------------------------------
    def build_ai_tab(self):
        # Top frame
        top_frame = Frame(self.tab_ai)
        top_frame.pack(fill="x", padx=10, pady=10)

        Label(top_frame, text="🤖 AI Codebase Preparation", font=("Arial", 11, "bold")).pack(anchor="w")
        Label(top_frame, text="Consolidate all code files into a single document for AI analysis.",
              font=("Arial", 9)).pack(anchor="w", pady=5)

        # Progress
        prog_frame = Frame(top_frame)
        prog_frame.pack(fill="x", pady=5)

        self.ai_progress = ttk.Progressbar(prog_frame, mode='determinate')
        self.ai_progress.pack(fill="x")

        self.ai_status = Label(prog_frame, text="Ready", anchor="w")
        self.ai_status.pack(fill="x")

        # Actions
        btn_frame = Frame(top_frame)
        btn_frame.pack(fill="x", pady=5)

        self.ai_prep_btn = Button(btn_frame, text="📂 Select Folder & Prepare", command=self.run_ai_prep,
                                   bg="#FF5722", fg="white", font=("Arial", 10, "bold"))
        self.ai_prep_btn.pack(side=LEFT, padx=5)

        self.ai_cancel_btn = Button(btn_frame, text="❌ Cancel", command=self.cancel_ai, state=DISABLED)
        self.ai_cancel_btn.pack(side=LEFT, padx=5)

        # Preview frame
        preview_frame = Frame(self.tab_ai)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)

        Label(preview_frame, text="Preview:", font=("Arial", 9, "bold")).pack(anchor="w")

        scroll = Scrollbar(preview_frame)
        scroll.pack(side=RIGHT, fill=Y)

        self.ai_preview = scrolledtext.ScrolledText(preview_frame, yscrollcommand=scroll.set,
                                                     wrap=WORD, height=20)
        self.ai_preview.pack(side=LEFT, fill="both", expand=True)
        scroll.config(command=self.ai_preview.yview)

    def run_ai_prep(self):
        folder = filedialog.askdirectory(title="Select codebase folder")
        if not folder:
            return

        self.ai_prep_btn.config(state=DISABLED)
        self.ai_cancel_btn.config(state=NORMAL)
        self.ai_progress['value'] = 0
        self.ai_preview.delete("1.0", END)

        token = CancellationToken()
        self.active_tokens.append(token)

        def progress_callback(current, total):
            def update():
                if total > 0:
                    self.ai_progress['value'] = (current / total) * 100
                    self.ai_status.config(text=f"Processing: {current}/{total}")
            self.queue_ui_update(update)

        def task():
            try:
                result = prepare_for_ai(Path(folder), token, progress_callback)

                def done():
                    # Show preview (first 10000 chars)
                    preview = result[:10000]
                    if len(result) > 10000:
                        preview += "\n\n... (truncated for preview)"

                    self.ai_preview.insert("1.0", preview)

                    self.ai_prep_btn.config(state=NORMAL)
                    self.ai_cancel_btn.config(state=DISABLED)
                    self.ai_progress['value'] = 100
                    self.ai_status.config(text=f"Complete! ({len(result)} chars)")

                    if token.is_cancelled():
                        messagebox.showinfo("Cancelled", "AI prep cancelled by user.")
                    else:
                        messagebox.showinfo("Done", f"AI preparation complete!\n\nOutput saved to:\n{LIBRARY}")

                    self.active_tokens.remove(token)

                self.queue_ui_update(done)

            except Exception as e:
                logger.log(f"AI prep error: {e}", "ERROR")
                def error():
                    self.ai_prep_btn.config(state=NORMAL)
                    self.ai_cancel_btn.config(state=DISABLED)
                    messagebox.showerror("Error", f"AI prep failed: {e}")
                    if token in self.active_tokens:
                        self.active_tokens.remove(token)
                self.queue_ui_update(error)

        threading.Thread(target=task, daemon=True).start()

    def cancel_ai(self):
        if self.active_tokens:
            self.active_tokens[-1].cancel()

    # ----------------------------------------------------------
    # SETTINGS TAB
    # ----------------------------------------------------------
    def build_settings_tab(self):
        # Scrollable frame
        canvas = Canvas(self.tab_settings)
        scroll = Scrollbar(self.tab_settings, orient=VERTICAL, command=canvas.yview)
        scrollable_frame = Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side=LEFT, fill="both", expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        # Settings content
        Label(scrollable_frame, text="⚙️ Configuration", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=10)

        # Quarantine folder
        Label(scrollable_frame, text="Quarantine Folder:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.q_var = StringVar(value=CONFIG.get("quarantine", str(QUARANTINE)))

        q_frame = Frame(scrollable_frame)
        q_frame.pack(fill="x", padx=10, pady=5)

        Entry(q_frame, textvariable=self.q_var, width=60).pack(side=LEFT, padx=5)
        Button(q_frame, text="Browse", command=self.pick_quarantine).pack(side=LEFT)

        # Hash algorithm
        Label(scrollable_frame, text="Hash Algorithm:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.hash_var = StringVar(value=CONFIG.get("hash_algorithm", "sha256"))

        hash_frame = Frame(scrollable_frame)
        hash_frame.pack(fill="x", padx=10, pady=5)

        Radiobutton(hash_frame, text="SHA256 (recommended)", variable=self.hash_var, value="sha256").pack(anchor="w")
        Radiobutton(hash_frame, text="MD5 (faster, less secure)", variable=self.hash_var, value="md5").pack(anchor="w")

        # Min file size
        Label(scrollable_frame, text="Minimum File Size for Duplicate Check (KB):", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.min_size_var = StringVar(value=str(CONFIG.get("min_file_size_kb", 10)))

        Entry(scrollable_frame, textvariable=self.min_size_var, width=20).pack(anchor="w", padx=10, pady=5)

        # Code extensions
        Label(scrollable_frame, text="Code File Extensions (comma-separated):", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        exts = CONFIG.get("code_extensions", DEFAULT_CONFIG["code_extensions"])
        self.code_ext_var = StringVar(value=", ".join(exts))

        Entry(scrollable_frame, textvariable=self.code_ext_var, width=80).pack(anchor="w", padx=10, pady=5)

        # Save button
        Button(scrollable_frame, text="💾 Save Settings", command=self.save_settings,
               bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=20)

        # Info section
        info_frame = LabelFrame(scrollable_frame, text="Paths", font=("Arial", 10, "bold"))
        info_frame.pack(fill="x", padx=10, pady=10)

        Label(info_frame, text=f"Library: {LIBRARY}", anchor="w").pack(fill="x", padx=5, pady=2)
        Label(info_frame, text=f"Code Repo: {CODE_REPO}", anchor="w").pack(fill="x", padx=5, pady=2)
        Label(info_frame, text=f"Organized: {ORGANIZED}", anchor="w").pack(fill="x", padx=5, pady=2)
        Label(info_frame, text=f"Logs: {LOGS_PATH}", anchor="w").pack(fill="x", padx=5, pady=2)

    def pick_quarantine(self):
        folder = filedialog.askdirectory()
        if folder:
            self.q_var.set(folder)

    def save_settings(self):
        try:
            CONFIG["quarantine"] = self.q_var.get()
            CONFIG["hash_algorithm"] = self.hash_var.get()
            CONFIG["min_file_size_kb"] = int(self.min_size_var.get())
            CONFIG["code_extensions"] = [ext.strip() for ext in self.code_ext_var.get().split(",")]

            save_config(CONFIG)
            messagebox.showinfo("Saved", "Settings saved successfully!")
            logger.log("Settings updated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            logger.log(f"Settings save error: {e}", "ERROR")

    def rotate_logs(self):
        logger.rotate_if_needed()
        messagebox.showinfo("Done", "Log rotation complete.")

# --------------------------------------------------------------
# RUN
# --------------------------------------------------------------

if __name__ == "__main__":
    logger.log("="*60)
    logger.log("HKO Grunt v12 Starting")
    logger.log("="*60)

    app = GruntApp()
    app.mainloop()

    logger.log("HKO Grunt v12 Shutdown")
