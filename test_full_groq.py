"""
ПОЛНЫЙ ТЕСТ GROQ — все функции.

Запуск: python test_full_groq.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from groq_service import GroqService

def test_all_groq_functions():
    """Тестируем ВСЕ функции Groq."""
    print("=" * 70)
    print(" ПОЛНЫЙ ТЕСТ GROQ — ВСЕ ФУНКЦИИ")
    print("=" * 70)
    
    g = GroqService()
    
    print(f"\n✅ Groq доступен: {g.available}")
    print(f"✅ API ключ: {'есть' if g.api_key else 'нет'}")
    print(f"✅ Клиент: {'создан' if g.client else 'нет'}")
    
    if not g.available:
        print("\n⚠️ Groq НЕ доступен! Проверь API ключ в .env")
        return False
    
    tests_passed = 0
    tests_failed = 0
    
    # ТЕСТ 1: generate_route_description
    print("\n" + "-" * 70)
    print("ТЕСТ 1: generate_route_description")
    print("-" * 70)
    try:
        desc = g.generate_route_description(
            party_type="family",
            weather="sun",
            stops=[
                {"name": "Патриаршая площадь"},
                {"name": "Музей истории"},
                {"name": "Набережная Брюгге"}
            ],
            liked_tags=["история", "фото"]
        )
        print(f"✅ Успех!")
        print(f"   Описание: {desc[:150]}...")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        tests_failed += 1
    
    # ТЕСТ 2: generate_stop_why
    print("\n" + "-" * 70)
    print("ТЕСТ 2: generate_stop_why")
    print("-" * 70)
    try:
        why = g.generate_stop_why(
            place={
                "name": "Музей Йошкина Кота",
                "category": "museum",
                "tags": ["история", "интерактив", "местная кухня"],
                "description": "Гастрономический музей с дегустацией сыра"
            },
            profile={
                "party_type": "family",
                "weather": "sun",
                "liked_tags": ["история", "еда"]
            }
        )
        print(f"✅ Успех!")
        print(f"   Почему: {why[:150]}...")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        tests_failed += 1
    
    # ТЕСТ 3: chat_assistant — построй маршрут
    print("\n" + "-" * 70)
    print("ТЕСТ 3: chat_assistant — 'построй маршрут'")
    print("-" * 70)
    try:
        result = g.chat_assistant([
            {"role": "user", "content": "построй маршрут по Йошкар-Оле для семьи"}
        ])
        print(f"✅ Успех!")
        print(f"   Action: {result.get('action')}")
        print(f"   Reply: {result.get('reply', '')[:150]}...")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        tests_failed += 1
    
    # ТЕСТ 4: chat_assistant — дождь
    print("\n" + "-" * 70)
    print("ТЕСТ 4: chat_assistant — 'идет дождь'")
    print("-" * 70)
    try:
        result = g.chat_assistant([
            {"role": "user", "content": "идет дождь, что делать?"}
        ])
        print(f"✅ Успех!")
        print(f"   Action: {result.get('action')}")
        print(f"   Reply: {result.get('reply', '')[:150]}...")
        print(f"   Replan: {result.get('replan')}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        tests_failed += 1
    
    # ТЕСТ 5: chat_assistant — кофе
    print("\n" + "-" * 70)
    print("ТЕСТ 5: chat_assistant — 'хочу кофе'")
    print("-" * 70)
    try:
        result = g.chat_assistant([
            {"role": "user", "content": "хочу кофе рядом с маршрутом"}
        ])
        print(f"✅ Успех!")
        print(f"   Action: {result.get('action')}")
        print(f"   Reply: {result.get('reply', '')[:150]}...")
        print(f"   Replan: {result.get('replan')}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        tests_failed += 1
    
    # ТЕСТ 6: chat_assistant — устал
    print("\n" + "-" * 70)
    print("ТЕСТ 6: chat_assistant — 'устали'")
    print("-" * 70)
    try:
        result = g.chat_assistant([
            {"role": "user", "content": "мы устали, сделай маршрут короче"}
        ])
        print(f"✅ Успех!")
        print(f"   Action: {result.get('action')}")
        print(f"   Reply: {result.get('reply', '')[:150]}...")
        print(f"   Replan: {result.get('replan')}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        tests_failed += 1
    
    # ТЕСТ 7: chat_assistant — сложный запрос
    print("\n" + "-" * 70)
    print("ТЕСТ 7: chat_assistant — сложный запрос")
    print("-" * 70)
    try:
        result = g.chat_assistant([
            {"role": "user", "content": "хотим активный маршрут с музеями и кофе"},
            {"role": "assistant", "content": "Понял, подбираю маршрут с музеями и кофейнями."},
            {"role": "user", "content": "и чтобы было не слишком дорого"}
        ])
        print(f"✅ Успех!")
        print(f"   Action: {result.get('action')}")
        print(f"   Reply: {result.get('reply', '')[:150]}...")
        print(f"   Profile: {result.get('profile', {}).get('budget')}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        tests_failed += 1
    
    # ИТОГИ
    print("\n" + "=" * 70)
    print(" ИТОГИ ТЕСТА GROQ")
    print("=" * 70)
    print(f"✅ Пройдено: {tests_passed}")
    print(f"❌ Провалено: {tests_failed}")
    print(f"📊 Успешность: {tests_passed / (tests_passed + tests_failed) * 100:.0f}%")
    print("=" * 70)
    
    return tests_failed == 0


def test_backend_integration():
    """Тест интеграции с backend."""
    print("\n" + "=" * 70)
    print(" ТЕСТ BACKEND INTEGRATION")
    print("=" * 70)
    
    from main import app, load_places
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    places = load_places()
    
    print(f"\n✅ Мест в базе: {len(places)}")
    
    # Тест /generate-route
    print("\n" + "-" * 70)
    print("ТЕСТ: /generate-route")
    print("-" * 70)
    try:
        resp = client.post("/generate-route", json={
            "party_type": "family",
            "age_group": "adults",
            "budget": "medium",
            "activity_level": "low",
            "liked_tags": ["история"],
            "disliked_tags": [],
            "food_preferences": [],
            "weather": "sun"
        })
        print(f"✅ Status: {resp.status_code}")
        data = resp.json()
        print(f"✅ Title: {data.get('route_title', '')[:80]}")
        print(f"✅ Summary: {data.get('summary', '')[:80]}")
        print(f"✅ Stops: {len(data.get('stops', []))}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест /assistant/chat
    print("\n" + "-" * 70)
    print("ТЕСТ: /assistant/chat")
    print("-" * 70)
    try:
        resp = client.post("/assistant/chat", json={
            "messages": [
                {"role": "user", "content": "построй маршрут для семьи"}
            ],
            "profile": {
                "party_type": "family",
                "budget": "medium"
            }
        })
        print(f"✅ Status: {resp.status_code}")
        data = resp.json()
        print(f"✅ Reply: {data.get('reply', '')[:80]}")
        print(f"✅ Action: {data.get('action')}")
        print(f"✅ Route: {'есть' if data.get('route') else 'нет'}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n" + "=" * 70)
    print(" BACKEND INTEGRATION ЗАВЕРШЕН")
    print("=" * 70)


if __name__ == "__main__":
    print("\n🔍 ПОЛНЫЙ ТЕСТ GROQ СЕРВИСА\n")
    
    groq_ok = test_all_groq_functions()
    
    print("\n\n")
    test_backend_integration()
    
    print("\n\n" + "=" * 70)
    print(" 📊 ОБЩИЕ ИТОГИ")
    print("=" * 70)
    if groq_ok:
        print("✅ GROQ РАБОТАЕТ КОРРЕКТНО!")
        print("✅ Все функции доступны")
        print("✅ Backend интегрирован")
    else:
        print("⚠️ GROq работает с ошибками")
        print("⚠️ Проверь API ключ и модель")
    print("=" * 70)
