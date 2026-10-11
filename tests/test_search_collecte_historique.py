"""Persistance et restitution de la collecte : serveur et Form réels, Anvil simulé."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import test_search_recherche_cpv as support
from test_search_reset_historique import charger_initialisation, Ligne


class TestsHistoriqueCollecte(unittest.TestCase):
    def setUp(self):
        self.row = Ligne(revision_recherche=0)
        self.table = SimpleNamespace(get=Mock(return_value=self.row))
        self.anvil = SimpleNamespace(users=SimpleNamespace(get_user=lambda: {'email': 'test@example.com'}))
        source = Path(__file__).resolve().parents[1] / 'server_code/Backup_param_recherche.py'
        arbre = ast.parse(source.read_text())
        fonctions = [n for n in arbre.body if isinstance(n, ast.FunctionDef)]
        for n in fonctions:
            n.decorator_list = []
        module = ast.fix_missing_locations(ast.Module(body=fonctions, type_ignores=[]))
        self.espace = dict(anvil=self.anvil, app_tables=SimpleNamespace(histo=self.table),
                           CPV_API=SimpleNamespace(valider_selection_cpv=lambda codes: {'ok': True, 'codes': codes}))
        exec(compile(module, str(source), 'exec'), self.espace)
        self.arguments = dict(sources=['BOAMP'], mots_cles='formation', mots_ou='', mots_exclus='',
                              nb_jours=30, departements='', date_heure='date-test', offres=[{'titre': 'A', 'vu': True}],
                              mode_recherche='cpv', cpv_selectionnes=['80560000'])

    def sauvegarder(self, **options):
        arguments = dict(self.arguments)
        arguments.update(options)
        return self.espace['backup_requete'](**arguments)

    def test_partielle_complete_classique_et_revision(self):
        self.assertTrue(self.sauvegarder(statut_collecte='partielle', message_collecte=' Avertissement ')['ok'])
        self.assertEqual(self.row['statut_collecte'], 'partielle')
        self.assertEqual(self.row['message_collecte'], 'Avertissement')
        self.assertEqual(self.row['offres'], self.arguments['offres'])
        self.assertEqual(self.row['revision_recherche'], 1)
        self.assertTrue(self.sauvegarder(statut_collecte='complete', message_collecte='Ancien avertissement')['ok'])
        self.assertEqual(self.row['message_collecte'], '')
        self.assertEqual(self.row['statut_collecte'], 'complete')
        self.sauvegarder(statut_collecte='partielle', message_collecte='Avertissement')
        self.assertTrue(self.sauvegarder(mode_recherche='classique')['ok'])
        self.assertEqual((self.row['statut_collecte'], self.row['message_collecte']), ('', ''))
        self.assertEqual(self.row['revision_recherche'], 4)
        self.table.get.assert_called_with(email='test@example.com')

    def test_ancien_client_et_refus_sans_ecriture(self):
        self.assertTrue(self.sauvegarder()['ok'])
        self.assertEqual(self.row['statut_collecte'], 'complete')
        original = dict(self.row)
        for statut, message in [('inconnu', ''), ('echouee', ''), ('partielle', ''), ('partielle', [])]:
            with self.subTest(statut=statut, message=message):
                self.assertFalse(self.sauvegarder(statut_collecte=statut, message_collecte=message)['ok'])
                self.assertEqual(self.row, original)

    def test_lecture_et_restauration_sans_task_ni_sauvegarde(self):
        for offres in ([], [{'titre': 'A', 'vu': True}, {'titre': 'B', 'vu': False}]):
            with self.subTest(offres=offres):
                self.sauvegarder(offres=offres, statut_collecte='partielle', message_collecte='Avertissement validé')
                api = charger_initialisation(self.anvil, SimpleNamespace(
                    histo=self.table, platformes=SimpleNamespace(search=lambda *args: [])))
                api['CPV_API'] = SimpleNamespace(obtenir_libelles_cpv=lambda codes: {'ok': True, 'resultats': []})
                historique = api['initialiser_form_search'](True)['histo']
                self.assertEqual(historique['offres'], offres)
                self.assertEqual(historique['statut_collecte'], 'partielle')
                p = support.TestsRechercheCPV()
                p.setUp()
                form = p.form
                form.label_jauge_globale = support.Composant()
                form._last_progress_role = None
                del form.afficher_progression_recherche
                form.regler_jauge = Mock()
                form.list_offres = offres
                form.restaurer_avertissement_collecte(historique)
                self.assertEqual(form.label_jauge_globale.text, 'Avertissement validé')
                self.assertEqual(form.list_offres, offres)
                self.assertIsNone(form.task_recherche)
                self.assertEqual(form.timer_recherche_progress.interval, 0)
                p.serveur.assert_not_called()
                self.assertFalse(any(c.args[1] == 100 for c in form.regler_jauge.call_args_list))

    def test_transmission_du_message_valide_uniquement(self):
        p = support.TestsRechercheCPV()
        p.setUp()
        p.lancer()
        p.form.traiter_offres_cpv_apres_background(p.resultat(
            statut_collecte='partielle', message_collecte='Diagnostic moteur', anomalies=['technique'], portails=['AWS']))
        arguments = p.serveur.call_args.kwargs
        self.assertEqual(arguments['statut_collecte'], 'partielle')
        self.assertEqual(arguments['message_collecte'], "Recherche incomplète — aucune offre récupérée. Certaines annonces n'ont pas pu être analysées.")
        self.assertNotIn('anomalies', arguments)
        self.assertNotIn('portails', arguments)

    def test_restaurations_classique_complete_et_ancienne_sans_avertissement(self):
        p = support.TestsRechercheCPV()
        p.setUp()
        for historique in ({'mode_recherche': 'classique', 'statut_collecte': 'partielle'},
                           {'mode_recherche': 'cpv', 'statut_collecte': 'complete'}, {'mode_recherche': 'cpv'}):
            p.form.restaurer_avertissement_collecte(historique)
        p.form.afficher_progression_recherche.assert_not_called()
