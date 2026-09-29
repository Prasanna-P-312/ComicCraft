"""
Integration tests for ComicCraft FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "ComicCraft"

def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "ComicCraft" in response.text
    assert "Generate AI Comic Strip" in response.text

def test_test_image_get():
    response = client.get("/test-image?prompt=Fox+Warrior&art_style=Comic+Book")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "image_url" in data

def test_test_image_post():
    response = client.post("/test-image", json={
        "prompt": "Cybernetic tiger in neon alley",
        "art_style": "Anime"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "image_filename" in data

def test_generate_comic_json():
    payload = {
        "story_prompt": "A young sorcerer solving a dungeon puzzle",
        "character_name": "Zephyr",
        "setting": "Ancient Ruins",
        "tone": "Mysterious",
        "art_style": "Comic Book"
    }
    response = client.post("/generate-comic/json", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["layout"]) == 5
    assert data["pdf_filename"].endswith(".pdf")
    assert data["pdf_download_url"].startswith("/download-pdf/")

def test_generate_comic_form():
    form_data = {
        "story_prompt": "A space pilot rescuing a stranded vessel",
        "character_name": "Nova",
        "setting": "Space Station",
        "tone": "Dramatic",
        "art_style": "Realistic"
    }
    response = client.post("/generate", data=form_data)
    assert response.status_code == 200
    assert "Nova" in response.text
    assert "PANEL 1" in response.text or "Panel 1" in response.text
    assert "Download Your Comic as PDF" in response.text

def test_export_success_page():
    response = client.get("/export-success?pdf=test_comic.pdf")
    assert response.status_code == 200
    assert "Comic Exported Successfully!" in response.text
    assert "test_comic.pdf" in response.text
