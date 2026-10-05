"""Parcours d'arrêt search/Menu, avec serveur et DOM simulés, sans réseau."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_search_recherche_cpv as support


def charger_menu():
    """Charge les méthodes réelles de Menu sans initialisation Anvil."""
    source = Path(__file__).resolve().parents[1] / "client_code/Menu/__init__.py"
    arbre = ast.parse(source.read_text())
    classe = next(n for n in arbre.body if isinstance(n, ast.ClassDef))
    methodes = [n for n in classe.body if isinstance(n, ast.FunctionDef) and n.name != "__init__"]
    for methode in methodes:
        methode.decorator_list = []
    classe_test = ast.ClassDef(name="Menu", bases=[], keywords=[], body=methodes, decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[classe_test], type_ignores=[]))
    espace = {"alert": Mock(), "get_dom_node": lambda composant: composant.node}
    exec(compile(module, str(source), "exec"), espace)
    return espace


class TestsAnnulation(unittest.TestCase):
    def setUp(self):
        preparation = support.TestsRechercheCPV()
        preparation.setUp()
        self.form = preparation.form
        self.espace_search = preparation.espace
        self.espace_menu = charger_menu()
        self.menu = self.espace_menu["Menu"]()
        for nom in ("navigation_link_retour navigation_link_search_go navigation_link_user_contact "
                    "navigation_link_user_parametres navigation_link_user_appels_offres "
                    "navigation_link_fermer Titre bt_user_mail").split():
            setattr(self.menu, nom, support.Composant())
        self.attributs_dom = {}
        self.menu.navigation_link_retour.node = SimpleNamespace(
            setAttribute=lambda nom, valeur: self.attributs_dom.update({nom: valeur}),
            removeAttribute=lambda nom: self.attributs_dom.pop(nom, None),
            style=SimpleNamespace(opacity=""),
        )
        self.menu._arret_bloque = False
        self.menu.content_panel = Mock()
        self.menu.actualiser_visibilite_derniere_recherche = Mock()
        self.menu.form_search = self.form
        self.form.f = self.menu
        # La veille métier est hors du parcours d'annulation testé.
        self.form.actualiser_bouton_veille_cpv = Mock()
        self.form._recherche_en_cours = True
        self.task = Mock()
        self.task.get_state.return_value = {}
        self.task.is_completed.return_value = True
        self.form.task_recherche = self.task
        self.form.timer_recherche_progress.interval = 1
        self.statut = None
        self.reponse_killer = {"ok": True, "status": "kill_requested"}
        self.serveur = self.espace_search["anvil"].server.call
        self.serveur.side_effect = self.appel_serveur
        self.form.traiter_offres_cpv_apres_background = Mock()
        self.form.traiter_offres_recuperees_apres_background = Mock()

    def appel_serveur(self, nom, *args, **kwargs):
        if nom == "task_killer":
            return self.reponse_killer
        if nom == "statut_tache_recherche":
            return self.statut
        return self.task

    def appels_killer(self):
        return [c for c in self.serveur.call_args_list if c.args[0] == "task_killer"]

    def verifier_menu(self):
        self.assertIsNone(self.menu.form_search)
        self.assertIsNone(self.form.task_recherche)
        self.assertFalse(self.form._recherche_en_cours)
        self.assertFalse(self.form._annulation_recherche_demandee)
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)
        self.assertFalse(self.menu._arret_bloque)
        self.assertNotIn("inert", self.attributs_dom)
        self.assertFalse(self.menu.navigation_link_retour.visible)
        self.menu.content_panel.clear.assert_called_once()
        self.menu.actualiser_visibilite_derniere_recherche.assert_called_once()

    def test_trois_clics_et_garde_search(self):
        for _ in range(3):
            self.menu.navigation_link_retour_click()
        # Vérifie aussi le garde de search indépendamment du verrou Menu.
        self.form.annuler_recherche_depuis_menu()
        self.assertEqual(len(self.appels_killer()), 1)
        self.espace_menu["alert"].assert_not_called()
        self.assertTrue(self.menu._arret_bloque)
        self.assertIn("inert", self.attributs_dom)
        self.assertEqual(self.attributs_dom["aria-disabled"], "true")
        self.form.afficher_progression_recherche.assert_called_once_with(
            ligne_1="Arrêt de la recherche en cours…", etat="stopping", afficher_jauges=False
        )
        self.assertIs(self.form.task_recherche, self.task)

    def test_tick_attente_lit_seulement_statut(self):
        self.menu.navigation_link_retour_click()
        self.serveur.reset_mock()
        for _ in range(3):
            self.form.timer_recherche_progress_tick()
        self.assertEqual([c.args[0] for c in self.serveur.call_args_list],
                         ["statut_tache_recherche"] * 3)
        self.task.get_state.assert_not_called()
        self.task.get_return_value.assert_not_called()
        self.espace_menu["alert"].assert_not_called()
        self.form.afficher_progression_recherche.assert_called_once()

    def test_echec_killer_permet_reessai(self):
        self.reponse_killer = {"ok": False, "message": "Échec technique simulé"}
        self.menu.navigation_link_retour_click()
        self.assertFalse(self.form._annulation_recherche_demandee)
        self.assertFalse(self.menu._arret_bloque)
        self.assertIs(self.form.task_recherche, self.task)
        self.assertTrue(self.form._recherche_en_cours)
        self.assertEqual(self.form.timer_recherche_progress.interval, 1)
        self.espace_menu["alert"].assert_called_once_with(
            "Échec technique simulé", title="Erreur d'arrêt de la recherche"
        )
        self.reponse_killer = {"ok": True}
        self.menu.navigation_link_retour_click()
        self.assertEqual(len(self.appels_killer()), 2)
        self.assertTrue(self.menu._arret_bloque)
        self.assertEqual(self.espace_menu["alert"].call_count, 1)

    def test_exception_killer_permet_reessai(self):
        def panne(nom, *args, **kwargs):
            if nom == "task_killer":
                raise RuntimeError("Serveur indisponible")
            return self.statut
        self.serveur.side_effect = panne
        self.menu.navigation_link_retour_click()
        self.assertFalse(self.form._annulation_recherche_demandee)
        self.assertFalse(self.menu._arret_bloque)
        self.serveur.side_effect = self.appel_serveur
        self.menu.navigation_link_retour_click()
        self.assertEqual(len(self.appels_killer()), 2)

    def test_confirmation_immediate_et_timer_meme_nettoyage(self):
        for immediate in (False, True):
            for mode in ("classique", "cpv"):
                for statut in ("completed", "failed", "killed"):
                    with self.subTest(immediate=immediate, mode=mode, statut=statut):
                        self.setUp()
                        self.form._ctx_recherche = {"mode_recherche": mode}
                        if immediate:
                            self.statut = statut
                        self.menu.navigation_link_retour_click()
                        if not immediate:
                            self.statut = statut
                            self.form.timer_recherche_progress_tick()
                        self.verifier_menu()
                        self.espace_menu["alert"].assert_not_called()
                        self.form.traiter_offres_cpv_apres_background.assert_not_called()
                        self.form.traiter_offres_recuperees_apres_background.assert_not_called()

    def test_statut_inconnu_conserve_suivi(self):
        self.menu.navigation_link_retour_click()
        for statut in (None, "missing", "inattendu"):
            self.statut = statut
            self.form.timer_recherche_progress_tick()
            self.assertIs(self.form.task_recherche, self.task)
            self.assertTrue(self.menu._arret_bloque)
            self.assertEqual(self.form.timer_recherche_progress.interval, 1)

    def test_annulation_pendant_get_return_value(self):
        for mode in ("classique", "cpv"):
            with self.subTest(mode=mode):
                self.setUp()
                self.form._ctx_recherche = {"mode_recherche": mode}
                def resultat():
                    self.menu.navigation_link_retour_click()
                    return {"ok": True, "offres": [{"titre": "Ignorer"}]}
                self.task.get_return_value.side_effect = resultat
                self.form.timer_recherche_progress_tick()
                self.form.traiter_offres_cpv_apres_background.assert_not_called()
                self.form.traiter_offres_recuperees_apres_background.assert_not_called()
                self.assertEqual(len(self.appels_killer()), 1)
                self.assertEqual(self.form.timer_recherche_progress.interval, 1)

    def test_task_remplacee_pendant_get_return_value(self):
        def resultat():
            self.form.task_recherche = Mock()
            return {"ok": True, "offres": []}
        self.task.get_return_value.side_effect = resultat
        self.form.timer_recherche_progress_tick()
        self.form.traiter_offres_cpv_apres_background.assert_not_called()
        self.form.traiter_offres_recuperees_apres_background.assert_not_called()

    def test_arret_avant_reception_task_classique_et_cpv(self):
        for mode in ("classique", "cpv"):
            with self.subTest(mode=mode):
                self.setUp()
                self.form.task_recherche = None
                self.form._recherche_en_cours = False
                self.form.afficher_offres = Mock()
                if mode == "classique":
                    self.form.cpv_selectionnes = []
                    self.form.text_box_mots_obligatoires_cpv.text = "formation"
                def lancement(nom, *args, **kwargs):
                    if nom.startswith("lancer_recherche_"):
                        self.menu.navigation_link_retour_click()
                        self.form.timer_recherche_progress_tick()
                        self.menu.navigation_link_retour_click()
                        self.assertTrue(self.form._recherche_en_cours)
                        self.assertTrue(self.menu._arret_bloque)
                        self.assertIs(self.menu.form_search, self.form)
                        self.assertEqual(len(self.appels_killer()), 0)
                        return self.task
                    return self.appel_serveur(nom, *args, **kwargs)
                self.serveur.side_effect = lancement
                self.form.lancer_recherche()
                self.assertEqual(len(self.appels_killer()), 1)
                self.assertIs(self.form.task_recherche, self.task)
                messages = [c.kwargs.get("ligne_1") for c in self.form.afficher_progression_recherche.call_args_list]
                self.assertEqual(messages.count("Arrêt de la recherche en cours…"), 1)
                self.assertEqual(messages[-1], "Arrêt de la recherche en cours…")
                self.statut = "killed"
                self.form.timer_recherche_progress_tick()
                self.verifier_menu()

    def test_get_return_value_exception_apres_annulation_sans_alerte(self):
        def resultat():
            self.menu.navigation_link_retour_click()
            raise RuntimeError("Tâche tuée")
        self.task.get_return_value.side_effect = resultat
        self.form.timer_recherche_progress_tick()
        self.espace_search["afficher_information"].assert_not_called()
        self.assertTrue(self.form._annulation_recherche_demandee)

    def test_lancement_echoue_apres_demande_sans_task(self):
        self.form.task_recherche = None
        self.menu.navigation_link_retour_click()
        self.assertTrue(self.menu._arret_bloque)
        # Le finally du lancement appelle ce nettoyage s'il ne reçoit pas de Task.
        self.form.deverrouiller_recherche(cacher_bouton=False)
        self.assertFalse(self.menu._arret_bloque)
        self.assertFalse(self.form._annulation_recherche_demandee)
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)
        self.assertEqual(len(self.appels_killer()), 0)
        self.menu.navigation_link_retour_click()
        self.verifier_menu()

    def test_texte_progression_exact_sans_pourcentage(self):
        self.form.label_jauge_globale = support.Composant()
        self.form._last_progress_role = None
        self.form.regler_jauge = Mock()
        # Réactive la méthode réelle, normalement simulée dans la préparation.
        del self.form.afficher_progression_recherche
        self.menu.navigation_link_retour_click()
        self.assertEqual(self.form.label_jauge_globale.text, "Arrêt de la recherche en cours…")


if __name__ == "__main__":
    unittest.main()
