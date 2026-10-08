import os
import json

base_dir = './assets/projects' 
gallery_data = []

# Rooms we are looking for
room_types = ['kitchen', 'bathroom', 'laundry', 'outdoor', 'fireplace', 'office']

for root, dirs, files in os.walk(base_dir):
    for filename in files:
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            
            clean_name = filename.lower().replace('.jpeg', '').replace('.jpg', '').replace('.png', '')
            
            # Default values
            filter_tag = "other"
            detected_loc = "Project"
            year_tag = os.path.basename(root) if os.path.basename(root).isdigit() else "2024"

            # 1. Extract Room Type
            for room in room_types:
                if room in clean_name:
                    filter_tag = room
                    break
            
            # 2. Extract Year
            parts = clean_name.split('-')
            found_year = next((p for p in parts if p.isdigit() and len(p) == 4), year_tag)
            year_tag = found_year

            # 3. Extract Location (The part between Room and Year)
            loc_step = clean_name.replace(filter_tag, '').replace(year_tag, '')
            for i in range(10): loc_step = loc_step.replace(str(i), '')
            detected_loc = loc_step.replace('-', ' ').strip().title()
            
            if not detected_loc: detected_loc = "Bay Area"

            relative_src = f"assets/projects/{os.path.basename(root)}/{filename}"
            
            gallery_data.append({
                "location": detected_loc,
                "filter_tag": filter_tag,
                "year": year_tag,
                "src": relative_src
            })

# --- SORTING LOGIC ---
# Newest year first. Within a year, the most recently added photos come first,
# using the date each file was first committed to git (renames keep the original date).
# Photos not yet committed count as newest. Ties fall back to location (as before).
import subprocess, time

def get_added_dates():
    dates = {}
    try:
        out = subprocess.run(
            ['git', 'log', '--reverse', '-M', '--format=C%ct', '--name-status', '--', 'assets/projects'],
            capture_output=True, text=True, check=True).stdout
    except Exception:
        return dates
    t = 0
    for line in out.splitlines():
        if line.startswith('C') and line[1:].isdigit():
            t = int(line[1:])
            continue
        parts = line.split('\t')
        if parts[0] == 'A' and len(parts) == 2:
            dates[parts[1]] = t
        elif parts[0].startswith('R') and len(parts) == 3:
            dates[parts[2]] = dates.get(parts[1], t)
    return dates

added = get_added_dates()
now = int(time.time())
for item in gallery_data:
    item['_added'] = added.get(item['src'], now)

gallery_data.sort(key=lambda x: (x['year'], x['_added'], x['location'], x['src']), reverse=True)
for item in gallery_data:
    del item['_added']

with open('gallery-data.json', 'w') as f:
    json.dump(gallery_data, f, indent=4)

print(f"--- Processed {len(gallery_data)} photos ---")
print(f"Filters found: {set(item['filter_tag'] for item in gallery_data)}")
