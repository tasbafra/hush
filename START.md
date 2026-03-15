# 🚀 ИНСТРУКЦИЯ ПО ЗАПУСКУ

## ✅ ВСЁ ГОТОВО

- ✅ Логотип: `Web/60825d736197900b9a8ba70cc42f1ff66a0b38ae.png`
- ✅ Groq API ключ: настроен
- ✅ Backend: 40 мест
- ✅ Frontend: чат + онбординг

---

## 1. ЗАПУСК BACKEND

### Вариант А: Через PowerShell (рекомендуется)
```powershell
cd C:\Users\Administrator\visiter\backend
$env:GROQ_API_KEY="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"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Вариант Б: Через .env файл
```powershell
cd C:\Users\Administrator\visiter\backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
(ключ уже в файле `backend/.env`)

### Проверка backend:
Открой: http://localhost:8000/health  
Должно быть: `{"status":"ok"}`

---

## 2. ЗАПУСК FRONTEND

### В новом окне PowerShell:
```powershell
cd C:\Users\Administrator\visiter\Web
npm run dev
```

### Проверка frontend:
Открой: http://localhost:3000

---

## 3. ТЕСТИРОВАНИЕ

### Тест чата с Groq:
1. Открой http://localhost:3000
2. В чате напиши: **"построй маршрут"**
3. Должен ответить умный ответ от Groq AI
4. Маршрут сгенерируется автоматически

### Тест команд чата:
- "хочу кофе рядом" → добавит кофейню
- "идет дождь" → перестроит под дождь
- "мы устали" → сократит маршрут
- "покажи музеи" → сгенерирует маршрут с музеями

### Тест кнопок:
- 🌧️ Дождь → rain_mode
- 😩 Устали → tired_mode
- ☕ Хочу кофе → coffee_nearby

---

## 4. API ЭНДПОИНТЫ

### Health check:
```bash
curl http://localhost:8000/health
```

### Generate route:
```bash
curl -X POST http://localhost:8000/generate-route ^
  -H "Content-Type: application/json" ^
  -d "{\"party_type\":\"family\",\"budget\":\"medium\",\"activity_level\":\"low\",\"weather\":\"sun\",\"liked_tags\":[\"история\"],\"disliked_tags\":[],\"food_preferences\":[]}"
```

### Replan route:
```bash
curl -X POST http://localhost:8000/replan-route ^
  -H "Content-Type: application/json" ^
  -d "{\"current_stop_ids\":[\"patriarshaya_emb\"],\"action\":\"rain_mode\",\"weather\":\"rain\"}"
```

### Assistant chat:
```bash
curl -X POST http://localhost:8000/assistant/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"построй маршрут\"}]}"
```

---

## 📊 ПРОВЕРКА GROQ

### Python тест:
```python
import os
os.environ['GROQ_API_KEY'] = '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'

from groq_service import GroqService
g = GroqService()

print('Groq доступен:', g.available)  # True

# Тест
result = g.chat_assistant([{'role': 'user', 'content': 'построй маршрут'}])
print('Action:', result['action'])  # generate_route
print('Reply:', result['reply'])  # Умный ответ от AI
```

---

## 🔧 ЕСЛИ GROQ НЕ РАБОТАЕТ

### 1. Проверь ключ:
```powershell
echo $env:GROQ_API_KEY
```

### 2. Перезапусти backend с ключом:
```powershell
$env:GROQ_API_KEY="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"
python -m uvicorn main:app --reload
```

### 3. Проверь в коде:
```python
from groq_service import GroqService
g = GroqService()
print(g.available)  # Должно быть True
```

---

## 📁 СТРУКТУРА

```
visiter/
├── backend/
│   ├── .env                    ← Groq API ключ
│   ├── main.py                 ← FastAPI сервер
│   ├── groq_service.py         ← Groq AI сервис
│   ├── replanner.py            ← Перестройка маршрута
│   ├── places.json             ← 40 мест
│   └── ...
└── Web/
    ├── .env.local              ← Groq API ключ (для фронта)
    ├── 60825d736197900b9a8ba70cc42f1ff66a0b38ae.png  ← Логотип
    ├── src/
    │   ├── App.tsx             ← Главный компонент
    │   ├── AssistantChat.tsx   ← Чат ассистент
    │   ├── OnboardingScreen.tsx
    │   └── RouteScreen.tsx
    └── ...
```

---

## ✅ ЧЕКЛИСТ

- [ ] Backend запущен на http://localhost:8000
- [ ] Frontend запущен на http://localhost:3000
- [ ] `/health` возвращает `{"status":"ok"}`
- [ ] Чат отвечает на "построй маршрут"
- [ ] Кнопки 🌧️😩☕ работают
- [ ] Логотип отображается

---

*Инструкция: 15 марта 2026*
