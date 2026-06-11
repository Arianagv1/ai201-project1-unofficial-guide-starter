import os
for fname in ["reddit_data.json", "uloop_professors.json", 
              "uicgrades_data.json", "professor_data.json"]:
    size = os.path.getsize(fname) if os.path.exists(fname) else "MISSING"
    print(f"{fname}: {size} bytes")