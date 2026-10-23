
from pathlib import Path
import re

import pymupdf
from docx import Document
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
    """Extract non-empty paragraphs from a Word document."""
    document = Document(path)
    text = clean_text(
        "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )
    )

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



