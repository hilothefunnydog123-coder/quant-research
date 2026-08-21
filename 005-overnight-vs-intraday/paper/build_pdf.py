#!/usr/bin/env python3
"""Render paper.md to a styled, print-ready paper.html (and paper.pdf via a
headless browser). Run: python build_pdf.py"""
import os

import markdown

HERE = os.path.dirname(__file__)
CSS = """
@page { size: A4; margin: 22mm 20mm; }
body { font-family: Georgia, 'Times New Roman', serif; color: #1a1a1a;
       line-height: 1.5; max-width: 720px; margin: 0 auto; font-size: 11.5pt; }
h1 { font-size: 20pt; line-height: 1.2; margin: 0 0 4px; }
h2 { font-size: 14pt; border-bottom: 1px solid #ccc; padding-bottom: 3px; margin-top: 22px; }
h3 { font-size: 12pt; margin-top: 16px; }
p, li { text-align: justify; }
em { color: #333; }
code { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 10pt;
       background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }
a { color: #0b5cad; text-decoration: none; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10.5pt; }
th, td { border: 1px solid #ccc; padding: 5px 9px; text-align: left; }
th { background: #f0f0f0; }
td:not(:first-child), th:not(:first-child) { text-align: right; }
img { max-width: 100%; display: block; margin: 12px auto; border: 1px solid #ddd; }
blockquote { color: #555; border-left: 3px solid #ccc; padding-left: 12px; }
hr { border: none; border-top: 1px solid #ccc; margin: 20px 0; }
"""


def main():
    with open(os.path.join(HERE, "paper.md")) as f:
        text = f.read()
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    html = (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<style>{CSS}</style></head><body>{body}</body></html>")
    out_html = os.path.join(HERE, "paper.html")
    with open(out_html, "w") as f:
        f.write(html)
    print(f"wrote {out_html}")

    # PDF via headless chromium if available
    try:
        from playwright.sync_api import sync_playwright
        exe = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=exe)
            page = browser.new_page()
            page.goto("file://" + out_html)
            page.pdf(path=os.path.join(HERE, "paper.pdf"),
                     format="A4", print_background=True)
            browser.close()
        print(f"wrote {os.path.join(HERE, 'paper.pdf')}")
    except Exception as exc:
        print(f"(PDF step skipped: {exc}) — open paper.html and print to PDF")


if __name__ == "__main__":
    main()
