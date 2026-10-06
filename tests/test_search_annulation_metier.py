"""Annulation métier via les vraies méthodes search/Menu, transport simulé."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid

import test_search_annulation as support


class TestsAnnulationMetier(unittest.TestCase):
    def setUp(self):
        preparation = support.TestsAnnulation()
        preparation.setUp()
        self.p = preparation
        self.form, self.menu = preparation.form, preparation.menu
        self.form.search_id = "ancienne-recherche"
        self.response = {"ok": True}
        self.callbacks = None
        self.async_call = Mock(side_effect=self.complement)
        preparation.espace_search["non_blocking"] = SimpleNamespace(call_async=self.async_call)
        preparation.espace_search["uuid"] = uuid
        preparation.serveur.side_effect = self.transport

    def complement(self, nom, task):
        self.assertIsNone(self.menu.form_search)
        self.assertEqual(nom, "task_killer")
        self.assertIs(task, self.p.task)
        def handlers(result, error):
            self.callbacks = (result, error)
        return SimpleNamespace(on_result=handlers)

    def transport(self, nom, *args, **kwargs):
        if nom == "demander_annulation_recherche_rao":
            return self.response
        if nom == "enregistrer_recherche_rao":
            return {"ok": True}
        return self.p.appel_serveur(nom, *args, **kwargs)

    def test_task_presente(self):
        self.menu.navigation_link_retour_click()
        self.p.verifier_menu()
        self.async_call.assert_called_once_with("task_killer", self.p.task)

    def test_task_absente(self):
        self.form.task_recherche = None
        self.menu.navigation_link_retour_click()
        self.p.verifier_menu()
        self.async_call.assert_not_called()

    def test_identifiant_exact_capture(self):
        self.menu.navigation_link_retour_click()
        self.p.serveur.assert_called_once_with("demander_annulation_recherche_rao", "ancienne-recherche")

    def test_retour_sans_attente_complement(self):
        self.menu.navigation_link_retour_click()
        self.assertIsNotNone(self.callbacks)
        self.p.verifier_menu()
        self.p.task.get_return_value.assert_not_called()

    def test_echec_complement_apres_acceptation(self):
        self.menu.navigation_link_retour_click()
        self.callbacks[1](RuntimeError("kill indisponible"))
        self.callbacks[0]({"ok": False})
        self.p.verifier_menu()
        self.p.espace_menu["alert"].assert_not_called()

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
        self.p.serveur.assert_called_once()
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
        self.callbacks[0]({"ok": False})
        self.callbacks[1](RuntimeError("Réponse tardive"))
        self.form.deverrouiller_recherche()
        self.form.timer_recherche_progress_tick()
        self.assertIs(self.menu.form_search, nouvelle)
        self.assertEqual(nouvelle.search_id, "nouvelle")
        self.assertEqual(nouvelle.timer, 1)
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)

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


if __name__ == "__main__":
    unittest.main()
