(
echo import sys
echo import os
echo import yaml
echo import json
echo from datetime import datetime
echo from core.google_drive import DriveFetcher
echo from core.processor import DocumentProcessor
echo.
echo # --- Configuration ---
echo with open('config.yaml', 'r') as f:
echo     CONFIG = yaml.safe_load(f)
echo.
echo OUTPUT_DIR = CONFIG['output_directory']
echo MANIFEST_FILE = CONFIG['manifest_file']
echo DRIVE_FOLDER_ID = CONFIG['source_drive_folder_id']
echo.
echo # --- 1. Validation Logic ---
echo def validate_document(text):
echo     print("... Validating document...")
echo     if len(text) < CONFIG['validation']['min_length']:
echo         print("... VALIDATION FAILED: Document is too short.")
echo         return False
echo     print("... Validation OK.")
echo     return True
echo.
echo # --- 2. Orchestration ---
echo def run_workflow(file_input):
echo     try:
echo         print(f"---== STARTING WORKFLOW FOR INPUT: {file_input} ==---")
echo.
echo         if file_input.startswith("local:"):
echo             # 1A. Fetch from Local Machine
echo             file_path = file_input.replace("local:", "")
echo             if not os.path.exists(file_path):
echo                 print(f"[!!] ERROR: Local file not found: {file_path}")
echo                 return
echo             file_name_raw = os.path.basename(file_path)
echo             with open(file_path, 'r', encoding='utf-8') as f:
echo                 raw_text = f.read()
echo             print(f"... Fetched local file: {file_name_raw}")
echo         else:
echo             # 1B. Fetch from Google Drive
echo             drive = DriveFetcher(DRIVE_FOLDER_ID)
echo             file_id = file_input
echo             file_metadata = drive.service.files().get(fileId=file_id, fields='name').execute()
echo             file_name_raw = file_metadata['name']
echo             raw_text = drive.download_file(file_id, file_name_raw)
echo.
echo         # 2. Process
echo         processor = DocumentProcessor()
echo         processing_prompt = "You are an expert editor. Review the following document, fix any errors, and format it clearly."
echo         processed_text = processor.process(raw_text, processing_prompt)
echo.
echo         # 3. Validate
echo         if not validate_document(processed_text):
echo             raise Exception("Validation failed for processed document.")
echo.
echo         # 4. Publish
echo         print("... Publishing to docs folder.")
echo         if not os.path.exists(OUTPUT_DIR):
echo             os.makedirs(OUTPUT_DIR)
echo.
echo         # --- UPDATED FILENAME LOGIC ---
echo         file_name_base, ext = os.path.splitext(file_name_raw) # Splits 'Test.txt' into 'Test' and '.txt'
echo         output_filename = f"{datetime.now().strftime('%Y-%m-%d')}-{file_name_base}.html" # Creates '...-Test.html'
echo         output_path = os.path.join(OUTPUT_DIR, output_filename)
echo         # --- End of Update ---
echo.
echo         html_content = f"<html><head><title>{file_name_base}</title></head><body>"
echo         html_content += f"<h1>{file_name_base}</h1>"
echo         html_content += f"<pre>{processed_text}</pre>"
echo         html_content += "</body></html>"
echo.
echo         with open(output_path, 'w', encoding='utf-8') as f:
echo             f.write(html_content)
echo         print(f"... Successfully saved to {output_path}")
echo.
echo         # 5. Update Manifest
echo         update_manifest(file_name_raw, output_filename)
echo         print(f"---== WORKFLOW COMPLETE FOR: {file_name_raw} ==---")
echo.
echo     except Exception as e:
echo         print(f"[!!] WORKFLOW FAILED for {file_input}: {e}")
echo.
echo def update_manifest(file_name, output_filename):
echo     manifest = []
echo     if os.path.exists(MANIFEST_FILE):
echo         with open(MANIFEST_FILE, 'r') as f:
echo             manifest = json.load(f)
echo.
echo     entry = {
echo         'source_name': file_name,
echo         'output_file': output_filename,
echo         'processed_date': datetime.now().isoformat()
echo     }
echo     manifest.append(entry)
echo.
echo     with open(MANIFEST_FILE, 'w') as f:
echo         json.dump(manifest, f, indent=2)
echo     print("... Manifest updated.")
echo.
echo # --- Main Entry Point ---
echo if __name__ == "__main__":
echo     if len(sys.argv) < 2:
echo         print("Usage: python hko.py <file_id_1> <local:path/to/file.txt> ...")
echo         sys.exit(1)
echo.
echo     file_inputs = sys.argv[1:]
echo     print(f"Starting batch process for {len(file_inputs)} file(s).")
echo     for file_input in file_inputs:
echo         run_workflow(file_input)
echo     print("Batch process finished.")
echo.
) > hko.py