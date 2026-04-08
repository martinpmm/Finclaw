"""Documents routes: upload, list, and manage financial documents."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile

router = APIRouter(tags=["documents"])

_DOCUMENTS_FILE = "DOCUMENTS.md"


def _load_documents(workspace: Path) -> str:
    p = workspace / _DOCUMENTS_FILE
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _parse_documents(content: str) -> list[dict]:
    """Parse DOCUMENTS.md into a list of document entries."""
    docs = []
    # Documents are stored as H2 sections
    sections = re.split(r"^## ", content, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section or section.startswith("#"):
            continue

        lines = section.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        # Extract metadata
        source_type = ""
        date = ""
        source_match = re.search(r"\*\*Source\*\*:\s*(.+)", body)
        date_match = re.search(r"\*\*Date\*\*:\s*(.+)", body)
        if source_match:
            source_type = source_match.group(1).strip()
        if date_match:
            date = date_match.group(1).strip()

        # Extract notes (everything after metadata)
        notes = ""
        notes_match = re.search(r"\*\*Key Notes\*\*:\s*\n(.*)", body, re.DOTALL)
        if notes_match:
            notes = notes_match.group(1).strip()

        docs.append({
            "title": title,
            "source_type": source_type,
            "date": date,
            "notes": notes,
            "notes_preview": notes[:200] + "..." if len(notes) > 200 else notes,
        })

    return docs


@router.get("/documents")
async def list_documents(request: Request):
    """List all documents in the knowledge base."""
    workspace = request.app.state.workspace
    content = _load_documents(workspace)
    docs = _parse_documents(content)
    return {"documents": docs}


@router.get("/documents/{title}")
async def get_document(title: str, request: Request):
    """Get a single document by title."""
    workspace = request.app.state.workspace
    content = _load_documents(workspace)
    docs = _parse_documents(content)

    for doc in docs:
        if doc["title"].lower() == title.lower():
            return doc

    return {"error": "Document not found", "title": title}


@router.post("/documents/upload")
async def upload_document(file: UploadFile, request: Request):
    """Upload a document file (PDF, etc.) to the workspace."""
    workspace = request.app.state.workspace
    uploads_dir = workspace / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    ext = Path(file.filename).suffix if file.filename else ".pdf"
    safe_name = re.sub(r"[^\w\-.]", "_", Path(file.filename).stem) if file.filename else "document"
    unique_name = f"{safe_name}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = uploads_dir / unique_name

    # Save file
    contents = await file.read()
    file_path.write_bytes(contents)

    return {
        "filename": unique_name,
        "original_name": file.filename,
        "path": str(file_path),
        "size": len(contents),
        "message": f"File uploaded. Use chat to analyze: 'Analyze the document at {file_path}'",
    }


@router.delete("/documents/{title}")
async def delete_document(title: str, request: Request):
    """Remove a document from the knowledge base."""
    workspace = request.app.state.workspace
    content = _load_documents(workspace)

    # Find and remove the section
    pattern = rf"^## {re.escape(title)}\s*$"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return {"error": "Document not found", "title": title}

    start = match.start()
    next_h2 = re.search(r"^## ", content[match.end():], re.MULTILINE)
    end = match.end() + next_h2.start() if next_h2 else len(content)

    new_content = content[:start] + content[end:]
    p = workspace / _DOCUMENTS_FILE
    p.write_text(new_content, encoding="utf-8")

    return {"removed": title}
