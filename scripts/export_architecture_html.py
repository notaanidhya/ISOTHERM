import os
import re
import mistune

def export_to_html(md_path, html_path1, html_path2):
    print(f"Reading Markdown from: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
        
    print("Converting Markdown to HTML using mistune...")
    # Convert markdown to HTML
    raw_html = mistune.html(md_content)
    
    # Replace <pre><code class="language-mermaid">...</code></pre> with <div class="mermaid">...</div> for Mermaid rendering
    # Mistune 3 format: <pre><code class="language-mermaid">...</code></pre> or <pre><code class="mermaid">...</code></pre>
    def mermaid_replacer(match):
        content = match.group(1)
        # Decode HTML entities if mistune escaped them
        content = content.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
        return f'<div class="mermaid-wrapper"><div class="mermaid">\n{content}\n</div></div>'
        
    processed_html = re.sub(r'<pre><code class="(?:language-)?mermaid">([\s\S]*?)</code></pre>', mermaid_replacer, raw_html)
    
    # HTML Template with Executive Styling & Print CSS
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ISOTHERM — System Architecture Document</title>
    <!-- Include Mermaid JS for diagram rendering -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'neutral',
            flowchart: {{ curve: 'linear', padding: 20 }}
        }});
    </script>
    <style>
        :root {{
            --primary: #003366;
            --text: #222222;
            --bg: #ffffff;
            --border: #e0e0e0;
            --code-bg: #f8f9fa;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background-color: var(--bg);
            max-width: 900px;
            margin: 40px auto;
            padding: 0 40px;
        }}
        h1, h2, h3, h4 {{
            color: var(--primary);
            font-weight: 700;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        h1 {{
            font-size: 2.2em;
            border-bottom: 2px solid var(--primary);
            padding-bottom: 10px;
            margin-top: 0;
        }}
        h2 {{
            font-size: 1.6em;
            border-bottom: 1px solid var(--border);
            padding-bottom: 6px;
            margin-top: 2em;
        }}
        h3 {{
            font-size: 1.25em;
        }}
        p, li {{
            font-size: 1.05em;
            color: #333;
        }}
        ul, ol {{
            padding-left: 24px;
            margin-bottom: 1em;
        }}
        li {{
            margin-bottom: 6px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.95em;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 12px 15px;
            text-align: left;
            vertical-align: top;
        }}
        th {{
            background-color: #f0f4f8;
            color: var(--primary);
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #fafbfc;
        }}
        pre, code {{
            font-family: "Consolas", "Monaco", "Courier New", monospace;
        }}
        code {{
            background-color: var(--code-bg);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
            color: #d63384;
            border: 1px solid #ebebeb;
        }}
        pre {{
            background-color: #1e1e1e;
            color: #d4d4d4;
            padding: 18px;
            border-radius: 6px;
            overflow-x: auto;
            line-height: 1.45;
        }}
        pre code {{
            background-color: transparent;
            color: inherit;
            padding: 0;
            border: none;
            font-size: 0.95em;
        }}
        .mermaid-wrapper {{
            background-color: #fbfbfb;
            border: 1px solid #eaeaea;
            border-radius: 8px;
            padding: 20px;
            margin: 25px 0;
            display: flex;
            justify-content: center;
        }}
        blockquote {{
            border-left: 4px solid var(--primary);
            margin: 0;
            padding-left: 16px;
            color: #555;
            font-style: italic;
        }}
        hr {{
            border: 0;
            height: 1px;
            background: var(--border);
            margin: 40px 0;
        }}
        /* Print Styles for clean PDF export */
        @media print {{
            body {{
                max-width: 100%;
                margin: 0;
                padding: 0 20px;
                font-size: 11pt;
            }}
            h1, h2 {{
                page-break-after: avoid;
            }}
            table, pre, .mermaid-wrapper {{
                page-break-inside: avoid;
            }}
            .mermaid-wrapper {{
                border: none;
                padding: 10px 0;
            }}
            pre {{
                background-color: #f8f9fa !important;
                color: #222 !important;
                border: 1px solid #ccc;
            }}
        }}
    </style>
</head>
<body>
    {processed_html}
</body>
</html>"""

    print(f"Writing standalone HTML to: {html_path1}")
    with open(html_path1, "w", encoding="utf-8") as f:
        f.write(full_html)
        
    if html_path2:
        print(f"Writing standalone HTML copy to: {html_path2}")
        with open(html_path2, "w", encoding="utf-8") as f:
            f.write(full_html)
            
    print("Flawlessly generated standalone HTML ready for 1-click PDF export!")

if __name__ == "__main__":
    md = r"c:\Projects\Honeywell_hack\docs\architecture.md"
    out1 = r"c:\Projects\Honeywell_hack\docs\architecture.html"
    out2 = r"C:\Users\aanid\Downloads\ISOTHERM_System_Architecture.html"
    export_to_html(md, out1, out2)
