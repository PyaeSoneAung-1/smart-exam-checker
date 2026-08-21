"""Cross-Answer Plagiarism Detection using TF-IDF cosine similarity."""
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class PlagiarismDetector:
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    def detect(self, answers: List[str]) -> Dict:
        if len(answers) < 2:
            return {"pairs": [], "summary": {"total_pairs": 0, "flagged_pairs": 0, "max_similarity": 0.0, "flagged_indices": []}}

        valid_answers = [a if a and a.strip() else "empty" for a in answers]
        try:
            vectorizer = TfidfVectorizer(stop_words='english')
            matrix = vectorizer.fit_transform(valid_answers)
            sim_matrix = cosine_similarity(matrix)
        except Exception:
            return {"pairs": [], "summary": {"total_pairs": 0, "flagged_pairs": 0, "max_similarity": 0.0, "flagged_indices": []}}

        pairs = []
        flagged_indices = set()
        max_sim = 0.0

        for i in range(len(answers)):
            for j in range(i + 1, len(answers)):
                sim = float(sim_matrix[i][j])
                max_sim = max(max_sim, sim)
                flagged = sim >= self.threshold
                if flagged:
                    flagged_indices.add(i)
                    flagged_indices.add(j)
                pairs.append({"answer_idx_1": i, "answer_idx_2": j, "similarity": round(sim, 4), "flagged": flagged})

        return {
            "pairs": pairs,
            "summary": {
                "total_pairs": len(pairs),
                "flagged_pairs": sum(1 for p in pairs if p["flagged"]),
                "max_similarity": round(max_sim, 4),
                "flagged_indices": sorted(list(flagged_indices))
            }
        }
