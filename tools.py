# tools.py
# these are the two tools the agent is allowed to call.
# they're just normal python functions - the agent decides when to use them.

from datetime import datetime
import memory
import planner


def add_task(name, due):
    """
    adds a task with a deadline to memory.
    due should be a string like '2026-08-30'
    """
    name = name.strip()

    # validate date format + not in the past
    try:
        due_date = datetime.strptime(due, planner.DATE_FMT)
    except ValueError:
        return {"status": "error", "message": f"'{due}' is not a valid date (use YYYY-MM-DD)"}

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if due_date < today:
        return {"status": "error", "message": f"'{due}' is in the past, can't schedule study time for that"}

    tasks = memory.load_tasks()

    # duplicate check (same task name, case-insensitive)
    for t in tasks:
        if t["name"].lower() == name.lower():
            return {"status": "error", "message": f"'{name}' is already in your task list (due {t['due']})"}

    new_task = {"name": name, "due": due}
    tasks.append(new_task)
    memory.save_tasks(tasks)

    urgent = planner.is_urgent(new_task)

    return {
        "status": "ok",
        "message": f"added '{name}', due {due}",
        "urgent": urgent,
        "task_count": len(tasks),
    }


def build_schedule():
    """
    builds/rebuilds the study schedule from whatever tasks are currently in memory.
    """
    tasks = memory.load_tasks()
    blocks, warnings = planner.make_schedule(tasks)

    if not tasks:
        return {"status": "empty", "message": "no tasks yet, add some first", "blocks": [], "warnings": warnings}

    return {
        "status": "ok",
        "blocks": blocks,
        "warnings": warnings,
        "task_count": len(tasks),
    }
