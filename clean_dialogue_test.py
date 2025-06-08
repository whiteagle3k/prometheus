#!/usr/bin/env python3
"""
💬 ЧИСТЫЙ ДИАЛОГ МЕЖДУ АГЕНТАМИ

Показывает только человекочитаемый диалог без технических логов.
Создает красивый отчет о взаимодействии агентов.
"""

import asyncio
import requests
import time
from datetime import datetime
import json

API_BASE = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE}/v1/chat"

class CleanDialogue:
    """Чистый диалог без технического мусора."""
    
    def __init__(self):
        self.conversation_log = []
        self.start_time = time.time()
    
    def add_message(self, speaker: str, message: str, response: str, timing: dict):
        """Добавляем сообщение в лог диалога."""
        self.conversation_log.append({
            "timestamp": datetime.now(),
            "speaker": speaker,
            "message": message,
            "response": response,
            "timing": timing
        })
    
    async def send_clean_message(self, agent_id: str, message: str) -> dict:
        """Отправляем сообщение агенту и получаем чистый ответ."""
        
        agent_names = {
            "supervisor": "Петрович (Supervisor)",
            "vasya": "Вася (Developer)",
            "marina": "Марина (QA)",
            "aletheia": "Алетейя (AI Assistant)"
        }
        
        speaker_name = agent_names.get(agent_id, agent_id)
        
        try:
            start_time = time.time()
            response = requests.post(
                CHAT_ENDPOINT,
                params={"entity": agent_id}, 
                json={"message": message, "user_id": "clean_dialogue"},
                timeout=60
            )
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', 'Нет ответа')
                route = result.get('route', 'unknown')
                latency = result.get('latency', elapsed_time)
                
                timing_info = {
                    "total_time": elapsed_time,
                    "llm_time": latency,
                    "route": route
                }
                
                self.add_message(speaker_name, message, answer, timing_info)
                
                return {
                    "success": True,
                    "speaker": speaker_name,
                    "response": answer,
                    "timing": timing_info
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def print_dialogue_header(self):
        """Печатаем заголовок диалога."""
        print("=" * 80)
        print("💬 ЧИСТЫЙ ДИАЛОГ PROMETHEUS AI TEAM")
        print("=" * 80)
        print(f"🕐 Начало сессии: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def print_message(self, entry: dict):
        """Печатаем сообщение в диалоге."""
        timestamp = entry["timestamp"].strftime("%H:%M:%S")
        speaker = entry["speaker"]
        message = entry["message"]
        response = entry["response"]
        timing = entry["timing"]
        
        print(f"[{timestamp}] 👤 ПОЛЬЗОВАТЕЛЬ → {speaker}:")
        print(f"   📝 Запрос: {message}")
        print()
        
        print(f"[{timestamp}] 🤖 {speaker} ОТВЕЧАЕТ:")
        print(f"   ⏱️  Время обработки: {timing['llm_time']:.1f}с")
        print(f"   🛤️  Маршрут: {timing['route']}")
        print(f"   💬 Ответ:")
        
        # Форматируем ответ для лучшей читаемости
        lines = response.split('\n')
        for line in lines:
            if line.strip():
                print(f"      {line}")
        
        print("-" * 60)
        print()
    
    def generate_dialogue_report(self):
        """Генерируем итоговый отчет диалога."""
        total_time = time.time() - self.start_time
        
        print("=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ДИАЛОГА")
        print("=" * 80)
        
        if not self.conversation_log:
            print("❌ Диалог не состоялся")
            return
        
        print(f"💬 Всего сообщений: {len(self.conversation_log)}")
        print(f"⏱️  Общее время сессии: {total_time:.1f} секунд")
        
        # Статистика по агентам
        agent_stats = {}
        total_llm_time = 0
        
        for entry in self.conversation_log:
            speaker = entry["speaker"]
            timing = entry["timing"]
            llm_time = timing["llm_time"]
            route = timing["route"]
            
            if speaker not in agent_stats:
                agent_stats[speaker] = {
                    "messages": 0,
                    "total_llm_time": 0,
                    "routes": {}
                }
            
            agent_stats[speaker]["messages"] += 1
            agent_stats[speaker]["total_llm_time"] += llm_time
            total_llm_time += llm_time
            
            if route not in agent_stats[speaker]["routes"]:
                agent_stats[speaker]["routes"][route] = 0
            agent_stats[speaker]["routes"][route] += 1
        
        print(f"🧠 Общее время LLM обработки: {total_llm_time:.1f} секунд")
        print()
        
        print("👥 СТАТИСТИКА ПО АГЕНТАМ:")
        for speaker, stats in agent_stats.items():
            print(f"   🤖 {speaker}:")
            print(f"      📨 Сообщений: {stats['messages']}")
            print(f"      ⏱️  Время LLM: {stats['total_llm_time']:.1f}с")
            print(f"      📊 Среднее время: {stats['total_llm_time']/stats['messages']:.1f}с")
            
            print(f"      🛤️  Маршруты:")
            for route, count in stats["routes"].items():
                print(f"         • {route}: {count} раз")
            print()
        
        # Показываем весь диалог
        print("=" * 80)
        print("📜 ПОЛНЫЙ ДИАЛОГ")
        print("=" * 80)
        
        for entry in self.conversation_log:
            self.print_message(entry)
    
    async def run_simple_test(self):
        """Запускаем простой тест диалога."""
        self.print_dialogue_header()
        
        # Тест 1: Простое приветствие с Петровичем
        print("🧪 ТЕСТ 1: Приветствие с Петровичем")
        result1 = await self.send_clean_message(
            "supervisor", 
            "Привет, Петрович! Как дела? Расскажи о своих возможностях."
        )
        
        if result1["success"]:
            print("✅ Петрович ответил!")
        else:
            print(f"❌ Ошибка: {result1['error']}")
            return
        
        await asyncio.sleep(2)
        
        # Тест 2: Простая задача для Васи
        print("🧪 ТЕСТ 2: Простая задача для Васи")
        result2 = await self.send_clean_message(
            "vasya",
            "Привет, Вася! Можешь создать простую функцию для вывода текущего времени?"
        )
        
        if result2["success"]:
            print("✅ Вася ответил!")
        else:
            print(f"❌ Ошибка: {result2['error']}")
        
        await asyncio.sleep(2)
        
        # Тест 3: Вопрос к Марине
        print("🧪 ТЕСТ 3: Вопрос к Марине о тестировании")
        result3 = await self.send_clean_message(
            "marina",
            "Привет, Марина! Как ты подходишь к тестированию функций?"
        )
        
        if result3["success"]:
            print("✅ Марина ответила!")
        else:
            print(f"❌ Ошибка: {result3['error']}")
        
        # Генерируем отчет
        self.generate_dialogue_report()

async def main():
    """Основная функция."""
    print("Убедитесь что API сервер запущен:")
    print("poetry run python prometheus.py api --entities supervisor,vasya,marina --host localhost --port 8000")
    print()
    
    input("Нажмите Enter когда сервер будет готов...")
    
    dialogue = CleanDialogue()
    await dialogue.run_simple_test()

if __name__ == "__main__":
    asyncio.run(main()) 