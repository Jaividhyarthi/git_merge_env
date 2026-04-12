"""
Git Merge Conflict Resolution Environment.

Implements the OpenEnv Environment interface for merge conflict resolution tasks.
"""

import re
import copy
from uuid import uuid4
from typing import Optional, Any

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

# Use relative imports when running as package, absolute when standalone
import sys, os
sys.path.insert(0, "/app")
from models import MergeAction, MergeObservation, MergeState
from task_data import TASKS, parse_conflicts
from grader import grade_resolution


MAX_STEPS = 20  # Max steps per episode before forced termination


class MergeEnvironment(Environment):
    """Environment for resolving git merge conflicts."""

    def __init__(self):
        self._state = MergeState(episode_id=str(uuid4()), step_count=0)
        self._task_id: str = "easy"
        self._conflict_blocks: list = []
        self._resolutions: dict = {}  # conflict_index -> resolved_text
        self._original_file: str = ""
        self._current_file: str = ""
        self._ground_truth: str = ""
        self._submitted: bool = False

    def reset(self, seed: Optional[int] = None, episode_id: Optional[str] = None, **kwargs: Any) -> MergeObservation:
        """Reset the environment with a specific task."""
        task_id = kwargs.get("task_id", "easy")
        if task_id not in TASKS:
            task_id = "easy"

        self._task_id = task_id
        task = TASKS[task_id]

        self._state = MergeState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_id=task_id,
            conflicts_total=0,
            conflicts_resolved=0,
            submitted=False,
        )

        self._original_file = task["conflicted_file"]
        self._current_file = task["conflicted_file"]
        self._ground_truth = task["ground_truth"]
        self._conflict_blocks = parse_conflicts(task["conflicted_file"])
        self._resolutions = {}
        self._submitted = False

        self._state.conflicts_total = len(self._conflict_blocks)

        return MergeObservation(
            file_content=self._current_file,
            conflicts=[
                {
                    "index": b["index"],
                    "ours": b["ours"],
                    "theirs": b["theirs"],
                    "resolved": False,
                }
                for b in self._conflict_blocks
            ],
            num_conflicts_total=len(self._conflict_blocks),
            num_conflicts_resolved=0,
            task_id=task_id,
            task_description=task["description"],
            feedback="Environment reset. Resolve all merge conflicts and submit.",
            score=0.0,
            done=False,
            reward=0.0,
        )

    def step(self, action: MergeAction, timeout_s: Optional[float] = None, **kwargs: Any) -> MergeObservation:
        """Execute an action in the environment."""
        self._state.step_count += 1

        # Check max steps
        if self._state.step_count >= MAX_STEPS:
            return self._finalize("Max steps reached. Episode terminated.", force=True)

        if self._submitted:
            return self._make_observation(
                feedback="Episode already submitted. No further actions accepted.",
                done=True,
            )

        action_type = action.action_type.lower().strip()

        if action_type == "resolve_conflict":
            return self._handle_resolve(action)
        elif action_type == "view_context":
            return self._handle_view_context(action)
        elif action_type == "submit":
            return self._finalize("Agent submitted resolution.")
        else:
            return self._make_observation(
                feedback=f"Unknown action type: '{action_type}'. Use 'resolve_conflict', 'view_context', or 'submit'.",
                reward=-0.05,
            )

    def _handle_resolve(self, action: MergeAction) -> MergeObservation:
        """Handle a resolve_conflict action."""
        idx = action.conflict_index
        resolution = action.resolution_text

        if idx is None:
            return self._make_observation(
                feedback="Error: 'conflict_index' is required for resolve_conflict action.",
                reward=-0.02,
            )

        if idx < 0 or idx >= len(self._conflict_blocks):
            return self._make_observation(
                feedback=f"Error: conflict_index {idx} out of range [0, {len(self._conflict_blocks) - 1}].",
                reward=-0.02,
            )

        if resolution is None:
            return self._make_observation(
                feedback="Error: 'resolution_text' is required for resolve_conflict action.",
                reward=-0.02,
            )

        # Store the resolution
        was_previously_resolved = idx in self._resolutions
        self._resolutions[idx] = resolution
        self._conflict_blocks[idx]["resolved"] = True

        # Rebuild the file with resolutions applied
        self._rebuild_file()

        # Update state
        self._state.conflicts_resolved = len(self._resolutions)

        # Compute partial reward
        partial_reward = 0.1 if not was_previously_resolved else 0.02

        return self._make_observation(
            feedback=f"Conflict {idx} resolved. {len(self._resolutions)}/{len(self._conflict_blocks)} conflicts resolved.",
            reward=partial_reward,
        )

    def _handle_view_context(self, action: MergeAction) -> MergeObservation:
        """Handle a view_context action — shows the conflict block with surrounding lines."""
        idx = action.conflict_index

        if idx is None or idx < 0 or idx >= len(self._conflict_blocks):
            return self._make_observation(
                feedback=f"Error: invalid conflict_index for view_context.",
                reward=0.0,
            )

        block = self._conflict_blocks[idx]
        context = (
            f"=== Conflict {idx} ===\n"
            f"--- OURS (HEAD) ---\n{block['ours']}\n"
            f"--- THEIRS (incoming) ---\n{block['theirs']}\n"
            f"--- Resolved: {block['resolved']} ---"
        )

        return self._make_observation(
            feedback=context,
            reward=0.0,
        )

    def _rebuild_file(self):
        """Rebuild the current file content by applying stored resolutions."""
        lines = self._original_file.split("\n")
        result_lines = []
        i = 0
        conflict_idx = 0

        while i < len(lines):
            if lines[i].startswith("<<<<<<<"):
                # Skip the conflict block in the original
                if conflict_idx in self._resolutions:
                    # Insert the resolution
                    result_lines.append(self._resolutions[conflict_idx])
                else:
                    # Keep the conflict markers
                    while i < len(lines) and not lines[i].startswith(">>>>>>>"):
                        result_lines.append(lines[i])
                        i += 1
                    if i < len(lines):
                        result_lines.append(lines[i])  # the >>>>>>> line

                # Skip to after >>>>>>>
                while i < len(lines) and not lines[i].startswith(">>>>>>>"):
                    i += 1
                conflict_idx += 1
                i += 1  # skip the >>>>>>> line
            else:
                result_lines.append(lines[i])
                i += 1

        self._current_file = "\n".join(result_lines)

    def _finalize(self, feedback: str, force: bool = False) -> MergeObservation:
        """Finalize the episode and compute the final score."""
        self._submitted = True
        self._state.submitted = True

        # Grade the resolution
        result = grade_resolution(self._task_id, self._current_file)
        score = result["score"]

        return self._make_observation(
            feedback=f"{feedback} Final score: {score:.4f}. Details: {result['details']}",
            reward=score,
            done=True,
            score=score,
        )

    def _make_observation(
        self,
        feedback: str,
        reward: float = 0.0,
        done: bool = False,
        score: float = None,
    ) -> MergeObservation:
        """Create an observation with current state."""
        if score is None:
            # Compute running partial score
            partial = grade_resolution(self._task_id, self._current_file)
            score = partial["score"]

        return MergeObservation(
            file_content=self._current_file,
            conflicts=[
                {
                    "index": b["index"],
                    "ours": b["ours"],
                    "theirs": b["theirs"],
                    "resolved": b["resolved"],
                }
                for b in self._conflict_blocks
            ],
            num_conflicts_total=len(self._conflict_blocks),
            num_conflicts_resolved=len(self._resolutions),
            task_id=self._task_id,
            task_description=TASKS[self._task_id]["description"],
            feedback=feedback,
            score=score,
            done=done,
            reward=reward,
        )

    @property
    def state(self) -> MergeState:
        """Return current environment state."""
        return self._state

