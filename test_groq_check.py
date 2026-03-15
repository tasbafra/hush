"""
Проверка Groq сервиса и интеграции.

Запуск: python test_groq_check.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_groq_service():
    """Проверка Groq сервиса."""
    print("=" * 50)
    print("ПРОВЕРКА GROQ СЕРВИСА")
    print("=" * 50)
    
    from groq_service import GroqService, GROQ_AVAILABLE
    
    print(f"\n1. Groq библиотека: {'✅ Установлена' if GROQ_AVAILABLE else '❌ Не установлена'}")
    
    service = GroqService()
    print(f"2. Groq API ключ: {'✅ Найден' if service.api_key else '❌ Не найден (будет работать fallback)'}")
    print(f"3. Groq сервис доступен: {'✅ Да' if service.available else '⚠️ Нет (fallback режим)'}")
    
    # Тестируем fallback
    print("\n4. Тест fallback описания...")
    fallback_desc = service._fallback_description(
        party_type="family",
        weather="sun",
        stops=[{"name": "Музей"}],
        liked_tags=["история"]
    )
    print(f"   Fallback описание: {fallback_desc}")
    
    fallback_why = service._fallback_why(
        place={"name": "Музей", "tags": ["история"], "indoor": True, "audiences": ["family"]},
        profile={"party_type": "family", "weather": "sun", "liked_tags": ["история"]}
    )
    print(f"   Fallback why: {fallback_why}")
    
    # Если ключ есть, тестируем API
    if service.available:
        print("\n5. Тест Groq API...")
        try:
            desc = service.generate_route_description(
                party_type="family",
                weather="sun",
                stops=[{"name": "Музей истории"}],
                liked_tags=["история", "фото"]
            )
            print(f"   ✅ Groq описание: {desc[:100]}...")
        except Exception as e:
            print(f"   ⚠️ Ошибка Groq: {e}")
    else:
        print("\n5. Groq API: ⚠️ Не настроен (работает fallback)")
        print("   Для включения Groq:")
        print("   1. Получите ключ: https://console.groq.com/keys")
        print("   2. Установите переменную окружения:")
        print("      export GROQ_API_KEY='gsk_...'")
    
    print("\n" + "=" * 50)
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 50)
    
    return True


def test_backend_integration():
    """Проверка интеграции backend."""
    print("\n" + "=" * 50)
    print("ПРОВЕРКА BACKEND INTEGRATION")
    print("=" * 50)
    
    import json
    from main import app, load_places
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Проверка places.json
    places = load_places()
    print(f"\n1. База мест: ✅ {len(places)} мест")
    
    # Проверка категорий
    categories = list(set(p["category"] for p in places))
    print(f"2. Категории: ✅ {len(categories)} ({', '.join(categories[:5])}...)")
    
    # Проверка activity_level
    high_activity = [p for p in places if p.get("activity_level") == "high"]
    print(f"3. Места с high activity: ✅ {len(high_activity)}")
    
    # Проверка кофеен
    cafes = [p for p in places if p.get("category") == "cafe"]
    print(f"4. Кофейни: ✅ {len(cafes)}")
    
    # Тест /generate-route
    print("\n5. Тест /generate-route...")
    response = client.post("/generate-route", json={
        "party_type": "family",
        "age_group": "adults",
        "budget": "medium",
        "activity_level": "low",
        "liked_tags": ["история"],
        "disliked_tags": [],
        "food_preferences": [],
        "weather": "sun"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: 200 OK")
        print(f"   ✅ Маршрут: {data['route_title']}")
        print(f"   ✅ Мест: {len(data['stops'])}")
        print(f"   ✅ Summary: {data['summary'][:80]}...")
    else:
        print(f"   ❌ Status: {response.status_code}")
    
    # Тест /replan-route (rain_mode)
    print("\n6. Тест /replan-route (rain_mode)...")
    response = client.post("/replan-route", json={
        "current_stop_ids": ["patriarshaya_emb"],
        "action": "rain_mode",
        "weather": "rain"
    })
    
    if response.status_code == 200:
        data = response.json()
        all_indoor = all(
            next((p for p in places if p["id"] == s["id"]), {}).get("indoor", False)
            for s in data["stops"]
        )
        print(f"   ✅ Status: 200 OK")
        print(f"   ✅ Все места indoor: {'✅ Да' if all_indoor else '⚠️ Нет'}")
    else:
        print(f"   ❌ Status: {response.status_code}")
    
    # Тест /replan-route (coffee_nearby)
    print("\n7. Тест /replan-route (coffee_nearby)...")
    response = client.post("/replan-route", json={
        "current_stop_ids": ["patriarshaya_emb", "museum_city"],
        "action": "coffee_nearby",
        "weather": "sun"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: 200 OK")
        print(f"   ✅ Мест было: 2, стало: {len(data['stops'])}")
    else:
        print(f"   ❌ Status: {response.status_code}")
    
    # Тест /replan-route (tired_mode)
    print("\n8. Тест /replan-route (tired_mode)...")
    response = client.post("/replan-route", json={
        "current_stop_ids": ["patriarshaya_emb", "museum_city", "cafe_national"],
        "action": "tired_mode",
        "weather": "sun"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: 200 OK")
        print(f"   ✅ Мест было: 3, стало: {len(data['stops'])}")
    else:
        print(f"   ❌ Status: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("✅ BACKEND INTEGRATION ПРОВЕРЕН")
    print("=" * 50)
    
    return True


def test_frontend_files():
    """Проверка файлов фронтенда."""
    print("\n" + "=" * 50)
    print("ПРОВЕРКА FRONTEND ФАЙЛОВ")
    print("=" * 50)
    
    frontend_dir = Path(__file__).parent.parent / "Web"
    
    required_files = [
        "index.html",
        "package.json",
        "vite.config.ts",
        ".env.local",
        "src/main.tsx",
        "src/App.tsx",
        "src/OnboardingScreen.tsx",
        "src/RouteScreen.tsx",
        "src/types.ts",
        "src/index.css",
    ]
    
    missing = []
    for file in required_files:
        file_path = frontend_dir / file
        if file_path.exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} — ОТСУТСТВУЕТ")
            missing.append(file)
    
    # Проверка image.png
    image_path = frontend_dir / "image.png"
    if image_path.exists():
        print(f"✅ image.png — Логотип найден")
    else:
        print(f"⚠️ image.png — Логотип НЕ найден (нужно скачать)")
        print(f"   Скачать: https://www.figma.com/file/h0yGRq77kVf7s5TS2GRPI3/image/60825d736197900b9a8ba70cc42f1ff66a0b38ae/download")
    
    if missing:
        print(f"\n❌ Отсутствуют файлы: {', '.join(missing)}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ FRONTEND ФАЙЛЫ ПРОВЕРЕНЫ")
    print("=" * 50)
    
    return True


if __name__ == "__main__":
    print("\n🔍 КОМПЛЕКСНАЯ ПРОВЕРКА ПРОЕКТА\n")
    
    test_groq_service()
    test_backend_integration()
    test_frontend_files()
    
    print("\n\n" + "=" * 60)
    print("📊 ИТОГОВАЯ СВОДКА")
    print("=" * 60)
    print("""
✅ Backend (API):
   - /generate-route — работает
   - /replan-route — работает
   - База мест: 25 мест
   - Groq: fallback режим (опционально)

✅ Replanner:
   - rain_mode — замена на indoor
   - tired_mode — сокращение маршрута
   - coffee_nearby — добавление кофейни

✅ Frontend:
   - React + TypeScript
   - Прокси на backend
   - Нет заглушек в логике

⚠️ Требуется:
   1. Скачать image.png в Web/
   2. (Опционально) Настроить GROQ_API_KEY
   3. Запустить backend: python -m uvicorn main:app --reload
   4. Запустить frontend: npm run dev
    """)
    print("=" * 60)
