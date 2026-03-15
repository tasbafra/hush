# backend/main.py
import json
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Добавляем родительскую директорию в path для импорта scoring
sys.path.insert(0, str(Path(__file__).parent.parent))
from scoring import build_route as build_route_scoring
from replanner import replan_route as replan_route_logic
from groq_service import get_groq_service

# ---------- Модели данных (по контракту) ----------
class RouteRequest(BaseModel):
    party_type: str
    age_group: str
    budget: str
    activity_level: str
    liked_tags: List[str]
    disliked_tags: List[str]
    food_preferences: List[str]
    weather: str

class Stop(BaseModel):
    id: str
    name: str
    why: str
    duration_min: int
    tags: List[str]
    promo: Optional[str] = None
    address: Optional[str] = None

class RouteResponse(BaseModel):
    route_title: str
    summary: str
    stops: List[Stop]

class ReplanRequest(BaseModel):
    current_stop_ids: List[str]
    action: str          # "rain_mode", "tired_mode", "coffee_nearby"
    weather: str


class ChatMessage(BaseModel):
    role: str
    content: str


class AssistantChatRequest(BaseModel):
    messages: List[ChatMessage]
    profile: Optional[Dict[str, Any]] = None
    route: Optional[Dict[str, Any]] = None


class AssistantChatResponse(BaseModel):
    reply: str
    action: str
    profile: Optional[Dict[str, Any]] = None
    route: Optional[RouteResponse] = None

# ---------- Загрузка данных ----------
PLACES_FILE = Path(__file__).parent / "places.json"

def load_places():
    with open(PLACES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------- Инициализация приложения ----------
app = FastAPI(
    title="Route Generator API",
    description="Генерация и перестроение маршрутов по Йошкар-Оле",
    version="1.0.0"
)

# CORS для фронта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # В реальном проекте заменить на конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Вспомогательные функции ----------
# get_place_by_id импортируется из replanner при необходимости

# ---------- Эндпоинты ----------
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/generate-route", response_model=RouteResponse)
async def generate_route(request: RouteRequest):
    """
    Эндпоинт генерации начального маршрута.
    Использует продвинутую логику из scoring.py (Максим)
    """
    places = load_places()
    
    # Формируем профиль пользователя из запроса
    profile = {
        "party_type": request.party_type,
        "age_group": request.age_group,
        "budget": request.budget,
        "activity_level": request.activity_level,
        "liked_tags": request.liked_tags,
        "disliked_tags": request.disliked_tags,
        "food_preferences": request.food_preferences,
        "weather": request.weather,
    }
    
    # Вызываем функцию генерации маршрута из scoring.py
    result = build_route_scoring(profile, places)
    
    # Проверяем, есть ли маршрут
    if not result.get("stops"):
        raise HTTPException(
            status_code=400,
            detail="Не удалось собрать подходящий маршрут по текущим параметрам. Попробуйте изменить предпочтения."
        )
    
    # Преобразуем словари stops в объекты Stop для Pydantic
    stops = [
        Stop(
            id=stop["id"],
            name=stop["name"],
            why=stop["why"],
            duration_min=stop["duration_min"],
            tags=stop["tags"],
            promo=stop.get("promo")
        )
        for stop in result.get("stops", [])
    ]
    
    return RouteResponse(
        route_title=result.get("route_title", "Маршрут по Йошкар-Оле"),
        summary=result.get("summary", "Маршрут сгенерирован"),
        stops=stops
    )

@app.post("/replan-route", response_model=RouteResponse)
async def replan_route_endpoint(request: ReplanRequest):
    """
    Эндпоинт перестроения маршрута.
    Использует логику из модуля replanner.py
    """
    places = load_places()
    
    # Вызываем функцию перестроения из replanner.py
    result = replan_route_logic(
        current_stop_ids=request.current_stop_ids,
        action=request.action,
        weather=request.weather,
        all_places=places
    )
    
    # Проверяем, не произошла ли ошибка (unchanged_reason указывает на проблему)
    if result.get("unchanged_reason") and not result.get("stops"):
        raise HTTPException(
            status_code=400,
            detail=result.get("unchanged_reason")
        )
    
    # Преобразуем словари stops в объекты Stop для Pydantic
    stops = [
        Stop(
            id=stop["id"],
            name=stop["name"],
            why=stop["why"],
            duration_min=stop["duration_min"],
            tags=stop["tags"],
            promo=stop.get("promo")
        )
        for stop in result.get("stops", [])
    ]
    
    return RouteResponse(
        route_title=result.get("route_title", "Обновлённый маршрут"),
        summary=result.get("summary", "Маршрут перестроен"),
        stops=stops
    )


@app.post("/assistant/chat", response_model=AssistantChatResponse)
async def assistant_chat(request: AssistantChatRequest):
    """
    Диалоговый эндпоинт AI-ассистента.
    
    Умный ассистент который:
    - собирает информацию о пользователе
    - автоматически генерирует маршрут когда достаточно данных
    - вызывает GroqService.chat_assistant для интерпретации диалога
    - при необходимости генерирует новый маршрут или перестраивает текущий
    """
    groq = get_groq_service()
    decision = groq.chat_assistant(
        messages=[{"role": m.role, "content": m.content} for m in request.messages],
        profile=request.profile,
        route=request.route.dict() if isinstance(request.route, RouteResponse) else request.route,
    )

    action = decision.get("action", "none")
    profile = decision.get("profile") or request.profile or {}
    reply = decision.get("reply", "Я готов помочь с маршрутом по Йошкар-Оле.")
    new_route: Optional[RouteResponse] = None
    
    # Проверка на замену конкретного места
    last_message = request.messages[-1].content.lower() if request.messages else ""
    
    # Если пользователь просит заменить место (например "не хочу в церковь")
    if request.route and ("не хочу" in last_message or "замени" in last_message or "не пойду" in last_message):
        # Извлекаем название места которое нужно заменить
        place_to_replace = None
        for stop in request.route.stops:
            stop_name_lower = stop.name.lower()
            # Проверяем есть ли название места в сообщении
            for word in stop_name_lower.split():
                if len(word) > 3 and word in last_message:
                    place_to_replace = stop.id
                    break
            if place_to_replace:
                break
        
        if place_to_replace:
            # Вызываем replanner для замены
            result = replan_route_logic(
                current_stop_ids=[s.id for s in request.route.stops],
                action=f"replace_place:{place_to_replace}",
                weather=profile.get("weather", "sun"),
                all_places=load_places(),
            )
            stops = [
                Stop(
                    id=stop["id"],
                    name=stop["name"],
                    why=stop["why"],
                    duration_min=stop["duration_min"],
                    tags=stop["tags"],
                    promo=stop.get("promo"),
                    address=stop.get("address"),
                )
                for stop in result.get("stops", [])
            ]
            new_route = RouteResponse(
                route_title=result.get("route_title", "Маршрут обновлён"),
                summary=result.get("summary", "Маршрут перестроен"),
                stops=stops,
            )
            action = "replan_route"
            reply = result.get("summary", "Маршрут обновлён")
    
    # Автоматически генерируем маршрут если AI сказал что достаточно информации
    # или если пользователь явно попросил маршрут
    should_generate = (
        action == "generate_route" or
        any(word in last_message for word in ["маршрут", "построй", "создай", "подбери", "хочу маршрут", "прогуляться"])
    ) and not new_route  # Только если ещё не заменили место

    places = load_places()

    if should_generate:
        result = build_route_scoring(profile, places)
        stops = [
            Stop(
                id=stop["id"],
                name=stop["name"],
                why=stop["why"],
                duration_min=stop["duration_min"],
                tags=stop["tags"],
                promo=stop.get("promo"),
                address=stop.get("address"),
            )
            for stop in result.get("stops", [])
        ]
        new_route = RouteResponse(
            route_title=result.get("route_title", "Маршрут по Йошкар-Оле"),
            summary=result.get("summary", "Маршрут сгенерирован"),
            stops=stops,
        )
        action = "generate_route"
    elif action == "replan_route" and request.route:
        replan_info = decision.get("replan") or {}
        replan_action = replan_info.get("action") or "tired_mode"
        current_stop_ids = [s["id"] if isinstance(s, dict) else s.id for s in request.route["stops"]] if isinstance(request.route, dict) else [s.id for s in request.route.stops]  # type: ignore

        result = replan_route_logic(
            current_stop_ids=current_stop_ids,
            action=replan_action,
            weather=profile.get("weather", "sun"),
            all_places=places,
        )

        stops = [
            Stop(
                id=stop["id"],
                name=stop["name"],
                why=stop["why"],
                duration_min=stop["duration_min"],
                tags=stop["tags"],
                promo=stop.get("promo"),
                address=stop.get("address"),
            )
            for stop in result.get("stops", [])
        ]
        new_route = RouteResponse(
            route_title=result.get("route_title", "Обновлённый маршрут"),
            summary=result.get("summary", "Маршрут перестроен"),
            stops=stops,
        )

    return AssistantChatResponse(
        reply=reply,
        action=action,
        profile=profile,
        route=new_route,
    )
