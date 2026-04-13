"""
기획서.md → PDF 변환 스크립트
markdown → HTML (스타일 적용) → Chrome 헤드리스 PDF 출력
"""

import subprocess
import sys
from pathlib import Path
import markdown

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_DIR = Path(__file__).parent
MD_FILE  = BASE_DIR / "기획서.md"
HTML_FILE = BASE_DIR / "기획서.html"
PDF_FILE  = BASE_DIR / "기획서.pdf"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

@page {
    size: A4;
    margin: 20mm 18mm 20mm 18mm;
}

body {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    font-size: 10pt;
    line-height: 1.7;
    color: #1a1a2e;
    background: #fff;
}

h1 {
    font-size: 20pt;
    font-weight: 700;
    color: #0d47a1;
    border-bottom: 3px solid #0d47a1;
    padding-bottom: 8px;
    margin: 24px 0 16px;
}

h2 {
    font-size: 14pt;
    font-weight: 700;
    color: #1565c0;
    border-left: 4px solid #1565c0;
    padding-left: 10px;
    margin: 20px 0 10px;
    page-break-after: avoid;
}

h3 {
    font-size: 11pt;
    font-weight: 600;
    color: #1976d2;
    margin: 14px 0 6px;
    page-break-after: avoid;
}

h4 {
    font-size: 10pt;
    font-weight: 600;
    color: #333;
    margin: 10px 0 4px;
}

p {
    margin: 6px 0 8px;
}

blockquote {
    border-left: 4px solid #1565c0;
    background: #e3f2fd;
    padding: 10px 16px;
    margin: 12px 0;
    border-radius: 0 4px 4px 0;
    font-style: italic;
    color: #0d47a1;
    font-size: 11pt;
    font-weight: 600;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 14px;
    font-size: 9pt;
    page-break-inside: avoid;
}

th {
    background: #1565c0;
    color: #fff;
    padding: 7px 10px;
    text-align: left;
    font-weight: 600;
}

td {
    padding: 6px 10px;
    border-bottom: 1px solid #e0e0e0;
    vertical-align: top;
}

tr:nth-child(even) td {
    background: #f5f9ff;
}

code {
    font-family: 'Consolas', 'D2Coding', monospace;
    background: #f0f4ff;
    color: #1a237e;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 9pt;
}

pre {
    background: #1e2a3a;
    color: #e8eaf6;
    padding: 12px 14px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 10px 0;
    font-size: 8.5pt;
    line-height: 1.6;
    page-break-inside: avoid;
}

pre code {
    background: transparent;
    color: #e8eaf6;
    padding: 0;
}

ul, ol {
    margin: 6px 0 8px 20px;
}

li {
    margin: 3px 0;
}

hr {
    border: none;
    border-top: 1px solid #bbdefb;
    margin: 16px 0;
}

.header-meta {
    color: #555;
    font-size: 9pt;
    margin-bottom: 4px;
}

strong {
    color: #0d47a1;
}
"""

def convert():
    md_text = MD_FILE.read_text(encoding="utf-8")
    body_html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
    )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
{CSS}
</style>
</head>
<body>
{body_html}
</body>
</html>"""

    HTML_FILE.write_text(html, encoding="utf-8")
    print(f"HTML 생성: {HTML_FILE}")

    result = subprocess.run([
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={PDF_FILE}",
        "--print-to-pdf-no-header",
        str(HTML_FILE),
    ], capture_output=True, text=True, timeout=60)

    if result.returncode == 0 and PDF_FILE.exists():
        size_kb = PDF_FILE.stat().st_size // 1024
        print(f"PDF 생성 완료: {PDF_FILE} ({size_kb} KB)")
    else:
        print("PDF 생성 실패")
        print(result.stderr)
        sys.exit(1)

if __name__ == "__main__":
    convert()
