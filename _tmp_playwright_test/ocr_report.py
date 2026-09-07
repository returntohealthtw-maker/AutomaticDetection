# -*- coding: utf-8 -*-
"""OCR 兒童報告測試 PDF，輸出逐頁文字供人工檢視。"""
import sys
import fitz
import pytesseract
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

PDF_PATH = r'D:\Write program\AutomaticDetection\_tmp_playwright_test\downloads\test_child_report.pdf'
OUT_PATH = r'D:\Write program\AutomaticDetection\_tmp_playwright_test\downloads\ocr_output.txt'

def main():
    doc = fitz.open(PDF_PATH)
    n = doc.page_count
    print(f'total pages: {n}', flush=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as out:
        for i in range(n):
            page = doc[i]
            pix = page.get_pixmap(dpi=180)
            img = Image.open(io.BytesIO(pix.tobytes('png')))
            text = pytesseract.image_to_string(img, lang='chi_tra+eng')
            out.write(f'\n===== PAGE {i+1} =====\n')
            out.write(text)
            print(f'page {i+1}/{n} done, chars={len(text)}', flush=True)
    print('DONE')

if __name__ == '__main__':
    main()
