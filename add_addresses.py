import json
from pathlib import Path

places_file = Path(r'C:\Users\Administrator\visiter\backend\places.json')
with open(places_file, 'r', encoding='utf-8') as f:
    places = json.load(f)

# Добавляем адреса ко всем местам
for place in places:
    place['address'] = 'г. Йошкар-Ола'

# Обновляем адреса для ключевых мест
addresses = {
    'patriarshaya_emb': 'наб. Брюгге',
    'museum_city': 'ул. Советская, 1',
    'cafe_national': 'ул. Советская, 5',
    'art_gallery': 'ул. Советская, 16',
    'coffee_house': 'наб. реки Малой Кокшаги, 1',
}

for place in places:
    if place['id'] in addresses:
        place['address'] = f'г. Йошкар-Ола, {addresses[place["id"]]}'

with open(places_file, 'w', encoding='utf-8') as f:
    json.dump(places, f, ensure_ascii=False, indent=2)

print(f'✅ Добавлены адреса к {len(places)} местам')
