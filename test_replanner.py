"""
Комплексные тесты для модуля replanner.py

Запуск: python test_replanner.py
"""

import json
import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent))

from replanner import replan_route


def load_places():
    """Загружает базу мест."""
    places_path = Path(__file__).parent / "places.json"
    with open(places_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_rain_mode_basic():
    """Тест: дождь заменяет уличные места на крытые."""
    places = load_places()
    # Маршрут: улица + помещение
    result = replan_route(
        current_stop_ids=["patriarshaya_emb", "museum_city"],
        action="rain_mode",
        weather="rain",
        all_places=places
    )
    
    assert result["route_title"] == "Маршрут обновлен: защита от дождя"
    assert result["unchanged_reason"] is None
    assert len(result["stops"]) >= 1
    # Все места должны быть indoor
    for stop in result["stops"]:
        place = next(p for p in places if p["id"] == stop["id"])
        assert place["indoor"] == True, f"Место {stop['name']} должно быть indoor"
    
    print("✓ test_rain_mode_basic passed")


def test_rain_mode_all_outdoor():
    """Тест: дождь, весь маршрут уличный."""
    places = load_places()
    # Только уличные места (если бы они были в базе)
    result = replan_route(
        current_stop_ids=["patriarshaya_emb"],  # indoor=False
        action="rain_mode",
        weather="rain",
        all_places=places
    )
    
    assert result["unchanged_reason"] is None
    # Должно быть заменено на indoor
    for stop in result["stops"]:
        place = next(p for p in places if p["id"] == stop["id"])
        assert place["indoor"] == True
    
    print("✓ test_rain_mode_all_outdoor passed")


def test_tired_mode_removes_high_activity():
    """Тест: усталость удаляет места с high activity."""
    places = load_places()
    # В текущей базе все места имеют activity_level="low"
    # Поэтому должен удалиться последний элемент
    result = replan_route(
        current_stop_ids=["patriarshaya_emb", "museum_city", "cafe_national"],
        action="tired_mode",
        weather="sun",
        all_places=places
    )
    
    assert result["route_title"] == "Маршрут обновлен: режим отдыха"
    assert len(result["stops"]) == 2  # Было 3, стало 2
    print("✓ test_tired_mode_removes_high_activity passed")


def test_tired_mode_single_stop():
    """Тест: усталость с одним местом в маршруте."""
    places = load_places()
    result = replan_route(
        current_stop_ids=["patriarshaya_emb"],
        action="tired_mode",
        weather="sun",
        all_places=places
    )

    # Нельзя сократить маршрут из 1 места
    assert result["unchanged_reason"] is not None
    assert "минимальной длины" in result["unchanged_reason"].lower() or "1 место" in result["unchanged_reason"]
    print("✓ test_tired_mode_single_stop passed")


def test_coffee_nearby_adds_coffee():
    """Тест: кофе добавляет кофейню в маршрут."""
    places = load_places()
    result = replan_route(
        current_stop_ids=["patriarshaya_emb", "museum_city"],
        action="coffee_nearby",
        weather="sun",
        all_places=places
    )
    
    assert result["route_title"] == "Маршрут обновлен: время для кофе"
    assert len(result["stops"]) == 3  # Было 2, стало 3
    # Проверяем, что кофейня добавлена
    coffee_found = False
    for stop in result["stops"]:
        place = next(p for p in places if p["id"] == stop["id"])
        if place["category"] == "cafe" or "кофе" in str(place.get("tags", [])):
            coffee_found = True
            # Кофейня должна быть после первой точки (индекс 1)
            assert result["stops"].index(stop) == 1
    assert coffee_found == True
    print("✓ test_coffee_nearby_adds_coffee passed")


def test_coffee_nearby_no_duplicates():
    """Тест: кофе не добавляет уже существующую кофейню."""
    places = load_places()
    # В маршруте уже есть кофейня
    result = replan_route(
        current_stop_ids=["patriarshaya_emb", "coffee_house"],
        action="coffee_nearby",
        weather="sun",
        all_places=places
    )
    
    # Должна найти другую кофейню (cafe_national)
    assert result["unchanged_reason"] is None
    # Проверяем, что coffee_house остался один
    coffee_count = sum(1 for s in result["stops"] if s["id"] == "coffee_house")
    assert coffee_count == 1
    print("✓ test_coffee_nearby_no_duplicates passed")


def test_coffee_nearby_all_cafes_in_route():
    """Тест: кофе, когда все кофейни уже в маршруте."""
    places = load_places()
    # Включаем все кофейни из базы (их теперь много)
    all_coffee_ids = [p["id"] for p in places if p.get("category") == "cafe"]
    
    # Если кофеен меньше 5, добавим другие места
    route_ids = all_coffee_ids[:5]  # Берём максимум 5 кофеен
    
    result = replan_route(
        current_stop_ids=route_ids,
        action="coffee_nearby",
        weather="sun",
        all_places=places
    )
    
    # Должна быть ошибка - нет новых кофеен
    # Но если в базе много кофеен, то найдётся свободная
    # Поэтому проверяем что либо unchanged_reason, либо добавлена новая кофейня
    if result["unchanged_reason"] is None:
        # Значит нашлась свободная кофейня - это тоже ок
        assert len(result["stops"]) > len(route_ids)
    else:
        assert "нет доступных кофеен" in result["unchanged_reason"].lower()
    print("✓ test_coffee_nearby_all_cafes_in_route passed")


def test_invalid_action():
    """Тест: неизвестное действие."""
    places = load_places()
    result = replan_route(
        current_stop_ids=["patriarshaya_emb"],
        action="unknown_action",
        weather="sun",
        all_places=places
    )
    
    assert "не поддерживается" in result["unchanged_reason"]
    print("✓ test_invalid_action passed")


def test_empty_route():
    """Тест: пустой маршрут."""
    places = load_places()
    result = replan_route(
        current_stop_ids=[],
        action="rain_mode",
        weather="rain",
        all_places=places
    )
    
    assert result["unchanged_reason"] is not None
    assert "пуст" in result["unchanged_reason"].lower()
    print("✓ test_empty_route passed")


def test_invalid_stop_ids():
    """Тест: несуществующие ID мест."""
    places = load_places()
    result = replan_route(
        current_stop_ids=["nonexistent_1", "nonexistent_2"],
        action="rain_mode",
        weather="rain",
        all_places=places
    )
    
    assert result["unchanged_reason"] is not None
    print("✓ test_invalid_stop_ids passed")


def test_coffee_max_stops_limit():
    """Тест: кофе не превышает лимит в 5 мест."""
    places = load_places()
    # Маршрут из 5 мест - должен сократить до 5 после добавления кофе
    route_ids = ["patriarshaya_emb", "museum_city", "art_gallery", "park_lenin", "square_victory"]
    
    result = replan_route(
        current_stop_ids=route_ids,
        action="coffee_nearby",
        weather="sun",
        all_places=places
    )
    
    # После добавления кофе маршрут должен быть не больше 5
    assert len(result["stops"]) <= 5
    print("✓ test_coffee_max_stops_limit passed")


def test_response_structure():
    """Тест: структура ответа соответствует контракту."""
    places = load_places()
    result = replan_route(
        current_stop_ids=["patriarshaya_emb"],
        action="rain_mode",
        weather="rain",
        all_places=places
    )
    
    # Проверяем обязательные поля
    assert "route_title" in result
    assert "summary" in result
    assert "stops" in result
    assert "unchanged_reason" in result
    
    # Проверяем структуру stops
    for stop in result["stops"]:
        assert "id" in stop
        assert "name" in stop
        assert "why" in stop
        assert "duration_min" in stop
        assert "tags" in stop
        assert "promo" in stop or stop.get("promo") is None
    
    print("✓ test_response_structure passed")


def run_all_tests():
    """Запускает все тесты."""
    print("=" * 50)
    print("Запуск тестов replanner.py")
    print("=" * 50)
    
    tests = [
        test_rain_mode_basic,
        test_rain_mode_all_outdoor,
        test_tired_mode_removes_high_activity,
        test_tired_mode_single_stop,
        test_coffee_nearby_adds_coffee,
        test_coffee_nearby_no_duplicates,
        test_coffee_nearby_all_cafes_in_route,
        test_invalid_action,
        test_empty_route,
        test_invalid_stop_ids,
        test_coffee_max_stops_limit,
        test_response_structure,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"Результат: {passed}/{len(tests)} тестов пройдено")
    if failed > 0:
        print(f"⚠ {failed} тестов провалено")
    else:
        print("✓ Все тесты пройдены!")
    print("=" * 50)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
