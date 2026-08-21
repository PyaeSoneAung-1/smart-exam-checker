"""Advanced NLP modules with graceful fallbacks."""

def _safe_import(import_func, fallback_name):
    try:
        return import_func()
    except Exception:
        return None

PlagiarismDetector = _safe_import(lambda: __import__('app.nlp.advanced.plagiarism_detector', fromlist=['PlagiarismDetector']).PlagiarismDetector, "PlagiarismDetector")
AIDetector = _safe_import(lambda: __import__('app.nlp.advanced.ai_detector', fromlist=['AIDetector']).AIDetector, "AIDetector")
FeedbackGenerator = _safe_import(lambda: __import__('app.nlp.advanced.feedback_generator', fromlist=['FeedbackGenerator']).FeedbackGenerator, "FeedbackGenerator")
