import os
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ZIP_PATH = os.path.join(ROOT, "voice-ops-agent.zip")

EXCLUDE_DIRS = {"node_modules", ".next", "__pycache__", ".pytest_cache", ".git"}
EXCLUDE_EXTS = {".pyc", ".db", ".zip"}

count = 0
with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(ROOT):
        # Prune excluded directories in-place so os.walk doesn't even traverse them
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in EXCLUDE_EXTS or file.endswith(".zip"):
                continue

            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, ROOT)
            zipf.write(full_path, rel_path)
            count += 1

size_kb = os.path.getsize(ZIP_PATH) / 1024
print(f"Successfully archived {count} files into {ZIP_PATH} ({size_kb:.1f} KB)")
