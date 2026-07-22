#!/usr/bin/env python3
"""
Скрипт для быстрого запуска E2E тестов автономного демона
"""

import sys
import subprocess
from pathlib import Path

def run_e2e_tests():
    """Запустить E2E тесты"""
    
    # Вариант 1: pytest (если установлен)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", 
             "test_autonomous_daemon_e2e.py", 
             "-v", "--tb=short"],
            cwd=Path(__file__).parent
        )
        return result.returncode
    except:
        pass
    
    # Вариант 2: unittest
    result = subprocess.run(
        [sys.executable, "test_autonomous_daemon_e2e.py"],
        cwd=Path(__file__).parent
    )
    return result.returncode

if __name__ == "__main__":
    print("=" * 70)
    print("Bober-Drive Autonomous Daemon E2E Test Suite")
    print("=" * 70)
    print()
    
    exit_code = run_e2e_tests()
    
    print()
    print("=" * 70)
    if exit_code == 0:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
    else:
        print(f"❌ ТЕСТЫ НЕ ПРОЙДЕНЫ (exit code: {exit_code})")
    print("=" * 70)
    
    sys.exit(exit_code)
