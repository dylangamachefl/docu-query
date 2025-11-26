from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

def create_pii_guardrail():
    """Initializes the Presidio analyzer and anonymizer."""
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer

def redact_pii_in_text(text: str, analyzer: AnalyzerEngine, anonymizer: AnonymizerEngine) -> str:
    """
    Analyzes and redacts PII from a given text.

    Args:
        text: The input string to be checked for PII.
        analyzer: The Presidio AnalyzerEngine instance.
        anonymizer: The Presidio AnonymizerEngine instance.

    Returns:
        The text with PII entities redacted.
    """
    analyzer_results = analyzer.analyze(text=text, language='en')
    anonymized_text = anonymizer.anonymize(
        text=text,
        analyzer_results=analyzer_results
    )
    return anonymized_text.text
