import argparse
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "discrawl_query.py"
spec = importlib.util.spec_from_file_location("discrawl_query", SCRIPT_PATH)
discrawl_query = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = discrawl_query
spec.loader.exec_module(discrawl_query)


class ParseHelpersTests(unittest.TestCase):
    def test_parse_key_value_lines(self):
        parsed = discrawl_query.parse_key_value_lines("config=ok\nfts=ok\n")
        self.assertEqual(parsed, {"config": "ok", "fts": "ok"})

    def test_parse_table(self):
        text = (
            "GUILD                USER                NAME              DISPLAY       PROFILE\n"
            "147  408  asynchronous0805  Asynchronous\n"
        )
        rows = discrawl_query.parse_table(text)
        self.assertEqual(rows[0]["guild"], "147")
        self.assertEqual(rows[0]["name"], "asynchronous0805")
        self.assertEqual(rows[0]["display"], "Asynchronous")
        self.assertEqual(rows[0]["profile"], "")

    def test_parse_member_show(self):
        text = (
            "guild=147\n"
            "user=408\n"
            "username=asynchronous0805\n"
            "display=Asynchronous\n"
            "\n"
            "Recent messages:\n"
            "[cron] 2026-04-11T14:53:08Z\n"
            "thanks, choom\n"
        )
        parsed = discrawl_query.parse_member_show(text)
        self.assertEqual(parsed["username"], "asynchronous0805")
        self.assertEqual(parsed["recent_messages"][0]["channel"], "cron")
        self.assertEqual(parsed["recent_messages"][0]["content"], "thanks, choom")


class CommandHandlerTests(unittest.TestCase):
    def make_result(self, stdout="", stderr="", returncode=0):
        return argparse.Namespace(stdout=stdout, stderr=stderr, returncode=returncode)

    def test_handle_search_uses_json_and_returns_items(self):
        args = argparse.Namespace(
            binary="discrawl",
            guild=None,
            channel="cron",
            author=None,
            limit=5,
            include_empty=False,
            query="allowlist",
        )
        result = self.make_result(stdout='[{"channel_name": "cron"}]')
        with mock.patch.object(discrawl_query, "run_discrawl", return_value=result) as run_discrawl:
            payload = discrawl_query.handle_search(args)
        run_discrawl.assert_called_once_with(
            "discrawl",
            ["search", "--channel", "cron", "--limit", "5", "allowlist"],
            json_output=True,
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["channel_name"], "cron")

    def test_handle_member_search_parses_table(self):
        args = argparse.Namespace(binary="discrawl", query="Asynchronous")
        result = self.make_result(
            stdout=(
                "GUILD  USER  NAME  DISPLAY  PROFILE\n"
                "147  408  asynchronous0805  Asynchronous\n"
            )
        )
        with mock.patch.object(discrawl_query, "run_discrawl", return_value=result):
            payload = discrawl_query.handle_member_search(args)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["display"], "Asynchronous")

    def test_handle_status_parses_key_values(self):
        args = argparse.Namespace(binary="discrawl")
        result = self.make_result(stdout="messages=4135\nlast_sync=2026-04-12T12:36:08Z\n")
        with mock.patch.object(discrawl_query, "run_discrawl", return_value=result):
            payload = discrawl_query.handle_status(args)
        self.assertEqual(payload["result"]["messages"], "4135")

    def test_resolve_binary_prefers_explicit(self):
        self.assertEqual(discrawl_query.resolve_binary("/tmp/discrawl"), "/tmp/discrawl")

    def test_require_success_raises_on_failure(self):
        with self.assertRaises(discrawl_query.DiscrawlError):
            discrawl_query.require_success(self.make_result(returncode=1, stderr="boom"), ["search"])


if __name__ == "__main__":
    unittest.main()
