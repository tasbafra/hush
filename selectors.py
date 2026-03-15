from __future__ import annotations

from typing import Any


MIN_STOPS = 3
TARGET_STOPS = 4
MAX_STOPS = 5


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _norm_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def sort_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Ожидает список словарей формата:
    {
        "score": float,
        "place": {
            "id": str,
            "name": str,
            "category": str,
            "promo_label": str | None,
            "duration_min": int,
            "local_score": float,
            "photo_score": float,
        }
    }
    """
    return sorted(
        candidates,
        key=lambda candidate: (
            -_to_float(candidate.get("score"), 0.0),
            -_to_float(candidate.get("place", {}).get("local_score"), 0.0),
            -_to_float(candidate.get("place", {}).get("photo_score"), 0.0),
            _norm_str(candidate.get("place", {}).get("name")),
            _norm_str(candidate.get("place", {}).get("id")),
        ),
    )


def choose_target_stop_count(candidates: list[dict[str, Any]]) -> int:
    count = len(candidates)
    if count <= 0:
        return 0
    if count < MIN_STOPS:
        return count

    if count >= 5:
        top_five = candidates[:5]
        avg_duration = sum(_to_int(item.get("place", {}).get("duration_min"), 45) for item in top_five) / len(top_five)
        if avg_duration <= 45:
            return 5

    return min(TARGET_STOPS, count)


def select_route_candidates(
    candidates: list[dict[str, Any]],
    *,
    min_stops: int = MIN_STOPS,
    target_stops: int = TARGET_STOPS,
    max_stops: int = MAX_STOPS,
) -> list[dict[str, Any]]:
    """
    Собирает маршрут:
    - сначала старается взять разные категории,
    - потом допускает повтор категории до 2 раз,
    - максимум 1 promo-точка,
    - добирает минимум min_stops, если база узкая.
    """
    ordered = sort_candidates(candidates)
    dynamic_target = choose_target_stop_count(ordered)

    if dynamic_target == 0:
        return []

    target_count = min(dynamic_target, target_stops, max_stops)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    category_counts: dict[str, int] = {}
    promo_used = False

    def can_take(candidate: dict[str, Any], *, max_per_category: int) -> bool:
        nonlocal promo_used

        place = candidate.get("place", {})
        place_id = str(place.get("id", "")).strip()
        category = _norm_str(place.get("category")) or "other"
        promo_label = place.get("promo_label")

        if not place_id or place_id in selected_ids:
            return False

        if category_counts.get(category, 0) >= max_per_category:
            return False

        if promo_label and promo_used:
            return False

        return True

    def take(candidate: dict[str, Any]) -> None:
        nonlocal promo_used

        place = candidate.get("place", {})
        place_id = str(place.get("id", "")).strip()
        category = _norm_str(place.get("category")) or "other"
        promo_label = place.get("promo_label")

        selected.append(candidate)
        selected_ids.add(place_id)
        category_counts[category] = category_counts.get(category, 0) + 1

        if promo_label:
            promo_used = True

    # Проход 1: максимум разнообразия
    for candidate in ordered:
        if len(selected) >= target_count:
            break
        if can_take(candidate, max_per_category=1):
            take(candidate)

    # Проход 2: допускаем до 2 мест одной категории
    if len(selected) < target_count:
        for candidate in ordered:
            if len(selected) >= target_count:
                break
            if can_take(candidate, max_per_category=2):
                take(candidate)

    # Проход 3: добираем минимум, если мест мало
    if len(selected) < min_stops:
        for candidate in ordered:
            if len(selected) >= min(target_count, max_stops):
                break

            place = candidate.get("place", {})
            place_id = str(place.get("id", "")).strip()
            promo_label = place.get("promo_label")

            if not place_id or place_id in selected_ids:
                continue
            if promo_label and promo_used:
                continue

            take(candidate)

    return selected[:max_stops]


__all__ = [
    "sort_candidates",
    "choose_target_stop_count",
    "select_route_candidates",
]
