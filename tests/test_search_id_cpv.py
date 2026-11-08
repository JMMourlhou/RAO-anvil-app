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

    def test_arret_transmet_identifiant_au_registre(self):
        self.form.lancer_recherche()
        search_id = self.form.search_id
        self.server.reset_mock()
        self.server.side_effect = None
        self.server.return_value = {"ok": True}
        self.form.f.activer_bouton_arret = Mock()
        self.form.f.revenir_menu_apres_arret = Mock()
        result = self.form.annuler_recherche_depuis_menu()
        self.assertTrue(result["ok"])
        self.server.assert_called_once_with("demander_annulation_recherche_rao", search_id)
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


# Empreintes des parcours hors correction TED 5H, version initiale 6542e0b381ce.
# Le timer et la sauvegarde sont couverts par les tests métier de collecte :
# ils font partie du périmètre autorisé et ne sont donc pas figés ici.
BASELINE_METHODES = {
    'annuler_recherche_depuis_menu': '110df51976e0ba7e548d31e0191aeaae54541383c4e0eacaf16813b9c067f8bd',
    'envoyer_annulation_recherche': '63fd4819dcaf63d7efe1a5174b94a0f3b85d769a0ff28d734fe546b78f3e5d7a',
    'abandonner_recherche': '31cc3988994e69895c9c7575a2fe208bbd3752606bfa8ef4b940b9c956fd69e6',
    'lancer_recherche': 'b9f5222c01b48e35848654cb7b5b5abbf516f503abfed09abe4ac5d025d78a92',
}

if __name__ == "__main__":
    unittest.main()
