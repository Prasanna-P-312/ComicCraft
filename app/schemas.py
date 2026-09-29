from pydantic import BaseModel, Field
from typing import List, Optional

class PromptRequest(BaseModel):
    story_prompt: str = Field(..., description="Main prompt or idea for the comic story", min_length=3)
    character_name: str = Field(default="Hero", description="Name of the main character")
    setting: str = Field(default="Forest", description="Setting or environment of the story")
    tone: str = Field(default="Dramatic", description="Mood/Tone of the story (e.g. Dramatic, Funny, Light-hearted, Poetic)")
    art_style: str = Field(default="Comic Book", description="Art visual style (e.g. Comic Book, Anime, Pixel Art, Realistic)")

class PanelOutline(BaseModel):
    panel_number: int
    title: str
    scene_description: str
    image_prompt: str

class PanelStory(BaseModel):
    panel_number: int
    caption: str
    narration: str
    dialogue: str

class ComicPanelLayout(BaseModel):
    panel_number: int
    title: str
    scene_description: str
    caption: str
    narration: str
    dialogue: str
    image_prompt: str
    image_path: str
    image_url: str

class ComicResponse(BaseModel):
    status: str = "success"
    story_prompt: str
    character_name: str
    setting: str
    tone: str
    art_style: str
    layout: List[ComicPanelLayout]
    pdf_filename: str
    pdf_download_url: str

class ImageTestRequest(BaseModel):
    prompt: str = Field(..., description="Prompt to generate test image for")
    art_style: Optional[str] = Field(default="Comic Book", description="Visual art style")

class ImageTestResponse(BaseModel):
    status: str = "success"
    prompt: str
    art_style: str
    image_filename: str
    image_url: str
