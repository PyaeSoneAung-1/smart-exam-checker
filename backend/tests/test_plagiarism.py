"""Plagiarism detection tiering: lexical decides, semantic only reviews."""
import numpy as np

from app.nlp.advanced.plagiarism_detector import PlagiarismDetector

IDENTICAL_A = (
    "Symmetric encryption uses one shared key for encryption and decryption. "
    "Asymmetric encryption uses a public key to encrypt and a private key to decrypt."
)
IDENTICAL_B = (
    "Symmetric encryption uses one shared key for encryption and decryption. "
    "Asymmetric encryption uses a public key to encrypt and a private key to decrypt."
)
PARAPHRASE = (
    "A single key is used by symmetric cryptography for both scrambling and "
    "unscrambling data, while public-key cryptography relies on two linked keys."
)
UNRELATED = "A firewall filters incoming and outgoing traffic against security rules."


class _StubDetector(PlagiarismDetector):
    """Detector with a fixed semantic matrix (no model download needed)."""

    def __init__(self, semantic_matrix=None, **kwargs):
        super().__init__(**kwargs)
        self._semantic = semantic_matrix

    def _semantic_matrix(self, texts):  # noqa: D102 - test double
        return self._semantic


class TestLexicalFlagging:
    def test_identical_answers_are_flagged(self):
        detector = _StubDetector(semantic_matrix=None, threshold=0.6)
        result = detector.detect([IDENTICAL_A, IDENTICAL_B])
        pair = result["pairs"][0]
        assert pair["flagged"] is True
        assert pair["similarity"] > 0.9
        assert result["summary"]["flagged_pairs"] == 1

    def test_unrelated_answers_are_not_flagged(self):
        detector = _StubDetector(semantic_matrix=None, threshold=0.6)
        result = detector.detect([IDENTICAL_A, UNRELATED])
        assert result["pairs"][0]["flagged"] is False
        assert result["summary"]["flagged_pairs"] == 0

    def test_single_answer_produces_empty_result(self):
        detector = _StubDetector(semantic_matrix=None)
        result = detector.detect([IDENTICAL_A])
        assert result["pairs"] == []
        assert result["summary"]["total_pairs"] == 0


class TestSemanticTiering:
    def test_high_semantic_only_is_reviewed_not_flagged(self):
        """Short answers to the same question reach 0.9+ semantics routinely —
        that must never be reported as plagiarism on its own."""
        semantic = np.array([[1.0, 0.95], [0.95, 1.0]])
        detector = _StubDetector(semantic_matrix=semantic, threshold=0.6)

        result = detector.detect([UNRELATED, PARAPHRASE])
        pair = result["pairs"][0]
        assert pair["flagged"] is False
        assert pair["semantic_review"] is True
        assert pair["method"] == "semantic-review"
        assert result["summary"]["flagged_pairs"] == 0
        assert result["summary"]["review_pairs"] == 1

    def test_lexical_and_semantic_together_are_corroborated(self):
        semantic = np.array([[1.0, 0.98], [0.98, 1.0]])
        detector = _StubDetector(semantic_matrix=semantic, threshold=0.6)

        result = detector.detect([IDENTICAL_A, IDENTICAL_B])
        pair = result["pairs"][0]
        assert pair["flagged"] is True
        assert pair["method"] == "lexical+semantic"

    def test_low_semantic_and_low_lexical_is_clean(self):
        semantic = np.array([[1.0, 0.4], [0.4, 1.0]])
        detector = _StubDetector(semantic_matrix=semantic, threshold=0.6)

        result = detector.detect([IDENTICAL_A, UNRELATED])
        pair = result["pairs"][0]
        assert pair["flagged"] is False
        assert pair["semantic_review"] is False

    def test_empty_answers_are_handled(self):
        detector = _StubDetector(semantic_matrix=None)
        result = detector.detect(["", "   "])
        assert result["summary"]["total_pairs"] == 1
        assert result["summary"]["flagged_pairs"] == 0
