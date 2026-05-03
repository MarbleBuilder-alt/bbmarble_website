import os
import hashlib
from pathlib import Path

def get_image_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def remove_duplicates(target_folder):
    trash_dir = os.path.join(target_folder, "duplicates_trash")
    if not os.path.exists(trash_dir):
        os.makedirs(trash_dir)

    hashes_found = {}
    duplicate_count = 0

    for path in Path(target_folder).rglob('*'):
        if path.is_file() and path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.heic']:
            file_hash = get_image_hash(path)
            if file_hash in hashes_found:
                print(f"Found duplicate: {path.name}")
                os.rename(path, os.path.join(trash_dir, path.name))
                duplicate_count += 1
            else:
                hashes_found[file_hash] = path.name

    print(f"\nFinished! Moved {duplicate_count} duplicates to: {trash_dir}")

my_project_path = "/Users/ryannyap/bbmarble_website_assets/assets/projects"
remove_duplicates(my_project_path)
