"""
Unit tests for ComicCraft core generation, layout, and exporter modules.
"""
import os
from pathlib import Path
from app.config import settings
from app.core.gemini_flash import generate_outline
from app.core.gemini_pro import generate_story
from app.core.image_generator import generate_image
from app.core.layout_builder import build_comic_layout
from app.core.exporters import save_pdf

def test_generate_outline():
    outline = generate_outline(
        story_prompt="A brave fox exploring an enchanted forest",
        character_name="Rusty",
        setting="Forest",
        tone="Dramatic",
        art_style="Comic Book"
    )
    assert isinstance(outline, list)
    assert len(outline) == 5
    for panel in outline:
        assert "panel_number" in panel
        assert "title" in panel
        assert "scene_description" in panel
        assert "image_prompt" in panel

def test_generate_story():
    outline = generate_outline(
        story_prompt="A cybernetic detective solving a crime",
        character_name="Kael",
        setting="Cyberpunk City",
        tone="Action-Packed",
        art_style="Anime"
    )
    story_data = generate_story(
        outline=outline,
        character_name="Kael",
        setting="Cyberpunk City",
        tone="Action-Packed",
        art_style="Anime"
    )
    assert isinstance(story_data, list)
    assert len(story_data) == 5
    for story in story_data:
        assert "panel_number" in story
        assert "caption" in story
        assert "narration" in story
        assert "dialogue" in story

def test_generate_image():
    img_path = generate_image(
        prompt="A robotic chef in outer space",
        art_style="Pixel Art",
        panel_num=1
    )
    assert img_path is not None
    assert "static/panels/" in img_path.replace("\\", "/")
    full_path = settings.BASE_DIR / img_path
    assert full_path.exists()
    assert full_path.stat().st_size > 0

def test_build_comic_layout():
    outline = generate_outline("Story premise", "Hero", "Ruins", "Epic", "Comic Book")
    story_data = generate_story(outline, "Hero", "Ruins", "Epic", "Comic Book")
    images = [generate_image(f"Scene {i}", "Comic Book", i) for i in range(1, 6)]

    layout = build_comic_layout(outline, story_data, images)
    assert len(layout) == 5
    for p in layout:
        assert p["panel_number"] in [1, 2, 3, 4, 5]
        assert "image_url" in p
        assert "title" in p
        assert "narration" in p

def test_save_pdf():
    outline = generate_outline("A magical quest", "Aria", "Castle", "Poetic", "Watercolor")
    story_data = generate_story(outline, "Aria", "Castle", "Poetic", "Watercolor")
    images = [generate_image(f"Aria panel {i}", "Watercolor", i) for i in range(1, 6)]
    layout = build_comic_layout(outline, story_data, images)

    pdf_result = save_pdf(
        layout=layout,
        story_prompt="A magical quest",
        character_name="Aria",
        tone="Poetic",
        art_style="Watercolor"
    )
    assert "filename" in pdf_result
    assert "filepath" in pdf_result
    assert Path(pdf_result["filepath"]).exists()
    assert Path(pdf_result["filepath"]).stat().st_size > 0
