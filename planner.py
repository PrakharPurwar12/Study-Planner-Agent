# planner.py
# this is where the actual scheduling logic lives.
# kept it simple: sort tasks by deadline, then greedily give each task
# study hours on the days before it's due, day by day, until either
# the task has enough hours or we run out of days (impossible case).

from datetime import datetime, timedelta

DATE_FMT = "%Y-%m-%d"
HOURS_PER_DAY_CAP = 4      # total study hours we allow in a single day (all tasks combined)
DEFAULT_HOURS_NEEDED = 4   # how many hours a "normal" task needs before its deadline
URGENT_WINDOW_DAYS = 2     # a task due within this many days counts as urgent


def parse_date(date_str):
    return datetime.strptime(date_str, DATE_FMT)


def is_urgent(task, today=None):
    today = today or datetime.now()
    due = parse_date(task["due"])
    days_left = (due - today).days
    return days_left <= URGENT_WINDOW_DAYS


def make_schedule(tasks, today=None):
    """
    builds a day-by-day study schedule for all tasks.
    returns (blocks, warnings)
    blocks = list of {date, task, hours}
    warnings = list of strings (e.g. task X doesn't have enough time)
    """
    today = today or datetime.now()
    today = today.replace(hour=0, minute=0, second=0, microsecond=0)

    if not tasks:
        return [], ["no tasks in memory, nothing to schedule"]

    # priority = earliest deadline first (simple but works fine for this use case)
    sorted_tasks = sorted(tasks, key=lambda t: parse_date(t["due"]))

    # day -> hours already used (shared capacity across all tasks)
    day_capacity_used = {}
    blocks = []
    warnings = []

    for task in sorted_tasks:
        due = parse_date(task["due"])
        days_left = (due - today).days

        if days_left <= 0:
            warnings.append(f"'{task['name']}' is already due or overdue, skipping scheduling for it")
            continue

        hours_needed = task.get("hours_needed", DEFAULT_HOURS_NEEDED)
        hours_scheduled = 0

        # walk through each day from today up to (but not including) the due date
        for d in range(days_left):
            day = today + timedelta(days=d)
            day_key = day.strftime(DATE_FMT)
            used = day_capacity_used.get(day_key, 0)
            free = HOURS_PER_DAY_CAP - used

            if free <= 0:
                continue

            # don't dump more than 2 hrs of one task on the same day, keeps it realistic
            chunk = min(2, free, hours_needed - hours_scheduled)
            if chunk <= 0:
                continue

            blocks.append({"date": day_key, "task": task["name"], "hours": chunk})
            day_capacity_used[day_key] = used + chunk
            hours_scheduled += chunk

            if hours_scheduled >= hours_needed:
                break

        if hours_scheduled < hours_needed:
            warnings.append(
                f"'{task['name']}' only got {hours_scheduled}/{hours_needed} study hours "
                f"before its deadline ({task['due']}) - not enough time, schedule is tight/impossible"
            )

    blocks.sort(key=lambda b: b["date"])
    return blocks, warnings
