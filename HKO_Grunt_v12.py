# ==============================================================
#   HKO GRUNT v12 — Desktop Maintenance Agent (Ultimate Edition)
#   Enhanced with: Maximum UX toggles, authorized folder schema,
#   preview-before-organize, and advanced duplicate management
# ==============================================================

import os
import sys
import json
import hashlib
import shutil
import threading
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

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

CONFIG_PATH = LIBRARY / "grunt_config.json"
ENV_FILE = HOME / "HKO_Env" / "HKO_Sleutels.env"

# --------------------------------------------------------------
# AUTHORIZED FOLDER SCHEMA
# --------------------------------------------------------------

AUTHORIZED_FOLDERS = {
    "ESL": {
        "path": DESKTOP / "ESL",
        "subfolders": ["Clients", "General_Docs", "Resources"],
        "description": "English as Second Language projects"
    },
    "OUTPLACEMENT": {
        "path": DESKTOP / "OUTPLACEMENT",
        "subfolders": ["Clients", "General_Docs", "Resources"],
        "description": "Outplacement services and CV work"
    },
    "COACHING": {
        "path": DESKTOP / "COACHING",
        "subfolders": ["Clients", "Templates", "Resources"],
        "description": "Coaching sessions and materials"
    },
    "PERSONAL": {
        "path": DESKTOP / "PERSONAL",
        "subfolders": ["Docs", "Ideas", "Admin"],
        "description": "Personal documents and projects"
    },
    "HKO": {
        "path": DESKTOP / "HKO",
        "subfolders": ["Brand", "Pitch", "Assets", "Strategy", "General_Docs"],
        "description": "HKO brand and business materials"
    },
    "GOLDMINE": {
        "path": DESKTOP / "GOLDMINE",
        "subfolders": ["Archive", "Resources"],
        "description": "Valuable archived content"
    },
    "HKO_METAVERSE": {
        "path": METAVERSE,
        "subfolders": ["CORE_ENGINE", "MODULES", "METAVERSE_LIBRARY", "LOGS"],
        "description": "HKO system core and modules"
    }
}

# FILE TYPE CATEGORIES FOR ORGANIZATION
FILE_CATEGORIES = {
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"],
    "Spreadsheets": [".xls", ".xlsx", ".csv", ".ods"],
    "Presentations": [".ppt", ".pptx", ".odp"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "Code": [".py", ".js", ".html", ".css", ".json", ".xml", ".java", ".cpp", ".c"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Executables": [".exe", ".msi", ".bat", ".sh"],
    "Databases": [".db", ".sqlite", ".mdb", ".sql"]
}

# --------------------------------------------------------------
# CONFIG LOADING & SAVING
# --------------------------------------------------------------

DEFAULT_CONFIG = {
    "quarantine": str(DESKTOP / "QUARANTINE"),
    "scan_mode": "both",
    "auto_organize": False,
    "deep_scan": True,
    "enabled_categories": list(FILE_CATEGORIES.keys()),
    "delete_unauthorized_folders": False,
    "create_subfolders": True
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except:
            return DEFAULT_CONFIG.copy()
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")

CONFIG = load_config()

# --------------------------------------------------------------
# LOGGING UTIL
# --------------------------------------------------------------

def log(msg):
    LOGS_PATH.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logfile = LOGS_PATH / "grunt_log.txt"
    log_entry = f"[{timestamp}] {msg}\n"

    if logfile.exists():
        logfile.write_text(logfile.read_text(encoding="utf-8") + log_entry, encoding="utf-8")
    else:
        logfile.write_text(log_entry, encoding="utf-8")
    print(msg)

# --------------------------------------------------------------
# BACKGROUND THREAD DECORATOR
# --------------------------------------------------------------

def threaded(fn):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=fn, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
    return wrapper

# --------------------------------------------------------------
# FOLDER SCHEMA MANAGEMENT
# --------------------------------------------------------------

def create_authorized_schema():
    """Create all authorized folders and their subfolders"""
    created = []
    for name, info in AUTHORIZED_FOLDERS.items():
        path = info["path"]
        path.mkdir(exist_ok=True)
        created.append(str(path))

        if CONFIG.get("create_subfolders", True):
            for subfolder in info["subfolders"]:
                subpath = path / subfolder
                subpath.mkdir(exist_ok=True)
                created.append(str(subpath))

    return created

def find_unauthorized_folders():
    """Find folders on desktop that are not in authorized schema"""
    unauthorized = []
    authorized_names = {name for name in AUTHORIZED_FOLDERS.keys()}

    try:
        for item in DESKTOP.iterdir():
            if item.is_dir() and item.name not in authorized_names:
                # Skip system folders
                if not item.name.startswith('.'):
                    unauthorized.append(item)
    except Exception as e:
        log(f"Error scanning desktop: {e}")

    return unauthorized

# --------------------------------------------------------------
# FILE CLASSIFICATION
# --------------------------------------------------------------

def classify_file(file_path):
    """Determine which category and folder a file belongs to"""
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    # Find category
    category = None
    for cat_name, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            category = cat_name
            break

    if not category:
        category = "Other"

    # Suggest destination folder based on filename and category
    filename_lower = file_path.stem.lower()

    # Smart routing based on keywords
    if any(word in filename_lower for word in ["cv", "resume", "linkedin", "outplacement"]):
        return category, "OUTPLACEMENT", "Contains career/CV keywords"
    elif any(word in filename_lower for word in ["esl", "english", "lesson", "student"]):
        return category, "ESL", "Contains ESL/teaching keywords"
    elif any(word in filename_lower for word in ["coach", "session", "client"]):
        return category, "COACHING", "Contains coaching keywords"
    elif any(word in filename_lower for word in ["hko", "brand", "pitch"]):
        return category, "HKO", "Contains HKO brand keywords"
    elif category == "Code":
        return category, "HKO_METAVERSE", "Code file - belongs in METAVERSE"
    else:
        return category, "PERSONAL", "Default: personal documents"

# --------------------------------------------------------------
# DUPLICATE LOGIC (MD5 HASHING) - Enhanced
# --------------------------------------------------------------

def file_hash(path):
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
    except:
        return None
    return h.hexdigest()

def find_duplicates_enhanced(root_paths):
    """Find duplicates with enhanced metadata"""
    seen = {}
    duplicates = []

    for root in root_paths:
        root = Path(root)
        if not root.exists():
            continue

        for file in root.rglob("*.*"):
            if file.is_file():
                try:
                    h = file_hash(file)
                    if h:
                        size = file.stat().st_size
                        mtime = file.stat().st_mtime

                        if h in seen:
                            # Found duplicate
                            original = seen[h]
                            duplicates.append({
                                "hash": h,
                                "original": original,
                                "duplicate": file,
                                "size": size,
                                "original_mtime": original.stat().st_mtime,
                                "duplicate_mtime": mtime,
                                "reason": f"Identical content (MD5: {h[:8]}...)"
                            })
                        else:
                            seen[h] = file
                except Exception as e:
                    log(f"Error processing {file}: {e}")

    return duplicates

# --------------------------------------------------------------
# CODE EXTRACTION LOGIC
# --------------------------------------------------------------

CODE_EXT = [".py", ".html", ".js", ".json", ".txt", ".css", ".md", ".xml", ".java", ".cpp", ".c"]

def extract_code_from_folder(folder):
    folder = Path(folder)
    extracted = []
    for file in folder.rglob("*"):
        if file.suffix.lower() in CODE_EXT:
            try:
                target = CODE_REPO / file.name
                shutil.copy(file, target)
                extracted.append(file.name)
            except Exception as e:
                log(f"Error extracting {file.name}: {e}")
    return extracted

# --------------------------------------------------------------
# TKINTER UI - Enhanced with Maximum Toggles
# --------------------------------------------------------------

class GruntApp(Tk):
    def __init__(self):
        super().__init__()
        self.title("HKO Grunt v12 — Ultimate Desktop Maintenance Agent")
        self.geometry("1400x800")

        # State variables for organization preview
        self.org_preview_data = []
        self.dup_data = []

        self.build_ui()

    # ----------------------------------------------------------
    def build_ui(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab_org = Frame(self.tabs)
        self.tab_dup = Frame(self.tabs)
        self.tab_code = Frame(self.tabs)
        self.tab_schema = Frame(self.tabs)
        self.tab_settings = Frame(self.tabs)

        self.tabs.add(self.tab_org, text="📁 Organize")
        self.tabs.add(self.tab_dup, text="🔍 Duplicates")
        self.tabs.add(self.tab_code, text="💻 Code Catalog")
        self.tabs.add(self.tab_schema, text="🗂️ Folder Schema")
        self.tabs.add(self.tab_settings, text="⚙️ Settings")

        self.build_org_tab()
        self.build_dup_tab()
        self.build_code_tab()
        self.build_schema_tab()
        self.build_settings_tab()

    # ----------------------------------------------------------
    # ORGANIZE TAB - With Preview & Toggles
    # ----------------------------------------------------------
    def build_org_tab(self):
        # Top frame - File type toggles
        toggle_frame = LabelFrame(self.tab_org, text="File Type Categories to Organize",
                                 font=("Arial", 10, "bold"))
        toggle_frame.pack(fill="x", padx=10, pady=5)

        self.category_vars = {}
        row = 0
        col = 0
        for category in FILE_CATEGORIES.keys():
            var = BooleanVar(value=category in CONFIG.get("enabled_categories", []))
            self.category_vars[category] = var
            cb = Checkbutton(toggle_frame, text=category, variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)
            col += 1
            if col > 3:
                col = 0
                row += 1

        # Control buttons
        btn_frame = Frame(self.tab_org)
        btn_frame.pack(fill="x", padx=10, pady=5)

        Button(btn_frame, text="Select Folder to Scan",
               command=self.select_folder_to_organize, bg="#4CAF50", fg="white",
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        Button(btn_frame, text="Preview Organization",
               command=self.preview_organization, bg="#2196F3", fg="white",
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        Button(btn_frame, text="Execute Organization",
               command=self.execute_organization, bg="#FF9800", fg="white",
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        # Preview tree
        preview_frame = LabelFrame(self.tab_org, text="Preview: Files and Destinations",
                                  font=("Arial", 10, "bold"))
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Create Treeview with scrollbars
        tree_scroll_y = Scrollbar(preview_frame)
        tree_scroll_y.pack(side=RIGHT, fill=Y)
        tree_scroll_x = Scrollbar(preview_frame, orient=HORIZONTAL)
        tree_scroll_x.pack(side=BOTTOM, fill=X)

        self.org_tree = ttk.Treeview(preview_frame,
                                     columns=("File", "Category", "Destination", "Reason"),
                                     show="headings",
                                     yscrollcommand=tree_scroll_y.set,
                                     xscrollcommand=tree_scroll_x.set)

        self.org_tree.heading("File", text="File Name")
        self.org_tree.heading("Category", text="Category")
        self.org_tree.heading("Destination", text="Destination Folder")
        self.org_tree.heading("Reason", text="Reason")

        self.org_tree.column("File", width=300)
        self.org_tree.column("Category", width=120)
        self.org_tree.column("Destination", width=180)
        self.org_tree.column("Reason", width=300)

        self.org_tree.pack(fill="both", expand=True)
        tree_scroll_y.config(command=self.org_tree.yview)
        tree_scroll_x.config(command=self.org_tree.xview)

        self.selected_org_folder = None

    def select_folder_to_organize(self):
        folder = filedialog.askdirectory(title="Select folder to organize")
        if folder:
            self.selected_org_folder = folder
            messagebox.showinfo("Selected", f"Will scan: {folder}")

    @threaded
    def preview_organization(self):
        if not self.selected_org_folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return

        # Clear previous preview
        for item in self.org_tree.get_children():
            self.org_tree.delete(item)

        self.org_preview_data = []
        enabled_cats = [cat for cat, var in self.category_vars.items() if var.get()]

        folder = Path(self.selected_org_folder)
        log(f"[ORGANIZE] Previewing: {folder}")

        for file in folder.rglob("*.*"):
            if file.is_file():
                category, dest_folder, reason = classify_file(file)

                if category in enabled_cats or category == "Other":
                    self.org_preview_data.append({
                        "file": file,
                        "category": category,
                        "destination": dest_folder,
                        "reason": reason
                    })

                    # Add to tree
                    self.org_tree.insert("", "end", values=(
                        file.name,
                        category,
                        dest_folder,
                        reason
                    ))

        messagebox.showinfo("Preview Complete",
                          f"Found {len(self.org_preview_data)} files to organize.\n"
                          f"Review the preview and click 'Execute Organization' to proceed.")

    @threaded
    def execute_organization(self):
        if not self.org_preview_data:
            messagebox.showerror("Error", "No preview data. Please run 'Preview Organization' first.")
            return

        if not messagebox.askyesno("Confirm",
                                  f"Move {len(self.org_preview_data)} files to their destinations?"):
            return

        moved = 0
        errors = 0

        for item in self.org_preview_data:
            try:
                source = item["file"]
                dest_base = AUTHORIZED_FOLDERS[item["destination"]]["path"]

                # Create category subfolder if needed
                if item["category"] != "Other":
                    dest_dir = dest_base / item["category"]
                else:
                    dest_dir = dest_base / "General_Docs"

                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = dest_dir / source.name

                # Handle name conflicts
                counter = 1
                while dest_file.exists():
                    dest_file = dest_dir / f"{source.stem}_{counter}{source.suffix}"
                    counter += 1

                shutil.move(str(source), str(dest_file))
                log(f"[ORGANIZE] Moved: {source.name} → {dest_file}")
                moved += 1

            except Exception as e:
                log(f"[ORGANIZE] Error moving {source}: {e}")
                errors += 1

        # Clear preview after execution
        self.org_preview_data = []
        for item in self.org_tree.get_children():
            self.org_tree.delete(item)

        messagebox.showinfo("Complete",
                          f"Organization complete!\n"
                          f"Moved: {moved}\nErrors: {errors}")

    # ----------------------------------------------------------
    # DUPLICATES TAB - Enhanced with Select All & Origin Display
    # ----------------------------------------------------------
    def build_dup_tab(self):
        # Control buttons
        btn_frame = Frame(self.tab_dup)
        btn_frame.pack(fill="x", padx=10, pady=5)

        Button(btn_frame, text="🔍 Scan for Duplicates",
               command=self.scan_duplicates, bg="#2196F3", fg="white",
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        Button(btn_frame, text="☑️ Select All",
               command=self.select_all_duplicates,
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        Button(btn_frame, text="⬜ Deselect All",
               command=self.deselect_all_duplicates,
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        Button(btn_frame, text="🗑️ Delete Selected",
               command=self.delete_selected_duplicates, bg="#F44336", fg="white",
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        # Duplicate tree
        dup_frame = LabelFrame(self.tab_dup, text="Duplicate Files (Check to Delete)",
                              font=("Arial", 10, "bold"))
        dup_frame.pack(fill="both", expand=True, padx=10, pady=5)

        tree_scroll = Scrollbar(dup_frame)
        tree_scroll.pack(side=RIGHT, fill=Y)

        self.dup_tree = ttk.Treeview(dup_frame,
                                     columns=("Select", "Original", "Duplicate", "Size", "Reason"),
                                     show="tree headings",
                                     yscrollcommand=tree_scroll.set)

        self.dup_tree.heading("#0", text="")
        self.dup_tree.heading("Select", text="Delete?")
        self.dup_tree.heading("Original", text="Original File (Keep)")
        self.dup_tree.heading("Duplicate", text="Duplicate File (Older/Newer)")
        self.dup_tree.heading("Size", text="Size")
        self.dup_tree.heading("Reason", text="Reason")

        self.dup_tree.column("#0", width=30)
        self.dup_tree.column("Select", width=80)
        self.dup_tree.column("Original", width=350)
        self.dup_tree.column("Duplicate", width=350)
        self.dup_tree.column("Size", width=100)
        self.dup_tree.column("Reason", width=250)

        self.dup_tree.pack(fill="both", expand=True)
        tree_scroll.config(command=self.dup_tree.yview)

        # Bind click to toggle selection
        self.dup_tree.bind("<Button-1>", self.toggle_dup_selection)

    @threaded
    def scan_duplicates(self):
        roots = [DESKTOP, HOME / "Downloads"]
        log("[DUPLICATES] Scanning...")

        # Clear tree
        for item in self.dup_tree.get_children():
            self.dup_tree.delete(item)

        self.dup_data = find_duplicates_enhanced(roots)

        for dup in self.dup_data:
            original = dup["original"]
            duplicate = dup["duplicate"]
            size = f"{dup['size'] / 1024:.1f} KB"

            # Determine which is older
            age_info = ""
            if dup["duplicate_mtime"] < dup["original_mtime"]:
                age_info = "(Duplicate is older)"
            else:
                age_info = "(Duplicate is newer)"

            item_id = self.dup_tree.insert("", "end", values=(
                "[ ]",  # Checkbox placeholder
                str(original),
                f"{duplicate} {age_info}",
                size,
                dup["reason"]
            ))
            # Store reference
            self.dup_tree.set(item_id, "item_data", str(duplicate))

        messagebox.showinfo("Scan Complete", f"Found {len(self.dup_data)} duplicate files.")

    def toggle_dup_selection(self, event):
        """Toggle checkbox on click"""
        region = self.dup_tree.identify("region", event.x, event.y)
        if region == "cell":
            item = self.dup_tree.identify_row(event.y)
            column = self.dup_tree.identify_column(event.x)

            if column == "#1":  # Select column
                current = self.dup_tree.item(item, "values")[0]
                new_val = "[✓]" if current == "[ ]" else "[ ]"
                values = list(self.dup_tree.item(item, "values"))
                values[0] = new_val
                self.dup_tree.item(item, values=values)

    def select_all_duplicates(self):
        for item in self.dup_tree.get_children():
            values = list(self.dup_tree.item(item, "values"))
            values[0] = "[✓]"
            self.dup_tree.item(item, values=values)

    def deselect_all_duplicates(self):
        for item in self.dup_tree.get_children():
            values = list(self.dup_tree.item(item, "values"))
            values[0] = "[ ]"
            self.dup_tree.item(item, values=values)

    @threaded
    def delete_selected_duplicates(self):
        to_delete = []

        for item in self.dup_tree.get_children():
            values = self.dup_tree.item(item, "values")
            if values[0] == "[✓]":
                # Extract file path from duplicate column
                dup_path = values[2].split(" (")[0]  # Remove age info
                to_delete.append(dup_path)

        if not to_delete:
            messagebox.showwarning("Nothing Selected", "No files selected for deletion.")
            return

        if not messagebox.askyesno("Confirm Deletion",
                                  f"Delete {len(to_delete)} duplicate files?"):
            return

        deleted = 0
        errors = 0

        for file_path in to_delete:
            try:
                Path(file_path).unlink()
                log(f"[DUPLICATES] Deleted: {file_path}")
                deleted += 1
            except Exception as e:
                log(f"[DUPLICATES] Error deleting {file_path}: {e}")
                errors += 1

        # Refresh the scan
        self.scan_duplicates()

        messagebox.showinfo("Complete", f"Deleted: {deleted}\nErrors: {errors}")

    # ----------------------------------------------------------
    # CODE CATALOG TAB
    # ----------------------------------------------------------
    def build_code_tab(self):
        btn_frame = Frame(self.tab_code)
        btn_frame.pack(fill="x", padx=10, pady=5)

        Button(btn_frame, text="📂 Select Folder to Extract Code",
               command=self.run_code_extract, bg="#4CAF50", fg="white",
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        Label(btn_frame, text=f"Extracted code saved to: {CODE_REPO}",
              font=("Arial", 9), fg="blue").pack(side=LEFT, padx=10)

        # Code list
        list_frame = LabelFrame(self.tab_code, text="Extracted Code Files",
                               font=("Arial", 10, "bold"))
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scroll = Scrollbar(list_frame)
        scroll.pack(side=RIGHT, fill=Y)

        self.code_list = Listbox(list_frame, yscrollcommand=scroll.set)
        self.code_list.pack(fill="both", expand=True)
        scroll.config(command=self.code_list.yview)

    @threaded
    def run_code_extract(self):
        folder = filedialog.askdirectory(title="Select folder containing code files")
        if not folder:
            return

        log(f"[CODE] Extracting from: {folder}")
        extracted = extract_code_from_folder(folder)

        self.code_list.delete(0, END)
        for e in extracted:
            self.code_list.insert(END, e)

        messagebox.showinfo("Complete", f"Extracted {len(extracted)} code files to:\n{CODE_REPO}")

    # ----------------------------------------------------------
    # FOLDER SCHEMA TAB
    # ----------------------------------------------------------
    def build_schema_tab(self):
        info_frame = LabelFrame(self.tab_schema, text="Authorized Folder Schema",
                               font=("Arial", 11, "bold"))
        info_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Schema info
        schema_text = Text(info_frame, height=20, wrap="word")
        schema_text.pack(fill="both", expand=True, padx=5, pady=5)

        schema_info = "AUTHORIZED DESKTOP FOLDERS:\n\n"
        for name, info in AUTHORIZED_FOLDERS.items():
            schema_info += f"📁 {name}\n"
            schema_info += f"   Path: {info['path']}\n"
            schema_info += f"   Purpose: {info['description']}\n"
            schema_info += f"   Subfolders: {', '.join(info['subfolders'])}\n\n"

        schema_text.insert("1.0", schema_info)
        schema_text.config(state="disabled")

        # Control buttons
        btn_frame = Frame(self.tab_schema)
        btn_frame.pack(fill="x", padx=10, pady=5)

        Button(btn_frame, text="✅ Create All Authorized Folders",
               command=self.create_schema, bg="#4CAF50", fg="white",
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        Button(btn_frame, text="🔍 Find Unauthorized Folders",
               command=self.find_unauthorized, bg="#FF9800", fg="white",
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        Button(btn_frame, text="🗑️ Delete Unauthorized Folders",
               command=self.delete_unauthorized, bg="#F44336", fg="white",
               font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)

        # Results list
        result_frame = LabelFrame(self.tab_schema, text="Results",
                                 font=("Arial", 10, "bold"))
        result_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scroll = Scrollbar(result_frame)
        scroll.pack(side=RIGHT, fill=Y)

        self.schema_list = Listbox(result_frame, yscrollcommand=scroll.set)
        self.schema_list.pack(fill="both", expand=True)
        scroll.config(command=self.schema_list.yview)

    def create_schema(self):
        created = create_authorized_schema()
        self.schema_list.delete(0, END)
        self.schema_list.insert(END, "=== CREATED FOLDERS ===")
        for folder in created:
            self.schema_list.insert(END, f"✓ {folder}")
        log("[SCHEMA] Created authorized folder structure")
        messagebox.showinfo("Success", f"Created {len(created)} folders/subfolders")

    def find_unauthorized(self):
        unauthorized = find_unauthorized_folders()
        self.schema_list.delete(0, END)
        self.schema_list.insert(END, "=== UNAUTHORIZED FOLDERS ===")

        if unauthorized:
            for folder in unauthorized:
                self.schema_list.insert(END, f"⚠️ {folder}")
            messagebox.showwarning("Found Unauthorized Folders",
                                 f"Found {len(unauthorized)} unauthorized folders.\n"
                                 f"Review them before deleting.")
        else:
            self.schema_list.insert(END, "✓ No unauthorized folders found")
            messagebox.showinfo("Clean", "Desktop follows authorized schema!")

    def delete_unauthorized(self):
        unauthorized = find_unauthorized_folders()

        if not unauthorized:
            messagebox.showinfo("Nothing to Delete", "No unauthorized folders found.")
            return

        msg = f"Delete {len(unauthorized)} unauthorized folders?\n\n"
        msg += "\n".join([str(f) for f in unauthorized[:5]])
        if len(unauthorized) > 5:
            msg += f"\n... and {len(unauthorized) - 5} more"

        if not messagebox.askyesno("Confirm Deletion", msg):
            return

        deleted = 0
        errors = 0

        for folder in unauthorized:
            try:
                # Move to quarantine instead of deleting
                quarantine = Path(CONFIG["quarantine"])
                quarantine.mkdir(exist_ok=True)
                dest = quarantine / folder.name
                shutil.move(str(folder), str(dest))
                log(f"[SCHEMA] Moved to quarantine: {folder}")
                deleted += 1
            except Exception as e:
                log(f"[SCHEMA] Error moving {folder}: {e}")
                errors += 1

        self.find_unauthorized()  # Refresh
        messagebox.showinfo("Complete",
                          f"Moved to quarantine: {deleted}\nErrors: {errors}")

    # ----------------------------------------------------------
    # SETTINGS TAB - Enhanced with Toggles
    # ----------------------------------------------------------
    def build_settings_tab(self):
        # Quarantine settings
        quarantine_frame = LabelFrame(self.tab_settings, text="Quarantine Folder",
                                     font=("Arial", 10, "bold"))
        quarantine_frame.pack(fill="x", padx=10, pady=5)

        self.q_var = StringVar(value=CONFIG.get("quarantine", str(DESKTOP / "QUARANTINE")))
        Entry(quarantine_frame, textvariable=self.q_var, width=60).pack(side=LEFT, padx=5)
        Button(quarantine_frame, text="Browse", command=self.pick_quarantine).pack(side=LEFT)

        # Behavior toggles
        behavior_frame = LabelFrame(self.tab_settings, text="Organization Behavior",
                                   font=("Arial", 10, "bold"))
        behavior_frame.pack(fill="x", padx=10, pady=5)

        self.auto_organize_var = BooleanVar(value=CONFIG.get("auto_organize", False))
        Checkbutton(behavior_frame, text="Auto-organize on scan (skip preview)",
                   variable=self.auto_organize_var).pack(anchor="w", padx=10, pady=2)

        self.deep_scan_var = BooleanVar(value=CONFIG.get("deep_scan", True))
        Checkbutton(behavior_frame, text="Deep scan (search subfolders)",
                   variable=self.deep_scan_var).pack(anchor="w", padx=10, pady=2)

        self.create_sub_var = BooleanVar(value=CONFIG.get("create_subfolders", True))
        Checkbutton(behavior_frame, text="Create category subfolders automatically",
                   variable=self.create_sub_var).pack(anchor="w", padx=10, pady=2)

        self.delete_unauth_var = BooleanVar(value=CONFIG.get("delete_unauthorized_folders", False))
        Checkbutton(behavior_frame, text="⚠️ Delete unauthorized folders automatically (dangerous!)",
                   variable=self.delete_unauth_var, fg="red").pack(anchor="w", padx=10, pady=2)

        # Save button
        Button(self.tab_settings, text="💾 Save Settings",
               command=self.save_settings, bg="#4CAF50", fg="white",
               font=("Arial", 11, "bold")).pack(pady=10)

        # Info label
        info = f"Config file: {CONFIG_PATH}\nLogs folder: {LOGS_PATH}"
        Label(self.tab_settings, text=info, font=("Arial", 9), fg="blue").pack(pady=5)

    def pick_quarantine(self):
        folder = filedialog.askdirectory(title="Select quarantine folder")
        if folder:
            self.q_var.set(folder)

    def save_settings(self):
        CONFIG["quarantine"] = self.q_var.get()
        CONFIG["auto_organize"] = self.auto_organize_var.get()
        CONFIG["deep_scan"] = self.deep_scan_var.get()
        CONFIG["create_subfolders"] = self.create_sub_var.get()
        CONFIG["delete_unauthorized_folders"] = self.delete_unauth_var.get()
        CONFIG["enabled_categories"] = [cat for cat, var in self.category_vars.items() if var.get()]

        save_config(CONFIG)
        log("[SETTINGS] Configuration saved")
        messagebox.showinfo("Saved", "Settings saved successfully!")

# --------------------------------------------------------------
# RUN
# --------------------------------------------------------------

if __name__ == "__main__":
    log("=" * 60)
    log("HKO GRUNT v12 STARTED")
    log("=" * 60)

    app = GruntApp()
    app.mainloop()
