"""
Meeting agent: lets the user start and stop meeting recordings via chat.

Tools:
- start_recording(project, topic): launch recorder.py in the background
- stop_recording(): send SIGTERM to the active recorder; post-processing runs automatically
- recording_status(): return current state

State is stored in data/recordings/.active.json.
"""
import asyncio
import json
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from project_context import PROJECT_CONTEXT
from user_profile import USER_PROFILE


# ===== Configuration =====
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RECORDINGS_DIR = PROJECT_ROOT / "data" / "recordings"
ACTIVE_FILE = RECORDINGS_DIR / ".active.json"
RECORDER_SCRIPT = PROJECT_ROOT / "agents" / "notes" / "recorder.py"

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


# ===== LLM =====
llm = ChatOpenAI(
    base_url="http://localhost:4000/v1",
    api_key="sk-cos-local-dev",
    model="granite-tiny",
    temperature=0,
)


# ===== Helpers for the active state file =====
def load_active() -> dict | None:
    """Return the active recording state, or None if no recording is running."""
    if not ACTIVE_FILE.exists():
        return None
    try:
        return json.loads(ACTIVE_FILE.read_text())
    except Exception:
        return None


def save_active(state: dict):
    """Persist the active recording state."""
    ACTIVE_FILE.write_text(json.dumps(state, indent=2))


def clear_active():
    """Remove the active state file."""
    if ACTIVE_FILE.exists():
        ACTIVE_FILE.unlink()


def is_pid_running(pid: int) -> bool:
    """Return True if the given PID is still alive."""
    try:
        os.kill(pid, 0)  # signal 0 just tests existence
        return True
    except OSError:
        return False


# ===== Tools =====
@tool
def start_recording(project: str = "default", topic: str = "") -> str:
    """
    Start a meeting recording in the background.

    The recorder runs in a detached subprocess. Use stop_recording() to end it.

    Args:
        project: Free-form project tag (e.g., "q2-roadmap", "client_x"). Hyphens, underscores, lowercase all OK.
        topic: Optional free-text meeting topic. Empty string is fine.

    Returns:
        Confirmation string with PID and target file.
    """
    # Refuse to start if a recording is already active
    existing = load_active()
    if existing and is_pid_running(existing["pid"]):
        return (
            f"⚠️  A recording is already in progress.\n"
            f"   PID: {existing['pid']}\n"
            f"   Project: {existing['project']}\n"
            f"   Topic: {existing['topic'] or '(none)'}\n"
            f"   Started at: {existing['started_at']}\n"
            f"   → Stop it first with stop_recording()."
        )
    elif existing:
        # Stale state file (PID dead) — clean it up silently
        clear_active()

    # Build the command
    venv_python = Path(sys.executable)
    cmd = [str(venv_python), str(RECORDER_SCRIPT), "start", "--project", project]
    if topic:
        cmd.extend(["--topic", topic])

    # Use a session name so the WAV file has the project in it
    session_name = project if project != "default" else "meeting"
    cmd.extend(["--name", session_name])

    # Launch in background, with new session group so SIGTERM hits only the recorder
    log_path = PROJECT_ROOT / "logs" / "recorder.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(log_path, "ab") as logf:
            proc = subprocess.Popen(
                cmd,
                stdout=logf,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                cwd=str(PROJECT_ROOT),
            )
    except Exception as e:
        return f"❌ Could not start recorder: {e}"

    # Save active state
    started_at = datetime.now().isoformat(timespec="seconds")
    state = {
        "pid": proc.pid,
        "project": project,
        "topic": topic,
        "started_at": started_at,
        "log_file": str(log_path),
    }
    save_active(state)

    return (
        f"✅ Recording started.\n"
        f"   PID: {proc.pid}\n"
        f"   Project: {project}\n"
        f"   Topic: {topic or '(none)'}\n"
        f"   Started at: {started_at}\n"
        f"   Logs: {log_path}\n"
        f"\n"
        f"→ When done, just say 'stop' and I'll close it cleanly.\n"
        f"   Transcription and summary will be generated automatically."
    )


@tool
def stop_recording() -> str:
    """
    Stop the active meeting recording.

    Sends SIGTERM to the recorder subprocess. The recorder will then trigger
    transcription, structured summary, and Qdrant indexing automatically.
    """
    state = load_active()
    if not state:
        return "ℹ️  No active recording to stop."

    pid = state["pid"]

    if not is_pid_running(pid):
        clear_active()
        return (
            f"ℹ️  The recorder (PID {pid}) is no longer running.\n"
            f"   It probably stopped on its own; check the recorder.log for details.\n"
            f"   State file cleared."
        )

    # Send SIGTERM
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        return f"❌ Could not send SIGTERM to PID {pid}: {e}"

    clear_active()

    return (
        f"⏹️  Stop signal sent to recorder (PID {pid}).\n"
        f"   Project: {state['project']}\n"
        f"   Topic: {state['topic'] or '(none)'}\n"
        f"   Started at: {state['started_at']}\n"
        f"\n"
        f"→ Transcription and structured summary are running in the background.\n"
        f"   Once finished, the meeting note will appear in vault/meetings/YYYY/MM/.\n"
        f"   You can follow progress with: tail -f logs/recorder.log"
    )


@tool
def recording_status() -> str:
    """Return the status of the current recording, if any."""
    state = load_active()
    if not state:
        return "ℹ️  No active recording."

    pid = state["pid"]
    if not is_pid_running(pid):
        clear_active()
        return f"ℹ️  Recorder PID {pid} is no longer alive. State file cleared."

    return (
        f"🎙️  Recording in progress.\n"
        f"   PID: {pid}\n"
        f"   Project: {state['project']}\n"
        f"   Topic: {state['topic'] or '(none)'}\n"
        f"   Started at: {state['started_at']}"
    )


# ===== System prompt template =====
SYSTEM_PROMPT_TEMPLATE = f"""You are the Meeting agent. You pilot meeting audio recordings.

═══════════════════════════════════════════════
🌐 LANGUAGE RULE — READ FIRST
You MUST respond ENTIRELY in {{user_language}}.
The PROFILE and CONTEXT below are in English, but your response
must be in {{user_language}}. No mixing of languages.
═══════════════════════════════════════════════

{USER_PROFILE}

{PROJECT_CONTEXT}

You have 3 tools:
- start_recording(project, topic): start the audio recording
- stop_recording(): stop the recording (transcription + summary auto-generated after)
- recording_status(): check current state

Strict rules:
1. To start: call start_recording. project is free-form (any string, hyphens OK, lowercase preferred). topic can be empty ("").
2. To stop: call stop_recording.
3. For status: call recording_status.
4. Faithfully report the tool's output in your response — do not reformulate or hide warnings.
5. NEVER invent a meeting summary. The summary is generated automatically after stop_recording, in vault/meetings/.
6. If the user asks for a summary or describes content "from the meeting", reply that summaries are produced automatically by the post-processing pipeline (not by you), and direct them to the Notes or Researcher agent to retrieve a finished summary.

Final output is in {{user_language}}. Be brief.
"""


# ===== Cached agents per language =====
_agents: dict[str, object] = {}


def _get_agent(user_language: str):
    """Build the Meeting agent (no MCP tools needed), cached per language."""
    if user_language not in _agents:
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(user_language=user_language)
        _agents[user_language] = create_agent(
            model=llm,
            tools=[start_recording, stop_recording, recording_status],
            system_prompt=system_prompt,
        )
    return _agents[user_language]


async def invoke_meeting(user_message: str, user_language: str = "French") -> str:
    """Async entry point for the Meeting agent."""
    agent = _get_agent(user_language)
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=user_message)],
    })
    return result["messages"][-1].content


def invoke_meeting_sync(user_message: str, user_language: str = "French") -> str:
    """Synchronous wrapper for CLI use."""
    return asyncio.run(invoke_meeting(user_message, user_language))


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "What's the status of any active recording?"
    print(f"\n❓ {q}\n")
    print(invoke_meeting_sync(q, "English"))