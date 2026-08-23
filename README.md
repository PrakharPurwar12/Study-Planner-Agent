# Study Planner Agent - CSE476 CA1, Topic T24

Goal: plan study blocks around real deadlines, so tasks actually get studied for before they're due
instead of just being written down somewhere.

**The two tools** are `add_task(name, due)`, which saves a task and its deadline, and
`build_schedule()`, which looks at every task currently in memory and builds a day-by-day study
plan around their deadlines. The agent never invents a schedule out of thin air - it only acts
through these two functions, and both are called for real (see the notebook trace).

**Memory** is a plain JSON file (`study_memory.json`, handled by `memory.py`). Every task and its
deadline gets written there when `add_task` runs, and `build_schedule` reads the whole file back
when it runs later - so tasks added in one turn are still there and get used in the next turn's
schedule. This is proven in the notebook by loading the task list from a completely separate
Python process, not just a variable held in memory during one session.

**One honest failure**: when too many tasks pile up on the same day(s), there just isn't enough
study-hour capacity to fit everyone before their deadline. Instead of faking a schedule that looks
fine, `planner.py` schedules whatever hours actually fit and reports the shortfall, e.g. `'Task C'
only got 0/4 study hours before its deadline - not enough time, schedule is tight/impossible`. We
hit this for real while testing three same-day deadlines and left it as-is rather than hiding it,
since an honest partial plan is more useful than a schedule that silently doesn't work.

## Why it's agentic, not a chatbot
The agent gets a request, decides which tool to call, actually calls it, looks at the real result,
and *then* decides the next step - e.g. seeing `urgent: True` come back from `add_task` is what
triggers a second `build_schedule()` call, it isn't scripted in advance. That decide → act →
observe → decide loop is what the notebook trace shows for each demo.

## Group of 3 add-on: auto re-plan on urgent tasks
If a new task's deadline is within 2 days, `add_task` flags it `urgent` in its result. The agent
checks that flag and automatically calls `build_schedule()` again on its own to re-plan the whole
schedule around it, not just slot the new task in. Shown in Demo 3 of the notebook.

## LLM lane
Uses GitHub Models (free, OpenAI-compatible endpoint - `https://models.inference.ai.azure.com`),
same lane the course allows. If no `GITHUB_TOKEN` is set, `agent.py` runs a small rule-based
decision function instead so the notebook still works offline for demo/grading - either way the
tools/memory/planner underneath are the same real code.

## Files
`memory.py` (load/save tasks), `planner.py` (scheduling logic), `tools.py` (the two tools + input
validation), `agent.py` (the plan-act loop), `study_planner_demo.ipynb` (runnable demo).

## Setup / run
```bash
pip install -r requirements.txt
cp .env.example .env
# optional: add a free GITHUB_TOKEN in .env for real LLM tool-calling
jupyter notebook study_planner_demo.ipynb
```

