"""
Groq API сервис для генерации умных описаний маршрутов и диалогового AI-ассистента.

Использует быстрые LLM модели Groq для персонализации текстов.
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

# Импортируем улучшенный промпт
try:
    from ai_prompt import SYSTEM_PROMPT
except ImportError:
    SYSTEM_PROMPT = None

# Пытаемся импортировать groq, но не ломаем если нет
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None  # type: ignore


class GroqService:
    """Сервис для работы с Groq API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализирует Groq клиент.

        Args:
            api_key: API ключ Groq. Если не указан, ищется в GROQ_API_KEY.
        """
        # Пробуем получить ключ из разных источников
        self.api_key = (
            api_key or
            os.getenv("GROQ_API_KEY") or
            self._load_env_key()
        )
        self.client = None
        self.available = False

        if GROQ_AVAILABLE and self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                self.available = True
            except Exception:
                self.available = False

    def _load_env_key(self) -> Optional[str]:
        """Загружает ключ из .env файла."""
        try:
            env_file = Path(__file__).parent / ".env"
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('GROQ_API_KEY='):
                            return line.split('=', 1)[1].strip()
        except Exception:
            pass
        return None
    
    def generate_route_description(
        self,
        party_type: str,
        weather: str,
        stops: List[Dict[str, Any]],
        liked_tags: List[str]
    ) -> str:
        """
        Генерирует персонализированное описание маршрута.
        
        Args:
            party_type: Тип компании (family, couple, solo, friends).
            weather: Погода (sun, rain, cloud).
            stops: Список мест маршрута.
            liked_tags: Предпочитаемые теги пользователя.
        
        Returns:
            Красивое описание маршрута.
        """
        if not self.available:
            return self._fallback_description(party_type, weather, stops, liked_tags)
        
        try:
            stop_names = ", ".join(s["name"] for s in stops[:3])
            
            prompt = f"""Создай короткое привлекательное описание маршрута по Йошкар-Оле (2-3 предложения).

Параметры:
- Компания: {self._translate_party_type(party_type)}
- Погода: {self._translate_weather(weather)}
- Места: {stop_names}
- Интересы: {", ".join(liked_tags) if liked_tags else "разное"}

Описание должно быть живым, не шаблонным, на русском языке."""

            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Новая модель вместо decommissioned llama-3.1-70b
                messages=[
                    {
                        "role": "system",
                        "content": "Ты помощник для туристов. Пиши кратко, живо, по-русски. Без шаблонов."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=150,
                top_p=1,
                stream=False,
                stop=None,
            )
            
            description = response.choices[0].message.content.strip()
            return description if description else self._fallback_description(
                party_type, weather, stops, liked_tags
            )
            
        except Exception:
            # При любой ошибке возвращаем fallback
            return self._fallback_description(party_type, weather, stops, liked_tags)
    
    def generate_stop_why(
        self,
        place: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> str:
        """
        Генерирует персонализированное объяснение почему это место в маршруте.
        
        Args:
            place: Данные места.
            profile: Профиль пользователя.
        
        Returns:
            Объяснение почему это место подходит.
        """
        if not self.available:
            return self._fallback_why(place, profile)
        
        try:
            prompt = f"""Объясни почему это место подходит туристу (1 предложение).

Место: {place.get('name', 'Неизвестно')}
Категория: {place.get('category', 'other')}
Теги: {', '.join(place.get('tags', []))}
Описание: {place.get('description', '')}

Параметры туриста:
- Компания: {profile.get('party_type', 'solo')}
- Интересы: {', '.join(profile.get('liked_tags', []))}
- Погода: {profile.get('weather', 'sun')}

Ответ на русском, без шаблонов."""

            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты помощник для туристов. Пиши кратко, по-русски."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=100,
                top_p=1,
                stream=False,
                stop=None,
            )
            
            why = response.choices[0].message.content.strip()
            return why if why else self._fallback_why(place, profile)
            
        except Exception:
            return self._fallback_why(place, profile)

    def _sanitize_input(self, text: str) -> str:
        """Защита от инъекций — очистка входного текста."""
        if not text:
            return ""
        # Удаляем потенциально опасные символы
        text = text.replace('"""', '').replace("'''", '')
        # Ограничиваем длину
        return text[:2000]

    def chat_assistant(
        self,
        messages: List[Dict[str, str]],
        profile: Optional[Dict[str, Any]] = None,
        route: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Диалоговый ассистент поверх Groq.
        
        Собирает информацию о пользователе и автоматически создаёт маршрут.
        
        На основе истории сообщений решает:
        - как обновить профиль пользователя;
        - нужно ли сгенерировать новый маршрут или перестроить текущий.
        
        Возвращает словарь:
        {
          "reply": str,
          "action": "generate_route" | "replan_route" | "ask_questions" | "none",
          "profile": {...} | None,
          "replan": {"action": str} | None
        }
        """
        base_profile: Dict[str, Any] = {
            "party_type": "couple",
            "age_group": "adults",
            "budget": "medium",
            "activity_level": "medium",
            "weather": "sun",
            "liked_tags": [],
            "disliked_tags": [],
            "food_preferences": [],
        }
        if profile:
            base_profile.update(profile)
        
        # Защита от инъекций — санизируем все сообщения
        sanitized_messages = [
            {"role": m.get("role", "user"), "content": self._sanitize_input(m.get("content", ""))}
            for m in messages
        ]

        if not self.available:
            # Fallback без Groq: простая эвристика по ключевым словам
            last_user = ""
            for m in reversed(sanitized_messages):
                if m.get("role") == "user":
                    last_user = m.get("content", "").lower()
                    break
            
            reply = "Я зафиксировал ваши пожелания. Нажмите «Собрать маршрут», чтобы я подобрал варианты."
            action = "none"
            replan = None
            
            # Простая эвристика для определения действия
            if any(word in last_user for word in ["дождь", "дождли", "мок", "wet", "rain"]):
                reply = "Понял, перестраиваю маршрут под дождь — будет больше крытых мест."
                action = "replan_route"
                replan = {"action": "rain_mode"}
            elif any(word in last_user for word in ["устал", "устали", "тяжел", "сложн", "короче", "легче", "tired", "легк"]):
                reply = "Вижу, вы устали. Делаю маршрут короче и проще."
                action = "replan_route"
                replan = {"action": "tired_mode"}
            elif any(word in last_user for word in ["кофе", "кофеин", "выпить", "перекус", "еда", "coffee", "чай", "tea"]):
                reply = "Нашёл отличную кофейню рядом с маршрутом!"
                action = "replan_route"
                replan = {"action": "coffee_nearby"}
            elif any(word in last_user for word in ["маршрут", "построй", "создай", "подбери", "предложи", "route", "build", "create"]):
                reply = "Сейчас подберу для вас оптимальный маршрут по Йошкар-Оле!"
                action = "generate_route"
            
            return {
                "reply": reply,
                "action": action,
                "profile": base_profile,
                "replan": replan,
            }

        try:
            # Используем улучшенный промпт если доступен
            system_content = SYSTEM_PROMPT if SYSTEM_PROMPT else (
                "Ты AI-ассистент для создания маршрутов по Йошкар-Оле. Твоя задача:\n\n"
                "1) ВЕЖЛИВО собрать информацию (2-3 вопроса максимум):\n"
                "   - С кем турист? (solo/пара/семья/друзья)\n"
                "   - Сколько времени есть? (30 мин / 1-2 часа / полдня)\n"
                "   - Что интересно? (музеи/еда/прогулки/фото)\n"
                "   - Бюджет? (эконом/средний/без ограничений)\n\n"
                "2) Когда достаточно информации — СОЗДАТЬ маршрут (action=generate_route)\n\n"
                "3) Вернуть СТРОГО JSON в поле tool_call:\n"
                "{\n"
                '  "action": "generate_route" | "replan_route" | "ask_questions" | "none",\n'
                '  "profile": { "party_type": "...", "budget": "...", "activity_level": "...", "liked_tags": [...], "food_preferences": [...] },\n'
                '  "replan": {"action": "rain_mode" | "tired_mode" | "coffee_nearby"} | null,\n'
                '  "questions_asked": 0-5\n'
                "}\n\n"
                "ПРАВИЛА:\n"
                "- Если пользователь сказал про еду → food_preferences = ['местная кухня']\n"
                "- Если пара → party_type = 'couple'\n"
                "- Если 20-30 минут → activity_level = 'low', budget = 'low'\n"
                "- Если музеи → liked_tags = ['музеи', 'история']\n"
                "- Если прогулки → liked_tags = ['прогулки', 'фото']\n"
                "- questions_asked показывает сколько уже спросил (0-2 = можно спросить ещё, 3+ = генерируй маршрут)\n"
                "- В ответе упомяни что места можно заменить (напиши 'места можно заменить' или 'можно заменить')\n"
            )
            
            system_message = {
                "role": "system",
                "content": system_content,
            }

            decision_response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[system_message, *sanitized_messages, {
                    "role": "user",
                    "content": (
                        f"Актуальный профиль: {base_profile}\n"
                        f"Текущий маршрут: {route or 'нет'}\n"
                        f"История диалога: {len(sanitized_messages)} сообщений\n"
                        "Верни JSON tool_call с action и profile."
                    ),
                }],
                temperature=0.4,  # Более сбалансированная креативность
                max_tokens=1000,
                top_p=1,
                stream=False,
                stop=None,
            )

            tool_raw = decision_response.choices[0].message.content or "{}"
            try:
                tool_call = json.loads(tool_raw)
            except Exception as e:
                # Если не удалось распарсить JSON, используем эвристику
                tool_call = {
                    "action": "none",
                    "profile": base_profile,
                    "replan": None,
                }

            action = tool_call.get("action", "none")
            new_profile = tool_call.get("profile") or base_profile
            replan = tool_call.get("replan")

            reply_response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты дружелюбный ассистент по маршрутам по Йошкар-Оле. Отвечай кратко, по-русски, 1–3 предложения. Если предлагаешь маршрут, упомяни что места можно заменить."
                    },
                    *sanitized_messages,
                    {
                        "role": "assistant",
                        "content": f"(Внутренняя заметка: action={action}, profile={new_profile}, replan={replan})",
                    },
                ],
                temperature=0.7,
                max_tokens=1000,  # Увеличено до 1000
                top_p=1,
                stream=False,
                stop=None,
            )

            reply_text = reply_response.choices[0].message.content.strip()

            return {
                "reply": reply_text,
                "action": action,
                "profile": new_profile,
                "replan": replan,
            }
        except Exception:
            return {
                "reply": "Я зафиксировал ваши пожелания. Попробуйте обновить маршрут или нажмите «Собрать маршрут».",
                "action": "none",
                "profile": base_profile,
                "replan": None,
            }
    
    def _translate_party_type(self, party_type: str) -> str:
        """Переводит тип компании на русский."""
        translations = {
            "family": "семья с детьми",
            "couple": "романтическая пара",
            "solo": "одиночный путешественник",
            "friends": "компания друзей",
            "seniors": "люди старшего возраста",
        }
        return translations.get(party_type, party_type)
    
    def _translate_weather(self, weather: str) -> str:
        """Переводит погоду на русский."""
        translations = {
            "sun": "солнечно",
            "rain": "дождь",
            "cloud": "пасмурно",
        }
        return translations.get(weather, weather)
    
    def _fallback_description(
        self,
        party_type: str,
        weather: str,
        stops: List[Dict[str, Any]],
        liked_tags: List[str]
    ) -> str:
        """Fallback описание без Groq."""
        party_map = {
            "family": "Семейный",
            "couple": "Романтический",
            "solo": "Индивидуальный",
            "friends": "Для компании",
            "seniors": "Спокойный",
        }
        
        weather_map = {
            "sun": "под хорошую погоду",
            "rain": "адаптирован под дождь",
            "cloud": "под пасмурную погоду",
        }
        
        party_label = party_map.get(party_type, "Маршрут")
        weather_label = weather_map.get(weather, "")
        
        if liked_tags:
            return f"{party_label} маршрут {weather_label} с акцентом на {', '.join(liked_tags[:2])}."
        return f"{party_label} маршрут {weather_label}."
    
    def _fallback_why(
        self,
        place: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> str:
        """Fallback объяснение без Groq."""
        reasons = []
        
        # Проверяем совпадение тегов
        liked_tags = profile.get("liked_tags", [])
        place_tags = place.get("tags", [])
        common = set(liked_tags) & set(place_tags)
        if common:
            reasons.append(f"интересы: {', '.join(list(common)[:2])}")
        
        # Проверяем погоду
        if profile.get("weather") == "rain" and place.get("indoor"):
            reasons.append("подходит для дождя")
        
        # Проверяем food preferences
        food_prefs = profile.get("food_preferences", [])
        food_tags = place.get("food_tags", [])
        common_food = set(food_prefs) & set(food_tags)
        if common_food:
            reasons.append(f"еда: {', '.join(list(common_food)[:1])}")
        
        # Проверяем аудиторию
        party_type = profile.get("party_type", "")
        audiences = place.get("audiences", [])
        if party_type and party_type in audiences:
            party_map = {
                "solo": "для solo-формата",
                "couple": "для пары",
                "family": "для семейного формата",
                "seniors": "для спокойного формата",
            }
            reasons.append(party_map.get(party_type, "подходит по формату"))
        
        if not reasons:
            return "Подходит под выбранные параметры маршрута."
        
        return "Подходит, потому что " + ", ".join(reasons[:3]) + "."


# Глобальный экземпляр сервиса
_groq_service: Optional[GroqService] = None


def get_groq_service(api_key: Optional[str] = None) -> GroqService:
    """Получает или создаёт GroqService."""
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqService(api_key)
    return _groq_service


def init_groq(api_key: Optional[str] = None) -> bool:
    """
    Инициализирует Groq сервис.
    
    Returns:
        True если Groq доступен, False иначе.
    """
    service = get_groq_service(api_key)
    return service.available


__all__ = [
    "GroqService",
    "get_groq_service",
    "init_groq",
]
