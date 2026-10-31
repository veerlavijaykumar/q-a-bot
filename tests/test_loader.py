import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf
from docx import Document

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from loader import load_documents


class TestDocumentLoader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_txt(self):
        file_path = self.data_dir / "sample.txt"
        file_path.write_text(
            "This is a sample document for testing.",
            encoding="utf-8",
        )

        records = load_documents(str(self.data_dir))

        self.assertEqual(len(records), 1)
        self.assertIn("sample document", records[0]["text"])
        self.assertEqual(
            records[0]["metadata"]["source"],
            "sample.txt",
        )
        self.assertIsNone(records[0]["metadata"]["page"])
        self.assertEqual(
            records[0]["metadata"]["file_type"],
            "txt",
        )

    def test_load_pdf(self):
        file_path = self.data_dir / "sample.pdf"

        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text(
                (72, 72),
                "Sample PDF document text",
            )
            pdf.save(file_path)

        records = load_documents(str(self.data_dir))

        self.assertEqual(len(records), 1)
        self.assertIn(
            "Sample PDF document text",
            records[0]["text"],
        )
        self.assertEqual(
            records[0]["metadata"]["source"],
            "sample.pdf",
        )
        self.assertEqual(
            records[0]["metadata"]["page"],
            1,
        )
        self.assertEqual(
            records[0]["metadata"]["file_type"],
            "pdf",
        )

    def test_load_docx(self):
        file_path = self.data_dir / "sample.docx"

        document = Document()
        document.add_paragraph("Sample DOCX document text")
        document.save(file_path)

        records = load_documents(str(self.data_dir))

        self.assertEqual(len(records), 1)
        self.assertIn(
            "Sample DOCX document text",
            records[0]["text"],
        )
        self.assertEqual(
            records[0]["metadata"]["source"],
            "sample.docx",
        )
        self.assertIsNone(
            records[0]["metadata"]["page"],
        )
        self.assertEqual(
            records[0]["metadata"]["file_type"],
            "docx",
        )

    def test_load_docx_with_table(self):
        file_path = self.data_dir / "table_sample.docx"

        document = Document()
        document.add_paragraph("Table Heading")
        table = document.add_table(rows=2, cols=2)
        table.rows[0].cells[0].text = "Header 1"
        table.rows[0].cells[1].text = "Header 2"
        table.rows[1].cells[0].text = "Value 1"
        table.rows[1].cells[1].text = "Value 2"
        document.save(file_path)

        records = load_documents(str(self.data_dir))
        table_record = next(r for r in records if r["metadata"]["source"] == "table_sample.docx")
        self.assertIn("Table Heading", table_record["text"])
        self.assertIn("Value 1", table_record["text"])
        self.assertIn("Value 2", table_record["text"])

    def test_unsupported_file_is_ignored(self):
        (self.data_dir / "sample.xyz").write_text(
            "Unsupported format",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            ValueError,
            "No PDF, TXT, or DOCX documents found",
        ):
            load_documents(str(self.data_dir))
    
    def test_scanned_pdf_uses_ocr(self):
        file_path = self.data_dir / "scanned.pdf"

        # Create an image containing text.
        from PIL import Image, ImageDraw

        image_path = self.data_dir / "scanned.png"
        image = Image.new("RGB", (1200, 300), "white")
        draw = ImageDraw.Draw(image)
        draw.text(
            (40, 80),
            "OCR SAMPLE DOCUMENT 12345",
            fill="black",
        )
        image.save(image_path)

        # Embed the image in a PDF with no selectable text.
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=600, height=150)
            page.insert_image(
                page.rect,
                filename=str(image_path),
            )
            pdf.save(file_path)

        # Remove the standalone image so only the PDF is loaded.
        image_path.unlink()

        records = load_documents(str(self.data_dir))

        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0]["metadata"]["source"],
            "scanned.pdf",
        )
        ocr_text = records[0]["text"].upper()
        self.assertIn("SAMPLE", ocr_text)
        self.assertIn("DOCUMENT", ocr_text)
        self.assertIn("12345", ocr_text)



if __name__ == "__main__":
    unittest.main(verbosity=2)