# agent.py
# this is the "brain" of the project. it decides which tool to call, looks at
# the result, and decides what to do next - that's what makes it agentic
# instead of just a chatbot that replies with text.
#
# LLM lane: we originally built this against GitHub Models, but GitHub fully
# retired that service on July 30, 2026. we then tried Azure/Microsoft Foundry
# (the assignment's other listed lane), but ran into region/quota deployment
# friction there. so this supports either Azure Foundry OR Groq (free,
# OpenAI-compatible, no card required) - whichever has keys set in .env wins.
# if neither is set, we fall back to a small rule-based decision function so
# the notebook still runs offline. either way the tools/memory/planner
# underneath are the same real code - nothing is faked.

import os
import re
import json
from dotenv import load_dotenv

import tools
import planner

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

# prefer Groq if set (simplest, most reliable free lane), else Azure, else fallback
USING_GROQ = bool(GROQ_API_KEY)
USING_AZURE = bool(AZURE_API_KEY and AZURE_ENDPOINT) and not USING_GROQ
USING_LLM = USING_GROQ or USING_AZURE

SYSTEM_PROMPT = """You are a study planner agent. You have two tools:
- add_task(name, due): saves a task and its deadline
- build_schedule(): builds a study schedule from all tasks currently in memory

Rules you must follow:
1. If the user wants to add one or more tasks, call add_task for each one.
2. After adding tasks, call build_schedule to actually produce the plan, unless the user only asked to add tasks.
3. If add_task tells you the new task is urgent (due soon), you MUST call build_schedule again
   afterwards to re-plan the whole schedule around it, even if you already built a schedule earlier.
4. If a tool returns an error (bad date, duplicate task, etc), tell the user plainly and don't retry blindly.
5. Keep your final answer short and practical - list the schedule or the issue, don't ramble.
"""

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Add a new study task with its deadline to memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "the task name"},
                    "due": {"type": "string", "description": "deadline, format YYYY-MM-DD"},
                },
                "required": ["name", "due"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_schedule",
            "description": "Build (or rebuild) the study schedule using every task currently stored in memory.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def run_tool(tool_name, tool_input):
    if tool_name == "add_task":
        return tools.add_task(tool_input["name"], tool_input["due"])
    elif tool_name == "build_schedule":
        return tools.build_schedule()
    else:
        return {"status": "error", "message": f"unknown tool {tool_name}"}


def print_trace(step, detail):
    print(f"[{step}] {detail}")


# ---------- real LLM path (Groq or Azure/Microsoft Foundry lane) ----------

def _get_llm_client_and_model():
    if USING_GROQ:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
        return client, GROQ_MODEL
    else:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            azure_endpoint=AZURE_ENDPOINT,
            api_version=AZURE_API_VERSION,
        )
        return client, AZURE_DEPLOYMENT  # this is the *deployment name* in Azure Foundry


def run_agent_llm(user_message):
    client, model_name = _get_llm_client_and_model()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    print_trace("agent decision", f"received request: \"{user_message}\"")

    final_text = ""
    for _ in range(6):  # safety cap so a weird loop can't run forever
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=TOOL_DEFS,
        )

        msg = response.choices[0].message
        tool_calls = msg.tool_calls or []

        if not tool_calls:
            final_text = (msg.content or "").strip()
            break

        messages.append(msg.model_dump())

        for call in tool_calls:
            call_input = json.loads(call.function.arguments or "{}")
            print_trace("tool call", f"{call.function.name}({call_input})")
            result = run_tool(call.function.name, call_input)
            print_trace("tool result", result)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

        print_trace("next decision", "checking tool result to decide next step")

    print_trace("final answer", final_text)
    return final_text


# ---------- fallback rule-based path (no API key, still real tools/memory) ----------

def _parse_add_requests(user_message):
    # handles things like: "add task Math HW due 2026-08-25"
    # or multiple tasks separated by "and"/commas
    chunks = re.split(r"\band\b|,", user_message, flags=re.IGNORECASE)
    found = []
    for chunk in chunks:
        m = re.search(
            r"(?:add task|task)\s+(.+?)\s+due\s+(\d{4}-\d{2}-\d{2})",
            chunk, flags=re.IGNORECASE,
        )
        if m:
            found.append((m.group(1).strip(), m.group(2).strip()))
    return found


def run_agent_fallback(user_message):
    print_trace("agent decision", f"received request: \"{user_message}\" (no Groq/Azure key set -> rule-based fallback brain)")

    tasks_to_add = _parse_add_requests(user_message)
    wants_schedule = bool(re.search(r"schedule|plan", user_message, flags=re.IGNORECASE))

    any_urgent = False
    last_result_text = []

    if not tasks_to_add and not wants_schedule:
        msg = "couldn't understand the request, try: \"add task X due YYYY-MM-DD\""
        print_trace("final answer", msg)
        return msg

    for name, due in tasks_to_add:
        print_trace("tool call", f"add_task({name!r}, {due!r})")
        result = tools.add_task(name, due)
        print_trace("tool result", result)
        if result.get("status") == "ok" and result.get("urgent"):
            any_urgent = True
        last_result_text.append(result["message"])

    should_schedule = wants_schedule or any_urgent or bool(tasks_to_add)

    if should_schedule:
        if any_urgent:
            print_trace("next decision", "new task is urgent -> re-planning full schedule")
        else:
            print_trace("next decision", "building schedule from current memory")

        print_trace("tool call", "build_schedule()")
        sched = tools.build_schedule()
        print_trace("tool result", sched)

        final_text = format_schedule_for_human(sched)
        print_trace("final answer", final_text)
        return final_text

    final_text = "; ".join(last_result_text)
    print_trace("final answer", final_text)
    return final_text


def format_schedule_for_human(sched):
    if sched["status"] == "empty":
        return sched["message"]

    lines = []
    if sched["blocks"]:
        lines.append("study plan:")
        for b in sched["blocks"]:
            lines.append(f"  {b['date']}: {b['task']} - {b['hours']}h")
    else:
        lines.append("no study blocks could be scheduled")

    if sched["warnings"]:
        lines.append("warnings:")
        for w in sched["warnings"]:
            lines.append(f"  - {w}")

    return "\n".join(lines)


# ---------- entry point used by the notebook ----------

def run_agent(user_message):
    print("=" * 60)
    if USING_LLM:
        return run_agent_llm(user_message)
    else:
        return run_agent_fallback(user_message)
