from PIL import Image, ImageDraw, ImageFont

PXW, PXH = 1240, 1754
cover = Image.open(r"D:\Write program\_teen_build\BrianaveReportImage_Teen\public\xin-cover.png").convert("RGB")
canvas = cover.resize((PXW, PXH))
draw = ImageDraw.Draw(canvas)

FILL_X = PXW * 0.5605
NAME_Y = PXH * 0.9023 - 3   # this is the alphabetic baseline in JS canvas terms

font = ImageFont.truetype(r"C:\Windows\Fonts\msjhbd.ttc", 32)
name = "鄭佳睿"

# PIL draw.text with anchor='ms' places text at (x, baseline) centered horizontally,
# matching canvas textAlign='center', textBaseline='alphabetic'
draw.text((FILL_X, NAME_Y), name, font=font, fill=(29, 78, 216), anchor="ms")

canvas.save(r"D:\Write program\AutomaticDetection\_tmp_playwright_test\cover_test_result.png")
print("saved")
