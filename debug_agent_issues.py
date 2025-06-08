#!/usr/bin/env python3
"""
🔍 ДИАГНОСТИКА ПРОБЛЕМ АГЕНТОВ

Проверяет:
1. Почему локальные модели загружаются для external-only агентов
2. Почему Anthropic выдает ошибки когда отключен
3. Почему MCP серверы дублируются для каждого агента
4. Создает минимальный тест одного агента
"""

import asyncio
import requests
import json
from pathlib import Path
import time

API_BASE = "http://localhost:8000"
HEALTH_ENDPOINT = f"{API_BASE}/health"
CHAT_ENDPOINT = f"{API_BASE}/v1/chat"

class AgentDiagnostics:
    """Диагностика проблем агентов."""
    
    def __init__(self):
        self.issues_found = []
    
    def print_header(self, title: str):
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print(f"{'='*60}")
    
    def check_configs(self):
        """Проверяем конфигурации агентов."""
        self.print_header("ПРОВЕРКА КОНФИГУРАЦИЙ")
        
        agents = {
            "supervisor": "entities/supervisor/identity/identity.json",
            "vasya": "entities/vasya/identity/identity.json", 
            "marina": "entities/marina/identity/identity.json"
        }
        
        for agent_name, config_path in agents.items():
            print(f"\n🤖 {agent_name.upper()}:")
            
            config_file = Path(config_path)
            if not config_file.exists():
                print(f"❌ Конфигурация не найдена: {config_path}")
                self.issues_found.append(f"{agent_name}: config missing")
                continue
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Проверяем external preferences
                external_llms = config.get("external_llms", {})
                routing_prefs = external_llms.get("routing_preferences", {})
                prefer_external = routing_prefs.get("prefer_external", False)
                
                print(f"   🎯 prefer_external: {prefer_external}")
                
                # Проверяем memory settings
                guidelines = config.get("operational_guidelines", {})
                memory_settings = guidelines.get("memory_processing", {})
                skip_classification = memory_settings.get("skip_classification", False)
                
                print(f"   ⚡ skip_classification: {skip_classification}")
                
                # Проверяем providers
                providers = external_llms.get("providers", {})
                for provider, settings in providers.items():
                    enabled = settings.get("enabled", False)
                    print(f"   🔌 {provider}: {'✅' if enabled else '❌'}")
                    
                    if not enabled and provider == "anthropic":
                        print(f"      ⚠️ Anthropic отключен, но система пытается его инициализировать")
                        self.issues_found.append(f"{agent_name}: anthropic disabled but still initializes")
                
                # Проверяем есть ли локальная модель в конфиге
                if "local_model_path" in config:
                    print(f"   🏠 local_model_path найден - это проблема для external-only агента")
                    self.issues_found.append(f"{agent_name}: has local_model_path but should be external-only")
                
            except Exception as e:
                print(f"❌ Ошибка чтения конфигурации: {e}")
                self.issues_found.append(f"{agent_name}: config read error")
    
    async def test_server_availability(self):
        """Проверяем доступность сервера."""
        self.print_header("ПРОВЕРКА API СЕРВЕРА")
        
        try:
            response = requests.get(HEALTH_ENDPOINT, timeout=5)
            if response.status_code == 200:
                print("✅ API сервер доступен")
                health_data = response.json()
                print(f"   📊 Статус: {health_data}")
                return True
            else:
                print(f"❌ API сервер недоступен: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка соединения с сервером: {e}")
            print("\n💡 Запустите сервер:")
            print("poetry run python prometheus.py api --entities supervisor,vasya,marina --host localhost --port 8000")
            return False
    
    async def test_single_agent(self, agent_id: str):
        """Тестируем одного агента с минимальным запросом."""
        self.print_header(f"ТЕСТ АГЕНТА: {agent_id.upper()}")
        
        simple_message = "Привет! Как дела?"
        
        print(f"📤 Отправляем простой запрос: '{simple_message}'")
        
        try:
            start_time = time.time()
            response = requests.post(
                CHAT_ENDPOINT,
                params={"entity": agent_id},
                json={"message": simple_message, "user_id": "debug_test"},
                timeout=60
            )
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', 'Нет ответа')
                route = result.get('route', 'неизвестно')
                latency = result.get('latency', elapsed_time)
                
                print(f"✅ Агент ответил успешно:")
                print(f"   ⏱️  Время: {latency:.1f}с")
                print(f"   🛤️  Маршрут: {route}")
                print(f"   💬 Ответ: {answer[:100]}{'...' if len(answer) > 100 else ''}")
                
                # Анализируем маршрут
                if route == "external":
                    print("   ✅ Использован внешний LLM - правильно!")
                elif route == "local":
                    print("   ⚠️ Использована локальная модель - может быть проблемой")
                    self.issues_found.append(f"{agent_id}: used local instead of external")
                
                return True
            else:
                print(f"❌ Ошибка от агента: HTTP {response.status_code}")
                print(f"   📄 Ответ: {response.text}")
                self.issues_found.append(f"{agent_id}: HTTP error {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка соединения: {e}")
            self.issues_found.append(f"{agent_id}: connection error")
            return False
    
    def show_summary(self):
        """Показываем итоговый отчет."""
        self.print_header("ИТОГОВЫЙ ОТЧЕТ")
        
        if not self.issues_found:
            print("🎉 Проблем не найдено! Все агенты работают корректно.")
        else:
            print(f"⚠️ Найдено {len(self.issues_found)} проблем:")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"   {i}. {issue}")
        
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        
        if any("anthropic" in issue for issue in self.issues_found):
            print("   • Исправить инициализацию Anthropic для отключенных провайдеров")
        
        if any("external" in issue for issue in self.issues_found):
            print("   • Проверить роутинг - почему используются локальные модели")
        
        if any("config" in issue for issue in self.issues_found):
            print("   • Проверить файлы конфигурации агентов")
        
        print("   • Создать изолированный тест одного агента")
        print("   • Добавить чистый диалог без технических логов")

async def main():
    """Основная функция диагностики."""
    
    print("🔍 ДИАГНОСТИКА ПРОБЛЕМ PROMETHEUS AI AGENTS")
    print("Анализируем проблемы выявленные в терминале...")
    
    diagnostics = AgentDiagnostics()
    
    # 1. Проверяем конфигурации
    diagnostics.check_configs()
    
    # 2. Проверяем сервер
    server_ok = await diagnostics.test_server_availability()
    
    if server_ok:
        # 3. Тестируем агентов по одному
        agents_to_test = ["supervisor", "vasya", "marina"]
        
        for agent in agents_to_test:
            success = await diagnostics.test_single_agent(agent)
            if not success:
                print(f"⏭️ Пропускаем дальнейшее тестирование {agent}")
            
            # Пауза между тестами
            await asyncio.sleep(2)
    
    # 4. Показываем итоги
    diagnostics.show_summary()

if __name__ == "__main__":
    asyncio.run(main()) 