"""
PII Masking Module using Microsoft Presidio.

Scans and anonymizes Sensitive Personal Identifiable Information (PII)
such as names, emails, phone numbers, SSNs, credit cards, and government IDs
before chunking, embedding, and storage.
"""

import re
import logging
from typing import List, Optional, Any

logger = logging.getLogger(__name__)

# Singleton holders for Presidio engines
_analyzer: Optional[Any] = None
_anonymizer: Optional[Any] = None
_presidio_available: Optional[bool] = None

SUPPORTED_ENTITIES: List[str] = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "NRP",
    "IBAN_CODE",
    "IP_ADDRESS"
]

# Regex fallback patterns in case Presidio/spaCy runtime model is unavailable
FALLBACK_PATTERNS = [
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'), "<EMAIL_ADDRESS>"),
    (re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), "<PHONE_NUMBER>"),
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), "<US_SSN>"),
    (re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'), "<CREDIT_CARD>"),
]


def _init_presidio():
    """Lazily load Presidio analyzer and anonymizer."""
    global _analyzer, _anonymizer, _presidio_available
    if _presidio_available is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            _analyzer = AnalyzerEngine()
            _anonymizer = AnonymizerEngine()
            _presidio_available = True
            logger.info("Presidio Analyzer & Anonymizer initialized successfully.")
        except Exception as e:
            logger.warning(f"Presidio initialization failed ({e}). Using regex PII fallback.")
            _presidio_available = False


def _regex_mask_pii(text: str) -> str:
    """Fallback regex masking when Presidio is not loaded."""
    anonymized = text
    for pattern, replacement in FALLBACK_PATTERNS:
        anonymized = pattern.sub(replacement, anonymized)
    return anonymized


def mask_pii(text: str, language: str = "en") -> str:
    """
    Detect and mask PII entities in the provided text.

    Args:
        text: Raw document text to scan and redact.
        language: Language code (default 'en').

    Returns:
        str: Sanitized text with PII replaced by standardized tags
             like <PERSON>, <EMAIL_ADDRESS>, <PHONE_NUMBER>, etc.
    """
    if not text or not text.strip():
        return text

    _init_presidio()

    if not _presidio_available or _analyzer is None or _anonymizer is None:
        return _regex_mask_pii(text)

    try:
        from presidio_anonymizer.entities import OperatorConfig

        # Analyze text for PII entities
        results = _analyzer.analyze(
            text=text,
            entities=SUPPORTED_ENTITIES,
            language=language
        )

        if not results:
            return text

        # Configure custom anonymization operators: replace with <ENTITY_TYPE>
        operators = {
            entity: OperatorConfig("replace", {"new_value": f"<{entity}>"})
            for entity in SUPPORTED_ENTITIES
        }

        # Execute anonymization
        anonymized_result = _anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )

        return anonymized_result.text

    except Exception as e:
        logger.error(f"Error during Presidio PII anonymization: {e}. Applying regex fallback.")
        return _regex_mask_pii(text)
