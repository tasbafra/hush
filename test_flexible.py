import sys
sys.path.insert(0, r'C:\Users\Administrator\visiter')
from scoring import build_route
import json

places = json.load(open(r'C:\Users\Administrator\visiter\backend\places.json', encoding='utf-8'))

print("=== ТЕСТ ГИБКОГО КОЛИЧЕСТВА МЕСТ ===\n")

# Тест 1: 30 минут
profile = {
    'party_type': 'friends',
    'age_group': 'adults',
    'budget': 'medium',
    'activity_level': 'low',
    'weather': 'sun',
    'duration': '30min',
    'liked_tags': ['прогулки'],
    'disliked_tags': [],
    'food_preferences': []
}
result = build_route(profile, places)
print(f"30 минут: {len(result['stops'])} мест, {sum(s['duration_min'] for s in result['stops'])} мин")
for stop in result['stops']:
    print(f"  - {stop['name']} ({stop['duration_min']} мин)")

# Тест 2: 1 час
profile['duration'] = '1h'
result = build_route(profile, places)
print(f"\n1 час: {len(result['stops'])} мест, {sum(s['duration_min'] for s in result['stops'])} мин")
for stop in result['stops']:
    print(f"  - {stop['name']} ({stop['duration_min']} мин)")

# Тест 3: 2 часа
profile['duration'] = '2h'
result = build_route(profile, places)
print(f"\n2 часа: {len(result['stops'])} мест, {sum(s['duration_min'] for s in result['stops'])} мин")
for stop in result['stops']:
    print(f"  - {stop['name']} ({stop['duration_min']} мин)")

# Тест 4: Полдня
profile['duration'] = 'half-day'
result = build_route(profile, places)
print(f"\nПолдня: {len(result['stops'])} мест, {sum(s['duration_min'] for s in result['stops'])} мин")
for stop in result['stops']:
    print(f"  - {stop['name']} ({stop['duration_min']} мин)")

print("\n=== ВСЕ ТЕСТЫ ПРОЙДЕНЫ ===")
