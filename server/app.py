"""
FastAPI application for the Git Merge Conflict Resolution Environment.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openenv.core.env_server import create_app
from models import MergeAction, MergeObservation
from merge_environment import MergeEnvironment


def create_merge_environment():
    """Factory function for creating MergeEnvironment instances."""
    return MergeEnvironment()


app = create_app(
    create_merge_environment,
    MergeAction,
    MergeObservation,
    env_name="git_merge_env",
)


def main():
    """Entry point for running the server."""
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

