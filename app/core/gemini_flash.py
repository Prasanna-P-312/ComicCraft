"""
Gemini Flash Module: Generates structured 5-panel comic outlines.
Uses Google Gemini Flash to generate panel-by-panel descriptions and image prompts.
"""
import json
import re
import logging
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

def _fallback_outline(story_prompt: str, character_name: str, setting: str, tone: str, art_style: str) -> List[Dict[str, Any]]:
    """Procedural fallback outline when Gemini API is unavailable or offline."""
    return [
        {
            "panel_number": 1,
            "title": f"The Journey Begins in {setting}",
            "scene_description": f"Introduction to {character_name} standing at the threshold of the {setting.lower()}, surveying the surroundings with determination.",
            "image_prompt": f"Comic book panel illustration of {character_name} in {setting}, establishing shot, {tone.lower()} atmosphere, {art_style.lower()} style, vibrant colors, comic art."
        },
        {
            "panel_number": 2,
            "title": "A Sudden Discovery",
            "scene_description": f"{character_name} uncovers an unexpected mystery or artifact within the {setting.lower()}, sparking tension.",
            "image_prompt": f"Detailed comic frame showing {character_name} discovering a glowing artifact in {setting}, close-up angle, {tone.lower()} mood, {art_style.lower()} art."
        },
        {
            "panel_number": 3,
            "title": "The Confrontation",
            "scene_description": f"The turning point where {character_name} faces the primary obstacle or challenge head-on with high energy.",
            "image_prompt": f"Dynamic action panel of {character_name} facing an intense challenge in {setting}, dramatic lighting, speed lines, {art_style.lower()} style, comic panel."
        },
        {
            "panel_number": 4,
            "title": "The Turning Tide",
            "scene_description": f"{character_name} utilizes clever wit and strength to overcome the obstacle, shifting the momentum.",
            "image_prompt": f"Heroic shot of {character_name} turning the tide of the conflict in {setting}, power aura, {tone.lower()} feeling, {art_style.lower()} aesthetic."
        },
        {
            "panel_number": 5,
            "title": "A New Horizon",
            "scene_description": f"The resolution showing {character_name} having prevailed, looking forward to the next adventure.",
            "image_prompt": f"Cinematic wide angle comic panel of {character_name} standing victorious in {setting} at sunset, {tone.lower()} resolution, {art_style.lower()} finish."
        }
    ]

def generate_outline(story_prompt: str, character_name: str = "Hero", setting: str = "Forest", tone: str = "Dramatic", art_style: str = "Comic Book") -> List[Dict[str, Any]]:
    """
    Generates a structured 5-panel comic outline using Gemini Flash.
    Returns a list of 5 panel dictionaries containing:
      - panel_number (int)
      - title (str)
      - scene_description (str)
      - image_prompt (str)
    """
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your_"):
        logger.warning("Gemini API key not configured. Using high-quality procedural outline fallback.")
        return _fallback_outline(story_prompt, character_name, setting, tone, art_style)

    prompt = f"""
You are an expert comic book creator and screenwriter.
Create a structured 5-panel comic outline based on the following creative specifications:
- Story Prompt: {story_prompt}
- Main Character: {character_name}
- Setting: {setting}
- Tone: {tone}
- Art Style: {art_style}

Return your response strictly as a JSON array of exactly 5 objects, with NO additional text or markdown comments outside the JSON.
Each object must have the following keys:
1. "panel_number": integer (1 to 5)
2. "title": a short, punchy title for the panel
3. "scene_description": a vivid 1-2 sentence description of the scene
4. "image_prompt": a detailed prompt optimized for image generation in {art_style} style, describing character appearance, background, action, and lighting.

Example format:
[
  {{
    "panel_number": 1,
    "title": "Panel Title",
    "scene_description": "Scene description here.",
    "image_prompt": "Detailed art prompt here."
  }}
]
"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_FLASH_MODEL)
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean JSON from markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        # Find JSON array using regex if necessary
        match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
        if match:
            text = match.group(0)

        outline_data = json.loads(text)
        if isinstance(outline_data, list) and len(outline_data) > 0:
            for idx, p in enumerate(outline_data):
                p["panel_number"] = idx + 1
            return outline_data[:5]
        else:
            raise ValueError("Parsed JSON is not a list")

    except Exception as e:
        logger.error(f"Error calling Gemini Flash: {e}. Falling back to procedural outline generator.")
        return _fallback_outline(story_prompt, character_name, setting, tone, art_style)
