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
            # We remove the room name and year/numbers to leave just the city
            loc_step = clean_name.replace(filter_tag, '').replace(year_tag, '')
            # Clean up leftover dashes or numbers at the end
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

with open('gallery-data.json', 'w') as f:
    json.dump(gallery_data, f, indent=4)

print(f"--- Processed {len(gallery_data)} photos ---")
print(f"Filters found: {set(item['filter_tag'] for item in gallery_data)}")
