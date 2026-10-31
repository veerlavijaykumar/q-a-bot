
from pathlib import Path
import re

import pymupdf
from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
from PIL import Image
import pytesseract
from io import BytesIO


SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".docx",
    ".png", ".jpg", ".jpeg",
    ".tif", ".tiff", ".bmp"
}


def clean_text(text: str) -> str:
    """Normalize whitespace in extracted document text."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()



def load_pdf(path: Path) -> list[dict]:
    """Extract PDF text, using OCR when a page has no selectable text."""
    records = []

    with pymupdf.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()

            # Use OCR when normal extraction finds no meaningful text.
            if not text:
                pix = page.get_pixmap(
                    matrix=pymupdf.Matrix(2, 2),
                    alpha=False,
                )
                image = Image.open(BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(image)

            text = clean_text(text)

            if text:
                records.append({
                    "text": text,
                    "metadata": {
                        "source": path.name,
                        "page": page_number,
                        "file_type": "pdf",
                    },
                })

    return records



def load_txt(path: Path) -> list[dict]:
    """Load a text file as one document record."""
    text = clean_text(path.read_text(encoding="utf-8"))

    if not text:
        return []

    return [{
        "text": text,
        "metadata": {
            "source": path.name,
            "page": None,
            "file_type": "txt",
        },
    }]


def load_docx(path: Path) -> list[dict]:
    """Extract non-empty paragraphs and tables from a Word document in document order."""
    document = Document(path)
    lines = []
    current_heading = ""

    for element in document.element.body:
        tag = element.tag.split("}")[-1]
        if tag == "p":
            p = Paragraph(element, document)
            text = p.text.strip()
            if text:
                lines.append(text)
                if p.style.name.startswith("Heading"):
                    current_heading = text
        elif tag == "tbl":
            tbl = Table(element, document)
            rows = tbl.rows
            if not rows:
                continue

            seen = set()
            header_cells = []
            for c in rows[0].cells:
                if c._tc not in seen:
                    seen.add(c._tc)
                    header_cells.append(c.text.strip().replace("\n", " "))

            is_pattern_map = "pattern" in current_heading.lower()

            for r_idx, row in enumerate(rows):
                seen_cells = set()
                cells = []
                for cell in row.cells:
                    if cell._tc not in seen_cells:
                        seen_cells.add(cell._tc)
                        cells.append(cell.text.strip().replace("\n", " "))

                if not any(cells):
                    continue

                if is_pattern_map and len(cells) == 2:
                    row_str = f"Pattern: {cells[1]} | Problem Cue: {cells[0]}"
                elif len(cells) > 1 and len(header_cells) == len(cells) and r_idx > 0 and any(h.lower() in ("period", "focus", "name", "type", "description") for h in header_cells):
                    row_str = " | ".join(f"{h}: {v}" for h, v in zip(header_cells, cells))
                else:
                    row_str = " | ".join(cells)

                if row_str.strip():
                    lines.append(row_str)

    # Fallback to standard paragraphs if body element traversal yielded nothing
    if not lines:
        for p in document.paragraphs:
            if p.text.strip():
                lines.append(p.text.strip())

    text = clean_text("\n".join(lines))

    if not text:
        return []

    return [{
        "text": text,
        "metadata": {
            "source": path.name,
            "page": None,
            "file_type": "docx",
        },
    }]

def load_image(path: Path) -> list[dict]:
    """Extract text from an image file using OCR."""
    with Image.open(path) as image:
        text = pytesseract.image_to_string(image)
        text=clean_text(text)
        if not text:
            return []
        return[{
            "text":text,
            "metadata":{
                "source":path.name,
                "page":None,
                "file_type":"image"
            }
        }]


def load_documents(data_dir: str | Path = "data") -> list[dict]:
    """Load all supported documents from a directory."""
    directory = Path(data_dir)

    if not directory.is_dir():
        raise FileNotFoundError(
            f"Document directory does not exist: {directory}"
        )

    records = []
    files = sorted(
        path for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        raise ValueError(
            f"No PDF, TXT, or DOCX documents found in {directory}"
        )

    for path in files:
        extension = path.suffix.lower()

        if extension == ".pdf":
            records.extend(load_pdf(path))
        elif extension == ".txt":
            records.extend(load_txt(path))
        elif extension == ".docx":
            records.extend(load_docx(path))
        elif extension in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
            records.extend(load_image(path))

    return records

if __name__ == "__main__":
    data_dir = input("Enter the path to your data folder: ").strip()

    try:
        docs = load_documents(data_dir)

        print(f"\nTotal records loaded: {len(docs)}")

        sources = sorted({
            doc["metadata"]["source"]
            for doc in docs
        })
        print(f"Documents loaded: {len(sources)}")

        for source in sources:
            print(f"- {source}")

        if docs:
            print("\nFirst record metadata:")
            print(docs[0]["metadata"])

            print("\nText preview:")
            print(docs[0]["text"][:300])

    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}")



