#!/usr/bin/env python3
from __future__ import annotations

import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4


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
            text = self._highlight_numeric_progress(step_match.group("text"))
            if not text:
                return badge
            return f"{badge} {text}"

        if "=" in segment:
            key, value = segment.split("=", 1)
            return f"{self._paint(key, self.BOLD, self.YELLOW)}={self._paint(value, *self._value_style(key, value))}"

        level_color = self.LEVEL_COLORS.get(levelno, self.WHITE)
        highlighted = self._highlight_numeric_progress(segment)
        if highlighted != segment:
            return highlighted
        return self._paint(segment, level_color if levelno >= logging.WARNING else self.WHITE)

    def _highlight_numeric_progress(self, text: str) -> str:
        pattern = re.compile(r"(?P<label>\b(?:page|file|item|attempt)\s+)(?P<current>\d+)(?P<sep>/)(?P<total>\d+)", re.IGNORECASE)

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

        if lowered_key in {"output_dir", "run_dir", "input_dir", "log_dir", "log_file", "manifest", "path"}:
            return (self.GREEN,)
        if lowered_key in {"source_file", "query", "skill"}:
            return (self.CYAN,)
        if lowered_key in {"files_total", "items_total", "accepted_total", "rejected_total"}:
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


class ReviewLogger:
    def __init__(self, workspace_root: Path) -> None:
        self.log_dir = workspace_root / "logs" / "review-cn-sososo-search_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"review-cn-sososo-search-{datetime.now():%y%m%d-%H%M%S}-{uuid4().hex[:6]}.log"
        self._step_counter = 0
        self._logger = logging.getLogger(f"review-cn-sososo-search.{uuid4().hex}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stderr)
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

