import os
import sys
import zipfile

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def build_submission_zip():
    print("=========================================================")
    print("📦 BUILDING FINAL HONEYWELL SUBMISSION ZIP PACKAGE")
    print("=========================================================")

    zip_filename = os.path.join(PROJECT_ROOT, "Honeywell_Submission.zip")

    files_to_include = [
        "requirements.txt",
        "README.md",
        "comparison_results.json",
        "comparison_results.csv",
        os.path.join("building_model", "5ZoneAirCooled.idf"),
        os.path.join("building_model", "5ZoneAirCooled_Prepared.idf"),
        os.path.join("building_model", "5ZoneAirCooled_AI_Optimized.idf"),
        os.path.join("building_model", "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"),
        os.path.join("docs", "architecture.md"),
        os.path.join("docs", "demo_video_script.md"),
    ]

    directories_to_include = ["src", "scripts", "dashboard", "tests"]

    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add single files
        for rel_path in files_to_include:
            abs_path = os.path.join(PROJECT_ROOT, rel_path)
            if os.path.exists(abs_path):
                zipf.write(abs_path, arcname=rel_path)
                print(f"  + Added file: {rel_path}")
            else:
                print(f"  - Warning: file missing {rel_path}")

        # Add directories recursively
        for dir_name in directories_to_include:
            dir_abs = os.path.join(PROJECT_ROOT, dir_name)
            if os.path.exists(dir_abs):
                for root, _, files in os.walk(dir_abs):
                    for file in files:
                        if file.endswith((".pyc", ".pyo", ".git")) or "__pycache__" in root:
                            continue
                        abs_file = os.path.join(root, file)
                        rel_file = os.path.relpath(abs_file, PROJECT_ROOT)
                        zipf.write(abs_file, arcname=rel_file)
                print(f"  + Added directory recursively: {dir_name}/")

    print(f"\nSUCCESS: Created Honeywell_Submission.zip at: {zip_filename}")

if __name__ == "__main__":
    build_submission_zip()
