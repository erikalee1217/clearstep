from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import ConfirmedTask, RankedTask


def rank_tasks(tasks: list[ConfirmedTask], now: datetime, zone: ZoneInfo) -> list[RankedTask]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    today = now.astimezone(zone).date()
    infinity = datetime.max.replace(tzinfo=timezone.utc)
    horizon = now + timedelta(days=7)

    def deadline(task):
        if task.due_at is not None:
            return task.due_at.astimezone(timezone.utc)
        if task.due_date is not None:
            return datetime.combine(task.due_date, time.max, zone).astimezone(timezone.utc)
        return infinity

    def urgent(task):
        if task.due_date is not None:
            return task.due_date <= today
        return task.due_at is not None and deadline(task) <= now + timedelta(hours=24)

    def key(task):
        tail = (task.created_at.astimezone(timezone.utc),)
        if urgent(task):
            return (0, deadline(task), *tail)
        near_deadline = deadline(task) if deadline(task) <= horizon else infinity
        return (1, task.importance != "high", near_deadline, *tail)

    def reasons(task):
        if urgent(task):
            if deadline(task) < now:
                return ["Overdue deadline"]
            return ["Due today" if task.due_date is not None else "Due within 24 hours"]
        result = []
        if task.importance == "high":
            result.append("Marked important")
        if deadline(task) <= horizon:
            result.append("Due within 7 days")
        return result or ["Available task; ties use oldest first"]

    # Python's stable sort preserves the incoming array order for equal keys.
    return [RankedTask(id=task.id, reasons=reasons(task))
            for task in sorted((task for task in tasks if task.status == "todo"), key=key)]
