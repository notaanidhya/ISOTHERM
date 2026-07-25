import os

idf_path = "5ZoneAirCooled.idf"
if os.path.exists(idf_path):
    with open(idf_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lines = content.splitlines()
    in_people = False
    people_blocks = []
    current_block = []
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("PEOPLE,"):
            in_people = True
            current_block = [line]
        elif in_people:
            current_block.append(line)
            if ";" in line:
                in_people = False
                people_blocks.append("\n".join(current_block))

    print("Found People blocks:")
    for pb in people_blocks:
        print("---")
        print(pb)
