from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SIZE = 256


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def centered_text(draw: ImageDraw.ImageDraw, center: tuple[int, int], text: str, text_font, fill: str) -> None:
    box = draw.textbbox((0, 0), text, font=text_font)
    width = box[2] - box[0]
    height = box[3] - box[1]
    draw.text((center[0] - width / 2, center[1] - height / 2 - box[1]), text, font=text_font, fill=fill)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    for y in range(SIZE):
        ratio = y / (SIZE - 1)
        color = tuple(round(start + (end - start) * ratio) for start, end in zip((23, 54, 93), (47, 117, 181)))
        draw.line((0, y, SIZE, y), fill=(*color, 255))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=54, fill=255)
    image.putalpha(mask)
    draw = ImageDraw.Draw(image)

    draw.ellipse((32, 78, 132, 178), fill="#EAF4FC")
    draw.ellipse((128, 78, 228, 178), fill="#D5EDFA")
    draw.line((111, 128, 143, 128), fill="#2F75B5", width=11)
    draw.line((130, 115, 143, 128, 130, 141), fill="#2F75B5", width=11, joint="curve")
    centered_text(draw, (82, 128), "MP", font(34), "#17365D")
    centered_text(draw, (181, 128), "C", font(43), "#17365D")

    png_path = ASSETS / "app-icon.png"
    ico_path = ASSETS / "app-icon.ico"
    image.save(png_path)
    image.save(ico_path, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)])


if __name__ == "__main__":
    main()
