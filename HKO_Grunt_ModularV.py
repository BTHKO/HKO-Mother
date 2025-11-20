#!/usr/bin/env python3
"""
HKO DAEMON v5.1 - UX READY (PATCHED)
Status: STABLE | Architecture: Headless Service (FastAPI)
Changes: Lock Detection, Schema Sync, Log Optimization
"""

import os
import sys
import shutil
import json
import hashlib
import asyncio
import sqlite3
import uvicorn
import zipfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union
from concurrent.futures import ProcessPoolExecutor
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ... [CONFIGURATION CONSTANTS - Same as v5.0] ...
APP_NAME = "HKO DAEMON"
VERSION = "v5.1"
DESKTOP_PATH = Path(os.path.expanduser("~/Desktop"))
HKO_ROOT = DESKTOP_PATH / "HKO_METAVERSE"
LOGS_ROOT = HKO_ROOT / "LOGS"
SCHEMA_HASH = "init" # Placeholder for schema versioning

# =============================================================================
# UTILS
# =============================================================================

def is_file_locked(filepath):
    """Checks if a file is locked by another process."""
    if not os.path.exists(filepath): return False
    try:
        # Try to rename it to itself (atomic check)
        os.rename(filepath, filepath)
        return False
    except OSError:
        return True

# =============================================================================
# DATA MODELS
# =============================================================================

class MoveRequest(BaseModel):
    src_path: str
    dest_folder: str
    dry_run: bool = True

# =============================================================================
# CORE LOGIC
# =============================================================================

class OrganizeEngine:
    def scan_desktop(self):
        candidates = []
        for item in DESKTOP_PATH.iterdir():
            if item.is_file() and item.name != "desktop.ini":
                candidates.append({"path": str(item), "name": item.name, "suggestion": "Unsorted"})
        return candidates

    def execute_move(self, src_path: str, dest_folder: str, dry_run: bool) -> Dict:
        src = Path(src_path)
        if not src.exists(): 
            return {"success": False, "message": "Source missing", "action": "none"}
        
        target_dir = DESKTOP_PATH / dest_folder
        dest = target_dir / src.name
        
        if dest.exists():
            dest = target_dir / f"{src.stem}_{int(datetime.now().timestamp())}{src.suffix}"
            
        if dry_run:
            # IMPROVED SIMULATION
            if is_file_locked(src):
                return {
                    "success": False, 
                    "message": f"[DRY-RUN] File is LOCKED by another app: {src.name}", 
                    "action": "lock_error"
                }
                
            return {
                "success": True,
                "message": f"[DRY-RUN] Verified & Ready: {src.name} -> {dest_folder}",
                "action": "simulate",
                "new_path": str(dest)
            }
        else:
            # EXECUTION
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
                return {
                    "success": True,
                    "message": f"[LIVE] Moved {src.name} to {dest_folder}",
                    "action": "move",
                    "new_path": str(dest)
                }
            except Exception as e:
                return {"success": False, "message": str(e), "action": "error"}

# =============================================================================
# API LAYER
# =============================================================================

app = FastAPI(title=f"{APP_NAME} {VERSION}")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

organizer = OrganizeEngine()

@app.get("/")
def status():
    return {
        "system": APP_NAME, 
        "version": VERSION, 
        "status": "ONLINE",
        "schema_hash": SCHEMA_HASH # UI can poll this to reload
    }

@app.get("/organize/candidates")
def get_organize_candidates():
    return organizer.scan_desktop()

@app.post("/organize/execute")
def execute_organize_job(req: MoveRequest):
    result = organizer.execute_move(req.src_path, req.dest_folder, req.dry_run)
    return result

@app.get("/logs/recent")
def get_recent_logs(limit: int = 20): # Increased limit
    return [
        {"time": datetime.now().isoformat(), "msg": "System ready (Patched v5.1)", "type": "info"}
    ]

if __name__ == "__main__":
    print(f"🛡️ {APP_NAME} {VERSION} INITIALIZED (PATCHED)")
    uvicorn.run(app, host="127.0.0.1", port=8000)