"""Advanced Grammar Checker with rule-based + language-tool fallback."""
from typing import List, Dict, Optional
import re


class GrammarChecker:
    """Multi-strategy grammar checking."""

    def __init__(self, language: str = "en-US", remote_url: Optional[str] = None):
        self._language = language
        self._remote_url = remote_url
        self._tool = None
        self._use_fallback = False

    @property
    def tool(self):
        if self._use_fallback:
            return None
        if self._tool is None:
            try:
                import language_tool_python
                if self._remote_url:
                    self._tool = language_tool_python.LanguageTool(self._language, remote_server=self._remote_url)
                else:
                    self._tool = language_tool_python.LanguageTool(self._language)
            except Exception:
                self._use_fallback = True
                return None
        return self._tool

    def _advanced_rule_check(self, text: str) -> List[Dict]:
        """Advanced rule-based grammar checking."""
        issues = []

        rules = [
            # Capitalization
            (r'(?<!\.\s)\bi\b(?![\'`])', "Capitalize 'I' when used as a pronoun", "CAPITALIZATION"),
            # Sentence start check disabled for robustness

            # Punctuation
            (r'\.{2,}', "Use a single period at end of sentence", "PUNCTUATION"),
            # CAPS rule disabled - too many false positives on normal text
            (r'(\w)\1{4,}', "Excessive repeated characters", "TYPO"),

            # Subject-verb agreement
            (r'\b(he|she|it)\s+(are|were|have)\b', "Subject-verb disagreement: singular subject needs singular verb", "AGREEMENT"),
            (r'\b(they|we|you)\s+(is|was|has)\b', "Subject-verb disagreement: plural subject needs plural verb", "AGREEMENT"),
            (r'\bI\s+is\b', "Use 'I am' not 'I is'", "AGREEMENT"),
            (r'\bI\s+was\b', "Consider 'I were' in subjunctive mood", "AGREEMENT"),

            # Common errors
            (r'\btheir\s+(is|are|was|were)\b', "Use 'there' (not 'their') before a verb", "WORD_CHOICE"),
            (r'\byour\s+(welcome|right|wrong)\b', "Use 'you're' (not 'your') before an adjective", "WORD_CHOICE"),
            (r'\b(alot)\b', "Should be 'a lot' (two words)", "SPELLING"),
            (r'\b(definately|definatly)\b', "Should be 'definitely'", "SPELLING"),
            (r'\b(seperate)\b', "Should be 'separate'", "SPELLING"),
            (r'\b(occured)\b', "Should be 'occurred'", "SPELLING"),

            # Double negatives
            (r"\b(don't|doesn't|didn't|can't|won't|couldn't|wouldn't)\s+\w+\s+(no|nothing|never|nobody|nowhere|neither)\b",
             "Double negative detected - consider rephrasing", "STYLE"),

            # Article usage
            (r'\ba\s+([aeiou])', "Consider using 'an' before a vowel sound", "ARTICLES"),
        ]

        for pattern, message, category in rules:
            for match in re.finditer(pattern, text, re.IGNORECASE if category != "CAPITALIZATION" else 0):
                issues.append({
                    "offset": match.start(),
                    "length": match.end() - match.start(),
                    "message": message,
                    "replacements": [],
                    "rule_id": f"RULE_{category}",
                    "category": category,
                    "context": text[max(0, match.start()-15):match.end()+15],
                })

        return issues

    def check_grammar(self, text: str) -> List[Dict]:
        """Check grammar using available method."""
        tool = self.tool
        if tool is not None:
            try:
                matches = tool.check(text)
                issues = []
                for match in matches:
                    issues.append({
                        "offset": match.offset,
                        "length": match.errorLength,
                        "message": match.message,
                        "replacements": match.replacements[:3] if match.replacements else [],
                        "rule_id": match.ruleId,
                        "category": match.category,
                        "context": match.context,
                    })
                # Also add rule-based checks
                rule_issues = self._advanced_rule_check(text)
                issues.extend(rule_issues)
                return issues
            except Exception:
                pass

        return self._advanced_rule_check(text)

    def count_errors(self, text: str) -> int:
        return len(self.check_grammar(text))

    def get_suggestions(self, text: str) -> List[str]:
        issues = self.check_grammar(text)
        suggestions = []
        for issue in issues[:5]:  # Top 5 only
            s = f"[{issue.get('category', 'OTHER')}] {issue['message']}"
            if issue["replacements"]:
                s += f" → {', '.join(issue['replacements'][:3])}"
            suggestions.append(s)
        return suggestions

    def calculate_grammar_score(self, text: str) -> float:
        """Score between 0.0 and 1.0."""
        if not text or len(text.strip()) == 0:
            return 0.0

        word_count = len(text.split())
        if word_count == 0:
            return 0.0

        error_count = self.count_errors(text)
        error_density = (error_count / word_count) * 100

        # More lenient: 0 errors = 1.0, 10+ per 100 words = 0.0
        score = max(0.0, 1.0 - (error_density / 10.0))
        return round(score, 4)

    def get_corrected_text(self, text: str) -> str:
        tool = self.tool
        if tool is None:
            return text
        try:
            return tool.correct(text)
        except Exception:
            return text


# Singleton
grammar_checker = GrammarChecker()
