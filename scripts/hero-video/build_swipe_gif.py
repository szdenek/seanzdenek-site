from PIL import Image, ImageDraw, ImageFont
import math
import os

FONT_PATH = "/System/Library/Fonts/SFNS.ttf"

def font(size, weight=b"Regular"):
    f = ImageFont.truetype(FONT_PATH, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f

def text_size(draw, text, f):
    bbox = draw.textbbox((0, 0), text, font=f)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def draw_centered(draw, cx, cy, text, f, fill):
    bbox = draw.textbbox((0, 0), text, font=f)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), text, font=f, fill=fill)

def rounded_rect(draw, box, radius, fill=None, outline=None, width=0):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def wrap_lines(text, f, max_width, probe):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        tw, _ = text_size(probe, trial, f)
        if tw <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

# Real Thrum app palette (from components/MovieCard.tsx, CardStack.tsx, lib/tmdb.ts)
W, H = 420, 908
BG = (27, 33, 38, 255)          # #1B2126 app/card background
SCRIM = (10, 14, 17)            # #0A0E11 overlay scrim + text-pill backing
INK = (236, 234, 226, 255)      # #ECEAE2 primary text
INK_SOFT = (184, 190, 185, 255) # #B8BEB9 secondary text (bumped for contrast — was #9BA39E)
AMBER = (240, 169, 78)          # #F0A94E genre chips
LIKE_BORDER = (111, 176, 125)   # #6FB07D
LIKE_BG = (62, 142, 90)         # #3E8E5A
PASS_BORDER = (219, 132, 103)   # #DB8467
PASS_BG = (178, 80, 58)         # #B2503A
LIKE_BTN_BG = (27, 38, 32)      # #1B2620
PASS_BTN_BG = (42, 31, 27)      # #2A1F1B

CARD_W, CARD_H = W, H  # full-bleed, matching the real app's native (non-web) card

def load_cover(path, size):
    """Load a photo and crop/scale it to fill size (like CSS object-fit: cover)."""
    w, h = size
    src = Image.open(path).convert("RGB")
    sw, sh = src.size
    scale = max(w / sw, h / sh)
    rw, rh = round(sw * scale), round(sh * scale)
    src = src.resize((rw, rh), Image.LANCZOS)
    x0 = (rw - w) // 2
    y0 = (rh - h) // 2
    return src.crop((x0, y0, x0 + w, y0 + h))

def render_card(title, year, genres, overview, photo_path):
    """Static card content: full-bleed poster + bottom scrim + title/year pill + genre chips + overview."""
    card = load_cover(photo_path, (CARD_W, CARD_H)).convert("RGBA")

    # Everything below is drawn on a transparent overlay and alpha-composited
    # onto the card, rather than drawn directly with ImageDraw -- PIL's
    # ImageDraw does not alpha-blend fill colors against existing pixels even
    # on an RGBA image with mode="RGBA"; it overwrites RGB and stores the
    # fill's alpha as the pixel's own alpha, which erases the photo under any
    # semi-transparent shape instead of tinting it.
    overlay = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay, "RGBA")

    # Bottom gradient scrim: transparent -> 55% -> 95%, top-to-bottom (MovieCard.tsx:323-326)
    scrim_top = int(CARD_H * 0.40)
    span = max(CARD_H - scrim_top - 1, 1)
    for y in range(scrim_top, CARD_H):
        t = (y - scrim_top) / span
        a = (t / 0.5) * 0.55 if t <= 0.5 else 0.55 + ((t - 0.5) / 0.5) * (0.95 - 0.55)
        od.line((0, y, CARD_W, y), fill=SCRIM + (int(min(a, 0.95) * 255),))

    # Title pill: "Title (Year)" (MovieCard.tsx:337-339, 494-510)
    f_title = font(24, b"Bold")
    f_year = font(17, b"Regular")
    title_text, year_text = title, f"({year})"
    tw, th = text_size(od, title_text, f_title)
    yw, yh = text_size(od, year_text, f_year)
    pad_h, pad_v, gap = 12, 8, 8
    pill_w, pill_h = tw + gap + yw + pad_h * 2, max(th, yh) + pad_v * 2
    pill_x0, pill_y0 = 20, CARD_H - 190
    rounded_rect(od, (pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h), 8, fill=SCRIM + (240,))
    pill_cy = pill_y0 + pill_h / 2
    od.text((pill_x0 + pad_h, pill_cy), title_text, font=f_title, fill=INK, anchor="lm")
    od.text((pill_x0 + pad_h + tw + gap, pill_cy), year_text, font=f_year, fill=INK_SOFT, anchor="lm")

    # Genre chips (MovieCard.tsx:370-378, 578-594) -- amber tint, separate pills
    f_genre = font(15, b"Bold")
    gx, gy = pill_x0, pill_y0 + pill_h + 10
    chip_h = 0
    for g in genres[:2]:
        gw, gh = text_size(od, g, f_genre)
        chip_w, chip_h = gw + 16, gh + 10
        rounded_rect(od, (gx, gy, gx + chip_w, gy + chip_h), 6, fill=SCRIM + (225,), outline=AMBER + (140,), width=1)
        od.text((gx + 8, gy + chip_h / 2), g, font=f_genre, fill=AMBER + (255,), anchor="lm")
        gx += chip_w + 8

    # Overview/synopsis, collapsed to 2 lines with a trailing "more" link
    # (MovieCard.tsx:379-386, 597-612)
    f_body = font(14, b"Regular")
    f_more = font(12, b"Bold")
    max_text_w = CARD_W - pill_x0 * 2 - 20
    lines = wrap_lines(overview, f_body, max_text_w, od)[:2]
    more_w, _ = text_size(od, " more", f_more)
    if len(lines) == 2:
        last_words = lines[1].split()
        while last_words and text_size(od, " ".join(last_words), f_body)[0] + more_w > max_text_w:
            last_words.pop()
        lines[1] = " ".join(last_words).rstrip(",.;: ")
    line_h = text_size(od, "Ag", f_body)[1] + 6
    ov_x0 = pill_x0
    ov_y0 = gy + chip_h + 14
    ov_w = max_text_w + 20
    ov_h = line_h * len(lines) + 20
    rounded_rect(od, (ov_x0, ov_y0, ov_x0 + ov_w, ov_y0 + ov_h), 8, fill=SCRIM + (240,))
    ly = ov_y0 + 10
    for i, line in enumerate(lines):
        od.text((ov_x0 + 10, ly), line, font=f_body, fill=INK_SOFT)
        if i == len(lines) - 1:
            lw, _ = text_size(od, line, f_body)
            od.text((ov_x0 + 10 + lw, ly + 2), " more", font=f_more, fill=AMBER + (255,))
        ly += line_h

    return Image.alpha_composite(card, overlay)

def draw_stamp(canvas, cx, cy, text, border_color, bg_color, alpha, rotation):
    """LIKE/PASS drag badge (MovieCard.tsx:640-681)."""
    f = font(36, b"Heavy")
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    tw, th = text_size(probe, text, f)
    pad_h, pad_v = 20, 14
    bw, bh = tw + pad_h * 2, th + pad_v * 2
    stamp = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp, "RGBA")
    rounded_rect(sd, (0, 0, bw - 1, bh - 1), 12, fill=bg_color + (int(alpha * 0.95),), outline=border_color + (alpha,), width=4)
    draw_centered(sd, bw / 2, bh / 2, text, f, INK[:3] + (alpha,))
    stamp = stamp.rotate(rotation, resample=Image.BICUBIC, expand=True)
    canvas.alpha_composite(stamp, (int(cx - stamp.width / 2), int(cy - stamp.height / 2)))

def decorate_swipe(card, drag_px, direction):
    """Per-frame wash + badge, composited onto a copy of the static card so both
    move and rotate together with it (MovieCard.tsx:260-296, 640-681)."""
    c = card.copy()
    wash_frac = min(1.0, abs(drag_px) / 200) * 0.45
    badge_frac = min(1.0, abs(drag_px) / 100)
    if wash_frac > 0:
        color = LIKE_BG if direction > 0 else PASS_BG
        overlay = Image.new("RGBA", c.size, color + (int(wash_frac * 255),))
        c = Image.alpha_composite(c, overlay)
    if badge_frac > 0:
        alpha = int(badge_frac * 255)
        if direction > 0:
            draw_stamp(c, int(CARD_W * 0.26), int(CARD_H * 0.42), "♥ LIKE", LIKE_BORDER, LIKE_BG, alpha, 12)
        else:
            draw_stamp(c, int(CARD_W * 0.74), int(CARD_H * 0.42), "× PASS", PASS_BORDER, PASS_BG, alpha, -12)
    return c

def draw_action_rail(canvas):
    """Floating like/pass button rail (CardStack.tsx:371-408, 431-541)."""
    cd = ImageDraw.Draw(canvas, "RGBA")
    d = 54
    r = d // 2
    cx = W - 16 - r
    like_cy = int(H * 0.40)
    pass_cy = like_cy + d + 20
    f_icon = font(24, b"Bold")
    cd.ellipse((cx - r, like_cy - r, cx + r, like_cy + r), fill=LIKE_BTN_BG + (255,), outline=LIKE_BORDER + (255,), width=2)
    # textbbox-based draw_centered already centers the glyph's true ink
    # bounds exactly on (cx, cy) — no offset needed for the X, which is
    # symmetric. The heart gets a small downward nudge because its shape
    # tapers to a point at the bottom, so a geometrically-centered heart
    # still reads as sitting high (same fix applied in CardStack.tsx).
    draw_centered(cd, cx, like_cy + 2, "♥", f_icon, INK)
    cd.ellipse((cx - r, pass_cy - r, cx + r, pass_cy + r), fill=PASS_BTN_BG + (255,), outline=PASS_BORDER + (255,), width=2)
    draw_centered(cd, cx, pass_cy, "×", f_icon, INK)

EMOJI_FONT_PATH = "/System/Library/Fonts/Apple Color Emoji.ttc"

def draw_header(canvas):
    """Top bar: partner pill (left) + search/matches/avatar (right) (App.tsx:851-905)."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay, "RGBA")

    # Top scrim for legibility (App.tsx:846-850, headerScrim)
    scrim_h = 110
    for y in range(scrim_h):
        a = 0.6 * (1 - y / scrim_h)
        od.line((0, y, W, y), fill=SCRIM + (int(a * 255),))

    chip_bg = (27, 33, 38, 204)
    chip_border = AMBER + (102,)
    y0, ch = 56, 40
    f_pill = font(13, b"Bold")
    f_matches = font(14, b"Bold")
    f_avatar = font(16, b"Heavy")
    emoji20 = ImageFont.truetype(EMOJI_FONT_PATH, 20)

    # Left: partner pill -- text only, no icon (App.tsx:852-867)
    label = "Paired with Sean"
    lw, lh = text_size(od, label, f_pill)
    pill_w = lw + 28
    rounded_rect(od, (20, y0, 20 + pill_w, y0 + ch), 20, fill=chip_bg, outline=chip_border, width=1)
    draw_centered(od, 20 + pill_w / 2, y0 + ch / 2, label, f_pill, INK)

    # Right, right-to-left: avatar, matches, search (App.tsx:868-904)
    right_x = W - 20
    ax0 = right_x - 40
    od.ellipse((ax0, y0, ax0 + 40, y0 + ch), fill=(27, 33, 38, 255), outline=(10, 14, 17, 217), width=2)
    draw_centered(od, ax0 + 20, y0 + ch / 2, "S", f_avatar, AMBER + (255,))

    match_count = "3"
    mw, mh = text_size(od, match_count, f_matches)
    matches_w = 20 + 6 + mw + 24
    mx0 = ax0 - 10 - matches_w
    rounded_rect(od, (mx0, y0, mx0 + matches_w, y0 + ch), 20, fill=chip_bg, outline=chip_border, width=1)
    od.text((mx0 + 12, y0 + (ch - 20) / 2), "\U0001F3AC", font=emoji20, embedded_color=True)
    od.text((mx0 + 12 + 20 + 6, y0 + (ch - mh) / 2 - 1), match_count, font=f_matches, fill=INK)

    sx0 = mx0 - 10 - 40
    rounded_rect(od, (sx0, y0, sx0 + 40, y0 + ch), 20, fill=chip_bg, outline=chip_border, width=1)
    od.text((sx0 + 10, y0 + (ch - 20) / 2), "\U0001F50D", font=emoji20, embedded_color=True)

    canvas.alpha_composite(overlay)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(SCRIPT_DIR, "photos")
CARD_A = render_card(
    "The Fog", 2026, ["Horror", "Thriller"],
    "After a strange mist rolls in over their small coastal town and refuses to lift, a group of old friends realize it followed something home from the woods.",
    f"{PHOTOS_DIR}/the-fog.jpg",
)
CARD_B = render_card(
    "Pilgrimage", 2025, ["Drama"],
    "An estranged daughter retraces her late mother's final journey through the mountains, one impossible switchback at a time, hoping to understand why she never finished it.",
    f"{PHOTOS_DIR}/pilgrimage.jpg",
)
CARD_C = render_card(
    "Wildflower", 2025, ["Comedy", "Adventure"],
    "Two feuding siblings inherit their grandmother's crumbling farmhouse, along with a very long list of conditions they must complete together before they can sell it.",
    f"{PHOTOS_DIR}/wildflower.jpg",
)

def blank_canvas():
    return Image.new("RGBA", (W, H), BG)

def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_in_cubic(t):
    return t ** 3

def paste_center(base, layer, cx, cy, angle=0):
    if angle:
        layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    lw, lh = layer.size
    base.alpha_composite(layer, (int(cx - lw / 2), int(cy - lh / 2)))

CENTER_X, CENTER_Y = W // 2, H // 2

frames = []
N_IDLE = 4
N_SWIPE = 9
N_SETTLE = 3

def add_idle(card, n=N_IDLE):
    for _ in range(n):
        canvas = blank_canvas()
        paste_center(canvas, card, CENTER_X, CENTER_Y, angle=0)
        draw_action_rail(canvas)
        draw_header(canvas)
        frames.append(canvas.convert("RGB"))

def add_swipe(card, direction, n=N_SWIPE):
    # direction: +1 = right/like, -1 = left/pass
    for i in range(n):
        t = ease_in_cubic((i + 1) / n)
        dx = direction * t * (W * 0.95)
        dy = -t * 12
        angle = -direction * t * 15  # MovieCard.tsx:260-265, up to +/-15deg
        decorated = decorate_swipe(card, dx, direction)
        canvas = blank_canvas()
        paste_center(canvas, decorated, CENTER_X + dx, CENTER_Y + dy, angle=angle)
        draw_action_rail(canvas)
        draw_header(canvas)
        frames.append(canvas.convert("RGB"))

def add_enter(card, n=N_SETTLE):
    for i in range(n):
        t = ease_out_cubic((i + 1) / n)
        canvas = blank_canvas()
        dy = (1 - t) * 60
        scale = 0.94 + 0.06 * t
        c = card.resize((int(CARD_W * scale), int(CARD_H * scale)), Image.LANCZOS)
        paste_center(canvas, c, CENTER_X, CENTER_Y + dy, angle=0)
        draw_action_rail(canvas)
        draw_header(canvas)
        frames.append(canvas.convert("RGB"))

add_idle(CARD_A)
add_swipe(CARD_A, +1)
add_enter(CARD_B)
add_idle(CARD_B, n=3)
add_swipe(CARD_B, -1)
add_enter(CARD_C)
add_idle(CARD_C, n=3)
add_swipe(CARD_C, +1)
add_enter(CARD_A)

frames_dir = os.path.join(SCRIPT_DIR, "video_frames")
os.makedirs(frames_dir, exist_ok=True)
for i, f in enumerate(frames):
    f.convert("RGB").save(os.path.join(frames_dir, f"frame_{i:03d}.png"))
print("saved", len(frames), "PNG frames to", frames_dir)
print("next: ffmpeg -framerate 100/7 -i", os.path.join(frames_dir, "frame_%03d.png"),
      "-c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart out.mp4")

out_path = os.path.join(SCRIPT_DIR, "swipe-demo.gif")

# Shared color palette across every frame -- see prior comment history; per-frame
# adaptive palettes make constant UI chrome (buttons, chips) flicker as the
# photo behind them changes.
sample = Image.new("RGB", (W, H * len(frames)))
for i, f in enumerate(frames):
    sample.paste(f, (0, i * H))
sample = sample.resize((W // 3, (H * len(frames)) // 3), Image.LANCZOS)
shared_palette = sample.quantize(colors=255, method=Image.MEDIANCUT)

quant_frames = [f.quantize(palette=shared_palette, dither=Image.NONE) for f in frames]

quant_frames[0].save(
    out_path,
    save_all=True,
    append_images=quant_frames[1:],
    duration=70,
    loop=0,
    disposal=2,
)
print("saved", out_path, "frames:", len(frames))
