# test_agent.py
import unittest
from datetime import datetime, timedelta
import os
import json

import planner
import memory
import tools
import agent

class TestStudyPlanner(unittest.TestCase):

    def setUp(self):
        # Backup existing memory file if it exists
        self.backup_exists = os.path.exists(memory.MEMORY_FILE)
        if self.backup_exists:
            with open(memory.MEMORY_FILE, 'r') as f:
                self.backup_data = f.read()
        memory.clear_memory()

    def tearDown(self):
        # Restore backup memory file
        memory.clear_memory()
        if self.backup_exists:
            with open(memory.MEMORY_FILE, 'w') as f:
                f.write(self.backup_data)

    def test_is_urgent(self):
        # Set a fixed "today"
        today = datetime(2026, 8, 25)
        
        # Due in 1 day -> Urgent
        task_urgent = {"name": "Test Urgent", "due": "2026-08-26"}
        self.assertTrue(planner.is_urgent(task_urgent, today=today))

        # Due in 3 days -> Not Urgent
        task_not_urgent = {"name": "Test Normal", "due": "2026-08-28"}
        self.assertFalse(planner.is_urgent(task_not_urgent, today=today))

    def test_make_schedule_simple(self):
        today = datetime(2026, 8, 25)
        tasks = [
            {"name": "Math Homework", "due": "2026-08-27"}, # due in 2 days, needs 4 hours (default)
        ]
        blocks, warnings = planner.make_schedule(tasks, today=today)
        
        # The scheduler should schedule 2 hours on 2026-08-25 and 2 hours on 2026-08-26 (4 hours total)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["date"], "2026-08-25")
        self.assertEqual(blocks[0]["hours"], 2)
        self.assertEqual(blocks[1]["date"], "2026-08-26")
        self.assertEqual(blocks[1]["hours"], 2)
        self.assertEqual(len(warnings), 0)

    def test_make_schedule_overload(self):
        today = datetime(2026, 8, 25)
        # Multiple tasks due on the same day, exceeding the capacity of 4 hours/day
        tasks = [
            {"name": "Math Homework", "due": "2026-08-26"}, # due in 1 day, needs 4 hours
            {"name": "OS Quiz", "due": "2026-08-26"},       # due in 1 day, needs 4 hours
        ]
        blocks, warnings = planner.make_schedule(tasks, today=today)
        
        # Max capacity per day is 4 hours. So only 4 hours total can be scheduled on 2026-08-25.
        total_hours = sum(b["hours"] for b in blocks)
        self.assertEqual(total_hours, 4)
        # We should have warnings because the tasks could not be fully scheduled.
        self.assertTrue(len(warnings) > 0)

    def test_memory_persistence(self):
        tasks = [
            {"name": "DBMS assignment", "due": "2026-08-30"}
        ]
        memory.save_tasks(tasks)
        loaded = memory.load_tasks()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["name"], "DBMS assignment")

    def test_add_task_tool(self):
        # We must mock datetime.now to ensure it doesn't complain about dates in the past
        # Wait, since the test runs in 2026 (or current year), we use a future date like 2029-12-31 to be safe
        future_date = "2029-12-31"
        result = tools.add_task("Physics Lab", future_date)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["task_count"], 1)

        # Try to add duplicate
        dup_result = tools.add_task("Physics Lab", future_date)
        self.assertEqual(dup_result["status"], "error")

    def test_agent_fallback_mode(self):
        # Test agent fallback execution path
        user_message = "add task Chemistry due 2029-12-30"
        response = agent.run_agent_fallback(user_message)
        self.assertIn("Chemistry", response)
        
        # Verify it was added to memory
        tasks = memory.load_tasks()
        self.assertTrue(any(t["name"] == "Chemistry" for t in tasks))

if __name__ == '__main__':
    unittest.main()
