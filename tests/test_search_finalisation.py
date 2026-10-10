"""Non-régression de la finalisation, sans serveur ni composants Anvil réels."""
import copy
import io
from contextlib import redirect_stdout
import unittest
from unittest.mock import Mock

import test_search_recherche_cpv as support


class TestsFinalisation(unittest.TestCase):
    def setUp(self):
        preparation = support.TestsRechercheCPV()
        preparation.setUp()
        preparation.lancer()
        self.form = preparation.form
        self.form.afficher_progression_recherche.reset_mock()
        self.espace = preparation.espace
        self.resultat = preparation.resultat
        self.form.sauvegarder_derniere_recherche = Mock(return_value=True)
        self.form._recherche_en_cours = True
        self.form.timer_recherche_progress.interval = 1
        self.form.task_recherche = Mock()
        self.form.f.navigation_link_search_go.enabled = False
        self.form.column_panel_params.visible = True

    def mode_classique(self):
        self.form._ctx_recherche = dict(
            mode_recherche="classique", mots_obligatoires=[], mots_ou=[],
            mots_exclus=[], selected_platformes=["BOAMP"], periode=30,
            departements=[], cpv_selectionnes=[]
        )

    def verifier_nettoyage(self, bouton_actif=True):
        self.assertFalse(self.form._recherche_en_cours)
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)
        self.assertIsNone(self.form.task_recherche)
        self.assertEqual(self.form.f.navigation_link_search_go.enabled, bouton_actif)

    def test_cpv_conserve_projection_doublons_panneaux_et_diagnostics(self):
        offre = dict(titre="Offre", lien="source", cpv_codes=["80560000"],
                     provenances=[{"source": "BOAMP"}])
        offres = [offre, offre]
        original = copy.deepcopy(offres)
        sortie = io.StringIO()
        with redirect_stdout(sortie):
            self.form.traiter_offres_cpv_apres_background(self.resultat(
                offres, errors=["source indisponible"], recherche_limitee=True,
                message_limite="Limite moteur"
            ))
        self.assertEqual(offres, original)
        self.assertEqual(len(self.form.list_offres), 2)
        self.assertEqual(self.form.list_offres[0]["provenances"], offre["provenances"])
        self.assertEqual(self.form.list_offres[0]["lien_source"], "source")
        self.assertFalse(self.form.list_offres[0]["vu"])
        self.assertTrue(self.form.column_panel_params.visible)
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs["ligne_1"], "2 offres retenues")
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs["ligne_2"], "")
        self.assertIn("source indisponible", sortie.getvalue())
        self.espace["afficher_information"].assert_called_once_with("Limite moteur", titre="Recherche limitée")
        for nom in ("build_offres_list", "filtrer_offres_criteres_positifs",
                    "filtrer_offres_exclues", "ajouter_correspondance_mots_ou",
                    "trier_offres_par_interet"):
            getattr(self.form, nom).assert_not_called()
        self.verifier_nettoyage()

    def test_classique_conserve_pipeline_et_politique_finale(self):
        self.mode_classique()
        appels = Mock()
        for nom in ("filtrer_offres_exclues", "build_offres_list",
                    "ajouter_correspondance_mots_ou", "trier_offres_par_interet"):
            methode = Mock(side_effect=lambda offres, *args, **kwargs: offres)
            setattr(self.form, nom, methode)
            appels.attach_mock(methode, nom)
        self.form.traiter_offres_recuperees_apres_background([{"titre": "Classique"}])
        self.assertEqual([appel[0] for appel in appels.mock_calls], [
            "filtrer_offres_exclues", "build_offres_list",
            "ajouter_correspondance_mots_ou", "trier_offres_par_interet"
        ])
        self.form.build_offres_list.assert_called_once_with([{"titre": "Classique"}], dedoublonner=True)
        self.form.filtrer_offres_criteres_positifs.assert_not_called()
        self.assertFalse(self.form.column_panel_saisie_recherche.visible)
        self.assertTrue(self.form.column_panel_param_summary.visible)
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs["ligne_1"], "1 offre retenue")
        self.verifier_nettoyage(bouton_actif=False)

    def test_sauvegarde_precede_publication(self):
        anciennes = [{"titre": "Ancienne"}]
        nouvelles = [{"titre": "Nouvelle"}]
        self.form.list_offres = anciennes
        def sauvegarder(offres):
            self.assertIs(self.form.list_offres, anciennes)
            self.assertIs(offres, nouvelles)
            self.form.afficher_progression_recherche.assert_not_called()
            return True
        self.form.sauvegarder_derniere_recherche.side_effect = sauvegarder
        self.assertTrue(self.form.finaliser_recherche(nouvelles))
        self.form.sauvegarder_derniere_recherche.assert_called_once_with(nouvelles)
        self.assertEqual(self.form.list_offres[0]["titre"], "Nouvelle")

    def test_refus_sauvegarde_ne_publie_pas_de_succes(self):
        anciennes = [{"titre": "Ancienne"}]
        self.form.list_offres = anciennes
        self.form.sauvegarder_derniere_recherche.return_value = False
        self.assertFalse(self.form.finaliser_recherche([{"titre": "Nouvelle"}], cacher_bouton=True))
        self.assertIs(self.form.list_offres, anciennes)
        self.form.afficher_progression_recherche.assert_not_called()
        self.verifier_nettoyage()

    def test_exceptions_sauvegarde_et_affichage_remontent(self):
        for methode in ("sauvegarder_derniere_recherche", "afficher_offres"):
            with self.subTest(methode=methode):
                self.setUp()
                setattr(self.form, methode, Mock(side_effect=RuntimeError("échec technique")))
                with self.assertRaisesRegex(RuntimeError, "échec technique"):
                    self.form.finaliser_recherche([{"titre": "Offre"}], cacher_bouton=True)
                self.form.afficher_progression_recherche.assert_not_called()
                self.verifier_nettoyage()

    def test_zero_cpv_ne_reinitialise_pas_la_case_globale(self):
        self.form.checkbox_on_off.checked = True
        self.form.traiter_offres_cpv_apres_background(self.resultat())
        self.assertTrue(self.form.checkbox_on_off.checked)
        self.assertFalse(self.form.checkbox_on_off.visible)
        self.assertTrue(self.form.column_panel_params.visible)
        arguments = self.form.afficher_progression_recherche.call_args.kwargs
        self.assertEqual(arguments["ligne_1"], "Pas d'offres correspondant aux critères")
        self.assertEqual(arguments["ligne_2"], "")
        self.verifier_nettoyage()

    def test_zero_classique_conserve_les_trois_messages(self):
        for message in ("Aucune offre trouvée", "Aucune offre ne contient les mots demandés",
                        "Aucune offre ne correspond à tous vos critères"):
            with self.subTest(message=message):
                self.setUp()
                self.mode_classique()
                self.form.checkbox_on_off.checked = True
                self.form.terminer_recherche_classique_sans_offre(message)
                self.assertFalse(self.form.checkbox_on_off.checked)
                self.assertFalse(self.form.checkbox_on_off.visible)
                self.assertTrue(self.form.bloc_selecteur_cpv_complet.visible)
                arguments = self.form.afficher_progression_recherche.call_args.kwargs
                self.assertEqual(arguments["ligne_1"], "Recherche terminée")
                self.assertEqual(arguments["ligne_2"], message)
                self.verifier_nettoyage()

    def test_erreur_cpv_ne_passe_pas_par_finalisation(self):
        self.form.finaliser_recherche = Mock(side_effect=AssertionError("finalisation interdite"))
        self.form.traiter_offres_cpv_apres_background(self.resultat(ok=False, message="Erreur moteur"))
        self.form.finaliser_recherche.assert_not_called()
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs["etat"], "error")
        self.verifier_nettoyage()

    def test_dispatch_timer_conserve_les_deux_parcours(self):
        for mode, methode in (("cpv", "traiter_offres_cpv_apres_background"),
                              ("classique", "traiter_offres_recuperees_apres_background")):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == "classique":
                    self.mode_classique()
                resultat = self.resultat([{"titre": "Offre"}])
                self.form.task_recherche.get_state.return_value = {}
                self.form.task_recherche.is_completed.return_value = True
                self.form.task_recherche.get_return_value.return_value = resultat
                self.form.traiter_offres_cpv_apres_background = Mock()
                self.form.traiter_offres_recuperees_apres_background = Mock()
                self.form.timer_recherche_progress_tick()
                attendu = resultat if mode == "cpv" else resultat["offres"]
                getattr(self.form, methode).assert_called_once_with(attendu)
                self.assertEqual(self.form.timer_recherche_progress.interval, 0)


if __name__ == "__main__":
    unittest.main()
