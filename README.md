# Telegram бот: уведомления о входящих USDT (TRC-20)

Бот отслеживает входящие транзакции **только USDT (TRC-20)** по указанному адресу TRON и отправляет уведомление в Telegram, как только появляется новый входящий перевод.

## Возможности

- Мониторинг входящих TRC-20 транзакций через TronGrid API.
- Фильтрация только по контракту USDT TRON (`TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj`).
- Мгновенное уведомление в Telegram с суммой, отправителем и ссылкой на Tronscan.
- Защита от дублей через локальную SQLite базу (`state.db`).

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка

1. Создай Telegram-бота через [@BotFather](https://t.me/BotFather) и возьми `TELEGRAM_BOT_TOKEN`.
2. Узнай `TELEGRAM_CHAT_ID` (например, через [@userinfobot](https://t.me/userinfobot)).
3. Укажи TRON адрес кошелька в `TRON_WALLET_ADDRESS`.

Скопируй пример:

```bash
cp .env.example .env
```

Заполни `.env`.

## Запуск

```bash
export $(grep -v '^#' .env | xargs)
python bot.py
```

## Пример уведомления

- 💸 Входящее поступление USDT (TRC-20)
- Сумма: `100.00 USDT`
- Отправитель, получатель, TxID и ссылка на Tronscan.

## Важно

- При первом старте бот начнет отслеживание и будет отправлять уведомления только для новых транзакций после запуска.
- Для продакшна рекомендуется запуск через `systemd`, Docker или PM2.
