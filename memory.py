# memory.py
# handles saving/loading tasks so they persist across turns (and across notebook restarts)
# just a plain json file, nothing fancy

import json
import os

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "study_memory.json")


def load_tasks():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_tasks(tasks):
    with open(MEMORY_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def clear_memory():
    # useful for demo resets
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
