import fitz
import pytesseract
from PIL import Image
import io
import sys

rid = sys.argv[1] if len(sys.argv) > 1 else "172"
doc = fitz.open(f"_tmp_child_{rid}.pdf")
out_lines = []
for i in range(doc.page_count):
    pg = doc.load_page(i)
    pix = pg.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img, lang="chi_tra")
    out_lines.append(f"\n===== PAGE {i+1} =====\n{text.strip()}\n")
    print(f"page {i+1}/{doc.page_count} done", flush=True)

with open(f"_tmp_child_{rid}_ocr.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
print("DONE")
