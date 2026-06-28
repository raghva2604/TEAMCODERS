import os
import json
from datetime import datetime


DEFAULT_AFFERENS_REPORT = {
    "people": 1,
    "objects": ["Laptop", "Backpack"],
    "environment": "Indoor",
    "lighting": "Normal",
    "risk": "LOW",
    "summary": "Unknown person carrying a laptop detected near the entrance."
}


def generate_ai_observation(people=1, objects=None, environment="Indoor", lighting="Normal", risk="LOW"):
    if objects is None:
        objects = ["Laptop", "Backpack"]

    report = {
        "people": people,
        "objects": list(objects),
        "environment": environment,
        "lighting": lighting,
        "risk": risk,
        "summary": (
            f"Unknown person detected with {', '.join(objects)} near the entrance."
            if objects else "Unknown person detected near the entrance."
        ),
    }
    return report


def should_send_alert(person_id, last_alert_time, cooldown_seconds=30, now=None):
    if now is None:
        from time import time
        now = time()

    if person_id not in last_alert_time:
        last_alert_time[person_id] = now
        return True, now

    if now - last_alert_time[person_id] > cooldown_seconds:
        last_alert_time[person_id] = now
        return True, now

    return False, last_alert_time[person_id]


def build_alert_message(person_name, observation=None, timestamp=None):
    ts = timestamp or datetime.now().strftime("%I:%M %p")
    observation = observation or generate_ai_observation()

    lines = [
        "🚨 ALERT",
        "",
        f"Unknown Person: {person_name}",
        "",
        "Objects:",
    ]
    lines.extend(f"• {obj}" for obj in observation.get("objects", []))
    lines.extend([
        "",
        f"Risk: {observation.get('risk', 'LOW')}",
        "",
        f"Time: {ts}",
    ])
    return "\n".join(lines)


def save_ai_report(report, folder="ai_reports"):
    os.makedirs(folder, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return path
