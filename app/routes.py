"""
FastAPI Routes: Main application routing and AI pipeline orchestration.
"""
import os
import logging
from typing import Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.schemas import PromptRequest, ComicResponse, ImageTestRequest, ImageTestResponse
from app.core.gemini_flash import generate_outline
from app.core.gemini_pro import generate_story
from app.core.image_generator import generate_image
from app.core.layout_builder import build_comic_layout
from app.core.exporters import save_pdf

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

@router.get("/", response_class=HTMLResponse, summary="Homepage")
async def home(request: Request):
    """Renders the ComicCraft homepage with the comic generator form."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "version": settings.VERSION
        }
    )

@router.post("/generate", response_class=HTMLResponse, summary="Generate Comic from Web Form")
async def generate_comic_form(
    request: Request,
    story_prompt: str = Form(..., description="Story prompt or idea"),
    character_name: str = Form("Hero", description="Main character name"),
    setting: str = Form("Forest", description="Setting / World"),
    tone: str = Form("Dramatic", description="Story tone"),
    art_style: str = Form("Comic Book", description="Visual art style")
):
    """
    Handles form submission from the homepage:
    1. Generates 5-panel outline via Gemini Flash
    2. Generates dialogue and narration via Gemini Pro
    3. Generates 5 comic panel illustrations via Diffusers / Image Generator
    4. Builds comic layout structure
    5. Exports comic to PDF via FPDF
    6. Renders comic_preview.html
    """
    if not story_prompt.strip():
        raise HTTPException(status_code=400, detail="Story prompt cannot be empty.")

    try:
        # Step 1: Generate Outline
        outline = generate_outline(
            story_prompt=story_prompt,
            character_name=character_name,
            setting=setting,
            tone=tone,
            art_style=art_style
        )

        # Step 2: Generate Story Narration and Dialogue
        story_data = generate_story(
            outline=outline,
            character_name=character_name,
            setting=setting,
            tone=tone,
            art_style=art_style
        )

        # Step 3: Generate Images for each panel
        image_paths = []
        for panel in outline:
            p_num = panel.get("panel_number", 1)
            img_prompt = panel.get("image_prompt", f"{character_name} in {setting}")
            img_path = generate_image(
                prompt=img_prompt,
                art_style=art_style,
                panel_num=p_num
            )
            image_paths.append(img_path)

        # Step 4: Build Comic Layout
        layout = build_comic_layout(outline, story_data, image_paths)

        # Step 5: Save PDF
        pdf_info = save_pdf(
            layout=layout,
            story_prompt=story_prompt,
            character_name=character_name,
            tone=tone,
            art_style=art_style
        )

        return templates.TemplateResponse(
            request=request,
            name="comic_preview.html",
            context={
                "story_prompt": story_prompt,
                "character_name": character_name,
                "setting": setting,
                "tone": tone,
                "art_style": art_style,
                "layout": layout,
                "pdf_filename": pdf_info["filename"],
                "pdf_download_url": pdf_info["download_url"],
                "export_success_url": f"/export-success?pdf={pdf_info['filename']}"
            }
        )

    except Exception as e:
        logger.exception(f"Comic generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate comic: {str(e)}")

@router.post("/generate-comic/json", response_model=ComicResponse, summary="Generate Comic via JSON API")
async def generate_comic_json(payload: PromptRequest):
    """
    JSON API endpoint for programmatic comic creation.
    Returns complete layout dictionaries and PDF download URL.
    """
    try:
        outline = generate_outline(
            story_prompt=payload.story_prompt,
            character_name=payload.character_name,
            setting=payload.setting,
            tone=payload.tone,
            art_style=payload.art_style
        )

        story_data = generate_story(
            outline=outline,
            character_name=payload.character_name,
            setting=payload.setting,
            tone=payload.tone,
            art_style=payload.art_style
        )

        image_paths = []
        for panel in outline:
            p_num = panel.get("panel_number", 1)
            img_prompt = panel.get("image_prompt", f"{payload.character_name} in {payload.setting}")
            img_path = generate_image(
                prompt=img_prompt,
                art_style=payload.art_style,
                panel_num=p_num
            )
            image_paths.append(img_path)

        layout = build_comic_layout(outline, story_data, image_paths)

        pdf_info = save_pdf(
            layout=layout,
            story_prompt=payload.story_prompt,
            character_name=payload.character_name,
            tone=payload.tone,
            art_style=payload.art_style
        )

        return ComicResponse(
            status="success",
            story_prompt=payload.story_prompt,
            character_name=payload.character_name,
            setting=payload.setting,
            tone=payload.tone,
            art_style=payload.art_style,
            layout=layout,
            pdf_filename=pdf_info["filename"],
            pdf_download_url=pdf_info["download_url"]
        )

    except Exception as e:
        logger.exception(f"JSON comic generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate comic via API: {str(e)}")

@router.get("/export-success", response_class=HTMLResponse, summary="Export Confirmation Screen")
async def export_success(request: Request, pdf: Optional[str] = None):
    """Displays confirmation page after user downloads their comic."""
    pdf_filename = pdf or "comic.pdf"
    download_url = f"/download-pdf/{pdf_filename}" if pdf else "#"
    return templates.TemplateResponse(
        request=request,
        name="export_success.html",
        context={
            "pdf_filename": pdf_filename,
            "download_url": download_url
        }
    )

@router.get("/download-pdf/{filename}", summary="Download Exported Comic PDF")
async def download_pdf(filename: str):
    """Serves the generated comic PDF file for direct download."""
    safe_filename = os.path.basename(filename)
    pdf_path = settings.EXPORTS_DIR / safe_filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF export file not found.")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=safe_filename
    )

@router.post("/test-image", response_model=ImageTestResponse, summary="Test Image Generation (POST API)")
async def test_image_api(payload: ImageTestRequest):
    """Developer route to test image generation directly from a prompt."""
    try:
        img_rel = generate_image(prompt=payload.prompt, art_style=payload.art_style or "Comic Book")
        filename = os.path.basename(img_rel)
        return ImageTestResponse(
            status="success",
            prompt=payload.prompt,
            art_style=payload.art_style or "Comic Book",
            image_filename=filename,
            image_url=f"/{img_rel.replace('\\', '/')}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image test generation failed: {str(e)}")

@router.get("/test-image", summary="Test Image Generation (GET)")
async def test_image_get(prompt: str = "A heroic warrior in an enchanted forest", art_style: str = "Comic Book"):
    """Quick GET endpoint to test image generation in browser."""
    img_rel = generate_image(prompt=prompt, art_style=art_style)
    return JSONResponse({
        "status": "success",
        "prompt": prompt,
        "art_style": art_style,
        "image_path": img_rel,
        "image_url": f"/{img_rel.replace('\\', '/')}"
    })
