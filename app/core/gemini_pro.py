"""
Gemini Pro Module: Generates rich dialogues, captions, and narrative story for comic panels.
Uses Google Gemini Pro to expand outline panels into engaging comic narratives.
"""
import json
import re
import logging
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

def _fallback_story(outline: List[Dict[str, Any]], character_name: str, setting: str, tone: str) -> List[Dict[str, Any]]:
    """Procedural fallback story when Gemini Pro API is unavailable."""
    stories = []
    default_captions = [
        f"The sun hangs low over {setting}, casting long shadows across unfamiliar terrain.",
        f"A peculiar whisper rustles through the air, breaking the heavy silence.",
        f"Without warning, danger strikes with explosive intensity!",
        f"Digging deep within, courage flares like a beacon in the dark.",
        f"As tranquility returns, legends are born in the heart of {setting}."
    ]
    default_dialogues = [
        f'"{character_name}: I must see this through, no matter the obstacles."',
        f'"{character_name}: What could this strange sign possibly mean...?"',
        f'"{character_name}: Not today! I will not back down!"',
        f'"{character_name}: Now is the moment to turn everything around!"',
        f'"{character_name}: The quest is won, but our story has just begun."'
    ]

    for idx, panel in enumerate(outline):
        p_num = panel.get("panel_number", idx + 1)
        cap = default_captions[idx % len(default_captions)]
        dlg = default_dialogues[idx % len(default_dialogues)]
        narration = f"{character_name} navigates the {panel.get('title', 'challenge')}, holding steadfast to resolve with a {tone.lower()} spirit."
        
        stories.append({
            "panel_number": p_num,
            "caption": cap,
            "narration": narration,
            "dialogue": dlg
        })
    return stories

def generate_story(outline: List[Dict[str, Any]], character_name: str = "Hero", setting: str = "Forest", tone: str = "Dramatic", art_style: str = "Comic Book") -> List[Dict[str, Any]]:
    """
    Generates detailed comic narration, captions, and dialogues for each panel using Gemini Pro.
    Returns a list of dictionaries with:
      - panel_number (int)
      - caption (str)
      - narration (str)
      - dialogue (str)
    """
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your_"):
        logger.warning("Gemini API key not configured. Using high-quality procedural story fallback.")
        return _fallback_story(outline, character_name, setting, tone)

    prompt = f"""
You are a master comic book scriptwriter.
Expand the following 5 comic panel outlines into engaging comic book narration, ambient captions, and character dialogue.

Specifications:
- Main Character: {character_name}
- Setting: {setting}
- Tone: {tone}
- Art Style: {art_style}

Panel Outlines:
{json.dumps(outline, indent=2)}

Return your response strictly as a JSON array of exactly 5 objects corresponding to panels 1 through 5, with NO extra text or markdown formatting outside the JSON.
Each object must have the following keys:
1. "panel_number": integer (1 to 5)
2. "caption": atmospheric ambient caption (e.g., "[CAPTION: Deep within the foggy woods...]")
3. "narration": 1-2 descriptive narration sentences about the action
4. "dialogue": quoted speech or thought bubble for {character_name} or other characters (e.g., '"{character_name}: We have to hurry!"')

Example JSON format:
[
  {{
    "panel_number": 1,
    "caption": "Deep within the silent woods...",
    "narration": "Alex adjusted his gear, gazing toward the forgotten path.",
    "dialogue": ""Alex: There is no turning back now.""
  }}
]
"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_PRO_MODEL)
        response = model.generate_content(prompt)
        text = response.text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
        if match:
            text = match.group(0)

        story_data = json.loads(text)
        if isinstance(story_data, list) and len(story_data) > 0:
            for idx, p in enumerate(story_data):
                p["panel_number"] = idx + 1
            return story_data[:5]
        else:
            raise ValueError("Parsed JSON is not a list")

    except Exception as e:
        logger.error(f"Error calling Gemini Pro: {e}. Falling back to procedural story generator.")
        return _fallback_story(outline, character_name, setting, tone)
