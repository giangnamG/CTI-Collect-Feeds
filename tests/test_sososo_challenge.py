import unittest
import json
import shutil
from pathlib import Path
from uuid import uuid4

from sososo import ArithmeticChallengeDetector, BotChallengeInspector, SOSOSO


def render_history(blocks):
    lines = []
    for block in blocks:
        message_lines = str(block["text"]).splitlines() or [""]
        lines.append(
            f"ID: {int(block['id'])} | {block['sender']} | Date: {block['date']} | Message: {message_lines[0]}"
        )
        lines.extend(message_lines[1:])
    return "\n".join(lines)


class FakeTransport:
    def __init__(self, histories, *, buttons_text: str = "", press_exception: BaseException | None = None):
        self.histories = list(histories)
        self.sent_messages = []
        self._history_index = 0
        self.buttons_text = buttons_text
        self.press_exception = press_exception
        self.pressed_buttons = []

    async def send_message(self, chat_id: str, message: str) -> str:
        self.sent_messages.append((chat_id, message))
        return "ok"

    async def get_history(self, chat_id: str, limit: int) -> str:
        if not self.histories:
            return ""
        if self._history_index >= len(self.histories):
            return self.histories[-1]
        history = self.histories[self._history_index]
        self._history_index += 1
        if isinstance(history, BaseException):
            raise history
        return history

    async def list_inline_buttons(self, chat_id: str, message_id: int) -> str:
        return self.buttons_text

    async def press_inline_button(self, chat_id: str, message_id: int, button_index: int) -> str:
        self.pressed_buttons.append((chat_id, message_id, button_index))
        if self.press_exception is not None:
            raise self.press_exception
        return "ok"


class ArithmeticChallengeDetectorTests(unittest.TestCase):
    def test_detects_basic_arithmetic_answers(self) -> None:
        detector = ArithmeticChallengeDetector()
        cases = {
            "6 + 10 = ?": "16",
            "9 - 4 = ?": "5",
            "7 x 8 = ?": "56",
            "12 ÷ 3 = ?": "4",
        }

        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                match = detector.detect(prompt)
                self.assertIsNotNone(match)
                self.assertEqual(match.answer, expected)


class SososoChallengeFlowTests(unittest.IsolatedAsyncioTestCase):
    def make_output_dir(self) -> str:
        return str(Path(".").resolve())

    def make_temp_output_dir(self) -> Path:
        temp_root = Path(".").resolve() / "tests" / "_tmp_runtime"
        temp_root.mkdir(parents=True, exist_ok=True)
        path = temp_root / f"case-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=False)
        return path

    async def test_verify_challenge_answer_recomputes_suggested_answer(self) -> None:
        challenge = BotChallengeInspector().detect_from_blocks(
            [
                {
                    "id": 50,
                    "sender": "Sender: @sososo",
                    "date": "2026-03-19 09:50:02",
                    "text": "6 + 10 = ?",
                }
            ]
        )
        self.assertIsNotNone(challenge)

        crawler = SOSOSO(
            FakeTransport([]),
            output_dir=self.make_output_dir(),
            poll_interval=0,
            max_polls_per_step=2,
        )
        verified_answer = crawler.verify_challenge_answer(challenge)

        self.assertEqual(verified_answer, "16")

    async def test_auto_solves_challenge_and_returns_result_page(self) -> None:
        histories = [
            render_history(
                [
                    {
                        "id": 100,
                        "sender": "Sender: @sososo",
                        "date": "2026-03-19 09:50:02",
                        "text": "6 + 10 = ?",
                    }
                ]
            ),
            render_history(
                [
                    {
                        "id": 101,
                        "sender": "Sender: @sososo",
                        "date": "2026-03-19 09:50:04",
                        "text": "关键词：`demo`\n当前第 1 页, 共 3 页\n[Result](https://example.com/1)",
                    }
                ]
            ),
        ]
        transport = FakeTransport(histories)

        crawler = SOSOSO(
            transport,
            output_dir=self.make_output_dir(),
            poll_interval=0,
            max_polls_per_step=3,
        )
        page_payload = await crawler.do_fetch_page("demo")

        self.assertEqual(transport.sent_messages, [("@sososo", "16")])
        self.assertEqual(page_payload["page"], 1)
        self.assertEqual(page_payload["total_pages"], 3)
        self.assertEqual(page_payload["items"], [{"title": "Result", "link": "https://example.com/1"}])

    async def test_auto_solve_fails_closed_when_bot_still_returns_challenge(self) -> None:
        histories = [
            render_history(
                [
                    {
                        "id": 100,
                        "sender": "Sender: @sososo",
                        "date": "2026-03-19 09:50:02",
                        "text": "6 + 10 = ?",
                    }
                ]
            ),
            render_history(
                [
                    {
                        "id": 101,
                        "sender": "Sender: @sososo",
                        "date": "2026-03-19 09:50:04",
                        "text": "6 + 10 = ?",
                    }
                ]
            ),
        ]
        transport = FakeTransport(histories)

        crawler = SOSOSO(
            transport,
            output_dir=self.make_output_dir(),
            poll_interval=0,
            max_polls_per_step=2,
        )
        with self.assertRaisesRegex(RuntimeError, "not solved successfully"):
            await crawler.do_fetch_page("demo")

        self.assertEqual(transport.sent_messages, [("@sososo", "16")])

    async def test_crawl_stops_when_bot_reports_no_more_information_after_next_page(self) -> None:
        page_one_history = render_history(
            [
                {
                    "id": 100,
                    "sender": "Sender: @sososo",
                    "date": "2026-03-19 09:50:02",
                    "text": "关键词：`demo`\n当前第 1 页, 共 9 页\n[Result](https://example.com/1)",
                }
            ]
        )
        no_more_history = render_history(
            [
                {
                    "id": 100,
                    "sender": "Sender: @sososo",
                    "date": "2026-03-19 09:50:02",
                    "text": "关键词：`demo`\n当前第 1 页, 共 9 页\n[Result](https://example.com/1)",
                },
                {
                    "id": 101,
                    "sender": "Sender: @sososo",
                    "date": "2026-03-19 09:50:05",
                    "text": "没有更多信息！",
                },
            ]
        )
        transport = FakeTransport(
            [page_one_history, no_more_history],
            buttons_text="[0] text='下一页', callback=yes",
        )

        output_dir = self.make_temp_output_dir()
        try:
            crawler = SOSOSO(
                transport,
                output_dir=str(output_dir),
                poll_interval=0,
                max_polls_per_step=2,
                batch_size=10,
            )
            result = await crawler.crawl("demo", max_page=5)

            self.assertEqual(result["pages_crawled"], [1])
            self.assertEqual(result["total_unique_items"], 1)
            self.assertEqual(len(result["batch_files"]), 1)
            self.assertEqual(transport.pressed_buttons, [("@sososo", 100, 0)])
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    async def test_crawl_flushes_partial_batch_when_interrupted(self) -> None:
        page_one_history = render_history(
            [
                {
                    "id": 100,
                    "sender": "Sender: @sososo",
                    "date": "2026-03-19 09:50:02",
                    "text": "关键词：`demo`\n当前第 1 页, 共 3 页\n[Result](https://example.com/1)",
                }
            ]
        )
        transport = FakeTransport(
            [page_one_history, KeyboardInterrupt()],
            buttons_text="[0] text='下一页', callback=yes",
        )

        output_dir = self.make_temp_output_dir()
        try:
            crawler = SOSOSO(
                transport,
                output_dir=str(output_dir),
                poll_interval=0,
                max_polls_per_step=2,
                batch_size=10,
            )

            with self.assertRaises(KeyboardInterrupt):
                await crawler.crawl("demo", max_page=3)

            batch_root = output_dir / "batches"
            batch_files = list(batch_root.glob("*/*.json"))
            self.assertEqual(len(batch_files), 1)

            payload = json.loads(batch_files[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["total_items"], 1)
            self.assertEqual(payload["items"], [{"title": "Result", "link": "https://example.com/1"}])
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)
