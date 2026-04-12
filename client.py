"""
Client for the Git Merge Conflict Resolution Environment.

Provides a typed WebSocket-based client for interacting with the merge environment server.
"""

from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from .models import MergeAction, MergeObservation, MergeState


class GitMergeEnv(EnvClient[MergeAction, MergeObservation, MergeState]):
    """Client for the Git Merge Conflict Resolution environment."""

    def _step_payload(self, action: MergeAction) -> dict:
        return {
            "action_type": action.action_type,
            "conflict_index": action.conflict_index,
            "resolution_text": action.resolution_text,
        }

    def _parse_result(self, payload: dict) -> StepResult[MergeObservation]:
        obs = MergeObservation(**payload["observation"])
        return StepResult(
            observation=obs,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> MergeState:
        return MergeState(**payload)
