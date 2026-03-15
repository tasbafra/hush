# ⚡ Быстрый старт frontend (ЙО-Йошка)

## Установка зависимостей

```bash
cd C:\Users\Administrator\visiter\Web
npm install
```

## Настройка

### 1. Логотип
✅ **Автоматически** загружается из Figma по публичной ссылке.
Ничего скачивать не нужно!

### 2. Groq API ключ (опционально)
1. Получите ключ на https://console.groq.com/keys
2. Вставьте в `.env.local`:
```
GROQ_API_KEY=gsk_...
```

### 3. Backend
Убедитесь, что backend запущен на `http://localhost:8000`:
```bash
cd C:\Users\Administrator\visiter\backend
python -m uvicorn main:app --reload
```

## Запуск разработки

```bash
npm run dev
```

Откройте http://localhost:3000

## Сборка

```bash
npm run build
```

## API Endpoints

Фронтенд проксирует запросы на backend:
- `POST /generate-route` — генерация маршрута
- `POST /replan-route` — перестройка маршрута
- `GET /health` — проверка сервера

## Проверка работы

1. Откройте http://localhost:3000
2. Заполните профиль (кто едет, бюджет, активность)
3. Отметьте интересы (что нравится)
4. Нажмите "Собрать маршрут"
5. Проверьте 3 кнопки адаптации:
   - 🌧️ Дождь
   - 😩 Устали
   - ☕ Хочу кофе

## Структура

```
Web/
├── index.html          # Точка входа
├── image.png           # Логотип (скачать!)
├── package.json
├── vite.config.ts      # Настроен прокси на backend
├── .env.local          # Groq API ключ
└── src/
    ├── main.tsx        # Entry point React
    ├── App.tsx         # Главный компонент
    ├── OnboardingScreen.tsx  # Экран профиля
    ├── RouteScreen.tsx       # Экран маршрута
    ├── types.ts        # TypeScript типы
    └── index.css       # Стили
```

## Требования

- Node.js 18+
- Backend на FastAPI (порт 8000)
