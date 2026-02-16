# Исправления ошибки 429 и проблем с клавиатурой для бота @duddlebreinbot

## Внесенные изменения

### 1. Создан новый файл `src/d_brain/utils.py`
- Добавлен класс `RateLimitException` для обработки ошибок ограничения частоты запросов
- Добавлена функция `handle_rate_limit()` для автоматической повторной попытки при ошибке 429 с экспоненциальной задержкой

### 2. Обновлен файл `src/d_brain/bot/keyboards.py`
- Добавлен параметр `one_time_keyboard=False` для предотвращения исчезновения клавиатуры после первого использования
- Теперь клавиатура остается видимой после каждого сообщения

### 3. Обновлен файл `src/d_brain/bot/handlers/voice.py`
- Добавлена обработка ошибки 429 при транскрибации голосовых сообщений
- Добавлена обработка ошибки 429 при отправке ответов
- При превышении лимита API бот отправляет пользователю сообщение "⚠️ Слишком много запросов. Попробуйте немного позже."

### 4. Обновлен файл `src/d_brain/bot/handlers/commands.py`
- Добавлена обработка ошибки 429 в команде `/start`
- Добавлен `import asyncio` для поддержки асинхронных задержек

### 5. Обновлен файл `src/d_brain/bot/handlers/process.py`
- Добавлена обработка ошибки 429 при отправке начального сообщения
- Добавлена обработка ошибки 429 при обработке через Claude Processor
- Добавлена обработка ошибки 429 при обновлении сообщения с результатом

### 6. Обновлен файл `src/d_brain/services/transcription.py`
- Добавлен класс `RateLimitException`
- Добавлена обработка ошибки 429 при транскрибации через Deepgram API

## Как развернуть исправления на сервере

### Вариант 1: Через git pull (если сервер использует git)

1. Подключитесь к серверу по SSH:
   ```bash
   ssh user@your-server-ip
   ```

2. Перейдите в директорию проекта:
   ```bash
   cd /path/to/agent-second-brain
   ```

3. Сделайте pull изменений:
   ```bash
   git pull origin main
   ```

4. Установите зависимости:
   ```bash
   uv sync
   ```

5. Перезапустите бота:
   ```bash
   sudo systemctl restart d-brain-bot
   ```

6. Проверьте статус:
   ```bash
   sudo systemctl status d-brain-bot
   ```

### Вариант 2: Через загрузку файлов вручную

1. Скопируйте измененные файлы на сервер:
   ```bash
   # С локального компьютера
   scp src/d_brain/utils.py user@your-server-ip:/path/to/agent-second-brain/src/d_brain/
   scp src/d_brain/bot/keyboards.py user@your-server-ip:/path/to/agent-second-brain/src/d_brain/bot/
   scp src/d_brain/bot/handlers/voice.py user@your-server-ip:/path/to/agent-second-brain/src/d_brain/bot/handlers/
   scp src/d_brain/bot/handlers/commands.py user@your-server-ip:/path/to/agent-second-brain/src/d_brain/bot/handlers/
   scp src/d_brain/bot/handlers/process.py user@your-server-ip:/path/to/agent-second-brain/src/d_brain/bot/handlers/
   scp src/d_brain/services/transcription.py user@your-server-ip:/path/to/agent-second-brain/src/d_brain/services/
   ```

2. Подключитесь к серверу по SSH:
   ```bash
   ssh user@your-server-ip
   ```

3. Перейдите в директорию проекта:
   ```bash
   cd /path/to/agent-second-brain
   ```

4. Перезапустите бота:
   ```bash
   sudo systemctl restart d-brain-bot
   ```

5. Проверьте логи:
   ```bash
   sudo journalctl -u d-brain-bot -f
   ```

### Вариант 3: Через Docker (если используется Docker)

1. Соберите новый образ:
   ```bash
   docker build -t d-brain-bot:latest .
   ```

2. Остановите старый контейнер:
   ```bash
   docker stop d-brain-bot
   ```

3. Запустите новый контейнер:
   ```bash
   docker run -d --name d-brain-bot --env-file .env d-brain-bot:latest
   ```

4. Проверьте логи:
   ```bash
   docker logs -f d-brain-bot
   ```

## Проверка работы

После развертывания проверьте:

1. **Клавиатура отображается:**
   - Отправьте команду `/start` в Telegram
   - Убедитесь, что кнопки отображаются под сообщением
   - Отправьте несколько сообщений и проверьте, что кнопки не исчезают

2. **Обработка ошибки 429:**
   - Проверьте логи бота на наличие предупреждений о rate limit
   - При частых запросах бот должен отправлять сообщение "⚠️ Слишком много запросов"

3. **Транскрибация голосовых:**
   - Отправьте голосовое сообщение
   - Проверьте, что оно транскрибируется корректно
   - При ошибке API должно появляться сообщение о временной недоступности

## Дополнительные рекомендации

1. **Мониторинг логов:**
   ```bash
   # В реальном времени
   sudo journalctl -u d-brain-bot -f
   
   # Только ошибки
   sudo journalctl -u d-brain-bot -p err -f
   ```

2. **Проверка использования API:**
   - Deepgram: https://console.deepgram.com/usage
   - Todoist: https://todoist.com/help/articles/developer-limits
   - Telegram: https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this

3. **Настройка логирования:**
   Если нужно увеличить уровень детализации логов, измените в файле конфигурации или в коде уровень логирования на `DEBUG`.

## Контакты

Если возникнут проблемы при развертывании, проверьте:
- Файл `.env` на сервере (должен содержать все необходимые токены)
- Права доступа к файлам
- Логи ошибок (`sudo journalctl -u d-brain-bot -p err`)
