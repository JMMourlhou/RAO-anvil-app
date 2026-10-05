"""Intégration CPV/registre avec méthodes réelles et transports Anvil simulés."""
import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid

import test_search_recherche_cpv as client_support
import test_control_recherches as server_support


class TestsSearchIdCPV(unittest.TestCase):
    def setUp(self):
        client = client_support.TestsRechercheCPV()
        client.setUp()
        self.form = client.form
        self.espace = client.espace
        self.uuid4 = Mock(side_effect=[uuid.UUID(int=1), uuid.UUID(int=2)])
        self.espace["uuid"] = SimpleNamespace(uuid4=self.uuid4)
        self.form.actualiser_bouton_veille_cpv = Mock()
        self.server = self.espace["anvil"].server.call
        registre = server_support.TestsControlRecherches()
        registre.setUp()
        self.table = registre.table
        self.api = registre.api
        self.task = Mock()
        self.server.side_effect = self.transport

    def transport(self, nom, *args, **kwargs):
        if nom == "enregistrer_recherche_rao":
            return self.api.enregistrer_recherche_rao(*args, **kwargs)
        if nom == "lancer_recherche_cpv_background":
            self.assertEqual(self.table.rows[-1]["search_id"], kwargs["search_id"])
            return self.task
        if nom == "lancer_recherche_multi_sources_background":
            return self.task
        raise AssertionError("Appel inattendu : " + nom)

    def test_generation_une_seule_fois(self):
        self.form.lancer_recherche()
        self.uuid4.assert_called_once_with()
        self.assertEqual(self.form.search_id, str(uuid.UUID(int=1)))
        self.assertIs(self.form.task_recherche, self.task)

    def test_meme_identifiant_inscription_et_lanceur(self):
        self.form.lancer_recherche()
        inscription, lancement = self.server.call_args_list
        self.assertEqual(inscription.args, ("enregistrer_recherche_rao", self.form.search_id))
        self.assertEqual(lancement.args, ("lancer_recherche_cpv_background",))
        self.assertEqual(lancement.kwargs["search_id"], self.form.search_id)
        self.assertEqual(len(self.table.rows), 1)
        self.assertEqual(self.table.rows[0]["status"], "registered")

    def test_refus_empeche_lancement_et_reactive_avant_message(self):
        self.server.side_effect = None
        self.server.return_value = {"ok": False, "message": "Détail interne"}
        def message(*args, **kwargs):
            self.assertFalse(self.form._recherche_en_cours)
            self.assertTrue(self.form.f.navigation_link_search_go.enabled)
            self.assertEqual(args, ("Impossible de lancer la recherche CPV.",))
        self.espace["afficher_information"].side_effect = message
        self.form.lancer_recherche()
        self.server.assert_called_once_with("enregistrer_recherche_rao", self.form.search_id)
        self.assertIsNone(self.form.task_recherche)
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)
        self.assertTrue(self.form.bloc_selecteur_cpv_complet.visible)
        self.assertEqual(self.table.rows, [])
        self.espace["afficher_information"].assert_called_once()

    def test_nouvelle_recherche_nouvel_identifiant(self):
        self.form.lancer_recherche()
        first = self.form.search_id
        self.form.deverrouiller_recherche()
        self.form.lancer_recherche()
        self.assertNotEqual(first, self.form.search_id)
        self.assertEqual(self.uuid4.call_count, 2)
        self.assertEqual(len(self.table.rows), 2)
        self.assertEqual(self.table.rows[0]["search_id"], first)
        self.assertEqual(self.table.rows[1]["search_id"], self.form.search_id)

    def test_classique_sans_uuid_ni_inscription(self):
        self.form.cpv_selectionnes = []
        self.form.text_box_mots_obligatoires_cpv.text = "formation"
        self.form.lancer_recherche()
        self.uuid4.assert_not_called()
        self.server.assert_called_once()
        call = self.server.call_args
        self.assertEqual(call.args, ("lancer_recherche_multi_sources_background",))
        self.assertNotIn("search_id", call.kwargs)
        self.assertEqual(self.table.rows, [])

    def test_arret_garde_appel_task_killer_seul(self):
        self.form.lancer_recherche()
        task = self.form.task_recherche
        self.server.reset_mock()
        self.server.side_effect = None
        self.server.return_value = {"ok": True}
        self.form.f.activer_bouton_arret = Mock()
        self.form.f.revenir_menu_apres_arret = Mock()
        result = self.form.annuler_recherche_depuis_menu()
        self.assertTrue(result["ok"])
        self.server.assert_called_once_with("task_killer", task)
        self.assertTrue(self.form._recherche_abandonnee)
        self.assertEqual(self.table.rows[0]["status"], "registered")

    def test_exception_inscription_deverrouille_et_remonte(self):
        self.server.side_effect = RuntimeError("Panne simulée")
        with self.assertRaisesRegex(RuntimeError, "Panne simulée"):
            self.form.lancer_recherche()
        self.assertFalse(self.form._recherche_en_cours)
        self.assertIsNone(self.form.task_recherche)
        self.server.assert_called_once()

    def test_retour_invalide_ne_lance_pas(self):
        self.server.side_effect = None
        self.server.return_value = {"ok": 1}
        with self.assertRaisesRegex(ValueError, "Réponse d'inscription"):
            self.form.lancer_recherche()
        self.assertFalse(self.form._recherche_en_cours)
        self.server.assert_called_once()

    def test_saisie_invalide_ne_genere_pas(self):
        self.form.text_box_nb_jours.text = "abc"
        self.form.lancer_recherche()
        self.uuid4.assert_not_called()
        self.server.assert_not_called()

    def test_methodes_hors_perimetre_inchangees(self):
        source = Path(__file__).resolve().parents[1] / "client_code/search/__init__.py"
        classe = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef))
        attendu = BASELINE_METHODES
        actuel = {n.name: hashlib.sha256(ast.dump(n).encode()).hexdigest()
                  for n in classe.body if isinstance(n, ast.FunctionDef) and n.name in attendu}
        self.assertEqual(actuel, attendu)


# Empreintes AST avant intégration : classique, Arrêt, timer et historique.
BASELINE_METHODES = {'abandonner_recherche': '5bed882929eaae2bd26c51ec69f865741de9370a7edcab5c4118f5050e807cc5',
 'annuler_recherche_depuis_menu': 'c0eaf241574f0a851d80d8e2e20853503c9136e023de874cc6e7b3d3cdc850e5',
 'envoyer_annulation_recherche': '55d5b59f840aa5568e73a33f3c0bfda07c926dc0253b550aefed698b6d60ef07',
 'lancer_recherche': '1af49757712e66aaaa93fcfcc2f361a4a18fc5fce83b690e16dcfcc307bd0009',
 'sauvegarder_derniere_recherche': 'b2a22d5a2981dc1d060260408be1c1e874c6e709f24d1bbf1de07bcfb9c78b94',
 'timer_recherche_progress_tick': 'bac9a6475f8bae52ead5958843678d27f2254544231a5026547676c677d3dc4e'}

if __name__ == "__main__":
    unittest.main()
