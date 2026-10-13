"""
Document Parser Module for Layout-Aware Vision and Structure Extraction.

Uses Docling for layout analysis, table extraction, and optical character recognition (OCR)
with fallback mechanisms for plain text and raw PDFs.
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Lazy initialization flag for Docling
_docling_converter: Optional[Any] = None


def get_docling_converter() -> Optional[Any]:
    """Lazily load DocumentConverter to optimize startup latency and memory."""
    global _docling_converter
    if _docling_converter is None:
        try:
            from docling.document_converter import DocumentConverter
            _docling_converter = DocumentConverter()
            logger.info("Docling DocumentConverter initialized successfully.")
        except ImportError:
            logger.warning("Docling is not installed. Falling back to lightweight PDF parsing.")
            _docling_converter = None
        except Exception as e:
            logger.error(f"Failed to initialize Docling: {e}. Using fallback parser.")
            _docling_converter = None
    return _docling_converter


def _fallback_pdf_parser(file_path: str) -> List[Dict[str, Any]]:
    """Robust fallback parser supporting PyMuPDF (fitz), pypdf, python-docx, and plain text."""
    lower_path = file_path.lower()

    # 1. PDF Handling
    if lower_path.endswith(".pdf"):
        pages: List[Dict[str, Any]] = []

        # Strategy A: PyMuPDF (fast, high-fidelity bounding box extraction)
        try:
            import fitz
            doc = fitz.open(file_path)
            for page_idx, page in enumerate(doc):
                text = (page.get_text("text") or "").replace("\x00", "").strip()
                rect = page.rect
                width = max(float(rect.width), 1.0)
                height = max(float(rect.height), 1.0)
                bboxes: List[Dict[str, Any]] = []

                try:
                    for b in page.get_text("blocks"):
                        # b is (x0, y0, x1, y1, text, block_no, block_type)
                        if len(b) >= 7 and b[6] == 0:
                            b_text = (b[4] or "").replace("\x00", "").strip()
                            if b_text:
                                bboxes.append({
                                    "text": b_text[:100],
                                    "xmin": round(max(0.0, min(1.0, float(b[0]) / width)), 4),
                                    "ymin": round(max(0.0, min(1.0, float(b[1]) / height)), 4),
                                    "xmax": round(max(0.0, min(1.0, float(b[2]) / width)), 4),
                                    "ymax": round(max(0.0, min(1.0, float(b[3]) / height)), 4),
                                })
                except Exception:
                    pass

                if not bboxes and text:
                    bboxes.append({
                        "text": text[:100],
                        "ymin": 0.0,
                        "xmin": 0.0,
                        "ymax": 1.0,
                        "xmax": 1.0,
                    })

                pages.append({
                    "page_number": page_idx + 1,
                    "content": text,
                    "bounding_boxes": bboxes,
                })

            if pages:
                return pages
        except Exception as fitz_err:
            logger.warning(f"PyMuPDF fallback failed ({fitz_err}). Trying pypdf.")

        # Strategy B: pypdf (pure Python fallback)
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            for page_idx, page in enumerate(reader.pages):
                text = (page.extract_text() or "").replace("\x00", "").strip()
                pages.append({
                    "page_number": page_idx + 1,
                    "content": text,
                    "bounding_boxes": [
                        {
                            "text": text[:100] if text else "",
                            "ymin": 0.0,
                            "xmin": 0.0,
                            "ymax": 1.0,
                            "xmax": 1.0,
                        }
                    ] if text else [],
                })
            if pages:
                return pages
        except Exception as pypdf_err:
            logger.error(f"pypdf fallback failed: {pypdf_err}")
            raise ValueError(f"Could not extract text from PDF document: {pypdf_err}") from pypdf_err

        raise ValueError(f"PDF document {file_path} contained no readable text pages.")

    # 2. DOCX Handling
    if lower_path.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(file_path)
            paragraphs = [p.text.replace("\x00", "").strip() for p in doc.paragraphs if p.text.strip()]
            full_text = "\n\n".join(paragraphs)
            return [{
                "page_number": 1,
                "content": full_text,
                "bounding_boxes": [],
            }]
        except Exception as docx_err:
            logger.error(f"DOCX parser failed: {docx_err}")
            raise ValueError(f"Could not parse DOCX file: {docx_err}") from docx_err

    # 3. Plain Text / Markdown / CSV / JSON Fallback
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().replace("\x00", "")
        return [{
            "page_number": 1,
            "content": content.strip(),
            "bounding_boxes": [],
        }]
    except Exception as read_err:
        logger.error(f"Failed to read file {file_path}: {read_err}")
        raise ValueError(f"Could not parse file: {read_err}") from read_err


def parse_document(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse a document into structured, page-level text representations with bounding boxes.

    Args:
        file_path: Absolute or relative path to the PDF/DOCX/TXT file.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries for each page:
            - page_number (int): 1-indexed page number
            - content (str): Structured plain text extracted from the page
            - bounding_boxes (list[dict]): Extracted bounding box coordinates:
                - text (str)
                - ymin (float): Normalized 0.0-1.0
                - xmin (float): Normalized 0.0-1.0
                - ymax (float): Normalized 0.0-1.0
                - xmax (float): Normalized 0.0-1.0

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If parsing fails or the document is empty.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Document not found at path: {file_path}")

    converter = get_docling_converter()
    if converter is None:
        return _fallback_pdf_parser(file_path)

    try:
        conv_result = converter.convert(file_path)
        doc = conv_result.document

        pages_dict: Dict[int, Dict[str, Any]] = {}

        # Safely extract pages
        pages_attr = getattr(doc, "pages", None)
        if isinstance(pages_attr, dict):
            for page_no in pages_attr.keys():
                pages_dict[page_no] = {
                    "page_number": page_no,
                    "content": "",
                    "bounding_boxes": []
                }

        # Iterate over text items, paragraphs, and tables
        texts_attr = getattr(doc, "texts", None)
        if texts_attr and hasattr(texts_attr, "__iter__"):
            for item in texts_attr:
                prov_list = getattr(item, "prov", None)
                page_no = 1
                if prov_list and len(prov_list) > 0:
                    page_no = getattr(prov_list[0], "page_no", 1)

                if page_no not in pages_dict:
                    pages_dict[page_no] = {
                        "page_number": page_no,
                        "content": "",
                        "bounding_boxes": []
                    }
                
                text_val = getattr(item, "text", "")
                if not isinstance(text_val, str) or not text_val.strip():
                    continue

                text_val = text_val.strip()

                # Append text to page content
                if pages_dict[page_no]["content"]:
                    pages_dict[page_no]["content"] += "\n\n" + text_val
                else:
                    pages_dict[page_no]["content"] = text_val

                # Extract normalized bounding box if provenance exists
                if prov_list and len(prov_list) > 0:
                    bbox = getattr(prov_list[0], "bbox", None)
                    if bbox:
                        ymin = float(getattr(bbox, "t", getattr(bbox, "ymin", 0.0)))
                        xmin = float(getattr(bbox, "l", getattr(bbox, "xmin", 0.0)))
                        ymax = float(getattr(bbox, "b", getattr(bbox, "ymax", 1.0)))
                        xmax = float(getattr(bbox, "r", getattr(bbox, "xmax", 1.0)))

                        pages_dict[page_no]["bounding_boxes"].append({
                            "text": text_val[:120],
                            "ymin": round(ymin / 1000.0 if ymin > 1.0 else ymin, 4),
                            "xmin": round(xmin / 1000.0 if xmin > 1.0 else xmin, 4),
                            "ymax": round(ymax / 1000.0 if ymax > 1.0 else ymax, 4),
                            "xmax": round(xmax / 1000.0 if xmax > 1.0 else xmax, 4)
                        })

        # If pages were extracted, return sorted by page number
        if pages_dict:
            return [pages_dict[p] for p in sorted(pages_dict.keys())]

        # Fallback to export_to_markdown if items were empty
        if hasattr(doc, "export_to_markdown") and callable(doc.export_to_markdown):
            export_text = doc.export_to_markdown()
        else:
            export_text = str(doc)

        return [{
            "page_number": 1,
            "content": export_text.strip(),
            "bounding_boxes": []
        }]

    except Exception as e:
        logger.warning(f"Docling parsing error: {e}. Attempting fallback parser.")
        return _fallback_pdf_parser(file_path)
