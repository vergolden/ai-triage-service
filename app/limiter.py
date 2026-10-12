"""Лимит запросов: скользящее окно 60 секунд на client_id, счёт по таблице tickets."""
import math
from datetime import datetime, timezone

from app import config, store

WINDOW_SECONDS = 60


def retry_after_seconds(client_id: str) -> int:
    """0, если запрос можно принять. Иначе - сколько секунд ждать до освобождения слота."""
    limit = config.rate_limit_per_minute()
    times = store.recent_tickets(client_id, WINDOW_SECONDS)
    if len(times) < limit:
        return 0
    # слот освободится, когда выйдет из окна самое старое из тех, что держат лимит
    oldest_blocking = times[len(times) - limit]
    wait = WINDOW_SECONDS - (datetime.now(timezone.utc) - oldest_blocking).total_seconds()
    return max(1, math.ceil(wait))
