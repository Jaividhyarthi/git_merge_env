---
title: Git Merge Env
emoji: ??
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Git Merge Conflict Resolution Environment

An OpenEnv environment where AI agents learn to resolve **real git merge conflicts** in Python source files. Every developer encounters merge conflicts — this environment provides a standardized, graded testbed for evaluating how well AI agents can understand code structure, detect semantic dependencies, and produce clean, correct resolutions.

## Motivation

Merge conflict resolution is one of the most common — and most error-prone — tasks in professional software development. It requires understanding both sides of a change, reasoning about code semantics, and producing a resolution that preserves correctness. Unlike toy environments, this directly models a task that every engineering team faces daily.

This environment fills a gap in the OpenEnv ecosystem by targeting **code comprehension and editing** — a skill critical for coding agents, PR review bots, and AI-assisted development tools.

## Environment Overview

The agent receives a Python source file containing git merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`). It must:

1. **Analyze** each conflict block (view both "ours" and "theirs" sides)
2. **Resolve** each conflict by providing the correct merged code
3. **Submit** the final resolution for grading

The environment grades resolutions against a deterministic ground truth, providing partial credit based on how much of the file is correctly resolved.

## Action Space

Actions are JSON objects with the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action_type` | string | Yes | One of: `resolve_conflict`, `view_context`, `submit` |
| `conflict_index` | int | For resolve/view | 0-based index of the conflict block |
| `resolution_text` | string | For resolve | The resolved code (no conflict markers) |

**Action types:**
- `resolve_conflict`: Replace a conflict block with resolved code
- `view_context`: Get detailed view of a conflict block's ours/theirs sides
- `submit`: Finalize the resolution and receive the final score

## Observation Space

Each observation includes:

| Field | Type | Description |
|-------|------|-------------|
| `file_content` | string | Current file content (with remaining conflict markers) |
| `conflicts` | list[dict] | Each conflict's `index`, `ours`, `theirs`, `resolved` status |
| `num_conflicts_total` | int | Total conflict blocks in the task |
| `num_conflicts_resolved` | int | How many have been resolved so far |
| `task_id` | string | Current task: `easy`, `medium`, or `hard` |
| `task_description` | string | Human-readable task description |
| `feedback` | string | Feedback on the last action |
| `score` | float | Current partial score (0.0–1.0) |
| `done` | bool | Whether the episode has ended |
| `reward` | float | Step reward signal |

## Tasks

### Task 1: Easy — Config File (1 conflict)
A Python config file where two branches changed database connection settings. The feature branch (`feature/db-migration`) has the correct updated settings. Straightforward accept-theirs resolution.

### Task 2: Medium — Utility Module (3 conflicts)
A data processing module with three independent conflicts: import statements, constants, and a function body. The feature branch (`feature/enhanced-parsing`) adds regex support, larger batch sizes, and a fallback parser. Each conflict can be resolved independently.

### Task 3: Hard — User Service Class (5 conflicts)
A user management service where the feature branch (`feature/rbac`) renames methods (`add_user` → `create_user`, `get_user` → `find_user`), adds new fields (`role`, `last_login`), and introduces new methods. **Critical:** Conflicts have semantic dependencies — the `deactivate_user` method and `create_default_admin` function must call the renamed methods. Resolving one conflict incorrectly cascades into others.

### Expected Difficulty
| Task | Conflicts | Semantic Dependencies | Expected Score (frontier model) |
|------|-----------|----------------------|-------------------------------|
| Easy | 1 | None | ~1.0 |
| Medium | 3 | None | ~0.9–1.0 |
| Hard | 5 | Yes (method renames) | ~0.7–0.9 |

## Reward Design

The reward function provides signal throughout the episode:

- **Partial credit per conflict**: +0.1 reward for each newly resolved conflict
- **Re-resolution**: +0.02 if updating a previously resolved conflict
- **Invalid actions**: -0.02 to -0.05 penalty for errors (bad index, missing fields, unknown action type)
- **Final score** (on submit): 0.0–1.0 based on line-level similarity to ground truth, with bonuses for removing all conflict markers and exact match
- **Unresolved marker penalty**: Remaining conflict markers reduce the final score

The grading formula: `score = line_similarity × 0.9 + no_markers_bonus × 0.1 - marker_penalty`

## Setup & Usage

### Prerequisites
- Python 3.10+
- Docker (for containerized deployment)

### Local Development
```bash
# Install dependencies
pip install "openenv-core[core]>=0.2.1" fastapi uvicorn pydantic openai

# Test the environment directly
python test_env.py

# Run the server locally
cd git_merge_env
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Docker
```bash
docker build -t git-merge-env .
docker run -p 7860:7860 git-merge-env
```

### Inference
```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct"
export HF_TOKEN="your-token-here"

python inference.py
```

### Hugging Face Space
```bash
openenv push --repo-id your-username/git-merge-env
```

## Baseline Scores

Scores from running `inference.py` with baseline model:

| Task | Score |
|------|-------|
| Easy | ~1.0 |
| Medium | ~0.85–1.0 |
| Hard | ~0.65–0.85 |
| **Average** | **~0.83–0.95** |

*(Actual scores depend on the model used. Ground truth resolution achieves 1.0 on all tasks.)*

## Project Structure
```
git_merge_env/
├── __init__.py              # Package exports
├── models.py                # Pydantic Action/Observation/State models
├── client.py                # EnvClient for WebSocket interaction
├── openenv.yaml             # OpenEnv manifest
├── pyproject.toml           # Package config
├── Dockerfile               # Container definition
├── inference.py             # Baseline inference script
├── test_env.py              # Direct environment test
├── README.md                # This file
├── tasks/
│   ├── __init__.py
│   ├── task_data.py         # Task definitions & ground truth
│   └── grader.py            # Deterministic grading logic
└── server/
    ├── __init__.py
    ├── merge_environment.py # Core environment logic
    └── app.py               # FastAPI application
```

## License

MIT


