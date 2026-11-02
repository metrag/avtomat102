#!/usr/bin/env python3
"""Скрипт сборки тренажёра в .exe через PyInstaller."""

import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

def check_venv():
    if not VENV_PYTHON.exists():
        print("❌ .venv не найден. Создайте виртуальное окружение.")
        sys.exit(1)

def check_pyinstaller():
    try:
        subprocess.run([str(VENV_PYTHON), "-m", "PyInstaller", "--version"], 
                      check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("📦 Устанавливаю PyInstaller...")
        subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "pyinstaller"], 
                      check=True)

def check_assets():
    icon_png = ROOT / "assets/images/icon.png"
    icon_ico = ROOT / "assets/images/icon.ico"
    
    if not icon_png.exists():
        print("⚠️  icon.png не найден в assets/images/")
    
    # Конвертировать PNG → ICO если нужно
    if icon_png.exists() and not icon_ico.exists():
        print("🔄 Конвертирую icon.png → icon.ico...")
        try:
            from PIL import Image
            img = Image.open(icon_png)
            img.save(icon_ico, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
            print("✅ icon.ico создан")
        except Exception as e:
            print(f"⚠️  Не удалось конвертировать: {e}")

def clean():
    print("🧹 Очищаю build/ и dist/...")
    for d in ['build', 'dist']:
        path = ROOT / d
        if path.exists():
            shutil.rmtree(path)

def build():
    print("🔨 Собираю trainer.exe...")
    result = subprocess.run([str(VENV_PYTHON), "-m", "PyInstaller", "trainer.spec"], 
                           cwd=ROOT)
    if result.returncode == 0:
        print("✅ Сборка завершена: dist/trainer.exe")
    else:
        print("❌ Ошибка сборки")
        sys.exit(result.returncode)

def main():
    print("=" * 60)
    print("Сборка тренажёра для отработки стрельбы по БПЛА")
    print("=" * 60)
    
    check_venv()
    check_pyinstaller()
    check_assets()
    clean()
    build()

if __name__ == "__main__":
    main()
