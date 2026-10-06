"""Ordre commit/signal et contrat public, avec file Background Task simulée."""
from pathlib import Path
import unittest
from unittest.mock import patch

import test_control_recherches as support


class TestsSignalAnnulation(unittest.TestCase):
    def setUp(self):
        self.support = support.TestsControlRecherches()
        self.support.setUp()
        self.api = self.support.api
        self.server = self.api.anvil.server
        self.support.running()
        self.row = self.support.table.rows[0]
        self.support.events.clear()
        self.queue = []
        self.server.launch_background_task.side_effect = self.enqueue

    def enqueue(self, task_name, search_id):
        self.assertFalse(self.support.transaction_active)
        self.assertEqual(self.row["status"], "cancellation_requested")
        self.assertIsNotNone(self.row["cancel_requested_at"])
        self.support.events.append("enqueue")
        self.queue.append((task_name, search_id))

    def execute_signal(self):
        task_name, search_id = self.queue.pop(0)
        return getattr(self.api, task_name)(search_id)

    def test_other_user_and_anonymous_no_signal(self):
        for user in (object(), None):
            self.support.user = user
            self.assertFalse(self.support.cancel()["ok"])
        self.server.launch_background_task.assert_not_called()
        self.server.call.assert_not_called()
        self.assertEqual(self.row["status"], "running")

    def test_write_failure_no_signal(self):
        with patch.object(self.row, "update", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                self.support.cancel()
        self.server.launch_background_task.assert_not_called()
        self.server.call.assert_not_called()

    def test_commit_failure_no_signal(self):
        self.support.commit_error = RuntimeError("commit failed")
        with self.assertRaises(RuntimeError):
            self.support.cancel()
        self.assertEqual(self.row["status"], "running")
        self.server.launch_background_task.assert_not_called()
        self.server.call.assert_not_called()

    def test_signal_after_commit_and_return(self):
        def signal(name, search_id):
            self.assertFalse(self.support.transaction_active)
            self.assertEqual(self.row["status"], "cancellation_requested")
            self.support.events.append("signal")
            return {"ok": True, "signaled": True}
        self.server.call.side_effect = signal
        result = self.support.cancel()
        self.assertTrue(result["ok"])
        self.server.call.assert_not_called()
        self.assertEqual(self.support.events, ["commit", "enqueue"])
        self.assertEqual(self.execute_signal(), "sent")
        self.assertEqual(self.support.events, ["commit", "enqueue", "signal"])
        self.server.call.assert_called_once_with("signaler_annulation_recherche_locale", "rao-1")

    def test_enqueue_failure_keeps_durable_success(self):
        self.server.launch_background_task.side_effect = RuntimeError("unavailable")
        self.assertTrue(self.support.cancel()["ok"])
        self.assertEqual(self.row["status"], "cancellation_requested")
        self.server.call.assert_not_called()

    def test_external_errors_keep_durable_success(self):
        for error in (RuntimeError("unknown callable"), ConnectionError("disconnected"), TimeoutError("timeout")):
            with self.subTest(error=error):
                result = self.support.cancel()
                before = dict(self.row)
                self.server.call.side_effect = error
                self.assertEqual(self.execute_signal(), "failed")
                self.assertTrue(result["ok"])
                self.assertEqual(dict(self.row), before)

    def test_invalid_responses_and_not_active(self):
        for response, diagnostic in ((None, "failed"), ({}, "failed"),
                                     ({"ok": False, "signaled": True}, "failed"),
                                     ({"ok": True, "signaled": 1}, "failed"),
                                     ({"ok": True}, "failed"),
                                     ({"ok": True, "signaled": False}, "not_active")):
            with self.subTest(response=response):
                result = self.support.cancel()
                before = dict(self.row)
                self.server.call.return_value = response
                self.assertEqual(self.execute_signal(), diagnostic)
                self.assertTrue(result["ok"])
                self.assertEqual(dict(self.row), before)

    def test_terminal_states_no_signal(self):
        for status in ("completed", "failed", "cancelled"):
            self.row["status"] = status
            before = dict(self.row)
            self.assertEqual(self.support.cancel()["status"], status)
            self.assertEqual(dict(self.row), before)
        self.server.launch_background_task.assert_not_called()
        self.server.call.assert_not_called()

    def test_double_request_preserves_contract_and_date(self):
        first = self.support.cancel()
        second = self.support.cancel()
        self.assertEqual(first, second)
        self.assertEqual(self.server.launch_background_task.call_count, 2)
        self.assertEqual(first, self.api.obtenir_etat_recherche_rao("rao-1"))
        self.assertEqual(set(first), {"ok", "search_id", "status", "cancel_requested", "finished",
                                     "created_at", "started_at", "cancel_requested_at", "finished_at",
                                     "background_task_id"})

    def test_no_new_browser_callable_or_client_signal(self):
        self.assertIn("demander_annulation_recherche_rao", self.support.callable_names)
        self.assertNotIn("_enregistrer_annulation_recherche_rao", self.support.callable_names)
        self.assertNotIn("_signaler_annulation_recherche_rao", self.support.callable_names)
        self.assertNotIn("signaler_annulation_recherche_locale", self.support.callable_names)
        root = Path(__file__).resolve().parents[1]
        for path in (root / "client_code").rglob("*.py"):
            self.assertNotIn("signaler_annulation_recherche_locale", path.read_text())
