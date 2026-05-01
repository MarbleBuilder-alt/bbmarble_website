import os
import json

base_dir = '.' 
gallery_data = []

# Potential cities to look for - you can add more to this list later
known_cities = ['menlo-park', 'cupertino', 'palo-alto', 'saratoga', 'san-francisco', 'south-san-francisco', 'atherton', 'los-altos', 'hillsborough', 'san-jose', 'mountain-view']

for root, dirs, files in os.walk(base_dir):
    for filename in files:
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            # 1. Determine Year (from folder name)
            folder_name = os.path.basename(root)
            year_tag = folder_name if (folder_name.isdigit() and len(folder_name) == 4) else "Archive"
            
            # 2. Determine Location (from filename)
            detected_loc = "Other Locations"
            filter_tag = "other"
            
            name_lower = filename.lower().replace('_', '-').replace(' ', '-')
            for city in known_cities:
                if name_lower.startswith(city):
                    detected_loc = city.replace('-', ' ').title()
                    filter_tag = city
                    break
            
            # 3. Create the entry
            # We use a relative path that will match your GitHub structure
            relative_src = f"assets/projects/{year_tag}/{filename}"
            
            gallery_data.append({
                "location": detected_loc,
                "filter_tag": filter_tag,
                "year": year_tag,
                "src": relative_src
            })

with open('gallery-data.json', 'w') as f:
    json.dump(gallery_data, f, indent=4)

# Print a summary for you
cities_found = set(item['location'] for item in gallery_data)
print(f"\n--- Process Complete ---")
print(f"Total Photos Found: {len(gallery_data)}")
print(f"Locations Identified: {', '.join(cities_found)}")
print(f"File created: gallery-data.json")
