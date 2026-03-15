from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# -----------------------------
# Конфигурация и веса
# -----------------------------

BUDGET_ORDER = {"low": 0, "medium": 1, "high": 2}
ACTIVITY_ORDER = {"low": 0, "medium": 1, "high": 2}

WEATHER_RAIN = "rain"
DEFAULT_WEATHER = "sun"
DEFAULT_PARTY_TYPE = "solo"
DEFAULT_BUDGET = "medium"
DEFAULT_ACTIVITY = "medium"
DEFAULT_CITY_LABEL = "Йошкар-Оле"

MIN_STOPS = 2
TARGET_STOPS = 4
MAX_STOPS = 5

LIKE_WEIGHT = 3.0
DISLIKE_WEIGHT = 4.0
FOOD_WEIGHT = 2.0
PHOTO_WEIGHT = 0.3
LOCAL_WEIGHT = 0.5
MINISTRY_WEIGHT = 0.35
INDOOR_RAIN_BONUS = 2.0
EXACT_AUDIENCE_BONUS = 1.0
EXACT_BUDGET_BONUS = 0.4
EXACT_ACTIVITY_BONUS = 0.4
LONG_DURATION_LOW_ACTIVITY_PENALTY = 1.0

RELAXED_BUDGET_PENALTY = 2.5
RELAXED_ACTIVITY_PENALTY = 2.0


# -----------------------------
# Внутренние структуры
# -----------------------------

@dataclass(frozen=True)
class ScoredCandidate:
    place: dict[str, Any]
    score: float
    why: str
    liked_matches: tuple[str, ...]
    disliked_matches: tuple[str, ...]
    food_matches: tuple[str, ...]
    used_relaxed_budget: bool = False
    used_relaxed_activity: bool = False


# -----------------------------
# Нормализация
# -----------------------------

def _norm_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _norm_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_norm_str(value)] if _norm_str(value) else []
    result: list[str] = []
    for item in value:
        normalized = _norm_str(item)
        if normalized:
            result.append(normalized)
    return result


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    liked_tags = _dedupe_preserve_order(_norm_list(profile.get("liked_tags")))
    disliked_tags = _dedupe_preserve_order(_norm_list(profile.get("disliked_tags")))
    food_preferences = _dedupe_preserve_order(_norm_list(profile.get("food_preferences")))

    weather = _norm_str(profile.get("weather")) or DEFAULT_WEATHER
    if weather not in {"sun", "cloud", "rain"}:
        weather = DEFAULT_WEATHER

    budget = _norm_str(profile.get("budget")) or DEFAULT_BUDGET
    if budget not in BUDGET_ORDER:
        budget = DEFAULT_BUDGET

    activity_level = _norm_str(profile.get("activity_level")) or DEFAULT_ACTIVITY
    if activity_level not in ACTIVITY_ORDER:
        activity_level = DEFAULT_ACTIVITY

    party_type = _norm_str(profile.get("party_type")) or DEFAULT_PARTY_TYPE
    
    # Сохраняем duration если есть
    duration = profile.get("duration")

    return {
        "party_type": party_type,
        "age_group": _norm_str(profile.get("age_group")),
        "budget": budget,
        "activity_level": activity_level,
        "liked_tags": liked_tags,
        "disliked_tags": disliked_tags,
        "food_preferences": food_preferences,
        "weather": weather,
        "duration": duration,
    }


def normalize_place(place: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(place)
    normalized["id"] = str(place.get("id", "")).strip()
    normalized["name"] = str(place.get("name", "Без названия")).strip() or "Без названия"
    normalized["category"] = _norm_str(place.get("category")) or "other"
    normalized["description"] = str(place.get("description", "")).strip()
    normalized["tags"] = _dedupe_preserve_order(_norm_list(place.get("tags")))
    normalized["indoor"] = bool(place.get("indoor", False))
    normalized["duration_min"] = _to_int(place.get("duration_min"), default=45)

    budget = _norm_str(place.get("budget")) or DEFAULT_BUDGET
    normalized["budget"] = budget if budget in BUDGET_ORDER else DEFAULT_BUDGET

    audiences = _dedupe_preserve_order(_norm_list(place.get("audiences")))
    normalized["audiences"] = audiences

    activity_level = _norm_str(place.get("activity_level")) or DEFAULT_ACTIVITY
    normalized["activity_level"] = activity_level if activity_level in ACTIVITY_ORDER else DEFAULT_ACTIVITY

    normalized["food_tags"] = _dedupe_preserve_order(_norm_list(place.get("food_tags")))
    normalized["photo_score"] = _to_float(place.get("photo_score"), default=0.0)
    normalized["local_score"] = _to_float(place.get("local_score"), default=0.0)
    normalized["coords"] = place.get("coords")

    weather_ok = _dedupe_preserve_order(_norm_list(place.get("weather_ok")))
    normalized["weather_ok"] = weather_ok

    normalized["ministry_boost"] = _to_float(place.get("ministry_boost"), default=0.0)
    promo_label = place.get("promo_label")
    normalized["promo_label"] = str(promo_label).strip() if promo_label else None

    return normalized


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


# -----------------------------
# Проверки совместимости
# -----------------------------

def _weather_ok(place: dict[str, Any], weather: str) -> bool:
    allowed = place.get("weather_ok") or []
    indoor = bool(place.get("indoor", False))

    if allowed:
        return weather in allowed

    # Без weather_ok делаем безопасный фолбэк:
    # indoor-места считаем допустимыми всегда,
    # outdoor в дождь — недопустимыми.
    if weather == WEATHER_RAIN and not indoor:
        return False
    return True


def _audience_ok(place: dict[str, Any], party_type: str) -> bool:
    audiences = place.get("audiences") or []
    if not audiences:
        return True
    return party_type in audiences


def _budget_delta(place_budget: str, user_budget: str) -> int:
    return BUDGET_ORDER.get(place_budget, BUDGET_ORDER[DEFAULT_BUDGET]) - BUDGET_ORDER.get(
        user_budget, BUDGET_ORDER[DEFAULT_BUDGET]
    )


def _activity_delta(place_activity: str, user_activity: str) -> int:
    return ACTIVITY_ORDER.get(place_activity, ACTIVITY_ORDER[DEFAULT_ACTIVITY]) - ACTIVITY_ORDER.get(
        user_activity, ACTIVITY_ORDER[DEFAULT_ACTIVITY]
    )


def _passes_strict_filters(place: dict[str, Any], profile: dict[str, Any]) -> bool:
    if not _weather_ok(place, profile["weather"]):
        return False
    if not _audience_ok(place, profile["party_type"]):
        return False
    if _budget_delta(place["budget"], profile["budget"]) > 0:
        return False
    if _activity_delta(place["activity_level"], profile["activity_level"]) > 0:
        return False
    return True


def _passes_relaxed_filters(place: dict[str, Any], profile: dict[str, Any]) -> bool:
    if not _weather_ok(place, profile["weather"]):
        return False
    if not _audience_ok(place, profile["party_type"]):
        return False

    # Разрешаем мягкий фолбэк только на 1 уровень выше по бюджету/активности,
    # чтобы маршрут не пустел при маленькой базе.
    if _budget_delta(place["budget"], profile["budget"]) > 1:
        return False
    if _activity_delta(place["activity_level"], profile["activity_level"]) > 1:
        return False
    return True


# -----------------------------
# Скоринг и объяснения
# -----------------------------

def score_place(place: dict[str, Any], profile: dict[str, Any]) -> ScoredCandidate:
    liked_matches = tuple(sorted(set(profile["liked_tags"]) & set(place.get("tags", []))))
    disliked_matches = tuple(sorted(set(profile["disliked_tags"]) & set(place.get("tags", []))))
    food_matches = tuple(sorted(set(profile["food_preferences"]) & set(place.get("food_tags", []))))

    score = 0.0
    score += len(liked_matches) * LIKE_WEIGHT
    score -= len(disliked_matches) * DISLIKE_WEIGHT
    score += len(food_matches) * FOOD_WEIGHT

    score += _to_float(place.get("photo_score"), 0.0) * PHOTO_WEIGHT
    score += _to_float(place.get("local_score"), 0.0) * LOCAL_WEIGHT
    score += _to_float(place.get("ministry_boost"), 0.0) * MINISTRY_WEIGHT

    if profile["weather"] == WEATHER_RAIN and place.get("indoor"):
        score += INDOOR_RAIN_BONUS

    if profile["party_type"] in (place.get("audiences") or []):
        score += EXACT_AUDIENCE_BONUS

    if place.get("budget") == profile["budget"]:
        score += EXACT_BUDGET_BONUS

    if place.get("activity_level") == profile["activity_level"]:
        score += EXACT_ACTIVITY_BONUS

    if profile["activity_level"] == "low" and _to_int(place.get("duration_min"), 45) > 90:
        score -= LONG_DURATION_LOW_ACTIVITY_PENALTY

    used_relaxed_budget = _budget_delta(place["budget"], profile["budget"]) == 1
    used_relaxed_activity = _activity_delta(place["activity_level"], profile["activity_level"]) == 1

    if used_relaxed_budget:
        score -= RELAXED_BUDGET_PENALTY
    if used_relaxed_activity:
        score -= RELAXED_ACTIVITY_PENALTY

    why = build_why(
        place=place,
        profile=profile,
        liked_matches=liked_matches,
        food_matches=food_matches,
        used_relaxed_budget=used_relaxed_budget,
        used_relaxed_activity=used_relaxed_activity,
    )

    return ScoredCandidate(
        place=place,
        score=round(score, 3),
        why=why,
        liked_matches=liked_matches,
        disliked_matches=disliked_matches,
        food_matches=food_matches,
        used_relaxed_budget=used_relaxed_budget,
        used_relaxed_activity=used_relaxed_activity,
    )


def build_why(
    place: dict[str, Any],
    profile: dict[str, Any],
    liked_matches: tuple[str, ...],
    food_matches: tuple[str, ...],
    used_relaxed_budget: bool,
    used_relaxed_activity: bool,
) -> str:
    reasons: list[str] = []

    if liked_matches:
        reasons.append(f"интересы: {', '.join(liked_matches[:2])}")

    if profile["weather"] == WEATHER_RAIN and place.get("indoor"):
        reasons.append("подходит для дождя")

    if food_matches:
        reasons.append(f"еда: {', '.join(food_matches[:1])}")

    if profile["party_type"] and profile["party_type"] in (place.get("audiences") or []):
        party_map = {
            "solo": "подходит для solo-формата",
            "couple": "подходит для пары",
            "family": "подходит для семейного формата",
            "seniors": "подходит для спокойного формата",
        }
        reasons.append(party_map.get(profile["party_type"], "совпадает по формату поездки"))

    if not reasons:
        reasons.append("подходит под выбранные параметры маршрута")

    if used_relaxed_budget:
        reasons.append("чуть выше по бюджету, но всё ещё уместно")
    if used_relaxed_activity:
        reasons.append("слегка активнее базового профиля")

    return "Подходит, потому что " + ", ".join(reasons[:3]) + "."


# -----------------------------
# Сборка маршрута
# -----------------------------

def _sort_candidates(candidates: list[ScoredCandidate]) -> list[ScoredCandidate]:
    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate.score,
            -_to_float(candidate.place.get("local_score"), 0.0),
            -_to_float(candidate.place.get("photo_score"), 0.0),
            _norm_str(candidate.place.get("name")),
            _norm_str(candidate.place.get("id")),
        ),
    )


def _choose_target_stop_count(candidates: list[ScoredCandidate], profile: Optional[dict[str, Any]] = None) -> int:
    """
    Выбирает целевое количество мест на основе времени и кандидатов.
    """
    count = len(candidates)
    if count <= 0:
        return 0
    
    # Проверяем duration из профиля
    duration = None
    if profile:
        duration = profile.get('duration')
    
    # Адаптивное количество мест от времени
    if duration:
        duration_map = {
            '30min': 1,    # 1 место на 30 минут
            '1h': 2,       # 2 места на 1 час
            '2h': 3,       # 3 места на 2 часа
            'half-day': 5, # 5 мест на полдня
        }
        target = duration_map.get(duration, TARGET_STOPS)
        return min(target, count)
    
    # Стандартная логика если duration не указан
    if count < MIN_STOPS:
        return count
    if count >= 5:
        top_five = candidates[:5]
        avg_duration = sum(_to_int(item.place.get("duration_min"), 45) for item in top_five) / len(top_five)
        if avg_duration <= 45:
            return 5
    return min(TARGET_STOPS, count)


def _select_route_candidates(candidates: list[ScoredCandidate], profile: Optional[dict[str, Any]] = None) -> list[ScoredCandidate]:
    """
    Собирает маршрут с учётом уникальности мест и времени.
    """
    ordered = _sort_candidates(candidates)
    
    # Учитываем время из профиля если есть
    target_count = _choose_target_stop_count(ordered, profile)
    if target_count == 0:
        return []
    
    # Ограничиваем по времени если указано в профиле
    duration_limit = None
    min_stops = MIN_STOPS
    if profile:
        duration_map = {
            '30min': 30,
            '1h': 60,
            '2h': 120,
            'half-day': 240,
        }
        duration_limit = duration_map.get(profile.get('duration'))
        # Для коротких маршрутов меньше минимальное количество мест
        if duration_limit and duration_limit <= 30:
            min_stops = 1
        elif duration_limit and duration_limit <= 60:
            min_stops = 2
    
    selected: list[ScoredCandidate] = []
    selected_ids: set[str] = set()
    category_counts: dict[str, int] = {}
    promo_used = False
    total_duration = 0

    def can_take(candidate: ScoredCandidate, *, max_per_category: int, check_duration: bool = True) -> bool:
        nonlocal total_duration
        place = candidate.place
        place_id = str(place.get("id", ""))
        
        # Проверка на дубликат
        if not place_id or place_id in selected_ids:
            return False
        
        # Проверка категории
        category = place.get("category", "other")
        if category_counts.get(category, 0) >= max_per_category:
            return False
        
        # Проверка promo
        if place.get("promo_label") and promo_used:
            return False
        
        # Проверка по времени
        if check_duration and duration_limit:
            place_duration = _to_int(place.get("duration_min"), 45)
            if total_duration + place_duration > duration_limit:
                return False
        
        return True

    def take(candidate: ScoredCandidate) -> None:
        nonlocal promo_used, total_duration
        place = candidate.place
        place_id = str(place.get("id", ""))
        
        selected.append(candidate)
        selected_ids.add(place_id)
        
        category = place.get("category", "other")
        category_counts[category] = category_counts.get(category, 0) + 1
        
        total_duration += _to_int(place.get("duration_min"), 45)
        
        if place.get("promo_label"):
            promo_used = True

    # Проход 1: максимальная диверсификация по категориям (макс 1 на категорию)
    for candidate in ordered:
        if len(selected) >= target_count:
            break
        if duration_limit and total_duration >= duration_limit:
            break
        if can_take(candidate, max_per_category=1):
            take(candidate)

    # Проход 2: разрешаем повтор категории (макс 2), но только если есть время
    if len(selected) < target_count:
        for candidate in ordered:
            if len(selected) >= target_count:
                break
            if duration_limit and total_duration >= duration_limit:
                break
            if can_take(candidate, max_per_category=2):
                take(candidate)

    # Проход 3: добираем до min_stops, игнорируя лимит времени если нужно
    if len(selected) < min_stops:
        for candidate in ordered:
            if len(selected) >= min_stops:
                break
            place = candidate.place
            place_id = str(place.get("id", ""))
            # Строгая проверка на дубликат
            if not place_id or place_id in selected_ids:
                continue
            if place.get("promo_label") and promo_used:
                continue
            selected.append(candidate)
            selected_ids.add(place_id)
            category = place.get("category", "other")
            category_counts[category] = category_counts.get(category, 0) + 1
            total_duration += _to_int(place.get("duration_min"), 45)
            if place.get("promo_label"):
                promo_used = True

    return selected[:MAX_STOPS]


def _plural_hours_ru(hours: int) -> str:
    remainder_10 = hours % 10
    remainder_100 = hours % 100
    if remainder_10 == 1 and remainder_100 != 11:
        return "час"
    if remainder_10 in {2, 3, 4} and remainder_100 not in {12, 13, 14}:
        return "часа"
    return "часов"


def _format_duration_rounded(total_minutes: int) -> str:
    if total_minutes <= 0:
        return "0 минут"

    rounded = int(round(total_minutes / 30.0) * 30)
    hours = rounded // 60
    minutes = rounded % 60

    if hours and minutes:
        return f"{hours} {_plural_hours_ru(hours)} {minutes} мин"
    if hours:
        return f"{hours} {_plural_hours_ru(hours)}"
    return f"{minutes} мин"


def _build_route_title(profile: dict[str, Any], total_minutes: int) -> str:
    pace_map = {
        "low": "Спокойный",
        "medium": "Сбалансированный",
        "high": "Активный",
    }
    pace_label = pace_map.get(profile["activity_level"], "Маршрут")
    duration_label = _format_duration_rounded(total_minutes)
    return f"{pace_label} маршрут по {DEFAULT_CITY_LABEL} на {duration_label}"


def _build_route_summary(profile: dict[str, Any], selected: list[ScoredCandidate]) -> str:
    parts: list[str] = []

    weather_map = {
        "rain": "Маршрут адаптирован под дождь",
        "cloud": "Маршрут адаптирован под пасмурную погоду",
        "sun": "Маршрут адаптирован под хорошую погоду",
    }
    parts.append(weather_map.get(profile["weather"], "Маршрут адаптирован под условия поездки"))

    party_map = {
        "solo": "для solo-формата",
        "couple": "для пары",
        "family": "для семейного формата",
        "seniors": "для спокойного формата",
    }
    if profile["party_type"] in party_map:
        parts.append(party_map[profile["party_type"]])

    top_interest_matches: list[str] = []
    for candidate in selected:
        for tag in candidate.liked_matches:
            if tag not in top_interest_matches:
                top_interest_matches.append(tag)
            if len(top_interest_matches) >= 2:
                break
        if len(top_interest_matches) >= 2:
            break

    if top_interest_matches:
        parts.append(f"с акцентом на {', '.join(top_interest_matches)}")

    return ", ".join(parts) + "."


def _stop_to_response(candidate: ScoredCandidate) -> dict[str, Any]:
    place = candidate.place
    tags = list(place.get("tags", []))
    if place.get("indoor") and "indoor" not in tags:
        tags.append("indoor")
    elif not place.get("indoor") and "outdoor" not in tags:
        tags.append("outdoor")

    return {
        "id": place.get("id"),
        "name": place.get("name"),
        "why": candidate.why,
        "duration_min": _to_int(place.get("duration_min"), 45),
        "tags": tags,
        "promo": place.get("promo_label"),
        "address": place.get("address"),
    }


# -----------------------------
# Публичный API
# -----------------------------

def build_route(profile: dict[str, Any], places: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Собирает маршрут на 3–5 точек по профилю пользователя и локальному списку мест.

    Алгоритм:
    1. Нормализует профиль и места.
    2. Применяет строгую фильтрацию по погоде, бюджету, аудитории и активности.
    3. Если мест слишком мало, включает мягкий фолбэк по бюджету/активности (не больше +1 уровня).
    4. Считает score для каждой точки.
    5. Собирает диверсифицированный маршрут с максимум одной promo-точкой.
    6. Возвращает route_json по контракту.
    """
    normalized_profile = normalize_profile(profile)
    normalized_places = [normalize_place(place) for place in places if isinstance(place, dict)]

    strict_candidates = [place for place in normalized_places if _passes_strict_filters(place, normalized_profile)]

    if len(strict_candidates) >= MIN_STOPS:
        candidate_pool = strict_candidates
    else:
        candidate_pool = [place for place in normalized_places if _passes_relaxed_filters(place, normalized_profile)]

    scored_candidates = [score_place(place, normalized_profile) for place in candidate_pool]
    selected_candidates = _select_route_candidates(scored_candidates, normalized_profile)

    total_duration = sum(_to_int(item.place.get("duration_min"), 45) for item in selected_candidates)

    if not selected_candidates:
        return {
            "route_title": f"Маршрут по {DEFAULT_CITY_LABEL}",
            "summary": "Не удалось собрать подходящий маршрут по текущим параметрам.",
            "stops": [],
        }

    # Пытаемся использовать Groq для генерации описания (если доступен)
    try:
        from backend.groq_service import get_groq_service
        groq = get_groq_service()
        if groq.available:
            summary = groq.generate_route_description(
                party_type=normalized_profile["party_type"],
                weather=normalized_profile["weather"],
                stops=[_stop_to_response(c) for c in selected_candidates],
                liked_tags=normalized_profile["liked_tags"]
            )
        else:
            summary = _build_route_summary(normalized_profile, selected_candidates)
    except Exception:
        # При любой ошибке используем fallback
        summary = _build_route_summary(normalized_profile, selected_candidates)

    return {
        "route_title": _build_route_title(normalized_profile, total_duration),
        "summary": summary,
        "stops": [_stop_to_response(candidate) for candidate in selected_candidates],
    }


__all__ = [
    "build_route",
    "normalize_profile",
    "normalize_place",
    "score_place",
    "build_why",
]
