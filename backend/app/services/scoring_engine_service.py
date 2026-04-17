from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class ScoringEngineService:
    def quick_text_score(self, *, answer_text: str | None, expected_keywords: list[str] | None = None) -> float:
        if not answer_text:
            return 0.0
        text = answer_text.strip().lower()
        if not text:
            return 0.0

        words = text.split()
        length_factor = min(len(words) / 120.0, 1.0)

        keyword_factor = 0.0
        keywords = expected_keywords or []
        if keywords:
            hits = sum(1 for kw in keywords if kw.lower() in text)
            keyword_factor = hits / len(keywords)

        score = 0.65 * length_factor + 0.35 * keyword_factor
        return round(max(0.0, min(score, 1.0)), 4)

    def quick_code_score(self, *, code: str | None, tests_passed_ratio: float | None = None) -> float:
        if not code:
            return 0.0

        loc = len([line for line in code.splitlines() if line.strip()])
        structure = min(loc / 80.0, 1.0)
        tests_factor = tests_passed_ratio if tests_passed_ratio is not None else 0.5
        score = 0.5 * structure + 0.5 * max(0.0, min(tests_factor, 1.0))
        return round(score, 4)

    def plagiarism_similarity(self, *, candidate_code: str, baseline_code: str) -> float:
        if not candidate_code or not baseline_code:
            return 0.0
        return round(SequenceMatcher(None, candidate_code, baseline_code).ratio(), 4)

    def aggregate_stage_score(self, scores: list[float]) -> float:
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 4)
