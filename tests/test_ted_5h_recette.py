"""Recette TED 5H consolidée, avec Form et serveur réels, transport/table simulés."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import test_search_recherche_cpv as client
import test_search_collecte_historique as historique_support
from test_search_reset_historique import charger_initialisation


class TestsRecetteTED5H(unittest.TestCase):
    def preparer(self, mode):
        """Branche la sauvegarde réelle sur une table mémoire, sans appel réseau."""
        self.backend = historique_support.TestsHistoriqueCollecte()
        self.backend.setUp()
        self.client = client.TestsRechercheCPV()
        self.client.setUp()
        self.client.lancer()
        self.form = self.client.form
        if mode == 'classique':
            self.form._ctx_recherche = dict(
                mode_recherche=mode, selected_platformes=['BOAMP', 'TED'],
                periode=30, departements=[], mots_obligatoires=[],
                mots_ou=[], mots_exclus=[], cpv_selectionnes=[])
            for nom in ('filtrer_offres_exclues', 'build_offres_list',
                        'ajouter_correspondance_mots_ou', 'trier_offres_par_interet'):
                setattr(self.form, nom, Mock(side_effect=lambda offres, *args, **kwargs: offres))
        self.form.actualiser_bouton_veille_cpv = Mock()
        self.form.f.revenir_menu_apres_arret = Mock()
        self.appels_backup = []

        def transport(nom, *args, **kwargs):
            if nom != 'backup_requete':
                raise AssertionError('Appel non simulé : ' + nom)
            self.appels_backup.append(copy.deepcopy(kwargs))
            return self.backend.espace['backup_requete'](**kwargs)

        self.client.serveur.side_effect = transport
        self.task = Mock(spec=['get_state', 'is_completed', 'get_return_value'])
        self.task.get_state.return_value = dict(progress=70, source_en_cours='BOAMP', source_progress=40)
        self.task.is_completed.return_value = True
        self.form.task_recherche = self.task

    def test_collecte_sauvegarde_restauration_deux_modes(self):
        for mode in ('classique', 'cpv'):
            for statut in ('complete', 'partielle', 'echouee'):
                for offres in ([], [{'titre': 'Formation', 'source': 'BOAMP'}]):
                    with self.subTest(mode=mode, statut=statut, offres=offres):
                        self.preparer(mode)
                        original = dict(self.backend.row)
                        self.task.get_return_value.return_value = dict(
                            ok=statut != 'echouee', statut_collecte=statut,
                            message_collecte='Source indisponible' if statut != 'complete' else '', offres=offres)
                        self.form.timer_recherche_progress_tick()
                        self.assertIsNone(self.form.task_recherche)
                        self.assertEqual(self.form.timer_recherche_progress.interval, 0)
                        if statut == 'echouee':
                            self.assertEqual(self.backend.row, original)
                            self.assertEqual(self.appels_backup, [])
                            self.backend.table.get.assert_not_called()
                            continue
                        self.assertEqual(len(self.appels_backup), 1)
                        self.assertEqual(self.appels_backup[0]['statut_collecte'], statut)
                        self.assertEqual(self.backend.row['statut_collecte'], statut)
                        self.assertEqual(len(self.backend.row['offres']), len(offres))
                        api = charger_initialisation(self.backend.anvil, SimpleNamespace(
                            histo=self.backend.table, platformes=SimpleNamespace(search=lambda *args: [])))
                        api['CPV_API'] = SimpleNamespace(obtenir_libelles_cpv=lambda codes: {'ok': True, 'resultats': []})
                        historique = api['initialiser_form_search'](True)['histo']
                        self.assertEqual(historique['statut_collecte'], statut)
                        self.assertEqual(historique['offres'], self.backend.row['offres'])
                        self.form.afficher_progression_recherche.reset_mock()
                        self.form.restaurer_avertissement_collecte(historique)
                        if statut == 'partielle':
                            self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs['etat'], 'warning')
                        else:
                            self.form.afficher_progression_recherche.assert_not_called()
                        self.assertEqual(len(self.appels_backup), 1)

    def test_partielle_filtree_a_zero_conserve_statut_et_message(self):
        self.preparer('classique')
        self.form.filtrer_offres_exclues.return_value = []
        self.form.filtrer_offres_exclues.side_effect = None
        self.task.get_return_value.return_value = dict(ok=True, statut_collecte='partielle',
            message_collecte='TED indisponible', offres=[{'titre': 'Offre exclue'}])
        self.form.timer_recherche_progress_tick()
        self.assertEqual(self.backend.row['offres'], [])
        self.assertEqual(self.backend.row['statut_collecte'], 'partielle')
        self.assertEqual(self.backend.row['message_collecte'], 'TED indisponible')
        message = self.form.afficher_progression_recherche.call_args.kwargs
        self.assertEqual(message['etat'], 'warning')
        self.assertIn("absence d'offres non garantie", message['ligne_1'])

    def test_annulation_ignore_retour_et_preserve_historique(self):
        for mode in ('classique', 'cpv'):
            with self.subTest(mode=mode):
                self.preparer(mode)
                original = dict(self.backend.row)
                self.form.abandonner_recherche()
                self.form.timer_recherche_progress_tick()
                self.task.get_return_value.assert_not_called()
                self.assertEqual(self.appels_backup, [])
                self.assertEqual(self.backend.row, original)

    def test_refus_avant_acces_historique(self):
        for mode in ('classique', 'cpv'):
            for options in ({'statut_collecte': None}, {'statut_collecte': ''},
                            {'statut_collecte': 'echouee'}, {'statut_collecte': 'annulee'},
                            {'statut_collecte': 'inconnu'}, {'statut_collecte': 'partielle'},
                            {'statut_collecte': 'partielle', 'message_collecte': []},
                            {'offres': None}, {'offres': 'invalide'},
                            {'offres': [{'titre': 'Valide'}, None]}):
                with self.subTest(mode=mode, options=options):
                    b = historique_support.TestsHistoriqueCollecte()
                    b.setUp()
                    original = dict(b.row)
                    self.assertFalse(b.sauvegarder(mode_recherche=mode, **options)['ok'])
                    b.table.get.assert_not_called()
                    self.assertEqual(b.row, original)

    def test_statut_omis_refuse_sans_ecriture(self):
        b = historique_support.TestsHistoriqueCollecte()
        b.setUp()
        del b.arguments['statut_collecte']
        self.assertFalse(b.sauvegarder()['ok'])
        b.table.get.assert_not_called()
