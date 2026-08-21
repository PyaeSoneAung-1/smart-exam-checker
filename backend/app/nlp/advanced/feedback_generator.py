"""Ollama LLM Feedback with template fallback."""
import requests

class FeedbackGenerator:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url

    def generate(self, question: str, model_answer: str, student_answer: str, score: float) -> str:
        try:
            resp = requests.post(f"{self.ollama_url}/api/generate", json={
                "model": "llama3",
                "prompt": f"Question: {question}\nModel Answer: {model_answer}\nStudent Answer: {student_answer}\nScore: {score}%\n\nGive brief feedback:",
                "stream": False
            }, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("response", self._template_feedback(score))
        except Exception:
            pass
        return self._template_feedback(score)

    def _template_feedback(self, score: float) -> str:
        if score >= 80:
            return "Excellent answer! You demonstrated strong understanding of the topic."
        elif score >= 60:
            return "Good answer. Consider adding more detail to strengthen your response."
        elif score >= 40:
            return "Fair answer. Review the key concepts and try to include more relevant information."
        else:
            return "Your answer needs improvement. Please study the topic more carefully and address all key points."
