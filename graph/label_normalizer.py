"""
graph/label_normalizer.py
==========================
Dynamic label normalization using runtime similarity detection.
Supplements the hardcoded MERGE_MAP with intelligent deduplication.

Merging strategies:
1. Case-insensitive exact match
2. Substring containment (shorter contained in longer)
3. Token-overlap similarity (Jaccard > 0.7)

All runtime-discovered merges are logged to data/merge_log.json for review.
"""

import json
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
MERGE_LOG_PATH = ROOT / "data" / "merge_log.json"


class LabelNormalizer:
    """
    Runtime label normalizer that detects similar labels and suggests canonical forms.
    Works for any domain without hardcoded domain knowledge.
    """
    
    def __init__(self, jaccard_threshold: float = 0.7):
        """
        Args:
            jaccard_threshold: Minimum Jaccard similarity to merge labels (default 0.7)
        """
        self.jaccard_threshold = jaccard_threshold
        self.merge_log = self._load_merge_log()
    
    def _load_merge_log(self) -> list:
        """Load existing merge log from disk."""
        if MERGE_LOG_PATH.exists():
            try:
                return json.loads(MERGE_LOG_PATH.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []
    
    def _save_merge_log(self) -> None:
        """Persist merge log to disk."""
        MERGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        MERGE_LOG_PATH.write_text(json.dumps(self.merge_log, indent=2, ensure_ascii=False), encoding="utf-8")
    
    def _tokenize(self, text: str) -> set:
        """
        Tokenize text into normalized word set.
        Strips punctuation, lowercases, removes stop words.
        """
        # Lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        return {t for t in tokens if t not in stop_words and len(t) > 1}
    
    def _jaccard_similarity(self, label_a: str, label_b: str) -> float:
        """Calculate Jaccard similarity between two labels."""
        tokens_a = self._tokenize(label_a)
        tokens_b = self._tokenize(label_b)
        
        if not tokens_a or not tokens_b:
            return 0.0
        
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        
        return len(intersection) / len(union) if union else 0.0
    
    def _is_substring_match(self, label_a: str, label_b: str) -> bool:
        """Check if one label is a substring of the other (case-insensitive)."""
        a_lower = label_a.lower()
        b_lower = label_b.lower()
        return a_lower in b_lower or b_lower in a_lower
    
    def _is_exact_match(self, label_a: str, label_b: str) -> bool:
        """Check if labels are exact matches (case-insensitive)."""
        return label_a.lower() == label_b.lower()
    
    def _log_merge(self, original: str, canonical: str, method: str, similarity: float) -> None:
        """Log a merge decision for human review."""
        entry = {
            "original": original,
            "canonical": canonical,
            "method": method,
            "similarity": round(similarity, 3),
            "timestamp": Path(__file__).stat().st_mtime  # Simple timestamp
        }
        self.merge_log.append(entry)
        self._save_merge_log()
    
    def normalize(self, label: str, existing_labels: list[str]) -> Optional[str]:
        """
        Find canonical form of a label by comparing against existing labels.
        
        Args:
            label: The label to normalize
            existing_labels: List of existing canonical labels in the graph
        
        Returns:
            Canonical label if a match is found, None otherwise
        """
        # Strategy 1: Exact match (case-insensitive)
        for existing in existing_labels:
            if self._is_exact_match(label, existing):
                if label != existing:  # Different case
                    self._log_merge(label, existing, "exact_case_insensitive", 1.0)
                return existing
        
        # Strategy 2: Substring containment
        # Prefer the shorter label as canonical (more general)
        for existing in existing_labels:
            if self._is_substring_match(label, existing):
                canonical = label if len(label) < len(existing) else existing
                other = existing if canonical == label else label
                similarity = len(canonical) / len(other)
                self._log_merge(other, canonical, "substring_containment", similarity)
                return canonical
        
        # Strategy 3: Token-overlap (Jaccard similarity)
        best_match = None
        best_similarity = 0.0
        
        for existing in existing_labels:
            similarity = self._jaccard_similarity(label, existing)
            if similarity >= self.jaccard_threshold and similarity > best_similarity:
                best_match = existing
                best_similarity = similarity
        
        if best_match:
            # Prefer shorter label as canonical
            canonical = label if len(label) < len(best_match) else best_match
            other = best_match if canonical == label else label
            self._log_merge(other, canonical, "token_overlap", best_similarity)
            return canonical
        
        # No match found
        return None
    
    def get_merge_stats(self) -> dict:
        """Return statistics about merge operations."""
        if not self.merge_log:
            return {
                "total_merges": 0,
                "by_method": {},
                "avg_similarity": 0.0
            }
        
        by_method = {}
        total_similarity = 0.0
        
        for entry in self.merge_log:
            method = entry["method"]
            by_method[method] = by_method.get(method, 0) + 1
            total_similarity += entry.get("similarity", 0.0)
        
        return {
            "total_merges": len(self.merge_log),
            "by_method": by_method,
            "avg_similarity": round(total_similarity / len(self.merge_log), 3) if self.merge_log else 0.0
        }


_normalizer_instance: LabelNormalizer | None = None


def get_normalizer(jaccard_threshold: float = 0.7) -> LabelNormalizer:
    """Return a module-level singleton LabelNormalizer instance."""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = LabelNormalizer(jaccard_threshold=jaccard_threshold)
    return _normalizer_instance


if __name__ == "__main__":
    # Test the normalizer
    normalizer = LabelNormalizer()
    
    existing = ["Machine Learning", "Natural Language Processing", "Computer Vision"]
    
    test_cases = [
        "machine learning",  # exact case-insensitive
        "ML",  # substring
        "Machine Learning Algorithms",  # substring
        "machine learning systems",  # token overlap
        "NLP",  # no match expected
        "Computer Vision Models",  # substring
    ]
    
    print("Label Normalizer Test")
    print("=" * 60)
    for label in test_cases:
        canonical = normalizer.normalize(label, existing)
        print(f"{label:35} → {canonical or '(new label)'}")
    
    print("\n" + "=" * 60)
    print("Merge Statistics:")
    stats = normalizer.get_merge_stats()
    print(json.dumps(stats, indent=2))
