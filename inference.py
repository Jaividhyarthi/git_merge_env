import os
import sys
import json
import textwrap
import types
from typing import Optional
from openai import OpenAI

# ── Path Setup (must happen FIRST) ────────────────────────────────────────────
sys.path.insert(0, "/app")
sys.path.insert(0, "/app/server")  # Ensure merge_environment is findable

# ── Patch the missing 'tasks' package ─────────────────────────────────────────
tasks_pkg = types.ModuleType("tasks")
tasks_pkg.__path__ = ["/app"]
sys.modules["tasks"] = tasks_pkg

import task_data as _td
import grader as _gr
sys.modules["tasks.task_data"] = _td
sys.modules["tasks.grader"] = _gr

# ── Core Imports (single, clean — no duplicates) ──────────────────────────────
from models import MergeAction, MergeObservation

# Try server.merge_environment first, fall back to merge_environment
try:
    from server.merge_environment import MergeEnvironment
except ImportError:
    from merge_environment import MergeEnvironment

# ── Configuration ─────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME   = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
MAX_STEPS    = 15
TEMPERATURE  = 0.1
MAX_TOKENS   = 2000

SYSTEM_PROMPT = textwrap.dedent("""\
You are an expert software engineer resolving git merge conflicts.
You interact with a merge conflict resolution environment via JSON actions.

Each action is a JSON object with these fields:
- "action_type": one of "resolve_conflict", "view_context", or "submit"
- "conflict_index": (integer) index of the conflict block
- "resolution_text": (string) resolved code, required for resolve_conflict

STRATEGY:
1. Read ALL conflicts first, understand both sides.
2. Resolve each conflict using "resolve_conflict".
3. After ALL conflicts resolved, call "submit".

RULES:
- resolution_text must have NO conflict markers (<<<<<<<, =======, >>>>>>>).
- Feature branch (theirs) usually has the correct newer changes.
- Watch for semantic dependencies (renamed methods must be updated in callers too).
- Respond with ONLY a single raw JSON object. No markdown, no backticks.
""")


def parse_action(text: str) -> Optional[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(l for l in text.split("\n") if not l.strip().startswith("```")).strip()
    try:
        a = json.loads(text)
        if isinstance(a, dict) and "action_type" in a:
            return a
    except json.JSONDecodeError:
        pass
    idx = text.find("{")
    if idx != -1:
        s = text[idx:]
        depth = 0
        for i, c in enumerate(s):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        a = json.loads(s[:i + 1])
                        if isinstance(a, dict) and "action_type" in a:
                            return a
                    except Exception:
                        break
    return None


def build_message(obs: MergeObservation, step: int) -> str:
    cinfo = ""
    for c in obs.conflicts:
        status = "RESOLVED" if c["resolved"] else "UNRESOLVED"
        cinfo += f"\n--- Conflict {c['index']} [{status}] ---\n"
        if not c["resolved"]:
            cinfo += f"OURS:\n{c['ours']}\n\nTHEIRS:\n{c['theirs']}\n"
        else:
            cinfo += "(resolved)\n"
    return (
        f"Step {step}/{MAX_STEPS} | Task: {obs.task_id} | "
        f"Resolved: {obs.num_conflicts_resolved}/{obs.num_conflicts_total} | "
        f"Score: {obs.score:.4f}\nFeedback: {obs.feedback}\n"
        f"\n=== CONFLICTS ==={cinfo}\n=== FILE ===\n{obs.file_content}\n\n"
        f"Respond with ONE JSON action."
    )


def run_task(env: MergeEnvironment, client: OpenAI, task_id: str) -> float:
    print(f"[START] task={task_id}", flush=True)
    try:
        obs = env.reset(task_id=task_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for step in range(1, MAX_STEPS + 1):
            messages.append({"role": "user", "content": build_message(obs, step)})
            try:
                resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                )
                llm_out = resp.choices[0].message.content or ""
            except Exception as e:
                print(f"LLM error step {step}: {e}", file=sys.stderr, flush=True)
                llm_out = '{"action_type": "submit"}'

            messages.append({"role": "assistant", "content": llm_out})
            ad = parse_action(llm_out) or {"action_type": "submit"}
            obs = env.step(MergeAction(
                action_type=ad.get("action_type", "submit"),
                conflict_index=ad.get("conflict_index"),
                resolution_text=ad.get("resolution_text"),
            ))
            print(f"[STEP] step={step} reward={obs.reward:.4f}", flush=True)
            if obs.done:
                print(f"[END] task={task_id} score={obs.score:.4f} steps={step}", flush=True)
                return obs.score

        # Force submit if MAX_STEPS reached without done
        obs = env.step(MergeAction(action_type="submit"))
        print(f"[END] task={task_id} score={obs.score:.4f} steps={MAX_STEPS}", flush=True)
        return obs.score

    except Exception as e:
        # CRITICAL: Even on crash, emit [END] so the evaluator captures something
        print(f"[END] task={task_id} score=0.0000 steps=0", flush=True)
        print(f"Task {task_id} crashed: {e}", file=sys.stderr, flush=True)
        return 0.0


def main():
    print(f"API: {API_BASE_URL} | Model: {MODEL_NAME}", file=sys.stderr, flush=True)
    if not API_KEY:
        print("ERROR: No API key. Set HF_TOKEN or API_KEY.", file=sys.stderr, flush=True)
        # Emit dummy output so evaluator doesn't fail on missing blocks
        for task_id in ["easy", "medium", "hard"]:
            print(f"[START] task={task_id}", flush=True)
            print(f"[STEP] step=1 reward=0.0000", flush=True)
            print(f"[END] task={task_id} score=0.0000 steps=1", flush=True)
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = MergeEnvironment()
    scores = {}

    for task_id in ["easy", "medium", "hard"]:
        scores[task_id] = run_task(env, client, task_id)

    avg = sum(scores.values()) / len(scores)
    print(
        f"[DONE] easy={scores['easy']:.4f} medium={scores['medium']:.4f} "
        f"hard={scores['hard']:.4f} avg={avg:.4f}",
        flush=True,
    )


if __name__ == "__main__":
    main()