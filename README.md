# Study Planner Agent — CSE476 CA1, Topic T24

**Repo:** https://github.com/PrakharPurwar12/Study-Planner-Agent

**Goal:** plan study blocks around real deadlines, so tasks actually get studied for before
they're due instead of just sitting on a to-do list.

**The two tools** are `add_task(name, due)`, which saves a task and its deadline, and
`build_schedule()`, which looks at every task currently in memory and builds a day-by-day study
plan around their deadlines. The agent only acts through these two functions — it never invents
a schedule on its own, and both tools are called for real, with real results feeding back into
the agent's next decision (shown in the notebook trace).

**Memory** is a plain JSON file (`study_memory.json`, handled by `memory.py`). Every task and its
deadline gets written there when `add_task` runs, and `build_schedule` reads the whole file back
when it runs later, so tasks added in one turn are still there and get used in a later turn's
schedule. The notebook proves this by loading the task list from a completely separate Python
process, not just a variable held in memory during one session. This file is generated at
runtime and is not part of the submitted code (it's excluded via `.gitignore`).

**One honest failure:** when too many tasks pile up on the same day(s), there just isn't enough
study-hour capacity to fit everyone before their deadline. Instead of faking a schedule that looks
fine, `planner.py` schedules whatever hours actually fit and reports the shortfall, e.g. `'Task C'
only got 0/4 study hours before its deadline — not enough time, schedule is tight/impossible`.
An honest partial plan is more useful than a schedule that silently doesn't work, so this is left
as a visible warning rather than hidden or smoothed over.

---

## How the agent works, step by step

This section walks through exactly what happens when a request comes in, so it's easy to follow
without needing to read the code line by line first.

1. **A request comes in** (e.g. "add task DBMS assignment due 2026-08-27").
2. **The agent decides which tool to call.** This decision is made by a real LLM using
   OpenAI-style function calling (see "LLM configuration" below). The model is given the two
   tool definitions and decides on its own whether to call `add_task`, `build_schedule`, or both.
3. **The tool actually runs.** `add_task` validates the date, checks for duplicates and past
   dates, and saves the task to `study_memory.json`. `build_schedule` reads every task from
   memory and hands it to the scheduling logic in `planner.py`.
4. **The tool's real result is sent back to the model.** This includes things like whether the
   task is urgent (`due` within 2 days), how many hours got scheduled, and any warnings.
5. **The agent decides the next step based on that result** — not a scripted sequence. For
   example, if a task comes back flagged as urgent, the agent calls `build_schedule()` again on
   its own to re-plan the whole schedule around it, even if a schedule was already built earlier
   in the conversation.
6. **This repeats until there's nothing left to do**, and the agent gives a short final answer
   (the schedule, or a clear explanation of a problem like a duplicate task or an impossible
   deadline).

This decide → act → observe → decide loop (visible as `[agent decision]`, `[tool call]`,
`[tool result]`, `[next decision]`, `[final answer]` in the notebook trace) is what makes this an
agent rather than a chatbot: the model's second decision is genuinely shaped by what the first
tool call returned.

## Extra feature: automatic re-plan on urgent tasks

Beyond the two required tools, the agent also re-plans proactively. If a newly added task's
deadline is within 2 days, `add_task` flags it `urgent` in its result. The agent checks this flag
and automatically calls `build_schedule()` again to rebuild the entire schedule around the new
urgent deadline — not just slot the new task in on the side. This is demonstrated in Demo 3 of
the notebook.

## Planner logic

`planner.py` contains the actual scheduling logic:
- Tasks are sorted by deadline (earliest due date first = highest priority).
- For each task, the planner walks forward day by day from today up to its deadline, allocating
  up to 2 study hours per day per task, out of a shared 4-hours-per-day capacity across all tasks.
- If a task runs out of days before it gets enough hours, the planner reports exactly how many
  hours it managed versus how many were needed, instead of pretending the plan works.

## LLM configuration

The agent uses a real LLM with OpenAI-style function calling to decide which tool to call and
when. It supports two interchangeable providers — whichever has credentials set in `.env` is
used automatically:

```bash
# Option 1: Groq (OpenAI-compatible chat completions API)
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b

# Option 2: Azure/Microsoft Foundry
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-10-21
```

If neither is set, `agent.py` runs a small rule-based decision function instead, so the project
still works offline for a quick demo — it uses the exact same tools, memory, and planner code
underneath, just with a simpler decision layer standing in for the LLM.

## Project files

- `agent.py` — the agent's decide → act → observe → decide loop (both the LLM path and the
  offline fallback path)
- `tools.py` — the two tools (`add_task`, `build_schedule`) and their input validation
- `memory.py` — loads/saves tasks to `study_memory.json`
- `planner.py` — deadline-based scheduling logic
- `study_planner_demo.ipynb` — runnable demo notebook with a visible multi-step trace
- `requirements.txt`, `.env.example` — dependencies and configuration template

## Setup and run

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in a GROQ_API_KEY (or Azure Foundry key + endpoint) for real LLM tool-calling
jupyter notebook study_planner_demo.ipynb
```

Without any credentials set, the agent still runs end-to-end in its offline fallback mode.