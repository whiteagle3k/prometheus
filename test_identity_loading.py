#!/usr/bin/env python3
"""
Тест загрузки identity файлов агентов.
"""

import json
from pathlib import Path


def test_identity_file(entity_name: str):
    """Тестирует загрузку identity файла агента."""
    print(f"\n{'='*50}")
    print(f"ТЕСТ ЗАГРУЗКИ: {entity_name}")
    print(f"{'='*50}")
    
    identity_path = Path(f"entities/{entity_name}/identity/identity.json")
    
    if not identity_path.exists():
        print(f"❌ Файл не найден: {identity_path}")
        return False
    
    try:
        with open(identity_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"✅ JSON файл загружен успешно")
        
        # Проверяем структуру personality
        personality = config.get('personality', {})
        print(f"📋 personality структура:")
        for key, value in personality.items():
            if isinstance(value, list):
                print(f"   {key}: list[{len(value)}] = {value[:2]}...")
            else:
                print(f"   {key}: {type(value).__name__} = {str(value)[:50]}...")
        
        # Проверяем наличие ключевых полей
        required_in_personality = ['summary', 'personality']
        for field in required_in_personality:
            if field in personality:
                print(f"   ✅ {field}: присутствует")
            else:
                print(f"   ❌ {field}: ОТСУТСТВУЕТ!")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return False


def main():
    """Главная функция тестирования."""
    print("🔍 ТЕСТ ЗАГРУЗКИ IDENTITY ФАЙЛОВ")
    print("=" * 60)
    
    entities = ["aletheia", "vasya", "marina"]
    
    for entity in entities:
        success = test_identity_file(entity)
        if not success:
            print(f"⚠️ Проблемы с {entity}")
    
    print(f"\n{'='*60}")
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print(f"{'='*60}")


if __name__ == "__main__":
    main() 