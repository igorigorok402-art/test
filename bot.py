import asyncio
import csv
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import UserStatusRecently, UserStatusLastMonth, UserStatusLastWeek, UserStatusOffline, UserStatusOnline


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("participant_parser_bot")


@dataclass
class Participant:
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    bot: bool
    premium: bool
    scam: bool
    fake: bool
    deleted: bool
    status: str


def _status_to_text(status: object) -> str:
    if status is None:
        return "unknown"
    if isinstance(status, UserStatusOnline):
        return "online"
    if isinstance(status, UserStatusOffline):
        return f"offline_until_{status.was_online.isoformat()}"
    if isinstance(status, UserStatusRecently):
        return "recently"
    if isinstance(status, UserStatusLastWeek):
        return "last_week"
    if isinstance(status, UserStatusLastMonth):
        return "last_month"
    return status.__class__.__name__


def participant_from_user(user) -> Participant:
    return Participant(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        bot=bool(getattr(user, "bot", False)),
        premium=bool(getattr(user, "premium", False)),
        scam=bool(getattr(user, "scam", False)),
        fake=bool(getattr(user, "fake", False)),
        deleted=bool(getattr(user, "deleted", False)),
        status=_status_to_text(getattr(user, "status", None)),
    )


def write_csv(rows: Iterable[Participant], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()) if rows else [
            "user_id", "username", "first_name", "last_name", "phone", "bot", "premium", "scam", "fake", "deleted", "status"
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_json(rows: Iterable[Participant], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(row) for row in rows]
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


HELP_TEXT = (
    "Привет! Я userbot-парсер участников.\n\n"
    "Команды:\n"
    "/help — показать это сообщение\n"
    "/parse <chat_or_channel> [csv|json|both] — выгрузить участников\n"
    "Пример: /parse https://t.me/somechat both\n\n"
    "Важно: этот скрипт работает от пользовательского аккаунта Telegram "
    "(через API_ID/API_HASH), потому что Bot API не дает получить полный список "
    "участников канала/чата."
)


async def parse_participants(client: TelegramClient, entity_ref: str) -> list[Participant]:
    participants: list[Participant] = []
    async for user in client.iter_participants(entity_ref):
        participants.append(participant_from_user(user))
    return participants


async def main() -> None:
    api_id_raw = os.getenv("API_ID", "").strip()
    api_hash = os.getenv("API_HASH", "").strip()
    session_name = os.getenv("SESSION_NAME", "participant_parser")
    output_dir = Path(os.getenv("OUTPUT_DIR", "exports"))

    if not api_id_raw.isdigit() or not api_hash:
        raise RuntimeError("Нужно задать API_ID и API_HASH в переменных окружения.")

    api_id = int(api_id_raw)
    client = TelegramClient(session_name, api_id, api_hash)

    @client.on(events.NewMessage(pattern=r"^/help$"))
    async def on_help(event):
        await event.respond(HELP_TEXT)

    @client.on(events.NewMessage(pattern=r"^/parse(?:\s+(.+))?$"))
    async def on_parse(event):
        args = (event.pattern_match.group(1) or "").strip()
        if not args:
            await event.respond("Использование: /parse <chat_or_channel> [csv|json|both]")
            return

        parts = args.split()
        entity_ref = parts[0]
        fmt = parts[1].lower() if len(parts) > 1 else "both"
        if fmt not in {"csv", "json", "both"}:
            await event.respond("Формат должен быть csv, json или both")
            return

        started = datetime.now()
        await event.respond(f"Начинаю парсинг: {entity_ref}")

        try:
            rows = await parse_participants(client, entity_ref)
        except FloodWaitError as e:
            await event.respond(f"Telegram просит подождать {e.seconds} сек. Повторите позже.")
            return
        except Exception as e:  # noqa: BLE001
            logger.exception("Ошибка парсинга")
            await event.respond(f"Ошибка: {e}")
            return

        stamp = started.strftime("%Y%m%d_%H%M%S")
        safe_name = entity_ref.replace("https://", "").replace("http://", "").replace("/", "_").replace("@", "")
        base = output_dir / f"{safe_name}_{stamp}"

        output_files: list[Path] = []
        if fmt in {"csv", "both"}:
            csv_path = base.with_suffix(".csv")
            write_csv(rows, csv_path)
            output_files.append(csv_path)
        if fmt in {"json", "both"}:
            json_path = base.with_suffix(".json")
            write_json(rows, json_path)
            output_files.append(json_path)

        elapsed = (datetime.now() - started).total_seconds()
        file_lines = "\n".join(str(p) for p in output_files)
        await event.respond(
            f"Готово! Найдено участников: {len(rows)}\n"
            f"Время: {elapsed:.2f} сек\n"
            f"Файлы:\n{file_lines}"
        )

    logger.info("Запуск userbot. Отправьте /help в любой чат, где есть ваш аккаунт.")
    await client.start()
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
