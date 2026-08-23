# Study Planner Agent

This project is a small agentic study planner. The main idea is simple: the user gives a goal like adding tasks or asking for a study plan, and the agent decides what to do next instead of just producing text. The project is built around real deadlines and task management, so the agent has to interact with actual tools and stored memory instead of handling everything in one prompt.

## What it does

The agent helps plan study time around assignment and exam deadlines. A user can add tasks with a date, and the system will build a study schedule that looks at all existing tasks and their due dates. It is meant to be a practical assignment project focused on agent behavior, tool use, and memory persistence.

## Why this is an agent, not a normal chatbot

This is not just a chat model replying with a schedule. The code in `agent.py` implements a plan-act loop:

User goal → agent decides action → tool call → tool result → next decision → final response

The agent checks the result of a tool and then decides whether to do another action. For example, after adding a task, it may decide that the task is urgent and rebuild the schedule. That decision depends on the actual result returned by the tool, not a hardcoded script.

## The actual tools

The project currently defines two real tools in `tools.py`:

### 1. add_task(name, due)

This function validates the task name and due date, rejects bad or past dates, checks for duplicate task names, and saves the task to persistent memory. It returns a JSON result including the task status and whether the task is urgent.

The agent uses this when the user asks to add tasks. Once the task is stored, the next step may be to build a schedule.

### 2. build_schedule()

This function loads all tasks from memory, calls the scheduling logic in `planner.py`, and returns study blocks with warnings if some deadlines are too tight. It is used when the agent wants to create or rebuild the plan based on the current task list.

## Memory

Memory is stored in `study_memory.json`, managed by `memory.py`.

- `load_tasks()` reads the JSON file and returns the saved task list.
- `save_tasks(tasks)` writes the list back to disk.
- `clear_memory()` removes the file for demo reset purposes.

Each task is stored as a JSON object with a task name and due date. This means earlier tasks are not lost when the agent continues with a later request. Later scheduling reads the persisted tasks again, so previous tasks continue to affect the next schedule that is built.

## Agent implementation

The main logic lives in `agent.py`.

### LLM/tool-calling path

If model keys are set, the agent uses the OpenAI Python client and supports two configuration paths:

- Groq via `GROQ_API_KEY` and `GROQ_MODEL`
- Azure OpenAI via `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, and `AZURE_OPENAI_API_VERSION`

The agent sends a system prompt and the user goal to the model, then checks whether the model wants to call a tool. If it does, it executes the tool through `run_tool()`, appends the tool result to the conversation, and decides whether another action is needed.

### Fallback path

If no Groq or Azure variables are set, the project falls back to a rule-based path instead of calling an external model. This still uses the same tools and memory, so the project can still function in a simple offline mode.

### Tool result → next decision

Tool results influence the next step. In the fallback path, if a newly added task is urgent, the agent triggers `build_schedule()` again. In the LLM path, the tool result is included in the next reasoning step so the agent can decide whether more work is needed.

## Planner logic

The scheduling logic in `planner.py` is simple but real.

- It sorts tasks by deadline.
- It checks how many days remain before the due date.
- It assigns study blocks day by day up to the deadline, with a daily capacity limit.
- It treats tasks due within a short window as urgent.
- If there is not enough time before a deadline, it produces a warning instead of pretending the plan is fully feasible.

This is the project’s honest failure mode: when multiple tasks are due too close together, the scheduler assigns what it can and reports the shortfall.

## Notebook demo

The notebook `study_planner_demo.ipynb` demonstrates the project end to end. It includes:

- adding multiple tasks in one request
- building a schedule after those tasks are added
- proving memory persistence across turns by reading `study_memory.json` in a separate Python process
- an urgent-task scenario where a new task triggers another schedule rebuild
- a failure case where multiple tasks are due on the same day and the schedule warns about insufficient time

The notebook uses trace lines such as:

- agent decision
- tool call
- tool result
- next decision
- final answer

This matches the project’s intended multi-step trace.

## LLM configuration

The current code supports these environment variables:

```bash
GROQ_API_KEY=
GROQ_MODEL=

AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=
AZURE_OPENAI_API_VERSION=
```

This project does not use GitHub Models or a `GITHUB_TOKEN` in the current implementation.

## Setup and run

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in the values you want to use before running the model-backed agent path
jupyter notebook study_planner_demo.ipynb
```

If no model credentials are set, the agent still works in its fallback mode using the same tools and memory logic.

## Project structure

- `agent.py` – agent decision logic and tool-calling flow
- `tools.py` – the actual tool functions
- `memory.py` – saves and loads persisted task memory
- `planner.py` – deadline-based scheduling and urgent-task logic
- `study_memory.json` – stored task data
- `study_planner_demo.ipynb` – demonstration notebook
- `requirements.txt` – project dependencies

## Honest limitation

One limitation already present in the project is that the planner does not invent a full feasible study plan when there is not enough time before a deadline. Instead, it schedules what fits and emits warnings for the shortfall. This is documented in the project and is treated as honest behavior rather than a fake success.

