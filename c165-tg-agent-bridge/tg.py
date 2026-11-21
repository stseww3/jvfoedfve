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
        self.client = self._make_api_client()
        self.poll_client = self._make_poll_client()

    @staticmethod
    def _make_api_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(45.0, connect=10.0, pool=10.0),
            limits=httpx.Limits(max_connections=32, max_keepalive_connections=6, keepalive_expiry=15.0),
        )

    @staticmethod
    def _make_poll_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(70.0, connect=15.0, pool=10.0),
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2, keepalive_expiry=65.0),
        )

    async def _recycle_client(self, *, is_poll: bool = False) -> None:
        attr = "poll_client" if is_poll else "client"
        old = getattr(self, attr, None)
        setattr(self, attr, self._make_poll_client() if is_poll else self._make_api_client())
        if old is not None:
            try:
                await old.aclose()
            except Exception:
                pass

    async def aclose(self) -> None:
        for attr in ("client", "poll_client"):
            cli = getattr(self, attr, None)
            if cli is not None:
                try:
                    await cli.aclose()
                except Exception:
                    pass

    def scrubbed(self, exc: Exception) -> TelegramError:
        # httpx 的报错可能带完整 URL，URL 里有 bot token：不能流进日志、聊天记录或 agent
        text = f"{type(exc).__name__}: {exc}"
        return TelegramError(text.replace(self.token, "<token>") if self.token else text)

    async def call(self, method: str, **payload: Any) -> Any:
        if not self.token:
            raise TelegramError("没有配置 Telegram bot token（.env 里的 TG_TOKEN）")
        is_poll = method == "getUpdates"
        max_attempts = 2 if is_poll else 4
        for attempt in range(max_attempts):
            cli = self.poll_client if is_poll else self.client
            try:
                res = await cli.post(f"{self.base}/{method}", json=payload)
            except httpx.TransportError as exc:
                await self._recycle_client(is_poll=is_poll)
                if not is_poll and attempt + 1 < max_attempts:
                    await asyncio.sleep(0.4 * (2 ** attempt))
                    continue
                raise self.scrubbed(exc) from None
            except httpx.HTTPError as exc:
                raise self.scrubbed(exc) from None
            if res.status_code in (502, 503, 504) and not is_poll and attempt + 1 < max_attempts:
                await asyncio.sleep(0.5 * (2 ** attempt))
                continue
            try:
                data = res.json()
            except ValueError as exc:
                if not is_poll and attempt + 1 < max_attempts:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise TelegramError(f"Telegram HTTP {res.status_code} invalid JSON: {exc}") from None
            if data.get("ok"):
                return data.get("result")
            retry = (data.get("parameters") or {}).get("retry_after")
            if data.get("error_code") == 429 and retry and attempt + 1 < max_attempts:
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
        for attempt in range(3):
            try:
                res = await self.client.post(
                    f"{self.base}/sendDocument",
                    data=data,
                    files={"document": (filename, content)},
                    timeout=300,
                )
                break
            except httpx.TransportError as exc:
                await self._recycle_client(is_poll=False)
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise self.scrubbed(exc) from None
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
