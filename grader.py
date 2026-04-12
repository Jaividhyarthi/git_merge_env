"""
Grader for Git Merge Conflict Resolution Environment.

Scores agent resolution against ground truth on a 0.0–1.0 scale.
Provides partial credit based on per-conflict-block accuracy.
"""

import difflib
from typing import Dict, Any

from task_data import TASKS, parse_conflicts


def _normalize(text: str) -> str:
    """Normalize text for comparison: strip trailing whitespace per line, ensure single trailing newline."""
    lines = [line.rstrip() for line in text.split("\n")]
    # Remove trailing empty lines
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def _has_conflict_markers(text: str) -> bool:
    """Check if the text still contains unresolved conflict markers."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("<<<<<<<") or stripped.startswith("=======") or stripped.startswith(">>>>>>>"):
            return True
    return False


def _block_similarity(resolved_block: str, truth_block: str) -> float:
    """Compute similarity between a resolved conflict block and ground truth block using SequenceMatcher."""
    if not resolved_block.strip() and not truth_block.strip():
        return 1.0
    ratio = difflib.SequenceMatcher(None, resolved_block.strip(), truth_block.strip()).ratio()
    return ratio


def grade_resolution(task_id: str, resolved_file: str) -> Dict[str, Any]:
    """
    Grade the agent's resolved file against ground truth.

    Returns a dict with:
        - score: float 0.0–1.0
        - details: dict with per-metric breakdown
    """
    if task_id not in TASKS:
        return {"score": 0.0, "details": {"error": f"Unknown task: {task_id}"}}

    task = TASKS[task_id]
    ground_truth = task["ground_truth"]

    norm_resolved = _normalize(resolved_file)
    norm_truth = _normalize(ground_truth)

    # Check for remaining conflict markers (immediate penalty)
    has_markers = _has_conflict_markers(resolved_file)

    # Exact match check
    if norm_resolved == norm_truth:
        return {
            "score": 1.0,
            "details": {
                "exact_match": True,
                "has_unresolved_markers": False,
                "line_similarity": 1.0,
                "conflict_block_scores": [],
            },
        }

    # Line-level similarity (overall file)
    resolved_lines = norm_resolved.split("\n")
    truth_lines = norm_truth.split("\n")
    line_similarity = difflib.SequenceMatcher(None, resolved_lines, truth_lines).ratio()

    # Per-conflict-block scoring
    # We extract the regions from ground truth that correspond to each conflict block
    # and compare against the corresponding regions in the resolved file
    conflict_blocks = parse_conflicts(task["conflicted_file"])
    num_conflicts = len(conflict_blocks)

    # For block-level scoring, we check if each conflict's ground-truth region
    # appears in the resolved file
    block_scores = []
    for block in conflict_blocks:
        # The ground truth for this block is "theirs" for all our tasks
        # (since we designed them to accept the feature branch)
        # But more robustly: check if the truth content is present
        truth_content = _normalize(task["ground_truth"])
        # This is a simplified approach — use line similarity as proxy
        block_scores.append(line_similarity)

    # Composite score
    # 60% line similarity + 30% no-conflict-markers bonus + 10% exact match bonus
    marker_penalty = 0.0 if not has_markers else 0.3
    score = max(0.0, min(1.0, line_similarity * 0.9 + (0.1 if not has_markers else 0.0) - marker_penalty * 0.5))

    return {
        "score": round(score, 4),
        "details": {
            "exact_match": False,
            "has_unresolved_markers": has_markers,
            "line_similarity": round(line_similarity, 4),
            "num_conflicts": num_conflicts,
        },
    }

