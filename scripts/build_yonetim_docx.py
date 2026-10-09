"""Build YONETIM_OZETI.docx from YONETIM_OZETI.md (format conversion only).

Usage: python scripts/build_yonetim_docx.py [--convert-svg]
Requires python-docx. --convert-svg renders figures/*.svg to figures/png/*.png
with headless Edge/Chrome (optional; committed PNGs are used otherwise).
"""
import re
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "docs" / "paper" / "results" / "week-2026-10-05-fleet"
MD = DIR / "YONETIM_OZETI.md"
OUT = DIR / "YONETIM_OZETI.docx"
PNG = DIR / "figures" / "png"

# (png name, svg size, caption, insert AFTER the block that starts with heading text)
FIGURES = {
    "pareto_front_combined": ((1010, 700), "Şekil 1. Pareto seçenekleri (tüm yolculuk süresi sınırları, birleşik)."),
    "pareto_borrowed_heatmap_R60": ((784, 854), "Şekil 2. Saat ve güne göre ödünç araç talebi (60 dakika sınırı)."),
}
# figure inserted before this heading / after this table-end marker
FIG1_BEFORE_LINE = "Tablodaki seçeneklerin hepsi"          # after key-options table
FIG2_BEFORE_HEADING = "Dikkat edilmesi gerekenler"          # after borrowing section


def convert_svgs():
    edge = next((p for p in [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"] if Path(p).exists()), None)
    if not edge:
        sys.exit("No Edge/Chrome found")
    PNG.mkdir(parents=True, exist_ok=True)
    for name, ((w, h), _) in FIGURES.items():
        subprocess.run([edge, "--headless", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={PNG / (name + '.png')}",
                        (DIR / "figures" / (name + ".svg")).as_uri()], check=True)


def add_runs(p, text):
    for part in re.split(r"(\*\*.+?\*\*|`.+?`)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            p.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            r = p.add_run(part[1:-1])
            r.font.name = "Consolas"
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        else:
            p.add_run(part)


def add_table(doc, rows):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, cell_text in enumerate(row):
            c = t.cell(i, j)
            p = c.paragraphs[0]
            add_runs(p, cell_text)
            for r in p.runs:
                r.font.size = Pt(9.5)
                if i == 0:
                    r.bold = True
            if i == 0:
                tcPr = c._tc.get_or_add_tcPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "D9E2F3")
                tcPr.append(shd)
    trPr = t.rows[0]._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)
    doc.add_paragraph()


def add_figure(doc, name):
    (w, h), caption = FIGURES[name]
    width = Cm(16.0)
    if h / w > 1:  # tall figure: limit height
        width = Cm(15.0 * w / h)
    doc.add_picture(str(PNG / (name + ".png")), width=width)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.keep_with_next = True
    cap = doc.add_paragraph(caption)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in cap.runs:
        r.italic = True; r.font.size = Pt(9.5)


def page_number_footer(doc):
    p = doc.sections[0].footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), kind)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = text
        run._r.append(e)


def main():
    if "--convert-svg" in sys.argv:
        convert_svgs()
    doc = Document()
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.5)
    st = doc.styles["Normal"]
    st.font.name = "Calibri"; st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    for name in ("Title", "Heading 1", "Heading 2"):
        doc.styles[name].font.name = "Calibri"
    page_number_footer(doc)

    lines = MD.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## ") and line[3:].strip() == FIG2_BEFORE_HEADING:
            add_figure(doc, "pareto_borrowed_heatmap_R60")
        if line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            add_table(doc, rows)
            continue
        elif line.startswith("- "):
            add_runs(doc.add_paragraph(style="List Bullet"), line[2:])
        elif re.match(r"\d+\. ", line):
            add_runs(doc.add_paragraph(style="List Number"), re.sub(r"^\d+\. ", "", line))
        elif line.strip():
            if line.startswith(FIG1_BEFORE_LINE):
                add_figure(doc, "pareto_front_combined")
            add_runs(doc.add_paragraph(), line)
        i += 1
    doc.save(OUT)
    print("wrote", OUT.name)


if __name__ == "__main__":
    main()
