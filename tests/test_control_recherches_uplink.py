"""API Uplink réelle, contexte et Data Tables simulés ; aucun appel réseau."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_control_recherches as support


class TestsControlRecherchesUplink(unittest.TestCase):
    def setUp(self):
        self.preparation = support.TestsControlRecherches()
        self.preparation.setUp()
        self.api = self.preparation.api
        self.table = self.preparation.table
        self.api.enregistrer_recherche_rao("rao-1")
        self.table.queries.clear()
        self.table.search = Mock(side_effect=self.search)
        self.api.anvil.server.context = SimpleNamespace(
            type="server_module",
            remote_caller=SimpleNamespace(type="uplink", is_trusted=True),
            client=SimpleNamespace(type="background_task"),
        )
        # Toute dépendance à la session utilisateur doit faire échouer le test.
        self.api.anvil.users.get_user = Mock(side_effect=AssertionError("get_user interdit pour Uplink"))

    def search(self, **filters):
        self.assertEqual(filters, {"search_id": "rao-1"})
        return iter(row for row in self.table.rows if row["search_id"] == filters["search_id"])

    def start(self, task_id=None):
        return self.api.marquer_recherche_en_cours_uplink("rao-1", task_id)

    def state(self):
        return self.api.obtenir_etat_recherche_rao_uplink("rao-1")

    def finish(self, issue):
        return self.api.finaliser_recherche_rao_uplink("rao-1", issue)

    def request_cancellation(self):
        self.table.rows[0].update(status="cancellation_requested", cancel_requested_at="date-annulation")

    def assert_refused(self):
        before = dict(self.table.rows[0])
        for call in (self.start, self.state, lambda: self.finish("completed")):
            self.assertEqual(call(), {"ok": False, "code": "uplink_not_authorized"})
        self.table.search.assert_not_called()
        self.assertEqual(self.table.queries, [])
        self.assertEqual(dict(self.table.rows[0]), before)
        self.api.anvil.users.get_user.assert_not_called()

    def test_uplink_trusted_autorise_sans_user(self):
        self.assertTrue(self.state()["ok"])
        self.assertEqual(self.start()["status"], "running")
        self.assertEqual(self.finish("completed")["status"], "completed")
        self.api.anvil.users.get_user.assert_not_called()

    def test_browser_refuse(self):
        self.api.anvil.server.context.remote_caller = SimpleNamespace(type="browser", is_trusted=False)
        self.assert_refused()

    def test_uplink_non_trusted_refuse(self):
        self.api.anvil.server.context.remote_caller.is_trusted = False
        self.assert_refused()

    def test_remote_caller_absent_refuse(self):
        for context in (None, SimpleNamespace(), SimpleNamespace(remote_caller=None)):
            with self.subTest(context=context):
                self.api.anvil.server.context = context
                self.assert_refused()

    def test_autres_types_et_confiance_ambigue_refuses(self):
        for caller in (SimpleNamespace(type="server_module", is_trusted=True),
                       SimpleNamespace(type="client_uplink", is_trusted=True),
                       SimpleNamespace(type="background_task", is_trusted=True),
                       SimpleNamespace(type="uplink", is_trusted=1),
                       SimpleNamespace(type="uplink"), SimpleNamespace()):
            with self.subTest(caller=caller):
                self.api.anvil.server.context.remote_caller = caller
                self.assert_refused()

    def test_search_id_inconnu(self):
        self.table.rows.clear()
        for call in (self.start, self.state, lambda: self.finish("completed")):
            self.assertEqual(call(), {"ok": False, "code": "not_found"})
        self.assertEqual(self.table.rows, [])

    def test_search_id_ambigu(self):
        autre = dict(self.table.rows[0])
        autre["user"] = object()
        self.table.add_row(**autre)
        before = [dict(row) for row in self.table.rows]
        for call in (self.start, self.state, lambda: self.finish("failed")):
            self.assertEqual(call(), {"ok": False, "code": "ambiguous_search_id"})
        self.assertEqual([dict(row) for row in self.table.rows], before)
        self.assertTrue(all(row.writes == 0 for row in self.table.rows))

    def test_registered_running(self):
        result = self.start()
        self.assertEqual(result["status"], "running")
        self.assertIsNotNone(result["started_at"])
        self.assertFalse(result["finished"])

    def test_cancellation_requested_inchange(self):
        self.request_cancellation()
        result = self.start("task-1")
        self.assertEqual(result["status"], "cancellation_requested")
        self.assertTrue(result["cancel_requested"])
        self.assertEqual(result["cancel_requested_at"], "date-annulation")
        self.assertEqual(result["background_task_id"], "task-1")

    def test_etats_terminaux_immuables(self):
        for terminal in ("completed", "cancelled", "failed"):
            with self.subTest(terminal=terminal):
                self.setUp()
                self.start("original-task")
                original = self.finish(terminal)
                writes = self.table.rows[0].writes
                self.assertEqual(self.start("late-task"), original)
                for issue in ("completed", "cancelled", "failed"):
                    self.assertEqual(self.finish(issue), original)
                self.assertEqual(self.state(), original)
                self.assertEqual(self.table.rows[0].writes, writes)

    def test_finalisation_completed(self):
        self.start()
        result = self.finish("completed")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["finished"])
        self.assertIsNotNone(result["finished_at"])

    def test_finalisation_failed(self):
        self.start()
        self.assertEqual(self.finish("failed")["status"], "failed")

    def test_finalisation_cancelled(self):
        self.start()
        self.assertEqual(self.finish("cancelled")["status"], "cancelled")

    def test_annulation_puis_completed_devient_cancelled(self):
        self.request_cancellation()
        self.assertEqual(self.finish("completed")["status"], "cancelled")

    def test_annulation_puis_failed_reste_failed(self):
        self.request_cancellation()
        result = self.finish("failed")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["cancel_requested_at"], "date-annulation")

    def test_background_task_id_memorise(self):
        result = self.start("task-1")
        self.assertEqual(result["background_task_id"], "task-1")
        self.assertEqual(self.start()["background_task_id"], "task-1")

    def test_idempotence_dates(self):
        first = self.start("task-1")
        self.assertEqual(first, self.start("task-1"))
        final = self.finish("completed")
        self.assertEqual(final, self.finish("completed"))
        self.assertEqual(final["started_at"], first["started_at"])

    def test_arguments_invalides_sans_lecture_table(self):
        for value in (None, "", "  ", 123):
            for call in (lambda: self.api.obtenir_etat_recherche_rao_uplink(value),
                         lambda: self.api.marquer_recherche_en_cours_uplink(value),
                         lambda: self.api.finaliser_recherche_rao_uplink(value, "completed")):
                self.assertEqual(call(), {"ok": False, "code": "invalid_search_id"})
        self.assertEqual(self.finish("running"), {"ok": False, "code": "invalid_issue"})
        self.assertEqual(self.start(42), {"ok": False, "code": "invalid_background_task_id"})
        self.table.search.assert_not_called()

    def test_erreur_table_propagee(self):
        self.table.search.side_effect = RuntimeError("Panne table")
        with self.assertRaisesRegex(RuntimeError, "Panne table"):
            self.state()

    def test_etat_sans_proprietaire(self):
        result = self.state()
        self.assertNotIn("user", result)
        self.assertEqual(result["search_id"], "rao-1")


if __name__ == "__main__":
    unittest.main()
