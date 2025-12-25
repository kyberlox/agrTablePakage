import logging
import logging.handlers
import os

# Настройка пути
LOG_DIR = "/etc/loggs/fastapi"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Создаём директорию
os.makedirs(LOG_DIR, exist_ok=True)

# Формат
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Файл-хэндлер с ротацией
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
)
file_handler.setFormatter(formatter)

# Настроим root-логгер, чтобы перехватить ВСЁ
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)

# Также оставим вывод в stdout (важно для docker logs)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# Отключим дублирование (чтобы не было дублей)
root_logger.propagate = True

print(f"✅ Логирование настроено. Логи пишутся в {LOG_FILE}")
