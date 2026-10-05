"""Tests du diagnostic temporaire avec contexte Anvil simulé, sans réseau."""
from types import SimpleNamespace
import unittest

import test_control_recherches as support


class TestsDiagnosticOrigineAppelRAO(unittest.TestCase):
    def setUp(self):
        self.support = support.TestsControlRecherches()
        self.support.setUp()
        self.api = self.support.api
        self.server = self.api.anvil.server

    def test_navigateur(self):
        self.server.context = SimpleNamespace(
            type="server_module",
            remote_caller=SimpleNamespace(type="browser", is_trusted=False),
            client=SimpleNamespace(type="browser"),
        )
        self.assertEqual(self.api.diagnostic_origine_appel_rao(), {
            "context_type": "server_module",
            "remote_caller_type": "browser",
            "remote_caller_is_trusted": False,
            "client_type": "browser",
            "user_present": True,
        })
        self.assertEqual(self.support.table.queries, [])
        self.assertEqual(self.support.table.rows, [])

    def test_uplink_trusted_sans_utilisateur(self):
        self.support.user = None
        self.server.context = SimpleNamespace(
            type="server_module",
            remote_caller=SimpleNamespace(type="uplink", is_trusted=True),
            client=SimpleNamespace(type="background_task"),
        )
        self.assertEqual(self.api.diagnostic_origine_appel_rao(), {
            "context_type": "server_module",
            "remote_caller_type": "uplink",
            "remote_caller_is_trusted": True,
            "client_type": "background_task",
            "user_present": False,
        })
        self.assertEqual(self.support.table.queries, [])
        self.assertEqual(self.support.table.rows, [])

    def test_proprietes_absentes(self):
        self.support.user = None
        attendu = {
            "context_type": None,
            "remote_caller_type": None,
            "remote_caller_is_trusted": None,
            "client_type": None,
            "user_present": False,
        }
        # Contexte absent, None, incomplet, ou sous-objets sans propriétés.
        for contexte in (None, SimpleNamespace(), SimpleNamespace(
                remote_caller=SimpleNamespace(), client=SimpleNamespace())):
            with self.subTest(contexte=contexte):
                self.server.context = contexte
                self.assertEqual(self.api.diagnostic_origine_appel_rao(), attendu)
        del self.server.context
        self.assertEqual(self.api.diagnostic_origine_appel_rao(), attendu)
        self.assertEqual(self.support.table.queries, [])
        self.assertEqual(self.support.table.rows, [])


if __name__ == "__main__":
    unittest.main()
