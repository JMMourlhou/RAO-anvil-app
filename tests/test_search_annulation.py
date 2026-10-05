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
        self.form._recherche_abandonnee = False
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
        def livraison(nom, *args, **kwargs):
            if nom == "task_killer":
                self.assertTrue(self.menu._arret_bloque)
                self.assertIn("inert", self.attributs_dom)
                self.assertEqual(self.attributs_dom["aria-disabled"], "true")
                self.menu.navigation_link_retour_click()
                self.menu.navigation_link_retour_click()
                self.form.annuler_recherche_depuis_menu()
            return self.appel_serveur(nom, *args, **kwargs)
        self.serveur.side_effect = livraison
        self.menu.navigation_link_retour_click()
        self.form.annuler_recherche_depuis_menu()
        self.menu.navigation_link_retour_click()
        self.assertEqual(len(self.appels_killer()), 1)
        self.espace_menu["alert"].assert_not_called()
        self.form.afficher_progression_recherche.assert_called_once_with(
            ligne_1="Arrêt de la recherche en cours…", etat="stopping", afficher_jauges=False
        )
        self.verifier_menu()

    def test_abandon_sans_lecture_statut_ni_polling_ulterieur(self):
        self.menu.navigation_link_retour_click()
        self.assertEqual([c.args[0] for c in self.serveur.call_args_list], ["task_killer"])
        self.verifier_menu()
        self.serveur.reset_mock()
        for _ in range(3):
            self.form.timer_recherche_progress_tick()
        self.serveur.assert_not_called()
        self.task.get_state.assert_not_called()
        self.task.is_completed.assert_not_called()
        self.task.get_return_value.assert_not_called()
        self.espace_menu["alert"].assert_not_called()
        self.form.afficher_progression_recherche.assert_called_once()
        self.verifier_menu()

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
        self.verifier_menu()
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

    def test_demande_acceptee_retour_immediat_classique_et_cpv(self):
        for mode in ("classique", "cpv"):
            for statut in (None, "missing", "kill_requested", "completed", "failed", "killed"):
                with self.subTest(mode=mode, statut=statut):
                    self.setUp()
                    self.form._ctx_recherche = {"mode_recherche": mode}
                    self.reponse_killer["status"] = statut
                    self.menu.navigation_link_retour_click()
                    self.verifier_menu()
                    self.assertTrue(self.form._recherche_abandonnee)
                    self.assertEqual(self.form._ctx_recherche, {})
                    self.assertEqual([c.args[0] for c in self.serveur.call_args_list], ["task_killer"])
                    self.espace_menu["alert"].assert_not_called()
                    self.form.traiter_offres_cpv_apres_background.assert_not_called()
                    self.form.traiter_offres_recuperees_apres_background.assert_not_called()

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
                self.assertEqual(self.form.timer_recherche_progress.interval, 0)
                self.verifier_menu()

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
                self.assertIsNone(self.form.task_recherche)
                messages = [c.kwargs.get("ligne_1") for c in self.form.afficher_progression_recherche.call_args_list]
                self.assertEqual(messages.count("Arrêt de la recherche en cours…"), 1)
                self.assertEqual(messages[-1], "Arrêt de la recherche en cours…")
                self.verifier_menu()
                self.form.timer_recherche_progress_tick()
                self.assertEqual(self.form.timer_recherche_progress.interval, 0)

    def test_get_return_value_exception_apres_annulation_sans_alerte(self):
        def resultat():
            self.menu.navigation_link_retour_click()
            raise RuntimeError("Tâche tuée")
        self.task.get_return_value.side_effect = resultat
        self.form.timer_recherche_progress_tick()
        self.espace_search["afficher_information"].assert_not_called()
        self.assertTrue(self.form._recherche_abandonnee)
        self.verifier_menu()

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

    def test_nouvelle_recherche_independante_et_ancien_resultat_ignore(self):
        for mode in ("classique", "cpv"):
            with self.subTest(mode=mode):
                self.setUp()
                ancienne = self.form
                ancienne._ctx_recherche = {"mode_recherche": mode}
                ancienne.list_offres = [{"titre": "Avant abandon"}]
                nouvelle = None
                nouvelle_task = Mock()
                def resultat_tardif():
                    nonlocal nouvelle
                    self.menu.navigation_link_retour_click()
                    preparation = support.TestsRechercheCPV()
                    preparation.setUp()
                    nouvelle = preparation.form
                    nouvelle.f = self.menu
                    nouvelle.actualiser_bouton_veille_cpv = Mock()
                    nouvelle.afficher_offres = Mock()
                    preparation.espace["anvil"].server.call.return_value = nouvelle_task
                    if mode == "classique":
                        nouvelle.cpv_selectionnes = []
                        nouvelle.text_box_mots_obligatoires_cpv.text = "nouvelle recherche"
                    self.menu.form_search = nouvelle
                    nouvelle.lancer_recherche()
                    self.assertIs(nouvelle.task_recherche, nouvelle_task)
                    self.assertTrue(nouvelle._recherche_en_cours)
                    return {"ok": True, "offres": [{"titre": "Ancienne Task"}]}
                self.task.get_return_value.side_effect = resultat_tardif
                ancienne.timer_recherche_progress_tick()
                contexte_nouveau = dict(nouvelle._ctx_recherche)
                ancienne.timer_recherche_progress_tick()
                ancienne.lancer_recherche()
                ancienne.lancer_recherche_offres_cpv()
                ancienne.deverrouiller_recherche()
                self.assertEqual(ancienne.list_offres, [{"titre": "Avant abandon"}])
                self.assertEqual(ancienne._ctx_recherche, {})
                self.assertEqual(ancienne.timer_recherche_progress.interval, 0)
                self.assertIs(self.menu.form_search, nouvelle)
                self.assertIs(nouvelle.task_recherche, nouvelle_task)
                self.assertEqual(nouvelle._ctx_recherche, contexte_nouveau)
                self.assertEqual(nouvelle.timer_recherche_progress.interval, 1)
                self.assertTrue(nouvelle._recherche_en_cours)
                ancienne.traiter_offres_cpv_apres_background.assert_not_called()
                ancienne.traiter_offres_recuperees_apres_background.assert_not_called()

    def test_abandon_pendant_suite_lancement_ne_rattache_pas_task(self):
        self.form.task_recherche = None
        self.form._recherche_en_cours = False
        self.form.cpv_selectionnes = []
        self.form.text_box_mots_obligatoires_cpv.text = "formation"
        def resume():
            self.menu.navigation_link_retour_click()
        self.form.display_param_summary = Mock(side_effect=resume)
        self.form.lancer_recherche()
        self.verifier_menu()
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)

    def test_sauvegarde_tardive_ne_publie_pas_apres_abandon(self):
        ancienne_liste = [{"titre": "Avant abandon"}]
        self.form.list_offres = ancienne_liste
        self.form.afficher_offres = Mock()
        def sauvegarde(offres):
            self.menu.navigation_link_retour_click()
            return True
        self.form.sauvegarder_derniere_recherche = Mock(side_effect=sauvegarde)
        self.assertFalse(self.form.finaliser_recherche([{"titre": "Ignorer"}]))
        self.assertIs(self.form.list_offres, ancienne_liste)
        self.form.afficher_offres.assert_not_called()
        self.verifier_menu()

    def test_backup_reponse_tardive_ignoree(self):
        self.form._ctx_recherche = dict(
            mode_recherche="classique", selected_platformes=["BOAMP"], periode=30,
            mots_obligatoires=["formation"], mots_ou=[], mots_exclus=[], departements=[]
        )
        self.espace_search["Time"] = SimpleNamespace(french_zone_time=lambda: "date")
        def backup(nom, *args, **kwargs):
            if nom == "backup_requete":
                self.menu.navigation_link_retour_click()
                return {"ok": True, "histo_id": "ignorer", "revision_recherche": 42}
            return self.appel_serveur(nom, *args, **kwargs)
        self.serveur.side_effect = backup
        self.assertFalse(self.form.sauvegarder_derniere_recherche([]))
        self.assertEqual(self.form.histo_id, "ancien-historique")
        self.assertFalse(self.form._offres_correspondent_histo)
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
