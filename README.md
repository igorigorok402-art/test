# Telegram бот-парсер участников чата/канала

Рабочий Telegram **userbot** на Python, который выгружает участников чата/канала в `CSV` и/или `JSON`.

> Почему userbot, а не обычный bot token?
> Telegram Bot API не предоставляет универсальный доступ к полному списку участников канала/чата. Поэтому для реального парсинга используется пользовательский аккаунт через `API_ID` + `API_HASH`.

## Возможности

- Команда `/parse <chat_or_channel> [csv|json|both]`
- Выгрузка полей:
  - `user_id`
  - `username`
  - `first_name`
  - `last_name`
  - `phone`
  - `bot`
  - `premium`
  - `scam`
  - `fake`
  - `deleted`
  - `status`
- Сохранение результатов в папку `exports/`

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка

1. Получите `API_ID` и `API_HASH` на https://my.telegram.org
2. Скопируйте `.env.example` в `.env` и заполните значения.

```bash
cp .env.example .env
set -a && source .env && set +a
```

## Запуск

```bash
python bot.py
```

При первом запуске Telethon попросит номер телефона и код подтверждения.

## Использование

Отправьте команду из аккаунта, под которым запущен userbot:

```text
/parse https://t.me/somechat both
```

или

```text
/parse @somechat csv
```

После завершения бот ответит количеством участников и путями к файлам.

## Важно

- Парсинг возможен только там, где ваш аккаунт имеет доступ к участникам.
- На больших чатах Telegram может выдавать `FloodWait` — бот сообщит, сколько нужно подождать.
