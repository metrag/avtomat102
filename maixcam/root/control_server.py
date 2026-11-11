"""
Управляющий TCP сервер для MaixCAM
Позволяет загружать скрипты, управлять процессами, получать логи
Без SSH - только через TCP (USB RNDIS или WiFi)

Протокол (JSON):
- {"cmd": "upload", "filename": "main.py", "content": "..."} - загрузить файл
- {"cmd": "run", "script": "main.py"} - запустить скрипт
- {"cmd": "stop"} - остановить текущий скрипт
- {"cmd": "status"} - получить статус
- {"cmd": "logs", "lines": 50} - получить последние N строк логов
- {"cmd": "reboot"} - перезагрузить MaixCAM
"""
import socket
import json
import os
import subprocess
import threading
import time

# Конфигурация
HOST = "0.0.0.0"  # Слушать на всех интерфейсах
PORT = 5005       # Порт управляющего сервера
SCRIPTS_DIR = "/root/maixcam_app"
LOG_FILE = "/tmp/maixcam_control.log"
CURRENT_SCRIPT = None
CURRENT_PROCESS = None

def log(msg):
    """Запись в лог"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def handle_command(data):
    """Обработка команды от клиента"""
    global CURRENT_SCRIPT, CURRENT_PROCESS
    
    try:
        cmd = data.get("cmd")
        
        if cmd == "upload":
            # Загрузить файл
            filename = data.get("filename")
            content = data.get("content")
            filepath = os.path.join(SCRIPTS_DIR, filename)
            os.makedirs(SCRIPTS_DIR, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            log(f"Файл загружен: {filename}")
            return {"status": "ok", "message": f"Файл {filename} загружен"}
        
        elif cmd == "run":
            # Запустить скрипт
            script = data.get("script", "main.py")
            script_path = os.path.join(SCRIPTS_DIR, script)
            
            if not os.path.exists(script_path):
                return {"status": "error", "message": f"Скрипт {script} не найден"}
            
            # Остановить предыдущий скрипт
            if CURRENT_PROCESS:
                try:
                    CURRENT_PROCESS.terminate()
                    CURRENT_PROCESS.wait(timeout=2)
                except:
                    CURRENT_PROCESS.kill()
            
            # Запустить новый
            log_path = "/tmp/maixcam_script.log"
            log_file = open(log_path, "w", encoding="utf-8")
            CURRENT_PROCESS = subprocess.Popen(
                ["python3", script_path],
                stdout=log_file,
                stderr=subprocess.STDOUT
            )
            CURRENT_SCRIPT = script
            log(f"Скрипт запущен: {script} (PID: {CURRENT_PROCESS.pid})")
            return {"status": "ok", "message": f"Скрипт {script} запущен", "pid": CURRENT_PROCESS.pid}
        
        elif cmd == "stop":
            # Остановить текущий скрипт
            if CURRENT_PROCESS:
                try:
                    CURRENT_PROCESS.terminate()
                    CURRENT_PROCESS.wait(timeout=2)
                    log(f"Скрипт остановлен: {CURRENT_SCRIPT}")
                    CURRENT_SCRIPT = None
                    CURRENT_PROCESS = None
                    return {"status": "ok", "message": "Скрипт остановлен"}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            else:
                return {"status": "ok", "message": "Нет запущенного скрипта"}
        
        elif cmd == "status":
            # Получить статус
            status = {
                "current_script": CURRENT_SCRIPT,
                "process_running": CURRENT_PROCESS is not None and CURRENT_PROCESS.poll() is None,
                "pid": CURRENT_PROCESS.pid if CURRENT_PROCESS else None,
                "uptime": time.time()  # Можно добавить реальное время работы
            }
            return {"status": "ok", "data": status}
        
        elif cmd == "logs":
            # Получить логи
            lines = data.get("lines", 50)
            log_file = data.get("file", "/tmp/maixcam_script.log")
            
            if not os.path.exists(log_file):
                return {"status": "ok", "logs": []}
            
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:]
            
            return {"status": "ok", "logs": last_lines}
        
        elif cmd == "reboot":
            # Перезагрузить MaixCAM
            log("Перезагрузка...")
            os.system("reboot &")
            return {"status": "ok", "message": "Перезагрузка initiated"}
        
        elif cmd == "list_files":
            # Список файлов в SCRIPTS_DIR
            if not os.path.exists(SCRIPTS_DIR):
                return {"status": "ok", "files": []}
            files = os.listdir(SCRIPTS_DIR)
            return {"status": "ok", "files": files}
        
        else:
            return {"status": "error", "message": f"Неизвестная команда: {cmd}"}
    
    except Exception as e:
        log(f"Ошибка обработки команды: {e}")
        return {"status": "error", "message": str(e)}

def handle_client(conn, addr):
    """Обработка подключения клиента"""
    log(f"Подключение от {addr}")
    
    try:
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            
            # Проверить, получили ли мы полный JSON
            try:
                request = json.loads(data.decode("utf-8"))
                response = handle_command(request)
                conn.sendall(json.dumps(response).encode("utf-8"))
                break
            except json.JSONDecodeError:
                # Продолжаем получать данные
                continue
    
    except Exception as e:
        log(f"Ошибка клиента {addr}: {e}")
    
    finally:
        conn.close()

def main():
    """Главный цикл сервера"""
    log("Управляющий сервер запущен")
    log(f"Слушаю на {HOST}:{PORT}")
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        log("Сервер готов к подключениям")
        
        while True:
            conn, addr = server.accept()
            # Обрабатываем каждого клиента в отдельном потоке
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
    
    except KeyboardInterrupt:
        log("Сервер остановлен")
    
    except Exception as e:
        log(f"Критическая ошибка: {e}")
    
    finally:
        server.close()

if __name__ == "__main__":
    main()
