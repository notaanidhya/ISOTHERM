import os
import mistune

def generate_portfolio():
    readme_path = r"c:\Projects\Honeywell_hack\README.md"
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_md = f.read()
        
    readme_html = mistune.html(readme_md)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ISOTHERM — Master Project Deliverables Portfolio</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; line-height: 1.6; color: #222; max-width: 950px; margin: 40px auto; padding: 0 40px; }}
        h1, h2, h3 {{ color: #003366; }}
        h1 {{ border-bottom: 2px solid #003366; padding-bottom: 10px; }}
        h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 6px; margin-top: 2em; }}
        table {{ width: 100%; border-collapse: collapse; margin: 25px 0; font-size: 0.95em; }}
        th, td {{ border: 1px solid #ccc; padding: 12px; text-align: left; }}
        th {{ background-color: #f0f4f8; color: #003366; }}
        pre {{ background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; overflow-x: auto; }}
        code {{ font-family: monospace; background: #f4f6f8; padding: 2px 5px; border-radius: 4px; color: #d63384; }}
        pre code {{ background: transparent; color: inherit; }}
        .box {{ background: #f8f9fa; border-left: 4px solid #003366; padding: 15px; margin: 20px 0; }}
        @media print {{
            body {{ padding: 0 20px; font-size: 11pt; }}
            pre, table {{ page-break-inside: avoid; }}
            h1, h2 {{ page-break-after: avoid; }}
        }}
    </style>
</head>
<body>
    <h1>ISOTHERM — Honeywell Campus Connect Deliverables Portfolio</h1>
    <div class="box">
        <strong>Submission Type:</strong> Individual Submission (Aanid)<br>
        <strong>Challenge #3:</strong> AI-Powered Autonomous Smart Building Optimization Challenge<br>
        <strong>Note on Source Code:</strong> All Python code (`src/`, `scripts/`), React UI (`react_dashboard/`), and complete `.idf` models (`building_model/`) are hosted in our public GitHub repository submitted on the portal form.
    </div>
    
    <h2>1. Deliverable Verification & Scorecard Summary</h2>
    <p>This portfolio consolidates our quantitative verification, EnergyPlus meter reconciliation, and architectural proof for portal evaluation.</p>
    
    {readme_html}
</body>
</html>"""

    out_path = r"C:\Users\aanid\Downloads\ISOTHERM_Master_Portfolio.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Created Master Portfolio HTML at: {out_path}")

if __name__ == "__main__":
    generate_portfolio()
