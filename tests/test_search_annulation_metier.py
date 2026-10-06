"""Annulation métier via les vraies méthodes search/Menu, transport simulé."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid

import test_search_annulation as support
import test_control_recherches as registre_support


class TestsAnnulationMetier(unittest.TestCase):
    def setUp(self):
        preparation = support.TestsAnnulation()
        preparation.setUp()
        self.p = preparation
        self.form, self.menu = preparation.form, preparation.menu
        self.form.search_id = "ancienne-recherche"
        self.response = {"ok": True}
        self.async_call = Mock(side_effect=AssertionError("Arrêt complémentaire interdit avec search_id"))
        preparation.espace_search["non_blocking"] = SimpleNamespace(call_async=self.async_call)
        preparation.espace_search["uuid"] = uuid
        preparation.serveur.side_effect = self.transport

    def transport(self, nom, *args, **kwargs):
        if nom == "demander_annulation_recherche_rao":
            return self.response
        if nom == "enregistrer_recherche_rao":
            return {"ok": True}
        return self.p.appel_serveur(nom, *args, **kwargs)

    def test_task_presente(self):
        self.menu.navigation_link_retour_click()
        self.p.verifier_menu()
        self.async_call.assert_not_called()
        self.p.serveur.assert_called_once_with("demander_annulation_recherche_rao", "ancienne-recherche")
        self.p.task.kill.assert_not_called()

    def test_task_absente(self):
        self.form.task_recherche = None
        self.menu.navigation_link_retour_click()
        self.p.verifier_menu()
        self.async_call.assert_not_called()

    def test_identifiant_exact_capture(self):
        self.menu.navigation_link_retour_click()
        self.p.serveur.assert_called_once_with("demander_annulation_recherche_rao", "ancienne-recherche")

    def test_retour_immediat_sans_arret_anvil(self):
        self.menu.navigation_link_retour_click()
        self.p.verifier_menu()
        self.async_call.assert_not_called()
        self.p.task.kill.assert_not_called()
        self.p.task.get_state.assert_not_called()
        self.p.task.get_return_value.assert_not_called()
        self.p.serveur.assert_called_once_with("demander_annulation_recherche_rao", "ancienne-recherche")

    def test_refus_registre_et_reessai(self):
        self.response = {"ok": False, "message": "Réessayer"}
        self.menu.navigation_link_retour_click()
        self.assertIs(self.menu.form_search, self.form)
        self.assertIs(self.form.task_recherche, self.p.task)
        self.assertFalse(self.menu._arret_bloque)
        self.assertFalse(self.form._annulation_recherche_demandee)
        self.async_call.assert_not_called()
        self.response = {"ok": True}
        self.menu.navigation_link_retour_click()
        self.p.verifier_menu()

    def test_double_clic(self):
        def response(nom, *args, **kwargs):
            self.menu.navigation_link_retour_click()
            self.form.annuler_recherche_depuis_menu()
            return {"ok": True}
        self.p.serveur.side_effect = response
        self.menu.navigation_link_retour_click()
        self.menu.navigation_link_retour_click()
        self.p.serveur.assert_called_once_with("demander_annulation_recherche_rao", "ancienne-recherche")
        self.async_call.assert_not_called()
        self.p.verifier_menu()

    def test_task_recue_apres_abandon_ignoree(self):
        self.form._recherche_en_cours = False
        self.form.task_recherche = None
        self.form.afficher_offres = Mock()
        def response(nom, *args, **kwargs):
            if nom == "lancer_recherche_cpv_background":
                self.menu.navigation_link_retour_click()
                self.assertIsNone(self.menu.form_search)
                return self.p.task
            return self.transport(nom, *args, **kwargs)
        self.p.serveur.side_effect = response
        self.form.lancer_recherche_offres_cpv()
        self.p.verifier_menu()
        self.form.timer_recherche_progress_tick()
        self.async_call.assert_not_called()

    def test_ancienne_reponse_ne_touche_pas_nouvelle_form(self):
        self.menu.navigation_link_retour_click()
        nouvelle = SimpleNamespace(search_id="nouvelle", task_recherche=object(), timer=1)
        self.menu.form_search = nouvelle
        self.p.task.get_return_value.return_value = {"ok": True, "offres": []}
        self.form.deverrouiller_recherche()
        self.form.timer_recherche_progress_tick()
        self.assertIs(self.menu.form_search, nouvelle)
        self.assertEqual(nouvelle.search_id, "nouvelle")
        self.assertEqual(nouvelle.timer, 1)
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)

    def test_nouvelle_recherche_lancee_independante(self):
        self.menu.navigation_link_retour_click()
        preparation = support.TestsAnnulation()
        preparation.setUp()
        nouvelle = preparation.form
        preparation.espace_search["uuid"] = uuid
        nouvelle.f = self.menu
        nouvelle._recherche_en_cours = False
        nouvelle.task_recherche = None
        nouvelle.afficher_offres = Mock()
        nouvelle_task = Mock()
        preparation.serveur.side_effect = lambda nom, *args, **kwargs: (
            {"ok": True} if nom == "enregistrer_recherche_rao" else nouvelle_task)
        self.menu.form_search = nouvelle
        nouvelle.lancer_recherche_offres_cpv()
        contexte = dict(nouvelle._ctx_recherche)
        self.form.timer_recherche_progress_tick()
        self.form.lancer_recherche_offres_cpv()
        self.form.deverrouiller_recherche()
        self.assertIs(self.menu.form_search, nouvelle)
        self.assertIs(nouvelle.task_recherche, nouvelle_task)
        self.assertEqual(nouvelle._ctx_recherche, contexte)
        self.assertEqual(nouvelle.timer_recherche_progress.interval, 1)
        self.assertTrue(nouvelle._recherche_en_cours)
        self.assertNotEqual(nouvelle.search_id, "ancienne-recherche")

    def test_historique_sans_search_id(self):
        del self.form.search_id
        self.menu.navigation_link_retour_click()
        self.p.serveur.assert_called_once_with("task_killer", self.p.task)
        self.async_call.assert_not_called()
        self.p.verifier_menu()

    def test_refus_sans_task_preserve_timer_zero(self):
        self.form.task_recherche = None
        self.form.timer_recherche_progress.interval = 0
        self.response = {"ok": False}
        self.menu.navigation_link_retour_click()
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)
        self.assertTrue(self.form._recherche_en_cours)
        self.assertFalse(self.menu._arret_bloque)

    def test_identifiant_existant_sans_task_ni_flag_exige_registre(self):
        self.form.task_recherche = None
        self.form._recherche_en_cours = False
        self.response = {"ok": False}
        self.menu.navigation_link_retour_click()
        self.p.serveur.assert_called_once_with("demander_annulation_recherche_rao", "ancienne-recherche")
        self.assertIs(self.menu.form_search, self.form)
        self.assertEqual(self.form.search_id, "ancienne-recherche")


    def test_uuid_du_lancement_et_ecriture_reelle_simulee(self):
        registre = registre_support.TestsControlRecherches()
        registre.setUp()
        self.form._recherche_en_cours = False
        self.form.task_recherche = None
        self.form.afficher_offres = Mock()
        uuid_inscrit = None

        def transport(nom, *args, **kwargs):
            nonlocal uuid_inscrit
            if nom == "enregistrer_recherche_rao":
                uuid_inscrit = args[0]
                self.assertEqual(self.form.search_id, uuid_inscrit)
                return registre.api.enregistrer_recherche_rao(*args, **kwargs)
            if nom == "lancer_recherche_cpv_background":
                self.assertEqual(kwargs["search_id"], uuid_inscrit)
                registre.api.marquer_recherche_en_cours(uuid_inscrit, "task-anvil")
                return self.p.task
            if nom == "demander_annulation_recherche_rao":
                self.assertEqual(args, (uuid_inscrit,))
                self.assertEqual(self.form.search_id, uuid_inscrit)
                self.assertIs(self.menu.form_search, self.form)
                self.assertEqual(self.form.timer_recherche_progress.interval, 1)
                self.assertFalse(self.form._recherche_abandonnee)
                return registre.api.demander_annulation_recherche_rao(*args)
            raise AssertionError(nom)

        self.p.serveur.side_effect = transport
        self.form.lancer_recherche_offres_cpv()
        self.assertEqual(registre.table.rows[0]["status"], "running")
        self.menu.navigation_link_retour_click()
        self.assertEqual(registre.table.rows[0]["status"], "cancellation_requested")
        self.assertIsNotNone(registre.table.rows[0]["cancel_requested_at"])
        self.assertIsNone(self.form.search_id)
        self.p.verifier_menu()

    def test_exception_registre_preserve_identifiant_task_et_timer(self):
        for task in (self.p.task, None):
            with self.subTest(task_presente=task is not None):
                self.setUp()
                if task is None:
                    self.form.task_recherche = None
                    self.form.timer_recherche_progress.interval = 0
                task_attendue = self.form.task_recherche
                interval = self.form.timer_recherche_progress.interval
                self.p.serveur.side_effect = RuntimeError("Erreur registre")
                self.menu.navigation_link_retour_click()
                self.assertIs(self.menu.form_search, self.form)
                self.assertFalse(self.form._recherche_abandonnee)
                self.assertEqual(self.form.search_id, "ancienne-recherche")
                self.assertIs(self.form.task_recherche, task_attendue)
                self.assertEqual(self.form.timer_recherche_progress.interval, interval)
                self.assertFalse(self.menu._arret_bloque)
                self.async_call.assert_not_called()
                self.p.serveur.side_effect = self.transport
                self.menu.navigation_link_retour_click()
                self.p.verifier_menu()

    def test_nettoyage_uniquement_apres_acceptation(self):
        for task_presente in (True, False):
            with self.subTest(task_presente=task_presente):
                self.setUp()
                if not task_presente:
                    self.form.task_recherche = None
                def transport(nom, *args, **kwargs):
                    self.assertEqual(nom, "demander_annulation_recherche_rao")
                    self.assertEqual(self.form.search_id, "ancienne-recherche")
                    self.assertIs(self.menu.form_search, self.form)
                    return {"ok": True}
                self.p.serveur.side_effect = transport
                self.menu.navigation_link_retour_click()
                self.assertIsNone(self.form.search_id)
                self.p.verifier_menu()

    def test_ok_literal_true_requis(self):
        for response in ({"ok": False}, {"ok": 1}, {"ok": "True"}, {}, None):
            with self.subTest(response=response):
                self.setUp()
                self.response = response
                self.menu.navigation_link_retour_click()
                self.assertIs(self.menu.form_search, self.form)
                self.assertEqual(self.form.search_id, "ancienne-recherche")
                self.assertIs(self.form.task_recherche, self.p.task)
                self.async_call.assert_not_called()

    def test_capture_locale_preservee_pendant_affichage(self):
        self.form.afficher_progression_recherche = Mock(
            side_effect=lambda **kwargs: setattr(self.form, "search_id", "autre-valeur"))
        self.menu.navigation_link_retour_click()
        self.p.serveur.assert_called_once_with("demander_annulation_recherche_rao", "ancienne-recherche")
        self.assertIsNone(self.form.search_id)



if __name__ == "__main__":
    unittest.main()
