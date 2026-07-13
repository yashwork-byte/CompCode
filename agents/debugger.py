from dotenv import load_dotenv
load_dotenv()

import os
import re
import json
import shlex
import subprocess

from openai import OpenAI
client = OpenAI()

# Execution is OFF by default. The debugger runs model-generated shell
# commands, so it must be explicitly enabled by the operator.
EXEC_ENABLED = os.getenv("CODECOMP_ALLOW_EXEC", "").lower() in {"1", "true", "yes"}

COMMAND_TIMEOUT = 20  # seconds

# Patterns we refuse to run even when execution is enabled. This is a
# backstop against catastrophic commands, not a complete sandbox.
_DANGEROUS_PATTERNS = [
    r"\brm\s+-[a-z]*r[a-z]*f",   # rm -rf / rm -fr
    r"\brm\s+-[a-z]*f[a-z]*r",
    r":\(\)\s*\{",                # fork bomb
    r"\bmkfs\b",
    r"\bdd\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bsudo\b",
    r">\s*/dev/sd",
    r"\bchmod\s+-R\b",
    r"\bcurl\b.*\|\s*(ba)?sh",    # curl ... | sh
    r"\bwget\b.*\|\s*(ba)?sh",
    r"\bgit\s+push\b",
]


def _is_dangerous(cmd: str) -> bool:
    return any(re.search(p, cmd) for p in _DANGEROUS_PATTERNS)


def run_command(cmd: str) -> str:
    """Run a shell command safely and return captured output.

    - Execution is disabled unless CODECOMP_ALLOW_EXEC is set.
    - Obviously destructive commands are refused.
    - stdout/stderr are captured and returned (os.system only returned an
      exit code, so the agent never actually saw command output before).
    """
    if not cmd:
        return "ERROR: no command provided"

    if not EXEC_ENABLED:
        return ("EXECUTION DISABLED: set CODECOMP_ALLOW_EXEC=1 to allow the "
                f"debugger to run shell commands. Proposed command: {cmd}")

    if _is_dangerous(cmd):
        return f"REFUSED: command matched a dangerous pattern and was not run: {cmd}"

    try:
        proc = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except FileNotFoundError:
        return f"ERROR: command not found: {cmd}"
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {COMMAND_TIMEOUT}s: {cmd}"
    except Exception as e:
        return f"ERROR: {e}"

    parts = [f"exit_code={proc.returncode}"]
    if proc.stdout:
        parts.append(f"stdout:\n{proc.stdout.strip()}")
    if proc.stderr:
        parts.append(f"stderr:\n{proc.stderr.strip()}")
    return "\n".join(parts)


SYSTEM_PROMPT = '''
You are a code debugging agent.

You have access to one tool:
- run_command(cmd: str): runs a shell command and returns its output.

You MUST respond with a single valid JSON object using double quotes, with
exactly these keys:

{
    "thought": "what you are thinking",
    "action": "run_command" or "DONE",
    "cmd": "shell command, required when action is run_command",
    "final_answer": "your answer, required when action is DONE"
}

STRICT RULES:
1. If the query involves any file operation (create, delete, modify, write),
   you MUST use run_command and observe the real result before answering.
2. NEVER claim a file does or does not exist without running a command.
3. Attempt the command first, then read the observation, then continue.
4. Do not add prose outside the JSON object.
5. Only use "DONE" after the required commands have been executed.
'''


def debugger_agent(query, context, max_steps=5):
    # Per-call history so one query's steps don't leak into the next.
    history = []

    for _ in range(max_steps):
        messages = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f'Query : {query}\n Context :\n {context}'},
        ]
        for h in history:
            messages.append(h)

        response = client.chat.completions.create(
            model='gpt-4.1-mini',
            messages=messages,
            response_format={"type": "json_object"},
        )

        output = response.choices[0].message.content

        try:
            data = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return output

        action = data.get("action")

        if action == "DONE":
            return data.get("final_answer", "Done")

        if action == "run_command":
            result = run_command(data.get("cmd"))
            history.append({'role': 'assistant', 'content': output})
            history.append({'role': 'user', 'content': f"Observation: {result}"})
        else:
            return "Invalid action"

    return "Max steps reached"
