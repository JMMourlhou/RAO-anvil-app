"""Récupération après erreur : méthodes réelles, transport strict et aucun réseau."""
import copy
import unittest
from unittest.mock import Mock

import test_search_recherche_cpv as support


class TestsErreursRecherche(unittest.TestCase):
    def preparer(self, mode):
        """Prépare une saisie non vide et un transport limité au protocole testé."""
        self.support = support.TestsRechercheCPV()
        self.support.setUp()
        self.form = self.support.form
        self.espace = self.support.espace
        self.serveur = self.support.serveur
        self.mode = mode
        if mode == 'classique':
            self.form.cpv_selectionnes = []
        self.form.text_box_mots_obligatoires_cpv.text = 'formation'
        self.form.text_box_mot_ou.text = 'sst'
        self.form.text_box_mots_exclus.text = 'exclu'
        self.form.text_box_departements.text = '34,30'
        self.form.afficher_saisie_recherche()
        self.task = Mock(spec=['get_state', 'is_completed', 'get_return_value'])
        self.task.get_state.return_value = {}
        self.task.is_completed.return_value = False
        self.serveur.return_value = self.task
        self.erreur_lancement = None
        self.erreur_sauvegarde = None
        self.refus_sauvegarde = False
        self.statut = None
        self.serveur.side_effect = self.transport
        self.criteres = self.lire_criteres()

    def transport(self, nom, *args, **kwargs):
        """Injecte les pannes aux frontières serveur sans remplacer le nettoyage."""
        if nom in ('lancer_recherche_cpv_background', 'lancer_recherche_multi_sources_background'):
            if self.erreur_lancement is not None:
                raise self.erreur_lancement
            return self.task
        if nom == 'statut_tache_recherche':
            self.assertEqual(args, (self.task,))
            if isinstance(self.statut, Exception):
                raise self.statut
            return self.statut
        if nom == 'backup_requete':
            if self.erreur_sauvegarde is not None:
                raise self.erreur_sauvegarde
            if self.refus_sauvegarde:
                return {'ok': False, 'message': 'Sauvegarde refusée : révision obsolète'}
        return self.support.appel_serveur(nom, *args, **kwargs)

    def lire_criteres(self):
        return copy.deepcopy((self.form.cpv_selectionnes,
            self.form.text_box_mots_obligatoires_cpv.text, self.form.text_box_mot_ou.text,
            self.form.text_box_mots_exclus.text, self.form.text_box_departements.text,
            self.form.text_box_nb_jours.text, self.form.multi_select_drop_down_platformes.selected))

    def verifier_nettoyage(self):
        self.assertTrue(self.form.column_panel_saisie_recherche.visible)
        self.assertFalse(self.form.column_panel_param_summary.visible)
        self.assertTrue(self.form.f.navigation_link_search_go.enabled)
        self.assertFalse(self.form._recherche_en_cours)
        self.assertFalse(self.form._annulation_recherche_demandee)
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)
        self.assertIsNone(self.form.task_recherche)
        self.assertEqual(self.lire_criteres(), self.criteres)

    def verifier_ticks_et_relance(self):
        """Les ticks nettoyés sont muets ; un nouveau lancement reçoit sa propre Task."""
        progression = self.form.afficher_progression_recherche.call_count
        messages = (self.espace['afficher_information'].call_count,
                    self.espace['afficher_avertissement'].call_count)
        appels = self.serveur.call_count
        for _ in range(3):
            self.form.timer_recherche_progress_tick()
        self.assertEqual(self.form.afficher_progression_recherche.call_count, progression)
        self.assertEqual((self.espace['afficher_information'].call_count,
                          self.espace['afficher_avertissement'].call_count), messages)
        self.assertEqual(self.serveur.call_count, appels)
        self.verifier_nettoyage()
        self.erreur_lancement = None
        self.erreur_sauvegarde = None
        self.refus_sauvegarde = False
        nouvelle_task = Mock(spec=['get_state', 'is_completed', 'get_return_value'])
        self.task = nouvelle_task
        self.form.lancer_recherche()
        self.assertIs(self.form.task_recherche, nouvelle_task)
        self.assertTrue(self.form._recherche_en_cours)
        self.assertFalse(self.form.f.navigation_link_search_go.enabled)
        self.assertEqual(self.form.timer_recherche_progress.interval, 1)
        self.assertFalse(self.form.column_panel_saisie_recherche.visible)
        self.assertTrue(self.form.column_panel_param_summary.visible)
        self.assertEqual(self.lire_criteres(), self.criteres)
        attendu = 'lancer_recherche_cpv_background' if self.mode == 'cpv' else 'lancer_recherche_multi_sources_background'
        self.assertEqual(self.serveur.call_args.args, (attendu,))

    def test_a_exception_lancement_deux_modes(self):
        for mode in ('cpv', 'classique'):
            with self.subTest(mode=mode):
                self.preparer(mode)
                self.erreur_lancement = self.espace['anvil'].server.UplinkDisconnectedError('Uplink indisponible')
                if mode == 'cpv':
                    with self.assertRaisesRegex(self.espace['anvil'].server.UplinkDisconnectedError, 'Uplink indisponible'):
                        self.form.lancer_recherche()
                else:
                    self.form.lancer_recherche()
                    self.espace['afficher_avertissement'].assert_called_once_with(
                        'Erreur pendant le lancement de la recherche :\n\nUplink indisponible', titre='Erreur de recherche')
                self.verifier_nettoyage()
                self.verifier_ticks_et_relance()

    def test_b_lancement_none_deux_modes(self):
        for mode in ('cpv', 'classique'):
            with self.subTest(mode=mode):
                self.preparer(mode)
                self.task = None
                self.form.lancer_recherche()
                self.verifier_nettoyage()
                # Sans référence, l'affichage ne doit pas annoncer un lancement réussi.
                derniers = self.form.afficher_progression_recherche.call_args.kwargs
                self.assertNotEqual(derniers.get('etat'), 'running')
                self.assertEqual(derniers['etat'], 'error')
                self.assertFalse(derniers['afficher_jauges'])
                if mode == 'classique':
                    self.assertEqual(derniers['ligne_1'], 'Impossible de démarrer la recherche')
                    self.assertFalse(any(appel.kwargs.get('ligne_1') == '🔎 Recherche lancée'
                                         for appel in self.form.afficher_progression_recherche.call_args_list))
                self.verifier_ticks_et_relance()

    def test_c_task_failed_deux_modes(self):
        for mode in ('cpv', 'classique'):
            with self.subTest(mode=mode):
                self.preparer(mode)
                self.form.lancer_recherche()
                self.task.get_state.side_effect = RuntimeError('Collecte interrompue')
                self.statut = 'failed'
                self.form.timer_recherche_progress_tick()
                self.espace['afficher_information'].assert_called_once_with(
                    'La tâche est terminée avec le statut failed.\n\nCollecte interrompue', titre='Erreur de recherche')
                self.verifier_nettoyage()
                self.verifier_ticks_et_relance()

    def test_c_cpv_ok_false(self):
        self.preparer('cpv')
        self.form.lancer_recherche()
        self.task.is_completed.return_value = True
        self.task.get_return_value.return_value = self.support.resultat(
            [{'titre': 'Ne pas publier'}], ok=False, message='Source indisponible')
        self.form.timer_recherche_progress_tick()
        self.assertEqual(self.form.list_offres, [])
        self.assertEqual(self.form.repeating_panel_offres.items, [])
        arguments = self.form.afficher_progression_recherche.call_args.kwargs
        self.assertEqual(arguments['etat'], 'error')
        self.assertEqual(arguments['ligne_2'], 'Source indisponible')
        self.assertFalse(arguments['afficher_jauges'])
        self.verifier_nettoyage()
        self.verifier_ticks_et_relance()

    def test_d_recuperation_deux_modes(self):
        for mode in ('cpv', 'classique'):
            with self.subTest(mode=mode):
                self.preparer(mode)
                self.form.lancer_recherche()
                self.task.is_completed.return_value = True
                self.task.get_return_value.side_effect = RuntimeError('Résultat inaccessible')
                self.form.timer_recherche_progress_tick()
                self.espace['afficher_information'].assert_called_once_with(
                    'Erreur pendant la recherche :\n\nRésultat inaccessible', titre='Erreur de recherche')
                arguments = self.form.afficher_progression_recherche.call_args.kwargs
                self.assertEqual(arguments['etat'], 'error')
                self.assertFalse(arguments['afficher_jauges'])
                self.verifier_nettoyage()
                self.verifier_ticks_et_relance()

    def test_e_finalisation_deux_modes(self):
        for mode in ('cpv', 'classique'):
            for panne in ('traitement', 'sauvegarde', 'refus'):
                with self.subTest(mode=mode, panne=panne):
                    self.preparer(mode)
                    self.form.lancer_recherche()
                    if panne == 'traitement':
                        # L'affichage fait partie de la finalisation après sauvegarde.
                        original = self.form.afficher_offres
                        self.form.afficher_offres = Mock(side_effect=RuntimeError('Affichage impossible'))
                    elif panne == 'sauvegarde':
                        self.erreur_sauvegarde = RuntimeError('Historique indisponible')
                    else:
                        self.refus_sauvegarde = True
                    if panne == 'refus':
                        self.assertFalse(self.form.finaliser_recherche([{'titre': 'Offre'}]))
                        self.espace['afficher_avertissement'].assert_called_once_with(
                            'Sauvegarde refusée : révision obsolète', titre='Erreur de sauvegarde')
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'Affichage impossible|Historique indisponible'):
                            self.form.finaliser_recherche([{'titre': 'Offre'}])
                    self.verifier_nettoyage()
                    if panne == 'traitement':
                        self.form.afficher_offres = original
                    self.verifier_ticks_et_relance()

    def test_f_incertitude_temporaire_deux_modes(self):
        for mode in ('cpv', 'classique'):
            for statut in (None, RuntimeError('Statut temporairement inaccessible')):
                with self.subTest(mode=mode, statut=statut):
                    self.preparer(mode)
                    self.form.lancer_recherche()
                    self.task.get_state.side_effect = RuntimeError('Suivi temporairement inaccessible')
                    self.statut = statut
                    self.form.timer_recherche_progress_tick()
                    self.assertIs(self.form.task_recherche, self.task)
                    self.assertTrue(self.form._recherche_en_cours)
                    self.assertFalse(self.form.f.navigation_link_search_go.enabled)
                    self.assertEqual(self.form.timer_recherche_progress.interval, 1)
                    self.assertFalse(self.form.column_panel_saisie_recherche.visible)
                    self.assertTrue(self.form.column_panel_param_summary.visible)
                    self.espace['afficher_information'].assert_not_called()
                    self.espace['afficher_avertissement'].assert_not_called()
                    self.assertEqual(self.lire_criteres(), self.criteres)
                    self.task.get_state.side_effect = None
                    self.form.timer_recherche_progress_tick()
                    self.assertIs(self.form.task_recherche, self.task)
                    self.assertTrue(self.form._recherche_en_cours)
                    self.assertEqual(self.form.timer_recherche_progress.interval, 1)
                    self.assertFalse(self.form.f.navigation_link_search_go.enabled)
                    self.assertEqual(self.task.get_state.call_count, 2)
                    self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs['etat'], 'running')
                    # Une erreur terminale ultérieure permet enfin le nettoyage.
                    self.task.get_state.side_effect = RuntimeError('Échec définitif')
                    self.statut = 'failed'
                    self.form.timer_recherche_progress_tick()
                    self.verifier_nettoyage()
                    self.verifier_ticks_et_relance()


if __name__ == '__main__':
    unittest.main()
