import argparse
import asyncio
import importlib
import json
import logging
import re
import shutil
import subprocess
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from datetime import datetime
from uuid import uuid4

ClientSession = Any
StdioServerParameters = Any
MCP_TRANSPORT_AVAILABLE: bool | None = None
MCP_TRANSPORT_ERROR: BaseException | None = None


def stdio_client(*args, **kwargs):
    raise RuntimeError("Optional MCP transport dependencies are not installed in this environment.")


PAGE_RE = re.compile(r"当前第\s*(?P<page>\d+)\s*页\s*[,，]\s*共\s*(?P<total>\d+)\s*页")
KEYWORD_RE = re.compile(r"关键词：\s*(?:`(?P<quoted>[^`\n]+)`|(?P<plain>[^\n]+))")
LINK_RE = re.compile(r"\[(?P<title>.+?)\]\((?P<link>https?://[^\s)]+)\)")
BUTTON_RE = re.compile(
    r"^\[(?P<index>\d+)\]\s+text='(?P<text>.*?)',\s+callback=(?P<callback>yes|no)(?:,\s+url=(?P<url>.*))?$"
)
NEXT_MARKERS = ("下一页", "下页", "后一页", "➡", "→", "▶")
CALLBACK_TIMEOUT_MARKERS = (
    "botresponsetimeouterror",
    "getbotcallbackanswerrequest",
    "did not answer to the callback query in time",
    "did not answer the callback query in time",
)
DEFAULT_HISTORY_LIMIT = 20
DEFAULT_POLL_INTERVAL = 2.0
DEFAULT_MAX_POLLS_PER_STEP = 90
DEFAULT_BATCH_SIZE = 50


def normalize(value: Any) -> str:
    return " ".join(str(value or "").split())


def describe_transport_import_failure(exc: BaseException | None) -> str:
    base = (
        "sososo.py requires optional MCP client transport dependencies "
        "(`anyio`, `mcp`, and stdio client modules`) to talk to telegram-mcp."
    )
    if exc is None:
        return base
    detail = normalize(exc) or exc.__class__.__name__
    return f"{base} Import failed with {exc.__class__.__name__}: {detail}"


def load_transport_dependencies(force_reload: bool = False) -> bool:
    global ClientSession, StdioServerParameters, stdio_client, MCP_TRANSPORT_AVAILABLE, MCP_TRANSPORT_ERROR
    if MCP_TRANSPORT_AVAILABLE is not None and not force_reload:
        return bool(MCP_TRANSPORT_AVAILABLE)

    try:
        session_module = importlib.import_module("mcp.client.session")
        stdio_module = importlib.import_module("mcp.client.stdio")
    except BaseException as exc:
        ClientSession = Any
        StdioServerParameters = Any
        MCP_TRANSPORT_AVAILABLE = False
        MCP_TRANSPORT_ERROR = exc

        def _missing_stdio_client(*args, **kwargs):
            raise RuntimeError(describe_transport_import_failure(exc))

        stdio_client = _missing_stdio_client
        return False

    ClientSession = session_module.ClientSession
    StdioServerParameters = stdio_module.StdioServerParameters
    stdio_client = stdio_module.stdio_client
    MCP_TRANSPORT_AVAILABLE = True
    MCP_TRANSPORT_ERROR = None
    return True


def ensure_transport_ready(docker_command: str, container: str) -> None:
    if not load_transport_dependencies():
        raise SystemExit(describe_transport_import_failure(MCP_TRANSPORT_ERROR))
    if shutil.which(docker_command) is None:
        raise SystemExit(f"Cannot find docker executable {docker_command!r} in PATH.")

    inspected = subprocess.run(
        [docker_command, "inspect", "-f", "{{.State.Running}}", container],
        capture_output=True,
        text=True,
    )
    if inspected.returncode != 0:
        detail = normalize(inspected.stderr or inspected.stdout) or "unknown docker inspect error"
        raise SystemExit(f"Cannot inspect docker container {container!r}: {detail}")
    if normalize(inspected.stdout).lower() != "true":
        raise SystemExit(f"Container {container!r} is not running.")


def extract_tool_text(result: Any) -> str:
    content = getattr(result, "content", None)
    parts: list[str] = []
    if content:
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
    if parts:
        return "\n".join(parts).strip()
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False, indent=2)
    raise RuntimeError("Tool result did not contain text output.")


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


class ConsoleColorFormatter(logging.Formatter):
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    WHITE = "\033[97m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    RED = "\033[91m"
    GRAY = "\033[90m"
    LEVEL_COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: BLUE,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: MAGENTA,
    }

    def _paint(self, text: str, *styles: str) -> str:
        prefix = "".join(styles)
        if not prefix:
            return text
        return f"{prefix}{text}{self.RESET}"

    def _format_segment(self, segment: str, levelno: int) -> str:
        step_match = re.match(r"(?P<badge>\[STEP\s+\d+\])\s*(?P<text>.*)", segment)
        if step_match:
            badge = self._paint(step_match.group("badge"), self.BOLD, self.CYAN)
            text = self._highlight_page_progress(step_match.group("text"))
            if not text:
                return badge
            return f"{badge} {text}"

        if "=" in segment:
            key, value = segment.split("=", 1)
            return f"{self._paint(key, self.BOLD, self.YELLOW)}={self._paint(value, *self._value_style(key, value))}"

        level_color = self.LEVEL_COLORS.get(levelno, self.WHITE)
        highlighted = self._highlight_page_progress(segment)
        if highlighted != segment:
            return highlighted
        return self._paint(segment, level_color if levelno >= logging.WARNING else self.WHITE)

    def _highlight_page_progress(self, text: str) -> str:
        pattern = re.compile(r"(?P<label>\bpage\s+)(?P<current>\d+)(?P<sep>/)(?P<total>\d+)", re.IGNORECASE)

        def _replace(match: re.Match[str]) -> str:
            label = self._paint(match.group("label"), self.WHITE)
            current = self._paint(match.group("current"), self.BOLD, self.CYAN)
            sep = self._paint(match.group("sep"), self.GRAY)
            total = self._paint(match.group("total"), self.BOLD, self.MAGENTA)
            return f"{label}{current}{sep}{total}"

        highlighted = pattern.sub(_replace, text)
        if highlighted == text:
            return self._paint(text, self.WHITE)
        return highlighted

    def _value_style(self, key: str, value: str) -> tuple[str, ...]:
        lowered_key = key.strip().lower()
        stripped_value = value.strip()

        if lowered_key in {"output_dir", "crawl_dir", "log_dir", "log_file", "path"}:
            return (self.GREEN,)
        if lowered_key in {"query", "prompt"}:
            return (self.CYAN,)
        if lowered_key in {"detector", "button_index", "message_id", "batch_index", "batch", "items", "total_unique_items"}:
            return (self.MAGENTA,)
        if re.fullmatch(r"\d+(?:/\d+)?", stripped_value):
            return (self.MAGENTA,)
        if "\\" in stripped_value or "/" in stripped_value:
            return (self.GREEN,)
        return (self.WHITE,)

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self._paint(self.formatTime(record, self.datefmt), self.DIM, self.WHITE)
        level = self._paint(record.levelname, self.BOLD, self.LEVEL_COLORS.get(record.levelno, self.WHITE))
        separator = self._paint("|", self.GRAY)
        message = f" {separator} ".join(
            self._format_segment(segment, record.levelno) for segment in record.getMessage().split(" | ")
        )
        return f"{timestamp} {separator} {level} {separator} {message}"


class SososoLogger:
    def __init__(self, output_dir: Path) -> None:
        self.log_dir = output_dir / "logs" / "sososo_search_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"sososo-{datetime.now():%y%m%d-%H%M%S}-{uuid4().hex[:6]}.log"
        self._step_counter = 0
        self._logger = logging.getLogger(f"sososo.{uuid4().hex}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            ConsoleColorFormatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
        )

        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )

        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

    def step(self, message: str) -> None:
        self._step_counter += 1
        self._logger.info(f"[STEP {self._step_counter:03d}] {message}")

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)


@dataclass
class ChallengeMatch:
    detector_name: str
    challenge_type: str
    prompt: str
    answer: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectedChallenge:
    message_id: int
    sender: str
    date: str
    match: ChallengeMatch


class BotChallengeError(RuntimeError):
    def __init__(self, challenge: DetectedChallenge) -> None:
        self.challenge = challenge
        answer_text = f" | answer={challenge.match.answer}" if challenge.match.answer is not None else ""
        super().__init__(
            "Bot challenge detected: "
            f"{challenge.match.detector_name} | prompt={challenge.match.prompt}{answer_text}"
        )


class ChallengeDetector(Protocol):
    name: str

    def detect(self, message_text: str) -> ChallengeMatch | None: ...


class ArithmeticChallengeDetector:
    name = "arithmetic"
    _pattern = re.compile(
        r"(?P<left>\d+)\s*(?P<operator>[+\-xX*/×÷])\s*(?P<right>\d+)\s*(?:=+\s*)?(?:\?+|？+|=?\s*$)"
    )

    def detect(self, message_text: str) -> ChallengeMatch | None:
        text = normalize(message_text)
        match = self._pattern.search(text)
        if not match:
            return None

        left = int(match.group("left"))
        right = int(match.group("right"))
        operator = match.group("operator")
        answer = self._calculate(left, right, operator)
        if answer is None:
            return None

        return ChallengeMatch(
            detector_name=self.name,
            challenge_type="math",
            prompt=match.group(0).strip(),
            answer=answer,
            metadata={"left": left, "right": right, "operator": operator},
        )

    def _calculate(self, left: int, right: int, operator: str) -> str | None:
        if operator == "+":
            return str(left + right)
        if operator == "-":
            return str(left - right)
        if operator in {"x", "X", "×", "*"}:
            return str(left * right)
        if operator in {"/", "÷"}:
            if right == 0:
                return None
            if left % right == 0:
                return str(left // right)
            return str(left / right)
        return None


class BotChallengeInspector:
    def __init__(self, detectors: list[ChallengeDetector] | None = None) -> None:
        self.detectors = detectors or [ArithmeticChallengeDetector()]

    def detect_from_blocks(self, blocks: list[dict[str, Any]]) -> DetectedChallenge | None:
        for block in reversed(blocks):
            text = block.get("text", "")
            if parse_page_info(text) or parse_items(text):
                continue
            for detector in self.detectors:
                match = detector.detect(text)
                if match is None:
                    continue
                return DetectedChallenge(
                    message_id=int(block["id"]),
                    sender=normalize(block.get("sender")),
                    date=normalize(block.get("date")),
                    match=match,
                )
        return None


def parse_history_blocks(history_text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in history_text.splitlines():
        if raw_line.startswith("ID: "):
            if current is not None:
                current["text"] = "\n".join(current["message_lines"]).strip("\n")
                current.pop("message_lines", None)
                blocks.append(current)

            if " | Message: " in raw_line:
                prefix, message_text = raw_line.split(" | Message: ", 1)
            else:
                prefix, message_text = raw_line, ""

            parts = prefix.split(" | ")
            if len(parts) < 3:
                current = None
                continue

            try:
                message_id = int(parts[0].split(": ", 1)[1])
            except (IndexError, ValueError):
                current = None
                continue

            sender = parts[1]
            date_value = parts[2][len("Date: ") :] if parts[2].startswith("Date: ") else parts[2]
            current = {
                "id": message_id,
                "sender": sender,
                "date": date_value,
                "message_lines": [message_text],
            }
            continue

        if current is not None:
            current["message_lines"].append(raw_line)

    if current is not None:
        current["text"] = "\n".join(current["message_lines"]).strip("\n")
        current.pop("message_lines", None)
        blocks.append(current)

    return blocks


def parse_page_info(message_text: str) -> tuple[int, int] | None:
    match = PAGE_RE.search(message_text)
    if not match:
        return None
    return int(match.group("page")), int(match.group("total"))


def parse_result_query(message_text: str) -> str | None:
    match = KEYWORD_RE.search(message_text)
    if not match:
        return None
    value = match.group("quoted") or match.group("plain") or ""
    normalized = normalize(value.strip("`"))
    return normalized or None


def parse_items(message_text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for match in LINK_RE.finditer(message_text):
        title = normalize(match.group("title"))
        link = normalize(match.group("link"))
        if title and link:
            items.append({"title": title, "link": link})
    return items


def parse_buttons(buttons_text: str) -> list[dict[str, Any]]:
    buttons: list[dict[str, Any]] = []
    for raw_line in buttons_text.splitlines():
        match = BUTTON_RE.match(raw_line.strip())
        if not match:
            continue
        buttons.append(
            {
                "index": int(match.group("index")),
                "text": match.group("text"),
                "has_callback": match.group("callback") == "yes",
            }
        )
    return buttons


def choose_next_button(buttons: list[dict[str, Any]]) -> dict[str, Any] | None:
    for button in buttons:
        text = normalize(button.get("text"))
        if button.get("has_callback") and any(marker in text for marker in NEXT_MARKERS):
            return button

    blank_callbacks = [
        button for button in buttons if button.get("has_callback") and not normalize(button.get("text"))
    ]
    if blank_callbacks:
        return sorted(blank_callbacks, key=lambda item: item["index"], reverse=True)[0]
    return None


def select_result_block(blocks: list[dict[str, Any]], query: str) -> dict[str, Any]:
    effective_query = normalize(query)
    candidates: list[dict[str, Any]] = []
    matching_query_candidates: list[dict[str, Any]] = []
    query_aware_candidates = 0

    for block in blocks:
        if not parse_page_info(block["text"]):
            continue
        if not parse_items(block["text"]):
            continue
        candidates.append(block)

        result_query = parse_result_query(block["text"])
        if result_query is None:
            continue
        query_aware_candidates += 1
        if normalize(result_query) == effective_query:
            matching_query_candidates.append(block)

    if matching_query_candidates:
        candidates = matching_query_candidates
    elif effective_query and query_aware_candidates > 0:
        candidates = []

    if not candidates:
        raise RuntimeError(f"Could not find a paginated @sososo result block for query {effective_query!r}.")

    candidates.sort(key=lambda item: item["id"])
    return candidates[-1]


def is_callback_timeout_error(exc: BaseException) -> bool:
    detail = normalize(exc).lower()
    if not detail:
        return False
    if any(marker in detail for marker in CALLBACK_TIMEOUT_MARKERS):
        return True
    return "callback" in detail and ("timeout" in detail or "did not answer" in detail)


class WorkerTransport(Protocol):
    async def send_message(self, chat_id: str, message: str) -> str: ...

    async def get_history(self, chat_id: str, limit: int) -> str: ...

    async def list_inline_buttons(self, chat_id: str, message_id: int) -> str: ...

    async def press_inline_button(self, chat_id: str, message_id: int, button_index: int) -> str: ...


class DockerExecTransport:
    def __init__(
        self,
        container: str = "telegram-mcp",
        docker_command: str = "docker",
        server_command: str = "python",
        server_args: tuple[str, ...] = ("/app/main.py",),
    ) -> None:
        self.container = container
        self.docker_command = docker_command
        self.server_command = server_command
        self.server_args = server_args
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "DockerExecTransport":
        ensure_transport_ready(self.docker_command, self.container)
        self._stack = AsyncExitStack()
        try:
            params = StdioServerParameters(
                command=self.docker_command,
                args=["exec", "-i", self.container, self.server_command, *self.server_args],
            )
            read_stream, write_stream = await self._stack.enter_async_context(stdio_client(params, errlog=sys.stderr))
            self._session = await self._stack.enter_async_context(ClientSession(read_stream, write_stream))
            await self._session.initialize()
            return self
        except BaseException as exc:
            if self._stack is not None:
                await self._stack.aclose()
            self._stack = None
            self._session = None
            raise SystemExit(
                f"Could not establish docker exec MCP transport for container {self.container!r}: {exc}"
            ) from exc

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._session = None

    async def _call_text_tool(self, name: str, arguments: dict[str, Any]) -> str:
        if self._session is None:
            raise RuntimeError("DockerExecTransport session is not initialized.")
        result = await self._session.call_tool(name, arguments)
        if result.isError:
            raise RuntimeError(f"Tool call failed for {name}: {result}")
        return extract_tool_text(result)

    async def send_message(self, chat_id: str, message: str) -> str:
        return await self._call_text_tool("send_message", {"chat_id": chat_id, "message": message})

    async def get_history(self, chat_id: str, limit: int) -> str:
        return await self._call_text_tool("get_history", {"chat_id": chat_id, "limit": limit})

    async def list_inline_buttons(self, chat_id: str, message_id: int) -> str:
        return await self._call_text_tool("list_inline_buttons", {"chat_id": chat_id, "message_id": str(message_id)})

    async def press_inline_button(self, chat_id: str, message_id: int, button_index: int) -> str:
        return await self._call_text_tool(
            "press_inline_button",
            {"chat_id": chat_id, "message_id": str(message_id), "button_index": str(button_index)},
        )


class SOSOSO:
    def __init__(
        self,
        transport: WorkerTransport,
        *,
        challenge_inspector: BotChallengeInspector | None = None,
        output_dir: str | Path = ".",
        batch_size: int = DEFAULT_BATCH_SIZE,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        max_polls_per_step: int = DEFAULT_MAX_POLLS_PER_STEP,
    ) -> None:
        self.transport = transport
        self.challenge_inspector = challenge_inspector or BotChallengeInspector()
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.logger = SososoLogger(self.output_dir)
        self.batch_size = batch_size
        self.history_limit = history_limit
        self.poll_interval = poll_interval
        self.max_polls_per_step = max_polls_per_step
        self.counter = 1
        self.crawl_dir = self.output_dir / "batches" / f"{datetime.now():%y%m%d-%H%M%S}"
        self.logger.step(
            "Initialized crawler "
            f"| output_dir={self.output_dir} | crawl_dir={self.crawl_dir} | log_file={self.logger.log_file}"
        )

    async def do_query(self, query: str) -> None:
        self.logger.step(f"Sending query to @sososo | query={normalize(query)!r}")
        await self.transport.send_message("@sososo", query)
        self.logger.info("Query sent successfully.")

    async def wait_for_challenge_resolution(self, challenge: DetectedChallenge) -> None:
        answer_hint = (
            f"- Suggested answer: {challenge.match.answer}\n" if challenge.match.answer is not None else ""
        )
        self.logger.warning(
            "Bot challenge detected "
            f"| detector={challenge.match.detector_name} | prompt={challenge.match.prompt}"
        )
        if challenge.match.answer is not None:
            self.logger.warning(f"Suggested answer: {challenge.match.answer}")
        self.logger.warning("Please solve the challenge in Telegram, then confirm here to continue.")

        while True:
            answer = await asyncio.to_thread(input, "Da giai challenge xong chua? (y/n): ")
            normalized_answer = normalize(answer).lower()
            if normalized_answer in {"y", "yes"}:
                self.logger.step("User confirmed challenge is resolved. Resuming crawl.")
                return
            if normalized_answer in {"n", "no"}:
                self.logger.error("User declined to continue after challenge prompt.")
                raise RuntimeError("User did not confirm challenge resolution.")
            self.logger.warning("Invalid challenge confirmation input. Expected 'y' or 'n'.")

    async def do_fetch_page(self, query: str, current_page: int | None = None) -> dict[str, Any]:
        for attempt in range(1, self.max_polls_per_step + 1):
            self.logger.info(
                f"Polling @sososo history for results | attempt={attempt}/{self.max_polls_per_step} "
                f"| current_page={current_page}"
            )
            history_text = await self.transport.get_history("@sososo", self.history_limit)
            blocks = parse_history_blocks(history_text)
            try:
                block = select_result_block(blocks, query)
            except RuntimeError as exc:
                challenge = self.challenge_inspector.detect_from_blocks(blocks)
                if challenge is not None:
                    await self.wait_for_challenge_resolution(challenge)
                    await asyncio.sleep(self.poll_interval)
                    continue
                self.logger.info("No matching paginated results block yet. Waiting for next poll.")
                await asyncio.sleep(self.poll_interval)
                continue

            page_info = parse_page_info(block["text"])
            if page_info is None:
                self.logger.warning("Found candidate message without parsable page info. Retrying.")
                await asyncio.sleep(self.poll_interval)
                continue

            page_number, total_pages = page_info
            if current_page is not None and page_number == current_page:
                self.logger.info(f"Still on page {page_number}. Waiting for a new page.")
                await asyncio.sleep(self.poll_interval)
                continue

            self.logger.step(
                f"Received results page {page_number}/{total_pages} | message_id={int(block['id'])} "
                f"| items={len(parse_items(block['text']))}"
            )
            return {
                "message_id": int(block["id"]),
                "page": page_number,
                "total_pages": total_pages,
                "items": parse_items(block["text"]),
                "raw_text": block["text"],
            }

        self.logger.error("Timed out waiting for a new @sososo result page.")
        raise RuntimeError("Timed out waiting for a new @sososo result page.")

    async def do_press_next(self, message_id: int) -> bool:
        self.logger.step(f"Inspecting inline buttons for next page | message_id={message_id}")
        buttons_text = await self.transport.list_inline_buttons("@sososo", message_id)
        next_button = choose_next_button(parse_buttons(buttons_text))
        if next_button is None:
            self.logger.warning(f"No next-page button found for message_id={message_id}.")
            return False

        try:
            self.logger.step(
                f"Pressing next-page button | message_id={message_id} | button_index={int(next_button['index'])}"
            )
            await self.transport.press_inline_button("@sososo", message_id, int(next_button["index"]))
        except BaseException as exc:
            if is_callback_timeout_error(exc):
                self.logger.error(f"Next-page callback timed out | message_id={message_id} | detail={normalize(exc)}")
                raise RuntimeError(f"Timed out when pressing next page button: {normalize(exc)}") from exc
            raise
        self.logger.info("Next-page button pressed successfully.")
        return True

    def flush_batch(
        self,
        *,
        query: str,
        batch_items: list[dict[str, str]],
        batch_pages: set[int],
        provider_total_pages: int | None,
    ) -> str | None:
        if not batch_items:
            return None

        batch_path = self.crawl_dir / f"{self.counter:04d}.json"
        payload = {
            "query": normalize(query),
            "batch_index": self.counter,
            "pages_crawled": sorted(batch_pages),
            "provider_total_pages": provider_total_pages,
            "total_items": len(batch_items),
            "items": batch_items,
        }
        write_json_atomic(batch_path, payload)
        self.logger.step(
            f"Flushed batch file | batch_index={self.counter} | items={len(batch_items)} | path={batch_path}"
        )
        self.counter += 1
        return str(batch_path)

    async def crawl(self, query: str, max_page: int) -> dict[str, Any]:
        if max_page < 1:
            raise ValueError("--max-page must be >= 1")
        if self.batch_size < 1:
            raise ValueError("--batch must be >= 1")

        self.logger.step(
            f"Starting crawl | query={normalize(query)!r} | max_page={max_page} | batch={self.batch_size}"
        )
        await self.do_query(query)

        pages: list[dict[str, Any]] = []
        all_items: list[dict[str, str]] = []
        seen_keys: set[str] = set()
        batch_items: list[dict[str, str]] = []
        batch_pages: set[int] = set()
        batch_files: list[str] = []
        current_page: int | None = None
        provider_total_pages: int | None = None

        while True:
            page_payload = await self.do_fetch_page(query, current_page=current_page)
            current_page = int(page_payload["page"])
            provider_total_pages = int(page_payload["total_pages"])
            pages.append(
                {
                    "page": current_page,
                    "message_id": int(page_payload["message_id"]),
                    "items_count": len(page_payload["items"]),
                }
            )
            self.logger.info(
                f"Processing page {current_page}/{provider_total_pages} | raw_items={len(page_payload['items'])}"
            )

            for item in page_payload["items"]:
                key = normalize(item["link"]).lower() or normalize(item["title"]).lower()
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                all_items.append(item)
                batch_items.append(item)
                batch_pages.add(current_page)
                if len(batch_items) >= self.batch_size:
                    batch_file = self.flush_batch(
                        query=query,
                        batch_items=batch_items,
                        batch_pages=batch_pages,
                        provider_total_pages=provider_total_pages,
                    )
                    if batch_file is not None:
                        batch_files.append(batch_file)
                    batch_items = []
                    batch_pages = set()

            if current_page >= max_page:
                self.logger.step(f"Reached requested max_page={max_page}. Stopping crawl.")
                break
            if provider_total_pages is not None and current_page >= provider_total_pages:
                self.logger.step(f"Reached provider last page={provider_total_pages}. Stopping crawl.")
                break

            has_next = await self.do_press_next(int(page_payload["message_id"]))
            if not has_next:
                self.logger.step("Pagination stopped because no next-page button was available.")
                break

        if batch_items:
            batch_file = self.flush_batch(
                query=query,
                batch_items=batch_items,
                batch_pages=batch_pages,
                provider_total_pages=provider_total_pages,
            )
            if batch_file is not None:
                batch_files.append(batch_file)

        result = {
            "query": normalize(query),
            "requested_max_page": max_page,
            "output_dir": str(self.output_dir),
            "crawl_dir": str(self.crawl_dir),
            "log_dir": str(self.logger.log_dir),
            "log_file": str(self.logger.log_file),
            "batch_size": self.batch_size,
            "batch_files": batch_files,
            "pages_crawled": [page["page"] for page in pages],
            "provider_total_pages": provider_total_pages,
            "total_unique_items": len(all_items),
            "items": all_items,
        }
        self.logger.step(
            f"Crawl completed | pages={result['pages_crawled']} | total_unique_items={result['total_unique_items']}"
        )
        return result


async def run_crawl(
    query: str,
    max_page: int,
    *,
    output_dir: str | Path,
    batch_size: int,
    history_limit: int,
    poll_interval: float,
    max_polls_per_step: int,
    container: str,
    docker_command: str,
) -> dict[str, Any]:
    async with DockerExecTransport(container=container, docker_command=docker_command) as transport:
        crawler = SOSOSO(
            transport,
            output_dir=output_dir,
            batch_size=batch_size,
            history_limit=history_limit,
            poll_interval=poll_interval,
            max_polls_per_step=max_polls_per_step,
        )
        return await crawler.crawl(query, max_page)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crawl @sososo and return only title + link pairs.")
    parser.add_argument("--query", required=True, help="Keyword to send to @sososo")
    parser.add_argument("--max-page", required=True, type=int, help="Maximum number of result pages to crawl")
    parser.add_argument("--output-dir", default=".", help="Base directory; files are written under batches/YYMMDD-HHMMSS/0001.json")
    parser.add_argument("--batch", dest="batch_size", type=int, default=DEFAULT_BATCH_SIZE, help="Items per output batch file")
    parser.add_argument("--history-limit", type=int, default=DEFAULT_HISTORY_LIMIT)
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL)
    parser.add_argument("--max-polls-per-step", type=int, default=DEFAULT_MAX_POLLS_PER_STEP)
    parser.add_argument("--container", default="telegram-mcp")
    parser.add_argument("--docker-command", default="docker")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = asyncio.run(
            run_crawl(
                query=args.query,
                max_page=args.max_page,
                output_dir=args.output_dir,
                batch_size=args.batch_size,
                history_limit=args.history_limit,
                poll_interval=args.poll_interval,
                max_polls_per_step=args.max_polls_per_step,
                container=args.container,
                docker_command=args.docker_command,
            )
        )
    except KeyboardInterrupt:
        raise SystemExit("Interrupted.")
    except Exception as exc:
        raise SystemExit(f"sososo crawl failed: {exc}") from exc

    console_summary = dict(result)
    console_summary.pop("items", None)
    print(json.dumps(console_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
