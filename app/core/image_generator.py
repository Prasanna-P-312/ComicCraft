"""
Fully rewritten image_generator.py
Primary: HuggingFace Inference API (Stable Diffusion runwayml/stable-diffusion-v1-5)
Fallback: Sophisticated Pillow-based comic panel renderer that is PROMPT-AWARE.
"""
import os
import re
import math
import random
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple, List

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.config import settings

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# COLOUR / KEYWORD MAPS
# ────────────────────────────────────────────────────────────────
SETTING_PALETTES = {
    "forest":        [(15, 40, 15), (30, 80, 30), (60, 130, 60), (160, 200, 100)],
    "enchanted":     [(20, 10, 50), (80, 30, 140), (160, 90, 220), (255, 200, 100)],
    "space":         [(5, 5, 20), (10, 10, 50), (30, 0, 80), (80, 40, 160)],
    "city":          [(20, 20, 35), (40, 40, 70), (80, 80, 120), (200, 180, 100)],
    "cyberpunk":     [(10, 5, 30), (40, 0, 80), (0, 180, 180), (255, 0, 100)],
    "neon":          [(5, 5, 20), (20, 0, 60), (0, 200, 255), (255, 50, 150)],
    "ocean":         [(0, 20, 50), (0, 60, 120), (0, 140, 200), (100, 220, 255)],
    "underwater":    [(0, 15, 45), (0, 50, 100), (20, 120, 180), (100, 200, 230)],
    "desert":        [(60, 35, 10), (120, 80, 20), (200, 150, 60), (240, 210, 140)],
    "ruins":         [(30, 25, 20), (70, 60, 45), (130, 110, 80), (200, 180, 140)],
    "castle":        [(30, 28, 35), (70, 65, 80), (130, 120, 150), (210, 200, 220)],
    "school":        [(40, 60, 30), (80, 120, 60), (160, 180, 120), (230, 240, 200)],
    "dungeon":       [(15, 10, 5), (40, 30, 15), (80, 60, 30), (140, 110, 60)],
    "sky":           [(40, 80, 180), (80, 140, 220), (160, 200, 240), (255, 240, 200)],
    "volcano":       [(60, 10, 5), (140, 30, 10), (220, 80, 20), (255, 160, 50)],
    "snow":          [(60, 80, 120), (120, 150, 180), (200, 215, 240), (255, 255, 255)],
    "jungle":        [(10, 35, 5), (20, 70, 15), (40, 120, 30), (100, 180, 60)],
    "default":       [(20, 30, 60), (50, 80, 130), (120, 150, 200), (220, 200, 160)],
}

TONE_PALETTES = {
    "dramatic":     [(15, 10, 25), (60, 20, 80), (160, 40, 50), (240, 180, 50)],
    "funny":        [(240, 200, 40), (80, 200, 80), (40, 160, 240), (255, 120, 40)],
    "light-hearted":[(200, 230, 180), (140, 210, 150), (80, 180, 120), (40, 140, 90)],
    "poetic":       [(60, 40, 100), (120, 80, 160), (200, 160, 220), (255, 230, 240)],
    "action-packed":[(200, 30, 20), (240, 100, 20), (255, 200, 20), (50, 50, 60)],
    "whimsical":    [(255, 180, 200), (200, 150, 240), (150, 210, 255), (255, 240, 150)],
    "mysterious":   [(10, 10, 30), (40, 30, 70), (100, 80, 140), (200, 170, 210)],
    "default":      [(20, 30, 60), (50, 80, 130), (120, 150, 200), (220, 200, 160)],
}

ART_STYLE_EFFECTS = {
    "Comic Book":   {"line_width": 3, "halftone": True,  "sharp": True,  "saturate": 1.4},
    "Anime":        {"line_width": 2, "halftone": False, "sharp": True,  "saturate": 1.6},
    "Pixel Art":    {"line_width": 1, "halftone": False, "sharp": False, "saturate": 1.2},
    "Realistic":    {"line_width": 1, "halftone": False, "sharp": True,  "saturate": 0.9},
    "Watercolor":   {"line_width": 1, "halftone": False, "sharp": False, "saturate": 1.1},
    "default":      {"line_width": 2, "halftone": True,  "sharp": True,  "saturate": 1.3},
}

# Subject/entity icons drawn using simple shapes
SUBJECT_RENDERERS = {
    "fox":      "animal_fox",
    "wolf":     "animal_wolf",
    "dragon":   "creature_dragon",
    "robot":    "machine_robot",
    "warrior":  "human_warrior",
    "detective":"human_detective",
    "wizard":   "human_wizard",
    "sorceress":"human_wizard",
    "knight":   "human_warrior",
    "pilot":    "human_pilot",
    "ship":     "vehicle_ship",
    "spaceship":"vehicle_spaceship",
    "castle":   "structure_castle",
    "tower":    "structure_tower",
    "house":    "structure_house",
    "tree":     "nature_tree",
    "star":     "nature_star",
    "moon":     "nature_moon",
    "sun":      "nature_sun",
    "ocean":    "nature_ocean",
    "default":  "human_hero",
}


def _sanitize_filename(text: str, max_len: int = 40) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_len] if cleaned else "panel"


def _detect_palette_key(prompt: str, setting: str = "", art_style: str = "") -> Tuple[List, List]:
    """Detect setting and tone palettes from prompt/setting text."""
    combined = (prompt + " " + setting).lower()
    
    setting_pal = SETTING_PALETTES["default"]
    for key, pal in SETTING_PALETTES.items():
        if key in combined:
            setting_pal = pal
            break

    # detect art-style override for tone
    tone_pal = TONE_PALETTES["default"]
    combined_lower = prompt.lower()
    for key, pal in TONE_PALETTES.items():
        if key in combined_lower:
            tone_pal = pal
            break

    return setting_pal, tone_pal


def _detect_subject(prompt: str) -> str:
    """Detect primary subject type from prompt."""
    pl = prompt.lower()
    for key in SUBJECT_RENDERERS:
        if key in pl:
            return SUBJECT_RENDERERS[key]
    return SUBJECT_RENDERERS["default"]


def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))


def _draw_gradient_bg(draw, width, height, colors):
    """Draw a multi-stop vertical gradient."""
    segments = len(colors) - 1
    for y in range(height):
        frac = y / height
        seg = min(int(frac * segments), segments - 1)
        local_t = (frac * segments) - seg
        c = _lerp_color(colors[seg], colors[seg + 1], local_t)
        draw.line([(0, y), (width, y)], fill=c)


def _draw_stars(draw, width, height, seed=42):
    rng = random.Random(seed)
    for _ in range(120):
        x = rng.randint(0, width)
        y = rng.randint(0, int(height * 0.6))
        r = rng.choice([1, 1, 1, 2])
        brightness = rng.randint(180, 255)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(brightness, brightness, brightness))


def _draw_halftone(draw, width, height, color=(255, 255, 255), alpha_factor=0.08):
    for dx in range(10, width, 20):
        for dy in range(10, int(height * 0.7), 20):
            r = 2
            c = tuple(int(cc * 0.3 + 255 * 0.7) for cc in color[:3])
            draw.ellipse([dx - r, dy - r, dx + r, dy + r], fill=c)


def _draw_speedlines(draw, cx, cy, count, width, height, color=(255,255,255), alpha=60):
    for i in range(count):
        angle = math.radians(i * (360 / count))
        x2 = cx + int(math.cos(angle) * max(width, height))
        y2 = cy + int(math.sin(angle) * max(width, height))
        draw.line([(cx, cy), (x2, y2)], fill=color + (alpha,), width=1)


def _draw_mountains(draw, width, height, colors, rng):
    """Draw stylised terrain silhouettes."""
    layers = [
        {"y_start": 0.55, "points_count": 8, "color": colors[0]},
        {"y_start": 0.65, "points_count": 6, "color": colors[1] if len(colors) > 1 else colors[0]},
        {"y_start": 0.75, "points_count": 4, "color": colors[2] if len(colors) > 2 else colors[0]},
    ]
    for layer in layers:
        base_y = int(height * layer["y_start"])
        pts = [(0, height)]
        step = width // (layer["points_count"] - 1)
        for i in range(layer["points_count"]):
            x = i * step
            y = base_y - rng.randint(int(height * 0.05), int(height * 0.22))
            pts.append((x, y))
        pts.append((width, height))
        draw.polygon(pts, fill=layer["color"])


def _draw_cityscape(draw, width, height, colors, rng):
    """Draw a simple city skyline."""
    base_y = int(height * 0.6)
    for _ in range(rng.randint(10, 18)):
        bw = rng.randint(20, 50)
        bh = rng.randint(int(height * 0.15), int(height * 0.45))
        bx = rng.randint(0, width - bw)
        col = colors[rng.randint(0, len(colors) - 1)]
        draw.rectangle([bx, base_y - bh, bx + bw, height], fill=col)
        # windows
        for wy in range(base_y - bh + 5, base_y - 5, 12):
            for wx in range(bx + 3, bx + bw - 3, 8):
                if rng.random() > 0.4:
                    draw.rectangle([wx, wy, wx + 4, wy + 6], fill=(255, 240, 150))


def _draw_forest_trees(draw, width, height, colors, rng):
    """Draw forest tree line."""
    for _ in range(rng.randint(8, 15)):
        tx = rng.randint(-20, width + 20)
        th = rng.randint(int(height * 0.25), int(height * 0.5))
        ty = height - th
        trunk_w = rng.randint(8, 18)
        trunk_col = _lerp_color(colors[0], (60, 35, 10), 0.5)
        draw.rectangle([tx - trunk_w // 2, ty + th // 2, tx + trunk_w // 2, height], fill=trunk_col)
        for layer in range(3):
            lw = rng.randint(int(height * 0.08), int(height * 0.18)) - layer * 10
            lh = rng.randint(int(height * 0.12), int(height * 0.25)) - layer * 8
            ly = ty + layer * int(th * 0.15)
            col = colors[min(layer, len(colors) - 1)]
            col = _lerp_color(col, (20, 100, 20), 0.3)
            draw.ellipse([tx - lw, ly, tx + lw, ly + lh * 2], fill=col)


def _draw_hero(draw, cx, base_y, art_style, rng, cape_color=(180, 20, 30), body_color=(10, 10, 20)):
    """Draw a stylized standing hero figure."""
    # Cape / aura
    draw.polygon([
        (cx - 30, base_y - 80), (cx - 55, base_y - 5),
        (cx + 55, base_y - 5), (cx + 30, base_y - 80),
    ], fill=cape_color)
    # Body
    draw.rectangle([cx - 18, base_y - 95, cx + 18, base_y - 15], fill=body_color)
    # Head
    draw.ellipse([cx - 15, base_y - 128, cx + 15, base_y - 98], fill=body_color)
    # Eyes
    draw.ellipse([cx - 8, base_y - 120, cx - 4, base_y - 115], fill=(255, 220, 50))
    draw.ellipse([cx + 4, base_y - 120, cx + 8, base_y - 115], fill=(255, 220, 50))
    # Legs
    draw.rectangle([cx - 16, base_y - 15, cx - 3, base_y], fill=body_color)
    draw.rectangle([cx + 3, base_y - 15, cx + 16, base_y], fill=body_color)


def _draw_robot(draw, cx, base_y, art_style, rng):
    """Draw a robot figure."""
    col = (80, 130, 160)
    # Torso
    draw.rectangle([cx - 22, base_y - 90, cx + 22, base_y - 35], fill=col)
    # Head
    draw.rectangle([cx - 18, base_y - 120, cx + 18, base_y - 95], fill=(100, 155, 185))
    # Eyes
    draw.ellipse([cx - 12, base_y - 115, cx - 4, base_y - 107], fill=(0, 255, 200))
    draw.ellipse([cx + 4, base_y - 115, cx + 12, base_y - 107], fill=(0, 255, 200))
    # Arms
    draw.rectangle([cx - 34, base_y - 88, cx - 22, base_y - 50], fill=(70, 110, 140))
    draw.rectangle([cx + 22, base_y - 88, cx + 34, base_y - 50], fill=(70, 110, 140))
    # Legs
    draw.rectangle([cx - 18, base_y - 35, cx - 5, base_y], fill=(70, 110, 140))
    draw.rectangle([cx + 5, base_y - 35, cx + 18, base_y], fill=(70, 110, 140))
    # Panel lights
    for li in range(3):
        draw.ellipse([cx - 10 + li * 8, base_y - 70, cx - 5 + li * 8, base_y - 65],
                     fill=(255, 100 + li * 50, 50))


def _draw_dragon(draw, cx, base_y, art_style, rng):
    """Draw a dragon silhouette."""
    col = (120, 30, 20)
    # Body
    draw.ellipse([cx - 40, base_y - 70, cx + 40, base_y - 20], fill=col)
    # Neck
    draw.polygon([(cx - 10, base_y - 65), (cx + 10, base_y - 65), (cx + 5, base_y - 105), (cx - 5, base_y - 105)], fill=(140, 35, 25))
    # Head
    draw.ellipse([cx - 18, base_y - 125, cx + 18, base_y - 105], fill=(150, 40, 30))
    # Eye
    draw.ellipse([cx + 5, base_y - 120, cx + 14, base_y - 112], fill=(255, 200, 0))
    # Wings
    draw.polygon([(cx, base_y - 55), (cx - 90, base_y - 85), (cx - 50, base_y - 30)], fill=(100, 20, 15))
    draw.polygon([(cx, base_y - 55), (cx + 90, base_y - 85), (cx + 50, base_y - 30)], fill=(100, 20, 15))
    # Fire breath
    for fi in range(5):
        fx = cx + 15 + fi * 15
        fy_top = base_y - 118 + fi * 4
        fy_bot = base_y - 110 + fi * 3
        draw.polygon([(cx + 15, base_y - 114), (fx, fy_top), (fx, fy_bot)], fill=(255, 140 - fi * 20, 0))


def _draw_fox(draw, cx, base_y, art_style, rng):
    """Draw a stylised fox."""
    col = (220, 100, 30)
    # Body
    draw.ellipse([cx - 25, base_y - 55, cx + 25, base_y - 10], fill=col)
    # Head
    draw.ellipse([cx - 18, base_y - 85, cx + 18, base_y - 55], fill=col)
    # Ears
    draw.polygon([(cx - 18, base_y - 80), (cx - 30, base_y - 110), (cx - 5, base_y - 82)], fill=col)
    draw.polygon([(cx + 5, base_y - 82), (cx + 30, base_y - 110), (cx + 18, base_y - 80)], fill=col)
    # Inner ear
    draw.polygon([(cx - 16, base_y - 82), (cx - 26, base_y - 105), (cx - 7, base_y - 84)], fill=(240, 160, 140))
    draw.polygon([(cx + 7, base_y - 84), (cx + 26, base_y - 105), (cx + 16, base_y - 82)], fill=(240, 160, 140))
    # Eyes
    draw.ellipse([cx - 10, base_y - 78, cx - 4, base_y - 72], fill=(50, 30, 10))
    draw.ellipse([cx + 4, base_y - 78, cx + 10, base_y - 72], fill=(50, 30, 10))
    # Snout
    draw.ellipse([cx - 6, base_y - 68, cx + 6, base_y - 60], fill=(240, 170, 140))
    draw.ellipse([cx - 3, base_y - 66, cx + 3, base_y - 63], fill=(60, 30, 20))
    # Tail
    draw.polygon([(cx + 20, base_y - 20), (cx + 60, base_y - 40), (cx + 55, base_y - 10), (cx + 15, base_y)], fill=col)
    draw.polygon([(cx + 40, base_y - 15), (cx + 58, base_y - 8)], fill=(255, 240, 220))
    # Legs
    draw.rectangle([cx - 18, base_y - 10, cx - 8, base_y], fill=(200, 80, 20))
    draw.rectangle([cx + 8, base_y - 10, cx + 18, base_y], fill=(200, 80, 20))


def _draw_spaceship(draw, cx, base_y, art_style, rng):
    col = (130, 150, 180)
    # Body
    draw.ellipse([cx - 40, base_y - 80, cx + 40, base_y - 20], fill=col)
    # Cockpit
    draw.ellipse([cx - 18, base_y - 70, cx + 18, base_y - 40], fill=(100, 200, 240))
    # Wings
    draw.polygon([(cx - 38, base_y - 50), (cx - 70, base_y - 15), (cx - 20, base_y - 20)], fill=(100, 120, 150))
    draw.polygon([(cx + 38, base_y - 50), (cx + 70, base_y - 15), (cx + 20, base_y - 20)], fill=(100, 120, 150))
    # Engine glow
    for j in range(3):
        draw.ellipse([cx - 8 + j * 8, base_y - 22, cx - 2 + j * 8, base_y - 16], fill=(0, 200 - j * 40, 255))


def _draw_moon_and_stars(draw, width, height, rng, colors):
    # Moon
    mx, my = int(width * 0.8), int(height * 0.15)
    draw.ellipse([mx - 30, my - 30, mx + 30, my + 30], fill=(240, 230, 200))
    draw.ellipse([mx + 10, my - 22, mx + 45, my + 13], fill=colors[0])  # Crescent shadow
    _draw_stars(draw, width, height, rng.randint(0, 9999))


def _draw_sun_and_rays(draw, cx, cy, rng, color=(255, 230, 80)):
    draw.ellipse([cx - 45, cy - 45, cx + 45, cy + 45], fill=color)
    for ri in range(12):
        angle = math.radians(ri * 30)
        x2 = cx + int(math.cos(angle) * 75)
        y2 = cy + int(math.sin(angle) * 75)
        draw.line([(cx + int(math.cos(angle) * 48), cy + int(math.sin(angle) * 48)), (x2, y2)],
                  fill=(255, 200, 50), width=3)


def _detect_environment(prompt: str) -> str:
    pl = prompt.lower()
    env_keywords = [
        ("space", ["space", "galaxy", "star", "cosmos", "void", "nebula", "planet", "orbit"]),
        ("cyberpunk", ["cyber", "neon", "hack", "glitch", "matrix", "chrome", "wired"]),
        ("city", ["city", "alley", "street", "building", "urban", "metro", "skyscraper"]),
        ("forest", ["forest", "wood", "tree", "grove", "jungle", "woods", "enchanted"]),
        ("ocean", ["ocean", "sea", "wave", "underwater", "depths", "aqua", "marine"]),
        ("desert", ["desert", "sand", "dune", "arid", "wasteland", "oasis"]),
        ("ruins", ["ruins", "ancient", "ruin", "crumble", "temple", "pyramid", "dungeon"]),
        ("castle", ["castle", "fortress", "citadel", "palace", "throne", "kingdom"]),
        ("sky", ["sky", "cloud", "aerial", "flight", "heaven", "flying"]),
        ("snow", ["snow", "ice", "arctic", "frozen", "winter", "tundra", "blizzard"]),
        ("volcano", ["volcano", "lava", "magma", "eruption", "molten", "fire"]),
    ]
    for env, kws in env_keywords:
        if any(kw in pl for kw in kws):
            return env
    return "default"


def _draw_comic_canvas(prompt: str, art_style: str, panel_num: Optional[int] = None,
                       width: int = 512, height: int = 512) -> Image.Image:
    """
    Draws a rich, prompt-aware comic panel illustration using Pillow.
    The environment, subject, mood, and color palette are all derived from the prompt.
    """
    rng = random.Random(hashlib.md5(f"{prompt}{panel_num}".encode()).hexdigest())

    img = Image.new("RGB", (width, height), (10, 10, 25))
    draw = ImageDraw.Draw(img)

    environment = _detect_environment(prompt)
    subject_type = _detect_subject(prompt)
    setting_colors, tone_colors = _detect_palette_key(prompt)

    # ── 1. Background gradient ──────────────────────────────────
    bg_colors = SETTING_PALETTES.get(environment, SETTING_PALETTES["default"])
    _draw_gradient_bg(draw, width, height, bg_colors)

    # ── 2. Atmospheric elements based on environment ─────────────
    if environment == "space":
        _draw_stars(draw, width, height, rng.randint(0, 99999))
        _draw_moon_and_stars(draw, width, height, rng, bg_colors)
    elif environment in ("sky", "castle", "ruins"):
        # clouds
        for _ in range(rng.randint(4, 8)):
            cx = rng.randint(0, width)
            cy = rng.randint(20, int(height * 0.4))
            cw = rng.randint(40, 100)
            cc = _lerp_color(bg_colors[-1], (255, 255, 255), 0.6)
            draw.ellipse([cx - cw, cy - 20, cx + cw, cy + 20], fill=cc)
            draw.ellipse([cx - cw + 15, cy - 30, cx + cw - 15, cy + 10], fill=cc)
        _draw_sun_and_rays(draw, int(width * 0.75), int(height * 0.18), rng)
    elif environment in ("city", "cyberpunk"):
        _draw_cityscape(draw, width, height, bg_colors, rng)
        if environment == "cyberpunk":
            for _ in range(20):
                sx = rng.randint(0, width)
                sy = rng.randint(0, height)
                sr = rng.randint(2, 6)
                sc = rng.choice([(0, 255, 255), (255, 0, 128), (128, 0, 255), (0, 200, 255)])
                draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=sc)
    elif environment in ("forest", "jungle", "enchanted"):
        _draw_forest_trees(draw, width, height, bg_colors, rng)
        # Mystical glow for enchanted
        if "enchanted" in prompt.lower() or "magic" in prompt.lower():
            for _ in range(15):
                gx = rng.randint(0, width)
                gy = rng.randint(int(height * 0.3), int(height * 0.8))
                gr = rng.randint(4, 12)
                gc = rng.choice([(180, 100, 255), (100, 255, 180), (255, 200, 80)])
                draw.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=gc)
        _draw_sun_and_rays(draw, int(width * 0.8), int(height * 0.15), rng, color=(255, 220, 100))
    elif environment in ("ocean", "underwater"):
        # waves
        for wy in range(int(height * 0.5), height, 20):
            wc = _lerp_color(bg_colors[1], bg_colors[-1], (wy - height * 0.5) / (height * 0.5))
            wave_pts = [(x, wy + int(12 * math.sin(x / 30.0 + panel_num or 1))) for x in range(0, width + 1, 2)]
            draw.polygon([(0, height)] + wave_pts + [(width, height)], fill=wc)
        # Bubbles
        for _ in range(30):
            bx = rng.randint(0, width)
            by = rng.randint(0, height)
            br = rng.randint(3, 10)
            draw.ellipse([bx - br, by - br, bx + br, by + br], outline=(150, 220, 255), width=1)
    elif environment in ("desert",):
        # Dunes
        for dy in range(int(height * 0.5), height, 30):
            dc = _lerp_color(bg_colors[1], bg_colors[2], (dy - height * 0.5) / (height * 0.5))
            dune_pts = [(x, dy + int(20 * math.sin(x / 60.0))) for x in range(0, width + 1, 4)]
            draw.polygon([(0, height)] + dune_pts + [(width, height)], fill=dc)
        _draw_sun_and_rays(draw, int(width * 0.7), int(height * 0.2), rng, color=(255, 210, 60))
    elif environment in ("ruins", "dungeon"):
        # Stone blocks
        for by in range(int(height * 0.6), height, 40):
            for bx in range(0, width, 50 + rng.randint(-10, 10)):
                bw = rng.randint(35, 60)
                bh = rng.randint(20, 35)
                bc = _lerp_color(bg_colors[1], bg_colors[2], rng.random())
                draw.rectangle([bx, by, bx + bw, by + bh], fill=bc, outline=(0, 0, 0), width=1)
    elif environment in ("snow",):
        _draw_mountains(draw, width, height, [(200, 210, 230), (220, 225, 245), (240, 242, 255)], rng)
        _draw_stars(draw, width, height, rng.randint(0, 9999))
        _draw_moon_and_stars(draw, width, height, rng, bg_colors)
        # Snowflakes
        for _ in range(40):
            sx = rng.randint(0, width)
            sy = rng.randint(0, height)
            draw.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(255, 255, 255))
    elif environment in ("volcano",):
        _draw_mountains(draw, width, height, [(60, 10, 5), (100, 20, 10), (150, 30, 15)], rng)
        # Lava flow
        lava_y = int(height * 0.6)
        for lx in range(0, width, 3):
            ly = lava_y + rng.randint(-5, 5)
            draw.line([(lx, ly), (lx, height)], fill=(220, 70 + rng.randint(0, 30), 10))
        # Sparks
        for _ in range(25):
            spx = rng.randint(int(width * 0.3), int(width * 0.7))
            spy = rng.randint(int(height * 0.2), int(height * 0.6))
            draw.ellipse([spx - 3, spy - 3, spx + 3, spy + 3], fill=(255, rng.randint(100, 200), 0))
    else:
        _draw_mountains(draw, width, height, bg_colors, rng)
        _draw_sun_and_rays(draw, int(width * 0.75), int(height * 0.2), rng)

    # ── 3. Halftone dots (comic book style) ─────────────────────
    style_cfg = ART_STYLE_EFFECTS.get(art_style, ART_STYLE_EFFECTS["default"])
    if style_cfg["halftone"]:
        _draw_halftone(draw, width, height)

    # ── 4. Speed/focus lines (action / dramatic) ────────────────
    prompt_lower = prompt.lower()
    if any(w in prompt_lower for w in ["action", "battle", "fight", "clash", "explosion", "power", "confrontation"]):
        sl_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        sl_draw = ImageDraw.Draw(sl_img)
        _draw_speedlines(sl_draw, width // 2, height // 2, 36, width, height, color=(255, 255, 255), alpha=35)
        img = Image.alpha_composite(img.convert("RGBA"), sl_img).convert("RGB")
        draw = ImageDraw.Draw(img)

    # ── 5. Subject / character silhouette ────────────────────────
    hero_x = width // 2 + rng.randint(-30, 30)
    hero_y = height - 10

    if subject_type == "machine_robot":
        _draw_robot(draw, hero_x, hero_y, art_style, rng)
    elif subject_type == "creature_dragon":
        _draw_dragon(draw, hero_x, hero_y, art_style, rng)
    elif subject_type == "animal_fox":
        _draw_fox(draw, hero_x, hero_y, art_style, rng)
    elif subject_type == "vehicle_spaceship":
        _draw_spaceship(draw, hero_x, int(hero_y * 0.7), art_style, rng)
    else:
        # Generic hero for warriors, detectives, wizards, etc.
        cape_col = rng.choice([(180, 20, 30), (20, 100, 180), (20, 130, 60), (130, 50, 180)])
        body_col = rng.choice([(10, 10, 20), (30, 20, 10), (20, 30, 10)])
        _draw_hero(draw, hero_x, hero_y, art_style, rng, cape_color=cape_col, body_color=body_col)

    # ── 6. Comic border / frame ──────────────────────────────────
    border_w = style_cfg["line_width"] + 2
    draw.rectangle([0, 0, width - 1, height - 1], outline=(0, 0, 0), width=border_w)
    draw.rectangle([border_w, border_w, width - border_w - 1, height - border_w - 1],
                   outline=(255, 255, 255), width=1)

    # ── 7. Panel badge top-left ──────────────────────────────────
    badge_label = f"PANEL {panel_num}" if panel_num else "PREVIEW"
    draw.rectangle([14, 14, 14 + len(badge_label) * 8 + 8, 38], fill=(255, 215, 0), outline=(0, 0, 0), width=2)
    draw.text((18, 19), badge_label, fill=(0, 0, 0))

    # ── 8. Art-style tag top-right ───────────────────────────────
    style_tag = f"[{art_style[:12]}]"
    sw = len(style_tag) * 7 + 8
    draw.rectangle([width - sw - 14, 14, width - 14, 38], fill=(0, 0, 0), outline=(255, 255, 255), width=1)
    draw.text((width - sw - 10, 19), style_tag, fill=(255, 255, 255))

    # ── 9. Apply Pixel Art downscale for pixel art style ─────────
    if art_style == "Pixel Art":
        small = img.resize((width // 4, height // 4), Image.NEAREST)
        img = small.resize((width, height), Image.NEAREST)

    return img


def generate_image(prompt: str, art_style: str = "Comic Book", panel_num: Optional[int] = None) -> str:
    """
    Generates a comic-style illustration for a panel.
    Attempts HuggingFace Inference API first, falls back to prompt-aware Pillow canvas.
    Returns the relative path: 'static/panels/<filename>.png'
    """
    settings.PANELS_DIR.mkdir(parents=True, exist_ok=True)

    # Unique filename derived from prompt content
    prompt_hash = hashlib.md5(f"{prompt}|{art_style}|{panel_num}".encode()).hexdigest()[:8]
    p_num_str = f"panel_{panel_num}" if panel_num else "test_image"
    safe_name = f"{p_num_str}_{_sanitize_filename(prompt, 24)}_{prompt_hash}.png"
    output_path = settings.PANELS_DIR / safe_name
    relative_path = f"static/panels/{safe_name}"

    if output_path.exists():
        logger.info(f"Panel image cache hit: {output_path}")
        return relative_path

    # ── Try HuggingFace Stable Diffusion Inference API ─────────
    hf_key = settings.HF_API_KEY
    if hf_key and not hf_key.startswith("your_"):
        try:
            import requests as req_lib
            api_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
            headers = {"Authorization": f"Bearer {hf_key}", "Content-Type": "application/json"}
            payload = {
                "inputs": f"{prompt}, {art_style} style, comic illustration, high quality, detailed, vivid colors",
                "parameters": {"num_inference_steps": 25, "guidance_scale": 7.5}
            }
            resp = req_lib.post(api_url, headers=headers, json=payload, timeout=30)
            ct = resp.headers.get("content-type", "")
            if resp.status_code == 200 and "image" in ct:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"HF SD image saved: {output_path}")
                return relative_path
            else:
                logger.warning(f"HF API response {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"HF Inference API unreachable ({e}). Using prompt-aware canvas renderer.")

    # ── Prompt-Aware Pillow Canvas Renderer (fallback) ─────────
    img = _draw_comic_canvas(prompt=prompt, art_style=art_style, panel_num=panel_num)
    img.save(str(output_path), format="PNG")
    logger.info(f"Prompt-aware panel illustration saved: {output_path}")
    return relative_path
