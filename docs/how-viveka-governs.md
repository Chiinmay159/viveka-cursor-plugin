# How Viveka Governs: The Runtime, Explained

This document explains the three runtime components that power Viveka's enforcement — the **hooks**, the **daemon**, and the **MCP server**. It is written for people who want to understand what these systems do and why they exist, without needing to read code.

---

## The Core Idea

When an AI agent works inside a code editor, it takes actions: editing files, running commands, searching code. Most of these actions are fine. Some are risky. A few are dangerous.

Viveka sits between the agent and these actions. Before the agent can do something, Viveka evaluates it. The evaluation is instant, deterministic (same input always produces the same output), and costs nothing — no AI calls, no cloud services, no API keys.

The evaluation produces one of four outcomes:

| Outcome | What happens | Example |
|---------|-------------|---------|
| **Permit** | The action proceeds silently. | Reading a file. Writing a test. |
| **Warn** | The action proceeds, but the agent sees a caution note. | Editing the 14th file when the limit is 15. Touching a file that might contain secrets. |
| **Block** | The action is stopped. The agent is told why and given alternatives. | Running `rm -rf` on a protected branch. Retrying the same failing command for the 4th time. |
| **Escalate** | The action is paused and the human is asked to decide. | A destructive command on production data. The agent ignoring repeated warnings. |

These four outcomes are the universal vocabulary across all of Viveka. Every component speaks in these terms.

---

## The Three Components

### 1. Hooks — The Checkpoint

Think of hooks as security checkpoints at an airport. Every passenger (action) must pass through. The checkpoint doesn't make the rules — it just sends each passenger to the people who do.

The code editor (Cursor) has a built-in hook system. Viveka registers for five events:

- **Session start** — the editor opens a project
- **Before tool use** — the agent is about to use a tool (edit a file, create something)
- **Before shell command** — the agent is about to run a terminal command
- **After file edit** — a file was just modified (for record-keeping, not blocking)
- **Session stop** — the editor is closing

When any of these events fire, the editor calls Viveka's hook script. The script is a thin, fast messenger — it takes the event details, sends them to the daemon (described next), and relays the response back to the editor. The entire round trip takes about 8 milliseconds.

**What if the hook fails?** The action proceeds. Viveka is designed to never accidentally lock up the editor. If something goes wrong with the hook infrastructure, the agent continues working normally. The thinking layer (the cognitive posture that shapes how the agent reasons) remains active regardless.

### 2. Daemon — The Decision Maker

The daemon is the brain of the enforcement system. It is a background process that starts when the editor opens a project and stays alive for the entire session.

**Why a background process?** Loading the decision engine requires importing libraries and scanning the project environment — about half a second of setup time. If this happened on every single action, the editor would feel sluggish (500ms delay on every file save, every command run). Instead, the daemon pays this cost once at startup. After that, each evaluation takes about 0.01 milliseconds — essentially instant.

**What happens at startup:**

1. The daemon reads the project directory and detects the environment: Which branch is checked out? Is it a protected branch (main, master, production, release)? Are there uncommitted changes? What tools are available (Git, Python, Docker, etc.)?

2. It reads the task description and detects the intent. Words like "fix" or "bug" signal a fix. Words like "refactor" or "optimize" signal an improvement. Words like "explore" or "prototype" signal exploration.

3. From the environment scan and task context, it computes a **risk score**. A routine development task scores low. Working on a protected branch scores higher. Production work with irreversible consequences scores highest.

4. The risk score determines the **enforcement mode** — how strict the rules are:

   | Mode | When | File limit | Retry limit | Stance |
   |------|------|-----------|-------------|--------|
   | **Permissive** | Exploration, prototyping | 30 files | 5 retries | Trust the agent |
   | **Standard** | Normal development | 15 files | 3 retries | Balanced |
   | **Guarded** | Protected branches, sensitive code | 8 files | 2 retries | Verify before allowing |
   | **Restricted** | Production, incidents | 3 files | 1 retry | Block unless clearly safe |

5. If the project has a policy file (a pre-defined set of rules for specific workflows like hotfixes or data migrations), the daemon loads and applies it.

**What the daemon checks on every action (seven rules):**

1. **Hard invariants** — Is the agent trying to force-push to main? Delete a protected path? Use a blocked tool? These are always blocked, regardless of mode.

2. **Secret exposure** — Does the action reference files that typically contain secrets (.env, API keys, passwords)? If so, warn.

3. **Retry loops** — Has the agent tried this exact action before? The same command failing three times in a row suggests the approach is wrong, not that it needs one more try. Block after the limit.

4. **Scope creep** — Has the agent modified more files than expected for this task? A "fix one bug" task that touches 20 files is probably drifting. Warn as it approaches the limit.

5. **Destructive actions** — Commands like `rm -rf`, `drop table`, `reset --hard` get special scrutiny. In stricter modes, they are blocked outright. In permissive mode, they are warned.

6. **Token budget** — If a cost budget was set for the session, warn when approaching it and block when exhausted.

7. **Session health** — If the agent has accumulated many warnings without changing behavior, escalate to the human. If total actions exceed the session limit, escalate — a possible runaway loop.

**The daemon remembers everything within a session.** It tracks which files were modified, which actions were taken, how many warnings were issued, how many times each action was retried. This accumulated context is what makes the behavioral rules (retry detection, scope creep, session health) possible.

**What happens when the session ends:**

If the session had meaningful activity (3 or more actions), the daemon writes a checkpoint file to the project. This checkpoint records what happened: which files were touched, how many actions were taken, how many were warned or blocked, and the full decision trace. This creates an audit trail.

**Idle timeout:** If the editor is closed without a clean shutdown (force-quit, crash), no stop event fires. The daemon has a 5-minute idle timer — if no requests arrive for 5 minutes, it writes the checkpoint and shuts itself down. This prevents abandoned processes from accumulating on the system.

### 3. MCP Server — The Agent's Advisor

The hooks and daemon work automatically — the agent has no say in whether they fire. The MCP server is different. It provides tools that the agent can voluntarily call to ask governance questions.

Think of it this way: the daemon is like a traffic light (automatic, mandatory), while the MCP server is like a navigation app (optional, advisory, but useful).

The MCP server provides ten tools:

| Tool | What the agent asks | What it gets back |
|------|-------------------|-------------------|
| **Check** | "Is this action safe to take?" | A permit/warn/block/escalate verdict with reasoning |
| **Memory Read** | "Has anything relevant been learned in past sessions?" | Past task memories, correction rules, framework insights |
| **Memory Write** | "I learned something worth remembering." | Saves the insight for future sessions |
| **Session State** | "What's my current governance context?" | Current risk mode, posture, task description, working directory |
| **Status** | "Is the governance system healthy?" | Layer-by-layer health check |
| **Update Posture** | "I need to switch to Adversarial mode." | Updates enforcement immediately |
| **Constraint Check** | "Does this text violate any hard constraints?" | List of violations found |
| **Scenarios** | "What could go wrong with this approach?" | Applicable failure scenarios for the current context |
| **Policies** | "What governance policies are available?" | List of named policy packs with their rules |
| **Session Trace** | "Show me every decision made this session." | Complete action-by-action history |

**How it connects to the daemon:** When the agent calls a tool like "Check," the MCP server first tries to send the request to the daemon over the same connection the hooks use. This is important — the daemon has the full session history (files modified, retries counted, warnings accumulated). A fresh evaluation without that history would miss behavioral patterns. If the daemon is unavailable, the MCP server falls back to running its own evaluation, but without session history.

---

## How They Work Together

Here is what happens during a typical work session, start to finish:

**Opening the project:**
The editor fires the session start event. The hook script starts the daemon. The daemon scans the environment, computes the risk level, and signals that it is ready. The MCP server starts alongside it. Total time: about 1-2 seconds.

**The agent works:**
The agent reads files, writes code, runs tests. Every action passes through the hook checkpoint, reaches the daemon, gets evaluated in microseconds, and receives a verdict. Most actions are permitted silently. The agent doesn't even know governance is running — it just works without friction.

**Something risky happens:**
The agent tries to run a destructive command, or modifies its 15th file, or retries a failing command for the third time. The daemon catches it. Depending on severity: a warning message appears in the agent's context, the action is blocked with an explanation, or the human is asked to approve.

**The agent asks for guidance:**
At any point, the agent can call MCP tools — check an action before attempting it, read past memories for context, or ask what failure scenarios are relevant.

**Closing the project:**
The editor fires the stop event. The daemon writes a session checkpoint (audit trail) and shuts down. Socket files and PID files are cleaned up. If the editor crashes instead, the 5-minute timeout handles cleanup automatically.

---

## Per-Project Isolation

Each editor window gets its own daemon. If you have two projects open — say, a web app and a data pipeline — each has its own governance process with its own risk assessment, its own session history, and its own enforcement rules.

This works by creating a unique identifier from the project directory. The identifier determines the names of all the temporary files (socket, process ID, state) used by that session. Two projects in different directories will never interfere with each other.

---

## The Safety Philosophy: Fail Open

Viveka follows a "fail-open" design. If anything goes wrong with the governance infrastructure — Python isn't installed, the daemon crashes, the socket is unreachable — the agent is allowed to proceed. Actions are never blocked due to an infrastructure problem.

This is a deliberate choice. The alternative — failing closed (blocking everything when governance is down) — would mean a crashed daemon locks up the entire editor. That's worse than no governance at all.

When enforcement is unavailable, the cognitive layer (the reasoning guidelines that shape how the agent thinks) continues to operate. The agent still follows the six-stage workflow, still applies decision gates, still escalates on irreversible actions — it just does so based on training and instruction, not a deterministic gate.

---

## What Viveka Does Not Do

- **No AI calls.** Every enforcement decision is pure rule evaluation. No tokens consumed, no API calls, no latency from model inference.
- **No network access.** Everything runs locally. No data leaves your machine.
- **No accounts or API keys.** Nothing to configure, nothing to pay for.
- **No mandatory blocking.** The system is advisory-first. Hard blocks only fire for clear safety violations (force-pushing to main, retry loops, budget exhaustion).
- **No post-hoc enforcement.** The after-file-edit hook only records what was changed — it doesn't undo or reject edits after the fact. All blocking happens before the action executes.

---

## Summary

| Component | Role | Automatic? | What if it fails? |
|-----------|------|-----------|-------------------|
| **Hooks** | Checkpoint — intercepts every action and sends it for evaluation | Yes, always fires | Falls open — action proceeds |
| **Daemon** | Decision maker — evaluates actions against seven rules, tracks session behavior | Yes, runs in background | Falls open — hook attempts one restart, then allows |
| **MCP Server** | Advisor — provides tools the agent can voluntarily call for guidance | No, agent chooses to call | Falls back to standalone evaluation, then allows |

The hooks are the hands. The daemon is the brain. The MCP server is the voice. Together, they create a governance layer that is fast enough to be invisible, strict enough to catch real problems, and graceful enough to never get in the way when it shouldn't.
