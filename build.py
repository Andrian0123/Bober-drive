#!/usr/bin/env python3
"""
Nexus Driver v3.0.0 - Build Script
Упаковка проекта для дистрибуции
"""

import os
import sys
import shutil
import zipfile
import json
from pathlib import Path
from datetime import datetime

VERSION = "3.0.0"
BUILD_DATE = datetime.now().strftime("%Y-%m-%d")
PROJECT_NAME = "nexus-driver"


class NexusBuilder:
    """Сборщик дистрибутива Nexus"""
    
    def __init__(self, root_dir: Path = None):
        self.root = root_dir or Path(__file__).parent
        self.build_dir = self.root / "build"
        self.dist_dir = self.root / "dist"
        self.package_name = f"{PROJECT_NAME}-v{VERSION}"
        
    def clean(self):
        """Очистка предыдущих сборок"""
        print("\n" + "="*60)
        print("  ОЧИСТКА ПРЕДЫДУЩИХ СБОРОК")
        print("="*60)
        
        for directory in [self.build_dir, self.dist_dir]:
            if directory.exists():
                print(f"Удаление: {directory}")
                shutil.rmtree(directory)
        
        # Удаление __pycache__ и .pyc файлов
        for pycache in self.root.rglob("__pycache__"):
            if pycache.is_dir():
                shutil.rmtree(pycache)
        
        for pyc in self.root.rglob("*.pyc"):
            pyc.unlink()
        
        print("✓ Очистка завершена")
    
    def create_directories(self):
        """Создание структуры директорий для сборки"""
        print("\n" + "="*60)
        print("  СОЗДАНИЕ СТРУКТУРЫ")
        print("="*60)
        
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
        
        self.package_dir = self.build_dir / self.package_name
        self.package_dir.mkdir(exist_ok=True)
        
        print(f"✓ Создана директория: {self.package_dir}")
    
    def copy_source_files(self):
        """Копирование исходных файлов"""
        print("\n" + "="*60)
        print("  КОПИРОВАНИЕ ИСХОДНИКОВ")
        print("="*60)
        
        # Директория driver (основной код)
        driver_src = self.root / "driver"
        driver_dst = self.package_dir / "driver"
        
        if driver_src.exists():
            shutil.copytree(driver_src, driver_dst, 
                          ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
            print(f"✓ Скопировано: driver/ ({self._count_files(driver_dst)} файлов)")
            # V3 core components and tests are included
        
        # Директория docs
        docs_src = self.root / "docs"
        docs_dst = self.package_dir / "docs"
        
        if docs_src.exists():
            shutil.copytree(docs_src, docs_dst)
            print(f"✓ Скопировано: docs/ ({self._count_files(docs_dst)} файлов)")
    
    def copy_config_files(self):
        """Копирование конфигурационных файлов"""
        print("\n" + "="*60)
        print("  КОПИРОВАНИЕ КОНФИГУРАЦИИ")
        print("="*60)
        
        config_files = [
            "requirements.txt",
            "README.md",
            "CHANGELOG.md",
            "INSTALL.md",
            "START-HERE.txt",
            "TESTING.txt",
            "TASK-COMPLETE.md",
            "NEXUS-FILES-LIST.txt",
            ".env.example",
        ]
        
        for filename in config_files:
            src = self.root / filename
            if src.exists():
                dst = self.package_dir / filename
                shutil.copy2(src, dst)
                print(f"✓ {filename}")
    
    def copy_scripts(self):
        """Копирование скриптов запуска и тестирования"""
        print("\n" + "="*60)
        print("  КОПИРОВАНИЕ СКРИПТОВ")
        print("="*60)
        
        scripts = [
            # Тестовые скрипты
            "test_nexus_full.py",
            "check_dependencies.py",
            "test_nexus.bat",
            "test_nexus.sh",
            
            # Скрипты установки
            "setup.bat",
            "setup.sh",
        ]
        
        for script in scripts:
            src = self.root / script
            if src.exists():
                dst = self.package_dir / script
                shutil.copy2(src, dst)
                # Установка прав на выполнение для .sh файлов
                if script.endswith('.sh'):
                    os.chmod(dst, 0o755)
                print(f"✓ {script}")
    
    def create_version_file(self):
        """Создание файла с информацией о версии"""
        print("\n" + "="*60)
        print("  СОЗДАНИЕ VERSION.json")
        print("="*60)
        
        version_info = {
            "name": "Nexus Driver - Unified Event-Driven Knowledge Management System",
            "version": VERSION,
            "build_date": BUILD_DATE,
            "architecture": "V3 Unified Event-Driven",
            "target_audience": "Large and Very Large Projects",
            "components": {
                "core_v3": [
                    "VaultCore V3",
                    "FTS5 Indexer V3",
                    "Rules Engine V3",
                    "Graphify Engine V3",
                    "Neural Reflex Engine V3",
                    "File System Mapper V3",
                    "Trash Manager V3"
                ],
                "infrastructure": [
                    "Event Bus",
                    "Nexus Orchestrator",
                    "DI Container",
                    "Pipeline Manager",
                    "Auto-Updater"
                ],
                "legacy_v2": [
                    "Project Rules Engine",
                    "Obsidian Bridge",
                    "Audio Generator",
                    "Context Extractor"
                ]
            },
            "features": {
                "event_driven": "Central EventBus with 25+ event types",
                "orchestrator": "Single entry point with DI Container",
                "pipelines": "Composable multi-stage workflows",
                "auto_update": "Automatic updates every 15 days",
                "observability": "Events, metrics, history tracking",
                "backward_compatible": "V2 modules work via adapters"
            },
            "dependencies": {
                "required": [
                    "Python >= 3.8",
                    "cryptography>=41.0.0",
                    "numpy>=1.24.0"
                ],
                "optional": [
                    "PyPDF2>=3.0.0",
                    "python-docx>=0.8.11",
                    "beautifulsoup4>=4.12.0",
                    "gTTS>=2.3.0",
                    "pyttsx3>=2.90",
                    "requests>=2.31.0"
                ]
            },
            "license": "MIT",
            "repository": "https://github.com/Andrian0123/Bober-drive"
        }
        
        version_file = self.package_dir / "VERSION.json"
        with open(version_file, "w", encoding="utf-8") as f:
            json.dump(version_info, f, indent=2, ensure_ascii=False)
        
        print(f"✓ VERSION.json создан")
    
    def create_install_script(self):
        """Создание скрипта быстрой установки"""
        print("\n" + "="*60)
        print("  СОЗДАНИЕ INSTALL")
        print("="*60)
        
        # Windows installer
        install_bat = self.package_dir / "INSTALL.bat"
        install_bat_content = """@echo off
echo.
echo ================================================================
echo   NEXUS v{version} - QUICK INSTALL
echo ================================================================
echo.

echo [1/3] Installing dependencies...
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/3] Running tests...
py -3 test_nexus_full.py
if errorlevel 1 (
    echo WARNING: Some tests failed, but installation continues
)

echo.
echo [3/3] Setting up environment...
if not exist ".nexus" mkdir .nexus
if not exist ".nexus\\skills" mkdir .nexus\\skills

echo.
echo ================================================================
echo   INSTALLATION COMPLETE!
echo ================================================================
echo.
echo Next steps:
echo   1. Create your first project:
echo      py -3 driver/nexus_cli.py init my-project ./workspace
echo.
echo   2. Start the dashboard:
echo      py -3 driver/unified_dashboard.py
echo.
echo   3. Read the documentation:
echo      docs/NEXUS-TESTING.md
echo.
pause
""".format(version=VERSION)
        
        with open(install_bat, "w", encoding="utf-8") as f:
            f.write(install_bat_content)
        
        # Linux/macOS installer
        install_sh = self.package_dir / "INSTALL.sh"
        install_sh_content = """#!/bin/bash

echo ""
echo "================================================================"
echo "  NEXUS v{version} - QUICK INSTALL"
echo "================================================================"
echo ""

echo "[1/3] Installing dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "[2/3] Running tests..."
python3 test_nexus_full.py
if [ $? -ne 0 ]; then
    echo "WARNING: Some tests failed, but installation continues"
fi

echo ""
echo "[3/3] Setting up environment..."
mkdir -p .nexus/skills

echo ""
echo "================================================================"
echo "  INSTALLATION COMPLETE!"
echo "================================================================"
echo ""
echo "Next steps:"
echo "  1. Create your first project:"
echo "     python3 driver/nexus_cli.py init my-project ./workspace"
echo ""
echo "  2. Start the dashboard:"
echo "     python3 driver/unified_dashboard.py"
echo ""
echo "  3. Read the documentation:"
echo "     docs/NEXUS-TESTING.md"
echo ""
""".format(version=VERSION)
        
        with open(install_sh, "w", encoding="utf-8") as f:
            f.write(install_sh_content)
        
        os.chmod(install_sh, 0o755)
        
        print("✓ INSTALL.bat создан")
        print("✓ INSTALL.sh создан")
    
    def create_archive(self):
        """Создание ZIP-архива"""
        print("\n" + "="*60)
        print("  СОЗДАНИЕ АРХИВА")
        print("="*60)
        
        archive_name = f"{self.package_name}.zip"
        archive_path = self.dist_dir / archive_name
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in self.package_dir.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(self.build_dir)
                    zipf.write(file, arcname)
        
        size_mb = archive_path.stat().st_size / (1024 * 1024)
        print(f"✓ Архив создан: {archive_name} ({size_mb:.2f} MB)")
        
        return archive_path
    
    def create_checksum(self, archive_path: Path):
        """Создание контрольной суммы"""
        print("\n" + "="*60)
        print("  СОЗДАНИЕ КОНТРОЛЬНОЙ СУММЫ")
        print("="*60)
        
        import hashlib
        
        sha256 = hashlib.sha256()
        with open(archive_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        
        checksum = sha256.hexdigest()
        checksum_file = archive_path.with_suffix('.zip.sha256')
        
        with open(checksum_file, 'w') as f:
            f.write(f"{checksum}  {archive_path.name}\n")
        
        print(f"✓ SHA256: {checksum}")
        print(f"✓ Файл: {checksum_file.name}")
        
        return checksum
    
    def generate_build_report(self, archive_path: Path, checksum: str):
        """Генерация отчёта о сборке"""
        print("\n" + "="*60)
        print("  ОТЧЁТ О СБОРКЕ")
        print("="*60)
        
        report_path = self.dist_dir / f"BUILD-REPORT-{VERSION}.txt"
        
        stats = self._collect_stats()
        
        report_content = f"""
════════════════════════════════════════════════════════════════
  NEXUS v{VERSION} - BUILD REPORT
════════════════════════════════════════════════════════════════

Build Date:     {BUILD_DATE}
Build Time:     {datetime.now().strftime("%H:%M:%S")}
Archive:        {archive_path.name}
Archive Size:   {archive_path.stat().st_size / (1024 * 1024):.2f} MB
SHA256:         {checksum}

────────────────────────────────────────────────────────────────
PACKAGE CONTENTS
────────────────────────────────────────────────────────────────

Core Modules:           {stats['core_modules']} files
Documentation:          {stats['docs']} files
Scripts:                {stats['scripts']} files
Configuration:          {stats['config']} files

Total Files:            {stats['total_files']} files
Total Size:             {stats['total_size_mb']:.2f} MB

────────────────────────────────────────────────────────────────
COMPONENTS
────────────────────────────────────────────────────────────────

Base Architecture (v2.0):
  ✓ ProjectRegistry
  ✓ Orchestrator
  ✓ EnhancedMemory
  ✓ EnhancedToolRuntime
  ✓ AgentConnector
  ✓ NexusIntegration
  ✓ NexusCLI

Extended Architecture (v2.1):
  ✓ BrowserAutomation
  ✓ CommandProxy
  ✓ TokenCompressor
  ✓ SkillEngine
  ✓ MCPToolRegistry
  ✓ StructuredMemory
  ✓ VectorMemory
  ✓ UnifiedDashboard

Testing Infrastructure:
  ✓ test_nexus_full.py (7 test blocks)
  ✓ check_dependencies.py
  ✓ Automated test scripts (BAT/SH)

────────────────────────────────────────────────────────────────
INSTALLATION
────────────────────────────────────────────────────────────────

1. Extract the archive:
   unzip {archive_path.name}

2. Run quick install:
   Windows:     INSTALL.bat
   Linux/macOS: ./INSTALL.sh

3. Or manual install:
   pip install -r requirements.txt
   python test_nexus_full.py

────────────────────────────────────────────────────────────────
VERIFICATION
────────────────────────────────────────────────────────────────

Verify archive integrity:
  sha256sum -c {archive_path.name}.sha256

Expected checksum:
  {checksum}

────────────────────────────────────────────────────────────────
LICENSE
────────────────────────────────────────────────────────────────

MIT License - Use freely

════════════════════════════════════════════════════════════════
  Build Complete - Ready for Distribution
════════════════════════════════════════════════════════════════
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✓ Отчёт сохранён: {report_path.name}")
        
        # Вывод отчёта в консоль
        print(report_content)
    
    def _count_files(self, directory: Path) -> int:
        """Подсчёт количества файлов в директории"""
        return sum(1 for _ in directory.rglob("*") if _.is_file())
    
    def _collect_stats(self) -> dict:
        """Сбор статистики о пакете"""
        stats = {
            'core_modules': 0,
            'docs': 0,
            'scripts': 0,
            'config': 0,
            'total_files': 0,
            'total_size_mb': 0.0
        }
        
        if (self.package_dir / "driver").exists():
            stats['core_modules'] = self._count_files(self.package_dir / "driver")
        
        if (self.package_dir / "docs").exists():
            stats['docs'] = self._count_files(self.package_dir / "docs")
        
        scripts_count = 0
        for pattern in ["*.py", "*.bat", "*.sh"]:
            scripts_count += len(list(self.package_dir.glob(pattern)))
        stats['scripts'] = scripts_count
        
        config_files = ["requirements.txt", "README.md", ".env.example", "VERSION.json"]
        stats['config'] = sum(1 for f in config_files if (self.package_dir / f).exists())
        
        total_size = 0
        total_files = 0
        for file in self.package_dir.rglob("*"):
            if file.is_file():
                total_files += 1
                total_size += file.stat().st_size
        
        stats['total_files'] = total_files
        stats['total_size_mb'] = total_size / (1024 * 1024)
        
        return stats
    
    def build(self):
        """Главная функция сборки"""
        print("\n" + "="*60)
        print(f"  NEXUS v{VERSION} - BUILD SYSTEM")
        print("="*60)
        print(f"Build Date: {BUILD_DATE}")
        print(f"Package: {self.package_name}")
        print("="*60)
        
        try:
            # Этапы сборки
            self.clean()
            self.create_directories()
            self.copy_source_files()
            self.copy_config_files()
            self.copy_scripts()
            self.create_version_file()
            self.create_install_script()
            
            # Создание дистрибутива
            archive_path = self.create_archive()
            checksum = self.create_checksum(archive_path)
            self.generate_build_report(archive_path, checksum)
            
            print("\n" + "="*60)
            print("  ✅ СБОРКА ЗАВЕРШЕНА УСПЕШНО!")
            print("="*60)
            print(f"\nДистрибутив: {archive_path}")
            print(f"Размер: {archive_path.stat().st_size / (1024 * 1024):.2f} MB")
            print(f"SHA256: {checksum[:16]}...")
            print("\n" + "="*60)
            
            return 0
            
        except Exception as e:
            print("\n" + "="*60)
            print("  ❌ ОШИБКА СБОРКИ")
            print("="*60)
            print(f"Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    """Главная функция"""
    builder = NexusBuilder()
    return builder.build()


if __name__ == "__main__":
    sys.exit(main())
