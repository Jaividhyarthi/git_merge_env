"""
Models for Git Merge Conflict Resolution Environment.

Defines typed Action, Observation, and State models for the OpenEnv spec.
"""

from typing import Dict, List, Optional, Any
from pydantic import Field
from openenv.core.env_server.types import Action, Observation, State


class MergeAction(Action):
    """Action the agent can take to resolve merge conflicts."""

    action_type: str = Field(
        ...,
        description=(
            "Type of action: 'resolve_conflict', 'view_context', or 'submit'. "
            "'resolve_conflict' resolves a specific conflict block. "
            "'view_context' shows expanded context around a conflict. "
            "'submit' finalizes the resolution and ends the episode."
        ),
    )
    conflict_index: Optional[int] = Field(
        default=None,
        description="Index of the conflict block to resolve (0-based). Required for 'resolve_conflict' and 'view_context'.",
    )
    resolution_text: Optional[str] = Field(
        default=None,
        description="The resolved text to replace the conflict block. Required for 'resolve_conflict'.",
    )


class ConflictBlock(Action):
    """Description of a single merge conflict in the file."""

    index: int = Field(..., description="0-based index of the conflict block")
    ours: str = Field(..., description="Content from the current branch (HEAD)")
    theirs: str = Field(..., description="Content from the incoming branch")
    resolved: bool = Field(default=False, description="Whether this conflict has been resolved")


class MergeObservation(Observation):
    """Observation returned after each action in the merge environment."""

    file_content: str = Field(..., description="Current file content with any remaining conflict markers")
    conflicts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of conflict blocks with 'index', 'ours', 'theirs', 'resolved' fields",
    )
    num_conflicts_total: int = Field(default=0, description="Total number of conflict blocks in this task")
    num_conflicts_resolved: int = Field(default=0, description="Number of conflicts resolved so far")
    task_id: str = Field(default="", description="Current task identifier (easy, medium, hard)")
    task_description: str = Field(default="", description="Human-readable description of the task")
    feedback: str = Field(default="", description="Feedback on the last action taken")
    score: float = Field(default=0.0, description="Current partial score (0.0 to 1.0)")


class MergeState(State):
    """Extended state for the merge environment."""

    task_id: str = Field(default="", description="Current task identifier")
    conflicts_resolved: int = Field(default=0, description="Conflicts resolved so far")
    conflicts_total: int = Field(default=0, description="Total conflicts in this task")
    submitted: bool = Field(default=False, description="Whether the agent has submitted")
