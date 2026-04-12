"""
Direct test of the Git Merge Conflict Resolution Environment.
Run: python test_env.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import MergeAction
from server.merge_environment import MergeEnvironment
from tasks.task_data import TASKS


def test_task(env, task_id):
    """Test a task by resolving conflicts with the theirs side."""
    print(f"\n--- Testing {task_id} ---")
    obs = env.reset(task_id=task_id)
    print(f"  Conflicts: {obs.num_conflicts_total}")

    # Resolve each conflict by accepting "theirs"
    for c in obs.conflicts:
        obs = env.step(MergeAction(
            action_type="resolve_conflict",
            conflict_index=c["index"],
            resolution_text=c["theirs"],
        ))
        print(f"  Resolved conflict {c['index']}: score={obs.score:.4f}")

    # Submit
    obs = env.step(MergeAction(action_type="submit"))
    print(f"  Submitted: score={obs.score:.4f}, done={obs.done}")
    return obs.score


def main():
    env = MergeEnvironment()
    scores = {}
    for task_id in ["easy", "medium", "hard"]:
        scores[task_id] = test_task(env, task_id)

    print(f"\n{'='*40}")
    print("Scores (accepting 'theirs' for all):")
    for tid, s in scores.items():
        print(f"  {tid}: {s:.4f}")
    avg = sum(scores.values()) / len(scores)
    print(f"  avg: {avg:.4f}")

    # Also test exact ground truth
    print(f"\n{'='*40}")
    print("Scores (exact ground truth):")
    from tasks.grader import grade_resolution
    for tid in ["easy", "medium", "hard"]:
        r = grade_resolution(tid, TASKS[tid]["ground_truth"])
        print(f"  {tid}: {r['score']:.4f}")


if __name__ == "__main__":
    main()
