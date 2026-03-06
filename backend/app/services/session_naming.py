from datetime import datetime
from zoneinfo import ZoneInfo


def format_session_name(now: datetime | None = None) -> str:
    local_time = (now or datetime.utcnow()).replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Australia/Sydney"))
    day = local_time.strftime("%d").lstrip("0") or "1"
    month = local_time.strftime("%b")
    hour = local_time.strftime("%I").lstrip("0") or "12"
    minute = local_time.strftime("%M")
    meridiem = local_time.strftime("%p").lower()
    return f"{day} {month} - {hour}.{minute}{meridiem}"
