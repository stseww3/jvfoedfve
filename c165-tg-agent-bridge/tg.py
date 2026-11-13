"""Telegram Bot API 的薄封装。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

log = logging.getLogger("bridge.tg")

TEXT_LIMIT = 4000


def split_text(text: str, limit: int = TEXT_LIMIT) -> list[str]:
    parts: list[str] = []
    rest = text
    while len(rest) > limit:
        cut = rest.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(rest[:cut])
        rest = rest[cut:].lstrip("\n")
    if rest or not parts:
        parts.append(rest)
    return parts


class TelegramError(Exception):
    pass


class Telegram:
    def __init__(self, token: str, api_base: str = "https://api.telegram.org") -> None:
        self.token = token
        self.api_base = api_base.rstrip("/")
        self.base = f"{self.api_base}/bot{token}"
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(70, connect=15))

    def scrubbed(self, exc: Exception) -> TelegramError:
        # httpx 的报错可能带完整 URL，URL 里有 bot token：不能流进日志、聊天记录或 agent
        text = f"{type(exc).__name__}: {exc}"
        return TelegramError(text.replace(self.token, "<token>") if self.token else text)

    async def call(self, method: str, **payload: Any) -> Any:
        if not self.token:
            raise TelegramError("没有配置 Telegram bot token（.env 里的 TG_TOKEN）")
        for attempt in range(4):
            try:
                res = await self.client.post(f"{self.base}/{method}", json=payload)
            except httpx.HTTPError as exc:
                raise self.scrubbed(exc) from None
            data = res.json()
            if data.get("ok"):
                return data.get("result")
            retry = (data.get("parameters") or {}).get("retry_after")
            if data.get("error_code") == 429 and retry and attempt < 3:
                await asyncio.sleep(min(float(retry), 30) + 0.5)
                continue
            log.warning("telegram %s failed: %s", method, data.get("description"))
            raise TelegramError(data.get("description") or method)
        raise TelegramError(method)

    async def try_call(self, method: str, **payload: Any) -> Any:
        try:
            return await self.call(method, **payload)
        except Exception as exc:
            log.warning("telegram %s error: %s", method, exc)
            return None

    async def send_text(
        self,
        chat_id: int,
        text: str,
        reply_to: int | None = None,
        reply_markup: dict | None = None,
    ) -> list[dict]:
        sent: list[dict] = []
        chunks = split_text(text)
        for index, chunk in enumerate(chunks):
            body: dict[str, Any] = {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True}
            if reply_to and index == 0:
                body["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
            if reply_markup and index == len(chunks) - 1:
                body["reply_markup"] = reply_markup
            sent.append(await self.call("sendMessage", **body))
        return sent

    async def send_document(
        self,
        chat_id: int,
        filename: str,
        content: bytes,
        caption: str = "",
        reply_to: int | None = None,
    ) -> dict:
        if not self.token:
            raise TelegramError("没有配置 Telegram bot token（.env 里的 TG_TOKEN）")
        data = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption[:1000]
        if reply_to:
            data["reply_parameters"] = f'{{"message_id": {int(reply_to)}, "allow_sending_without_reply": true}}'
        try:
            res = await self.client.post(
                f"{self.base}/sendDocument",
                data=data,
                files={"document": (filename, content)},
                timeout=300,
            )
        except httpx.HTTPError as exc:
            raise self.scrubbed(exc) from None
        body = res.json()
        if not body.get("ok"):
            raise TelegramError(body.get("description") or "sendDocument")
        return body["result"]

    async def download(self, file_id: str) -> bytes:
        info = await self.call("getFile", file_id=file_id)
        path = (info or {}).get("file_path")
        if not path:
            raise TelegramError("Telegram 没有返回文件路径（Bot API 只能下载 20MB 以内的文件）")
        try:
            res = await self.client.get(f"{self.api_base}/file/bot{self.token}/{path}", timeout=300)
        except httpx.HTTPError as exc:
            raise self.scrubbed(exc) from None
        if res.status_code != 200:
            raise TelegramError(f"下载文件失败：HTTP {res.status_code}")
        return res.content
