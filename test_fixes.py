import sys
sys.path.insert(0, r'C:\Users\Administrator\visiter')
from scoring import build_route
import json

places = json.load(open(r'C:\Users\Administrator\visiter\backend\places.json', encoding='utf-8'))

# Тест 1: 30 минут
profile_30min = {
    'party_type': 'couple',
    'age_group': 'adults',
    'budget': 'medium',
    'activity_level': 'low',
    'weather': 'sun',
    'duration': '30min',
    'liked_tags': ['прогулки'],
    'disliked_tags': [],
    'food_preferences': []
}

result = build_route(profile_30min, places)
print('Тест 30 минут:')
print(f'  Мест: {len(result.get("stops", []))}')
print(f'  Общее время: {sum(s["duration_min"] for s in result.get("stops", []))} мин')
ids = [s['id'] for s in result.get('stops', [])]
print(f'  Уникальные ID: {len(set(ids))}')
print(f'  Дубликаты: {len(ids) != len(set(ids))}')

# Тест 2: 1 час
profile_1h = profile_30min.copy()
profile_1h['duration'] = '1h'
result2 = build_route(profile_1h, places)
print('\nТест 1 час:')
print(f'  Мест: {len(result2.get("stops", []))}')
print(f'  Общее время: {sum(s["duration_min"] for s in result2.get("stops", []))} мин')
ids2 = [s['id'] for s in result2.get('stops', [])]
print(f'  Дубликаты: {len(ids2) != len(set(ids2))}')
