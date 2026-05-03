import os
import hashlib
from pathlib import Path

def get_image_hash(file_path):
    """Creates a unique fingerprint for the photo data."""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        # Read in chunks to handle high-res files without crashing
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def remove_duplicates(target_folder):
    # Create a 'trash' folder so nothing is permanently lost yet
    trash_dir = os.path.join(target_folder, "duplicates_trash")
    if not os.path.exists(trash_dir):
        os.makedirs(trash_dir)

    hashes_found = {}
    duplicate_count = 0

    # Go through every subfolder (2025, 2026, Cupertino, etc.)
    for path in Path(target_folder).rglob('*'):
        if path.is_file() and path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.heic']:
            file_hash = get_image_hash(path)

            if file_hash in hashes_found:
                print(f"Found duplicate: {path.name} is the same as {hashes_found[file_hash]}")
                # Move to trash instead of deleting
                os.rename(path, os.path.join(trash_dir, path.name))
                duplicate_count += 1
            else:
                hashes_found[file_hash] = path.name

    print(f"\nFinished! Moved {duplicate_count} duplicates to: {trash_dir}")

# UPDATE THIS to your actual project path
my_project_path = "/Users/ryannyap/bbmarble_website_assets/assets/projects"
remove_duplicates(my_project_path)