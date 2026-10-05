"""Tests du vrai Server Module avec Users/Data Tables simulés, sans réseau.

Ces doubles ne simulent pas l'isolation transactionnelle du moteur Anvil.
"""
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class FakeRow(dict):
    def __init__(self, valeurs):
        super().__init__(valeurs)
        self.writes = 0

    def update(self, **valeurs):
        self.writes += 1
        super().update(valeurs)


class FakeTable:
    def __init__(self):
        self.rows = []
        self.queries = []

    def get(self, **filters):
        # Toute lecture du registre doit être limitée au user courant.
        if set(filters) != {"search_id", "user"}:
            raise AssertionError("Lecture non limitée à l'utilisateur")
        self.queries.append(filters)
        matches = [row for row in self.rows if all(row[key] == value for key, value in filters.items())]
        if len(matches) > 1:
            raise RuntimeError("Registre dupliqué")
        return matches[0] if matches else None

    def add_row(self, **valeurs):
        row = FakeRow(valeurs)
        self.rows.append(row)
        return row


class TestsControlRecherches(unittest.TestCase):
    def setUp(self):
        self.table = FakeTable()
        self.user = object()
        anvil = ModuleType("anvil")
        users = ModuleType("anvil.users")
        server = ModuleType("anvil.server")
        tables = ModuleType("anvil.tables")
        users.get_user = Mock(side_effect=lambda: self.user)
        self.transaction_functions = []

        def transaction(function):
            self.transaction_functions.append(function.__name__)
            return function

        tables.in_transaction = transaction
        tables.app_tables = SimpleNamespace(bg_task_ctrl=self.table)
        server.callable = lambda function: function
        anvil.users, anvil.server, anvil.tables = users, server, tables
        modules = {"anvil": anvil, "anvil.users": users, "anvil.server": server, "anvil.tables": tables}
        path = Path(__file__).resolve().parents[1] / "server_code/Control_recherches.py"
        spec = importlib.util.spec_from_file_location("control_under_test", path)
        self.api = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", modules):
            spec.loader.exec_module(self.api)

    def register(self):
        return self.api.enregistrer_recherche_rao("rao-1")

    def running(self):
        self.register()
        return self.api.marquer_recherche_en_cours("rao-1")

    def cancel(self):
        return self.api.demander_annulation_recherche_rao("rao-1")

    def finish(self, issue):
        return self.api.finaliser_recherche_rao("rao-1", issue)

    def test_creation_registered(self):
        result = self.register()
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "registered")
        self.assertFalse(result["cancel_requested"])
        self.assertFalse(result["finished"])
        self.assertIsNotNone(result["created_at"].tzinfo)
        for key in ("started_at", "cancel_requested_at", "finished_at", "background_task_id"):
            self.assertIsNone(result[key])

    def test_creation_repetee(self):
        first = self.register()
        self.assertEqual(first, self.register())
        self.assertEqual(len(self.table.rows), 1)

    def test_registered_running(self):
        self.assertEqual(self.running()["status"], "running")

    def test_started_at_une_fois(self):
        first = self.running()["started_at"]
        self.assertIsNotNone(first)
        self.assertEqual(first, self.api.marquer_recherche_en_cours("rao-1")["started_at"])

    def test_registered_annulation(self):
        self.register()
        result = self.cancel()
        self.assertEqual(result["status"], "cancellation_requested")
        self.assertTrue(result["cancel_requested"])
        self.assertFalse(result["finished"])

    def test_running_annulation(self):
        self.running()
        self.assertEqual(self.cancel()["status"], "cancellation_requested")

    def test_double_annulation(self):
        self.register()
        self.assertEqual(self.cancel(), self.cancel())

    def test_cancel_requested_at_une_fois(self):
        self.register()
        first = self.cancel()["cancel_requested_at"]
        self.assertIsNotNone(first)
        self.assertEqual(first, self.cancel()["cancel_requested_at"])

    def test_annulation_avant_demarrage(self):
        self.register()
        cancelled = self.cancel()
        result = self.api.marquer_recherche_en_cours("rao-1", "task-1")
        self.assertEqual(result["status"], "cancellation_requested")
        self.assertEqual(result["cancel_requested_at"], cancelled["cancel_requested_at"])
        self.assertIsNotNone(result["started_at"])
        self.assertEqual(result["background_task_id"], "task-1")

    def assert_terminal_immutable(self, issue):
        self.running()
        first = self.finish(issue)
        writes = self.table.rows[0].writes
        self.assertEqual(first, self.register())
        self.assertEqual(first, self.cancel())
        self.assertEqual(first, self.api.marquer_recherche_en_cours("rao-1", "late-task"))
        for other in ("completed", "cancelled", "failed"):
            self.assertEqual(first, self.finish(other))
        self.assertEqual(writes, self.table.rows[0].writes)
        self.assertTrue(first["finished"])

    def test_completed_immuable(self):
        self.assert_terminal_immutable("completed")

    def test_failed_immuable(self):
        self.assert_terminal_immutable("failed")

    def test_cancelled_immuable(self):
        self.assert_terminal_immutable("cancelled")

    def test_annulation_puis_completed(self):
        self.register()
        self.cancel()
        self.assertEqual(self.finish("completed")["status"], "cancelled")

    def test_running_completed(self):
        self.running()
        result = self.finish("completed")
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["cancel_requested"])

    def test_running_failed(self):
        self.running()
        self.assertEqual(self.finish("failed")["status"], "failed")

    def test_running_cancelled(self):
        self.running()
        self.assertEqual(self.finish("cancelled")["status"], "cancelled")

    def test_search_id_inconnu(self):
        calls = (lambda: self.api.obtenir_etat_recherche_rao("absent"),
                 lambda: self.api.marquer_recherche_en_cours("absent"),
                 lambda: self.api.demander_annulation_recherche_rao("absent"),
                 lambda: self.api.finaliser_recherche_rao("absent", "completed"))
        for call in calls:
            self.assertEqual(call()["error"], "not_found_or_not_authorized")
        self.assertEqual(self.table.rows, [])

    def test_utilisateur_different(self):
        self.running()
        original = dict(self.table.rows[0])
        self.user = object()
        for call in (self.cancel, lambda: self.finish("failed"),
                     lambda: self.api.obtenir_etat_recherche_rao("rao-1"),
                     lambda: self.api.marquer_recherche_en_cours("rao-1", "foreign")):
            self.assertEqual(call()["error"], "not_found_or_not_authorized")
        self.assertEqual(dict(self.table.rows[0]), original)
        # L'identité est le couple user/search_id, jamais le seul search_id.
        self.assertEqual(self.register()["status"], "registered")
        self.assertEqual(len(self.table.rows), 2)
        self.assertEqual(dict(self.table.rows[0]), original)

    def test_background_task_id(self):
        self.register()
        first = self.api.marquer_recherche_en_cours("rao-1", "task-1")
        self.assertEqual(first["background_task_id"], "task-1")
        self.assertEqual(first, self.api.marquer_recherche_en_cours("rao-1"))

    def test_background_task_id_terminal(self):
        self.running()
        first = self.finish("completed")
        self.assertEqual(first, self.api.marquer_recherche_en_cours("rao-1", "task-2"))

    def test_finalisation_repetee(self):
        self.running()
        first = self.finish("failed")
        self.assertIsNotNone(first["finished_at"])
        self.assertEqual(first, self.finish("failed"))
        self.assertEqual(first, self.finish("completed"))

    def test_enregistrement_tardif_preserve_annulation(self):
        self.register()
        first = self.cancel()
        self.assertEqual(first, self.register())

    def test_annulation_puis_failed(self):
        self.register()
        self.cancel()
        result = self.finish("failed")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["cancel_requested"])

    def test_utilisateur_non_connecte(self):
        self.user = None
        for call in (self.register, self.cancel, lambda: self.finish("completed"),
                     lambda: self.api.marquer_recherche_en_cours("rao-1"),
                     lambda: self.api.obtenir_etat_recherche_rao("rao-1")):
            self.assertEqual(call()["error"], "authentication_required")
        self.assertEqual(self.table.queries, [])
        self.assertEqual(self.table.rows, [])

    def test_arguments_invalides(self):
        for value in (None, "", "   ", 42, []):
            self.assertEqual(self.api.enregistrer_recherche_rao(value)["error"], "invalid_search_id")
        self.register()
        first = dict(self.table.rows[0])
        self.assertEqual(self.finish("running")["error"], "invalid_issue")
        self.assertEqual(self.api.marquer_recherche_en_cours("rao-1", 42)["error"], "invalid_background_task_id")
        self.assertEqual(dict(self.table.rows[0]), first)

    def test_etat_structure_sans_row_user(self):
        self.running()
        state = self.api.obtenir_etat_recherche_rao("rao-1")
        self.assertEqual(state["status"], "running")
        self.assertNotIn("user", state)
        self.assertIs(type(state), dict)
        self.assertFalse(state["finished"])

    def test_toutes_fonctions_transactionnelles(self):
        self.assertEqual(set(self.transaction_functions), {
            "enregistrer_recherche_rao", "marquer_recherche_en_cours",
            "demander_annulation_recherche_rao", "obtenir_etat_recherche_rao",
            "finaliser_recherche_rao"})

    def test_erreur_table_propagee(self):
        with patch.object(self.table, "get", side_effect=RuntimeError("Panne table")):
            with self.assertRaisesRegex(RuntimeError, "Panne table"):
                self.register()

    def test_etat_corrompu_propage(self):
        self.register()
        self.table.rows[0]["status"] = "unexpected"
        with self.assertRaisesRegex(ValueError, "État RAO invalide"):
            self.cancel()


if __name__ == "__main__":
    unittest.main()
