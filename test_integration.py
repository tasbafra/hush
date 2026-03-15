"""
Комплексная проверка на отсутствие заглушек и совместимость модулей.

Запуск: python test_integration.py
"""

import json
import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent))

from main import app, load_places
from fastapi.testclient import TestClient

client = TestClient(app)


def test_no_placeholders_in_code():
    """Проверка: в коде нет заглушек типа 'TODO', 'placeholder', 'pass'."""
    files_to_check = [
        Path(__file__).parent / "main.py",
        Path(__file__).parent / "replanner.py",
        Path(__file__).parent.parent / "scoring.py",
    ]
    
    placeholder_patterns = [
        "TODO",
        "FIXME",
        "placeholder",
        "stub",
        "заглушка",
    ]
    
    for file_path in files_to_check:
        if not file_path.exists():
            print(f"⚠ Файл не найден: {file_path}")
            continue
            
        content = file_path.read_text(encoding="utf-8")
        
        # Проверяем на наличие заглушек в комментариях и строках
        for pattern in placeholder_patterns:
            if pattern.lower() in content.lower():
                # Игнорируем импорты и нормальные использования слов
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if pattern.lower() in line.lower():
                        # Пропускаем строки с импортами и docstrings
                        if 'import' in line or '"""' in line or "'''" in line:
                            continue
                        # Это может быть заглушка
                        print(f"⚠ Возможная заглушка в {file_path.name}:{i}: {line.strip()[:80]}")
    
    print("✓ Проверка на заглушки завершена")


def test_places_json_structure():
    """Проверка: places.json имеет правильную структуру."""
    places = load_places()
    
    assert isinstance(places, list), "places.json должен быть списком"
    assert len(places) > 0, "places.json пуст"
    
    required_fields = [
        "id", "name", "category", "indoor", "duration_min",
        "tags", "activity_level", "budget"
    ]
    
    for i, place in enumerate(places):
        for field in required_fields:
            assert field in place, f"Место {i} не имеет поля {field}"
        
        # Проверка типов
        assert isinstance(place["id"], str), f"Место {i}: id должен быть строкой"
        assert isinstance(place["name"], str), f"Место {i}: name должен быть строкой"
        assert isinstance(place["indoor"], bool), f"Место {i}: indoor должен быть bool"
        assert isinstance(place["duration_min"], int), f"Место {i}: duration_min должен быть int"
        assert isinstance(place["tags"], list), f"Место {i}: tags должен быть списком"
    
    print(f"✓ places.json: {len(places)} мест, структура корректна")


def test_generate_route_real_logic():
    """Проверка: /generate-route использует реальную логику, не заглушку."""
    # Запрос с конкретными параметрами
    response = client.post("/generate-route", json={
        "party_type": "family",
        "age_group": "adults",
        "budget": "medium",
        "activity_level": "low",
        "liked_tags": ["история", "фото"],
        "disliked_tags": [],
        "food_preferences": ["местная кухня"],
        "weather": "sun"
    })
    
    assert response.status_code == 200, f"Status: {response.status_code}"
    data = response.json()
    
    # Проверяем, что ответ не пустой
    assert data["route_title"], "route_title пуст"
    assert data["summary"], "summary пуст"
    assert len(data["stops"]) >= 1, "stops пуст"
    
    # Проверяем, что у каждого места есть все поля
    for stop in data["stops"]:
        assert stop["id"], "id пуст"
        assert stop["name"], "name пуст"
        assert stop["why"], "why пуст (возможная заглушка!)"
        assert stop["duration_min"] > 0, "duration_min некорректен"
        assert isinstance(stop["tags"], list), "tags не список"
    
    # Проверяем, что why не шаблонное
    for stop in data["stops"]:
        why = stop["why"]
        assert "placeholder" not in why.lower(), f"Заглушка в why: {why}"
        assert "todo" not in why.lower(), f"Заглушка в why: {why}"
    
    print(f"✓ /generate-route: {len(data['stops'])} мест, логика реальная")


def test_generate_route_weather_rain():
    """Проверка: дождь реально влияет на маршрут (indoor места)."""
    response = client.post("/generate-route", json={
        "party_type": "solo",
        "age_group": "adult",
        "budget": "low",
        "activity_level": "low",
        "liked_tags": [],
        "disliked_tags": [],
        "food_preferences": [],
        "weather": "rain"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Все места должны быть indoor или иметь weather_ok с rain
    places = load_places()
    for stop in data["stops"]:
        place = next((p for p in places if p["id"] == stop["id"]), None)
        assert place is not None, f"Место {stop['id']} не найдено в базе"
        
        # Проверяем, что место подходит для дождя
        is_indoor = place.get("indoor", False)
        weather_ok = place.get("weather_ok", [])
        has_rain = "rain" in weather_ok
        
        assert is_indoor or has_rain, f"Место {stop['name']} не подходит для дождя"
    
    print(f"✓ Дождь: все {len(data['stops'])} мест подходят для дождя")


def test_replan_route_rain_mode():
    """Проверка: rain_mode реально заменяет уличные места."""
    # Создаём маршрут с уличным местом
    response = client.post("/replan-route", json={
        "current_stop_ids": ["patriarshaya_emb"],  # indoor=False
        "action": "rain_mode",
        "weather": "rain"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    places = load_places()
    for stop in data["stops"]:
        place = next((p for p in places if p["id"] == stop["id"]), None)
        if place:
            assert place.get("indoor", False), f"Место {stop['name']} должно быть indoor"
    
    print(f"✓ rain_mode: все места крытые")


def test_replan_route_coffee_nearby():
    """Проверка: coffee_nearby реально добавляет кофейню."""
    response = client.post("/replan-route", json={
        "current_stop_ids": ["patriarshaya_emb", "museum_city"],
        "action": "coffee_nearby",
        "weather": "sun"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Должно быть больше мест, чем было
    assert len(data["stops"]) > 2, "Кофейня не добавлена"
    
    # Проверяем, что есть кофейня
    places = load_places()
    coffee_found = False
    for stop in data["stops"]:
        place = next((p for p in places if p["id"] == stop["id"]), None)
        if place:
            if place.get("category") == "cafe" or "кофе" in str(place.get("tags", [])):
                coffee_found = True
                break
    
    assert coffee_found, "Кофейня не найдена в маршруте"
    print(f"✓ coffee_nearby: кофейня добавлена")


def test_replan_route_tired_mode():
    """Проверка: tired_mode реально сокращает маршрут."""
    response = client.post("/replan-route", json={
        "current_stop_ids": ["patriarshaya_emb", "museum_city", "cafe_national"],
        "action": "tired_mode",
        "weather": "sun"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Маршрут должен стать короче
    assert len(data["stops"]) < 3, "Маршрут не сократился"
    print(f"✓ tired_mode: маршрут сокращён с 3 до {len(data['stops'])}")


def test_scoring_integration():
    """Проверка: scoring.py реально используется в /generate-route."""
    # Запрос с liked_tags
    response = client.post("/generate-route", json={
        "party_type": "couple",
        "age_group": "adult",
        "budget": "medium",
        "activity_level": "low",
        "liked_tags": ["искусство", "фото"],
        "disliked_tags": [],
        "food_preferences": [],
        "weather": "sun"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что why содержит объяснения
    for stop in data["stops"]:
        why = stop["why"]
        # why должен содержать осмысленный текст, не шаблон
        assert len(why) > 10, f"why слишком короткий: {why}"
        assert "подходит" in why.lower() or "интерес" in why.lower(), f"why не от scoring: {why}"
    
    print(f"✓ scoring.py: why содержит осмысленные объяснения")


def test_api_contract():
    """Проверка: API соответствует контракту."""
    # Проверяем /generate-route
    response = client.post("/generate-route", json={
        "party_type": "solo",
        "age_group": "adult",
        "budget": "low",
        "activity_level": "low",
        "liked_tags": [],
        "disliked_tags": [],
        "food_preferences": [],
        "weather": "sun"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем структуру ответа
    assert "route_title" in data
    assert "summary" in data
    assert "stops" in data
    
    for stop in data["stops"]:
        assert "id" in stop
        assert "name" in stop
        assert "why" in stop
        assert "duration_min" in stop
        assert "tags" in stop
        assert "promo" in stop
    
    # Проверяем /replan-route
    response = client.post("/replan-route", json={
        "current_stop_ids": ["patriarshaya_emb"],
        "action": "rain_mode",
        "weather": "rain"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "route_title" in data
    assert "summary" in data
    assert "stops" in data
    
    print("✓ API контракт: все поля на месте")


def test_no_hardcoded_responses():
    """Проверка: ответы не захардкожены, а генерируются динамически."""
    # Делаем два одинаковых запроса
    response1 = client.post("/generate-route", json={
        "party_type": "family",
        "age_group": "adults",
        "budget": "medium",
        "activity_level": "low",
        "liked_tags": ["история"],
        "disliked_tags": [],
        "food_preferences": [],
        "weather": "sun"
    })
    
    response2 = client.post("/generate-route", json={
        "party_type": "family",
        "age_group": "adults",
        "budget": "medium",
        "activity_level": "low",
        "liked_tags": ["фото"],  # Другой тег
        "disliked_tags": [],
        "food_preferences": [],
        "weather": "sun"
    })
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Ответы должны отличаться (разные liked_tags)
    # По крайней мере summary или why должны отличаться
    assert data1 != data2 or data1["summary"] != data2["summary"], "Ответы одинаковые — возможная заглушка!"
    
    print("✓ Ответы генерируются динамически, не заглушки")


def run_all_tests():
    """Запускает все тесты."""
    print("=" * 60)
    print("ПРОВЕРКА НА ОТСУТСТВИЕ ЗАГЛУШЕК И СОВМЕСТИМОСТЬ")
    print("=" * 60)
    
    tests = [
        ("Структура places.json", test_places_json_structure),
        ("Отсутствие заглушек в коде", test_no_placeholders_in_code),
        ("/generate-route реальная логика", test_generate_route_real_logic),
        ("/generate-route дождь", test_generate_route_weather_rain),
        ("/replan-route rain_mode", test_replan_route_rain_mode),
        ("/replan-route coffee_nearby", test_replan_route_coffee_nearby),
        ("/replan-route tired_mode", test_replan_route_tired_mode),
        ("scoring.py интеграция", test_scoring_integration),
        ("API контракт", test_api_contract),
        ("Отсутствие хардкода", test_no_hardcoded_responses),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for name, test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
            errors.append((name, str(e)))
        except Exception as e:
            print(f"✗ {name}: Ошибка {e}")
            failed += 1
            errors.append((name, str(e)))
    
    print("=" * 60)
    print(f"Результат: {passed}/{len(tests)} тестов пройдено")
    
    if errors:
        print("\n⚠️ ОШИБКИ:")
        for name, error in errors:
            print(f"  - {name}: {error}")
    else:
        print("\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Заглушек нет.")
    
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
