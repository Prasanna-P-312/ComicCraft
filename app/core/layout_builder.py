"""
Layout Builder Module: Assembles panel outlines, dialogues, narration, and images into comic layout structure.
"""
from typing import List, Dict, Any

def build_comic_layout(outline: List[Dict[str, Any]], story_data: List[Dict[str, Any]], image_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Combines outline data, expanded stories, and image paths into a cohesive comic panel layout.
    Returns a list of complete panel layout dictionaries.
    """
    layout = []
    num_panels = max(len(outline), len(story_data), len(image_paths))

    for idx in range(num_panels):
        panel_num = idx + 1
        out = outline[idx] if idx < len(outline) else {}
        story = story_data[idx] if idx < len(story_data) else {}
        img_path = image_paths[idx] if idx < len(image_paths) else ""

        # Normalize web URL path
        img_url = f"/{img_path.replace('\\', '/')}" if not img_path.startswith("/") else img_path

        panel_layout = {
            "panel_number": panel_num,
            "title": out.get("title", f"Panel {panel_num}"),
            "scene_description": out.get("scene_description", "A scene in the story unfolds."),
            "image_prompt": out.get("image_prompt", f"Comic panel {panel_num}"),
            "caption": story.get("caption", f"Panel {panel_num} setting the scene..."),
            "narration": story.get("narration", "The adventure continues."),
            "dialogue": story.get("dialogue", '"Hero: We will forge ahead!"'),
            "image_path": img_path,
            "image_url": img_url
        }
        layout.append(panel_layout)

    return layout
