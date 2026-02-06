"""
Generate PWA icons for Social Contract app.
Creates PNG icons at all required sizes from a canvas-drawn design.
Run once: python generate_icons.py
Requires: pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

ICON_DIR = os.path.join(os.path.dirname(__file__), 'static', 'icons')
os.makedirs(ICON_DIR, exist_ok=True)

# Standard PWA sizes
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
MASKABLE_SIZES = [192, 512]

# Colors matching the app theme
BG_COLOR = (8, 9, 10)         # --bg-base: #08090a
ACCENT = (16, 185, 129)       # --accent: #10b981
WHITE = (244, 244, 245)       # --text-primary: #f4f4f5


def draw_icon(size, maskable=False):
    """Draw the Social Contract icon — crossed swords emblem."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if maskable:
        # Maskable icons need full bleed background with safe zone (80% center)
        draw.rectangle([0, 0, size, size], fill=BG_COLOR)
        # Content inside 80% safe zone
        padding = int(size * 0.1)
    else:
        # Regular icon — rounded rectangle background
        draw.rounded_rectangle(
            [0, 0, size - 1, size - 1],
            radius=int(size * 0.2),
            fill=BG_COLOR
        )
        padding = int(size * 0.15)

    inner = size - padding * 2
    cx = size // 2
    cy = size // 2

    # Draw a shield shape
    shield_w = int(inner * 0.6)
    shield_h = int(inner * 0.72)
    shield_top = cy - int(shield_h * 0.45)
    shield_left = cx - shield_w // 2
    shield_right = cx + shield_w // 2
    shield_mid_y = shield_top + int(shield_h * 0.45)
    shield_bottom = shield_top + shield_h

    # Shield outline
    outline_w = max(2, int(size * 0.035))

    # Draw shield body (top rectangle + bottom triangle)
    shield_points = [
        (shield_left, shield_top),
        (shield_right, shield_top),
        (shield_right, shield_mid_y),
        (cx, shield_bottom),
        (shield_left, shield_mid_y),
    ]
    draw.polygon(shield_points, fill=ACCENT)

    # Inner shield (darker)
    inset = max(2, int(size * 0.04))
    inner_points = [
        (shield_left + inset, shield_top + inset),
        (shield_right - inset, shield_top + inset),
        (shield_right - inset, shield_mid_y - inset // 2),
        (cx, shield_bottom - int(inset * 1.8)),
        (shield_left + inset, shield_mid_y - inset // 2),
    ]
    draw.polygon(inner_points, fill=BG_COLOR)

    # Checkmark inside shield
    check_size = int(inner * 0.22)
    check_x = cx
    check_y = cy + int(inner * 0.02)
    check_w = max(2, int(size * 0.04))

    # Checkmark: short left stroke + long right stroke
    draw.line(
        [(check_x - check_size // 2, check_y),
         (check_x - check_size // 6, check_y + check_size // 2)],
        fill=ACCENT, width=check_w
    )
    draw.line(
        [(check_x - check_size // 6, check_y + check_size // 2),
         (check_x + check_size // 2, check_y - check_size // 3)],
        fill=ACCENT, width=check_w
    )

    # "SC" text at bottom (only for larger icons)
    if size >= 128:
        try:
            font_size = max(10, int(size * 0.08))
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

    return img


def main():
    # Generate regular icons
    for size in SIZES:
        icon = draw_icon(size, maskable=False)
        path = os.path.join(ICON_DIR, f'icon-{size}.png')
        icon.save(path, 'PNG', optimize=True)
        print(f'Created {path} ({size}x{size})')

    # Generate maskable icons
    for size in MASKABLE_SIZES:
        icon = draw_icon(size, maskable=True)
        path = os.path.join(ICON_DIR, f'icon-maskable-{size}.png')
        icon.save(path, 'PNG', optimize=True)
        print(f'Created {path} ({size}x{size} maskable)')

    # Generate apple-touch-icon (180x180)
    apple = draw_icon(180, maskable=False)
    apple_path = os.path.join(ICON_DIR, 'apple-touch-icon.png')
    apple.save(apple_path, 'PNG', optimize=True)
    print(f'Created {apple_path} (180x180 apple-touch-icon)')

    # Generate favicon (32x32)
    fav = draw_icon(32, maskable=False)
    fav_path = os.path.join(ICON_DIR, 'favicon-32.png')
    fav.save(fav_path, 'PNG', optimize=True)
    print(f'Created {fav_path} (32x32 favicon)')

    # Generate 16x16 favicon
    fav16 = draw_icon(16, maskable=False)
    fav16_path = os.path.join(ICON_DIR, 'favicon-16.png')
    fav16.save(fav16_path, 'PNG', optimize=True)
    print(f'Created {fav16_path} (16x16 favicon)')

    print('\nAll icons generated! You can now delete generate_icons.py if desired.')


if __name__ == '__main__':
    main()
