"""
Модуль перестроения маршрутов (replanner.py)

Этот модуль содержит функцию replan_route, которая перестраивает маршрут
на основе действия пользователя (дождь, усталость, желание кофе).

Используется в эндпоинте /replan-route в main.py
"""

from typing import List, Dict, Any, Optional


def replan_route(
    current_stop_ids: List[str],
    action: str,
    weather: str,
    all_places: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Перестраивает маршрут на основе действия пользователя.
    
    Args:
        current_stop_ids: Список ID мест, которые сейчас в маршруте.
        action: Действие пользователя ("rain_mode", "tired_mode", "coffee_nearby") или ID места для замены.
        weather: Текущая погода ("rain", "sun", "cloud" и т.д.).
        all_places: Вся база мест (список словарей).
    
    Returns:
        Словарь с новым маршрутом в формате:
        {
            "route_title": str,
            "summary": str,
            "stops": List[Dict],
            "unchanged_reason": Optional[str]
        }
    """
    # Получаем текущие места маршрута
    current_places = []
    for pid in current_stop_ids:
        place = _get_place_by_id(pid, all_places)
        if place:
            current_places.append(place)
    
    if not current_places:
        return {
            "route_title": "Ошибка перестроения",
            "summary": "Не удалось найти места текущего маршрута.",
            "stops": [],
            "unchanged_reason": "Текущий маршрут пуст или содержит несуществующие места."
        }
    
    # Проверка на замену конкретного места (action содержит ID места)
    if action and action.startswith("replace_place:"):
        place_to_replace = action.replace("replace_place:", "").strip()
        return _handle_replace_place(current_places, place_to_replace, all_places)
    
    # Обработка в зависимости от действия
    if action == "rain_mode":
        return _handle_rain_mode(current_places, all_places)
    elif action == "tired_mode":
        return _handle_tired_mode(current_places, all_places)
    elif action == "coffee_nearby":
        return _handle_coffee_nearby(current_places, all_places)
    else:
        return {
            "route_title": "Ошибка перестроения",
            "summary": f"Неизвестное действие: {action}",
            "stops": [],
            "unchanged_reason": f"Действие '{action}' не поддерживается."
        }


def _handle_replace_place(
    current_places: List[Dict],
    place_name_or_id: str,
    all_places: List[Dict]
) -> Dict[str, Any]:
    """
    Заменяет конкретное место в маршруте на альтернативное.
    
    Args:
        current_places: Текущие места маршрута.
        place_name_or_id: Название или ID места которое нужно заменить.
        all_places: Вся база мест.
    """
    place_name_lower = place_name_or_id.lower()
    
    # Находим место которое нужно заменить
    place_to_replace = None
    place_index = -1
    
    for i, place in enumerate(current_places):
        if (place_name_lower in place["name"].lower() or 
            place_name_lower in place.get("category", "").lower() or
            place_name_lower == place["id"].lower()):
            place_to_replace = place
            place_index = i
            break
    
    if not place_to_replace:
        return {
            "route_title": "Ошибка замены",
            "summary": f"Место '{place_name_or_id}' не найдено в маршруте.",
            "stops": [_build_stop_dict(p) for p in current_places],
            "unchanged_reason": f"Место '{place_name_or_id}' не найдено в текущем маршруте."
        }
    
    # Находим альтернативу (той же категории но другое)
    current_ids = {p["id"] for p in current_places}
    replacement = None
    
    for place in all_places:
        if place["id"] in current_ids:
            continue
        # Ищем место похожей категории но не то же самое
        if (place["category"] == place_to_replace["category"] or 
            place["category"] in ["cafe", "restaurant"] and place_to_replace["category"] in ["cafe", "restaurant"]):
            replacement = place
            break
    
    # Если не нашли той же категории, берём любое другое
    if not replacement:
        for place in all_places:
            if place["id"] not in current_ids:
                replacement = place
                break
    
    if not replacement:
        return {
            "route_title": "Ошибка замены",
            "summary": "Нет доступных мест для замены.",
            "stops": [_build_stop_dict(p) for p in current_places],
            "unchanged_reason": "Нет доступных мест для замены."
        }
    
    # Заменяем место
    new_stops = [_build_stop_dict(p) for p in current_places]
    new_stops[place_index] = _build_stop_dict(
        replacement,
        f"Замена вместо '{place_to_replace['name']}' — {replacement.get('description', '')[:50]}..."
    )
    
    return {
        "route_title": "Маршрут обновлён",
        "summary": f"Заменили '{place_to_replace['name']}' на '{replacement['name']}'.",
        "stops": new_stops,
        "unchanged_reason": None
    }


def _get_place_by_id(place_id: str, places: List[Dict]) -> Optional[Dict]:
    """Находит место по ID."""
    for p in places:
        if p["id"] == place_id:
            return p
    return None


def _build_stop_dict(place: Dict, why: str = "") -> Dict:
    """Создаёт словарь Stop из данных места."""
    return {
        "id": place["id"],
        "name": place["name"],
        "why": why or place.get("description", "")[:50] + "...",
        "duration_min": place["duration_min"],
        "tags": place["tags"],
        "promo": place.get("promo_label"),
        "address": place.get("address"),
    }


def _handle_rain_mode(
    current_places: List[Dict],
    all_places: List[Dict]
) -> Dict[str, Any]:
    """
    Обработка режима "дождь".
    Заменяет уличные локации (indoor=False) на крытые (indoor=True).
    """
    new_stops = []
    replaced_count = 0
    
    for place in current_places:
        if place.get("indoor", False):
            # Место уже в помещении — оставляем
            new_stops.append(_build_stop_dict(place))
        else:
            # Уличная локация — нужно заменить на крытую
            replacement = _find_indoor_replacement(place, all_places, current_places)
            if replacement:
                new_stops.append(_build_stop_dict(
                    replacement,
                    f"Замена на крытое место из-за дождя (было: {place['name']})"
                ))
                replaced_count += 1
            else:
                # Не нашли замену — пропускаем место
                pass
    
    if not new_stops:
        return {
            "route_title": "Маршрут не изменён",
            "summary": "К сожалению, не удалось найти крытые места для замены.",
            "stops": [],
            "unchanged_reason": "В базе нет доступных крытых мест (indoor=True) для замены уличных локаций."
        }
    
    return {
        "route_title": "Маршрут обновлен: защита от дождя",
        "summary": f"Мы заменили {replaced_count} уличн{'ую' if replaced_count == 1 else 'ые' if replaced_count < 5 else 'ых'} локаци{'ю' if replaced_count == 1 else 'и' if replaced_count < 5 else 'й'} на крытые, чтобы вы не промокли.",
        "stops": new_stops,
        "unchanged_reason": None
    }


def _find_indoor_replacement(
    current_place: Dict,
    all_places: List[Dict],
    current_route: List[Dict]
) -> Optional[Dict]:
    """Ищет крытую замену для уличного места."""
    current_ids = {p["id"] for p in current_route}
    
    for place in all_places:
        if place["id"] in current_ids:
            continue
        if place.get("indoor", False):
            return place
    
    return None


def _handle_tired_mode(
    current_places: List[Dict],
    all_places: List[Dict]
) -> Dict[str, Any]:
    """
    Обработка режима "устали".
    Удаляет активные локации (activity_level="high") или сокращает маршрут.
    """
    new_stops = []
    removed_count = 0

    for place in current_places:
        activity = place.get("activity_level", "low")
        if activity == "high":
            # Пропускаем активное место
            removed_count += 1
        else:
            new_stops.append(_build_stop_dict(place))

    # Если не было активных мест, просто удаляем последнее (но только если мест > 1)
    if removed_count == 0 and len(new_stops) > 1:
        removed_place = new_stops.pop()
        removed_count = 1

    if not new_stops:
        return {
            "route_title": "Маршрут не изменён",
            "summary": "К сожалению, не удалось сократить маршрут.",
            "stops": [],
            "unchanged_reason": "Маршрут уже минимальной длины (1 место) или все места имеют высокую активность."
        }
    
    # Если маршрут не изменился (было 1 место, оно не high activity)
    if removed_count == 0 and len(new_stops) == len(current_places):
        return {
            "route_title": "Маршрут не изменён",
            "summary": "К сожалению, не удалось сократить маршрут.",
            "stops": new_stops,
            "unchanged_reason": "Маршрут уже минимальной длины (1 место)."
        }
    
    return {
        "route_title": "Маршрут обновлен: режим отдыха",
        "summary": f"Мы сократили маршрут, убрав {removed_count} активн{'ую' if removed_count == 1 else 'ые' if removed_count < 5 else 'ых'} локаци{'ю' if removed_count == 1 else 'и' if removed_count < 5 else 'й'}, чтобы вы могли отдохнуть.",
        "stops": new_stops,
        "unchanged_reason": None
    }


def _handle_coffee_nearby(
    current_places: List[Dict],
    all_places: List[Dict]
) -> Dict[str, Any]:
    """
    Обработка режима "хочу кофе рядом".
    Добавляет кофейню в маршрут (после первой точки).
    """
    # Ищем кофейню в базе
    coffee_place = _find_coffee_place(all_places, current_places)
    
    if not coffee_place:
        return {
            "route_title": "Маршрут не изменён",
            "summary": "К сожалению, рядом нет свободных кофеен.",
            "stops": [_build_stop_dict(p) for p in current_places],
            "unchanged_reason": "В базе нет доступных кофеен (category='cafe' или tags содержат 'кофе'), которые ещё не включены в маршрут."
        }
    
    # Формируем новый маршрут: вставляем кофейню после первой точки
    new_stops = []
    for i, place in enumerate(current_places):
        new_stops.append(_build_stop_dict(place))
        if i == 0:  # После первой точки
            new_stops.append(_build_stop_dict(
                coffee_place,
                "Добавили уютное место для кофе и отдыха."
            ))
    
    # Если маршрут стал слишком длинным (>5 точек), удаляем последнюю
    if len(new_stops) > 5:
        new_stops = new_stops[:5]
    
    return {
        "route_title": "Маршрут обновлен: время для кофе",
        "summary": "Мы добавили уютную кофейню поблизости, чтобы вы могли передохнуть.",
        "stops": new_stops,
        "unchanged_reason": None
    }


def _find_coffee_place(
    all_places: List[Dict],
    current_route: List[Dict]
) -> Optional[Dict]:
    """Ищет кофейню, которой ещё нет в маршруте."""
    current_ids = {p["id"] for p in current_route}
    
    for place in all_places:
        if place["id"] in current_ids:
            continue
        
        # Проверяем: category == "cafe" или в tags есть "кофе"
        category = place.get("category", "")
        tags = place.get("tags", [])
        
        if category == "cafe":
            return place
        
        # Проверяем теги на наличие слова "кофе"
        for tag in tags:
            if "кофе" in tag.lower():
                return place
        
        # Проверяем food_tags
        food_tags = place.get("food_tags", [])
        for tag in food_tags:
            if "кофе" in tag.lower():
                return place
    
    return None
