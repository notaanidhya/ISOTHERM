import os

idf_path = "building_model/5ZoneAirCooled.idf"
if not os.path.exists(idf_path):
    idf_path = "5ZoneAirCooled.idf"

with open(idf_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

in_people = False
cur = []
for line in lines:
    st = line.strip()
    if st.upper().startswith("PEOPLE,"):
        in_people = True
        cur = []
    elif in_people:
        if ";" in st:
            cur.append(st)
            in_people = False
            print("PEOPLE object:")
            for l in cur:
                print("  ", l)
        else:
            cur.append(st)
