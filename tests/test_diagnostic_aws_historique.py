"""Tests de sécurité sans réseau, tables ni Tasks réelles."""
import importlib.util
import json
from pathlib import Path
from types import ModuleType
import unittest
from unittest.mock import Mock, patch


class TestsDiagnosticAWS(unittest.TestCase):
    def setUp(self):
        anvil = ModuleType('anvil')
        self.server = ModuleType('anvil.server')
        self.users = ModuleType('anvil.users')
        self.server.BackgroundTaskNotFound = type('BackgroundTaskNotFound', (Exception,), {})
        self.registered = []

        def register(function):
            self.registered.append(function.__name__)
            return function

        self.server.callable = register
        self.server.get_background_task = Mock()
        self.users.get_user = Mock(return_value={'role': 'A'})
        anvil.server, anvil.users = self.server, self.users
        modules = {'anvil': anvil, 'anvil.server': self.server, 'anvil.users': self.users}
        path = Path(__file__).resolve().parents[1] / 'server_code/Diagnostic_AWS_Historique.py'
        spec = importlib.util.spec_from_file_location('diagnostic_under_test', path)
        self.api = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', modules):
            spec.loader.exec_module(self.api)
        self.task = Mock(spec=['get_termination_status', 'get_return_value'])
        self.task.get_termination_status.return_value = 'completed'
        self.task.get_return_value.return_value = {}
        self.server.get_background_task.return_value = self.task

    def test_import_sans_consultation(self):
        self.users.get_user.assert_not_called()
        self.server.get_background_task.assert_not_called()
        self.assertEqual(self.registered, ['consulter_diagnostics_aws_historiques'])

    def test_refus_avant_consultation(self):
        for user in (None, {'role': 'C'}, {'role': 'a'}, {'role': None}):
            with self.subTest(user=user):
                self.users.get_user.return_value = user
                with self.assertRaises(PermissionError):
                    self.api.consulter_diagnostics_aws_historiques()
                self.server.get_background_task.assert_not_called()

    def test_arguments_navigateur_refuses(self):
        with self.assertRaises(TypeError):
            self.api.consulter_diagnostics_aws_historiques(role='A', task_id='autre')
        self.server.get_background_task.assert_not_called()

    def test_uniquement_deux_tasks(self):
        self.api.consulter_diagnostics_aws_historiques()
        self.assertEqual(self.server.get_background_task.call_args_list,
                         [unittest.mock.call(task_id) for _, task_id in self.api._TASKS])

    def test_non_terminees_sans_lecture_retour(self):
        for statut in (None, 'failed', 'killed', 'missing'):
            self.task.get_termination_status.return_value = statut
            self.api.consulter_diagnostics_aws_historiques()
        self.task.get_return_value.assert_not_called()

    def test_disparition_aux_trois_etapes(self):
        for methode in (self.server.get_background_task, self.task.get_termination_status,
                        self.task.get_return_value):
            methode.side_effect = self.server.BackgroundTaskNotFound('SECRET')
            rapports = self.api.consulter_diagnostics_aws_historiques()
            self.assertTrue(all(not rapport['accessible'] for rapport in rapports))
            self.assertNotIn('SECRET', json.dumps(rapports))
            methode.side_effect = None

    def test_retour_absent_ou_invalide(self):
        for resultat in (None, [], 'SECRET'):
            self.task.get_return_value.return_value = resultat
            rapports = self.api.consulter_diagnostics_aws_historiques()
            self.assertTrue(all(not rapport['resultat_exploitable'] for rapport in rapports))
            self.assertNotIn('SECRET', json.dumps(rapports))

    def test_expurgation_et_compteurs_presents(self):
        self.task.get_return_value.return_value = {
            'ok': True, 'statut_collecte': 'partielle', 'message_collecte': 'SECRET',
            'offres': [{'email': 'SECRET'}],
            'portails': {'gm': {'offres_conservees': 0, 'nb_offres': True, 'url': 'SECRET'},
                         'SECRET': {'fiches_verifiees': 2, 'motif': 'SECRET'}},
            'anomalies': [{'portail': 'gm', 'etape': 'format', 'motif': 'SECRET'},
                          {'portail': 'ml', 'etape': 'cpv', 'url': 'SECRET'},
                          {'portail': 'SECRET', 'etape': 'SECRET'}],
        }
        rapports = self.api.consulter_diagnostics_aws_historiques()
        self.assertNotIn('SECRET', json.dumps(rapports))
        bilan = rapports[0]['bilan']
        self.assertEqual(bilan['portails'][0]['compteurs'], {'offres_conservees': 0})
        self.assertEqual(bilan['portails'][1]['portail'], 'portail_non_reconnu')
        self.assertEqual(bilan['anomalies_par_portail_et_etape'][1]['portail'], 'ml')

    def test_structures_inconnues_et_champs_absents(self):
        self.task.get_return_value.return_value = {'portails': ['SECRET'], 'anomalies': ['SECRET']}
        rapports = self.api.consulter_diagnostics_aws_historiques()
        self.assertNotIn('SECRET', json.dumps(rapports))
        self.assertIn('ok', rapports[0]['champs_absents'])
        self.assertEqual(rapports[0]['bilan']['portails'][0]['structure_reconnue'], False)

    def test_erreur_inattendue_remonte(self):
        self.task.get_return_value.side_effect = RuntimeError('incident technique')
        with self.assertRaises(RuntimeError):
            self.api.consulter_diagnostics_aws_historiques()

    def test_sept_portails_et_valeurs_reelles(self):
        portails = ('gm', 'ml', 'nr', 'so', 'dl', 'mp74', 'ldm')
        self.task.get_return_value.return_value = {'portails': {
            portail: {'nombre_offres': 0, 'nombre_anomalies': 3,
                      'nombre_avis_verifies': 7, 'candidats_parcourus': True,
                      'collecte_exploitable': False}
            for portail in portails
        }}
        bilan = self.api.consulter_diagnostics_aws_historiques()[0]['bilan']
        self.assertEqual([ligne['portail'] for ligne in bilan['portails']], list(portails))
        for ligne in bilan['portails']:
            self.assertEqual(ligne['compteurs'], {
                'nombre_offres': 0, 'nombre_anomalies': 3, 'nombre_avis_verifies': 7})
            self.assertIs(ligne['candidats_parcourus'], True)
            self.assertIs(ligne['collecte_exploitable'], False)

    def test_champs_absents_et_types_invalides_non_inventes(self):
        for valeur in (None, True, -1, 2.5, 'SECRET', [], {}):
            self.task.get_return_value.return_value = {'portails': {'gm': {
                'nombre_offres': valeur, 'candidats_parcourus': 1,
                'collecte_exploitable': 'false'}}}
            ligne = self.api.consulter_diagnostics_aws_historiques()[0]['bilan']['portails'][0]
            self.assertEqual(ligne['compteurs'], {})
            self.assertNotIn('candidats_parcourus', ligne)
            self.assertNotIn('collecte_exploitable', ligne)

    def test_motifs_incertains_expurges_et_agreges(self):
        for motif in ('SECRET https://exemple.invalid cle', 'CPV absent', None, [], {}):
            self.task.get_return_value.return_value = {'anomalies': [
                {'portail': 'mp74', 'etape': 'cpv', 'motif': motif},
                {'portail': 'mp74', 'etape': 'cpv', 'motif': motif},
            ]}
            bilan = self.api.consulter_diagnostics_aws_historiques()[0]['bilan']
            self.assertEqual(bilan['anomalies_par_portail_et_categorie'], [{
                'portail': 'mp74', 'etape': 'cpv', 'categorie': 'motif_non_classe', 'nombre': 2}])
            self.assertNotIn('SECRET', json.dumps(bilan))
            self.assertNotIn('CPV absent', json.dumps(bilan))

    def test_portails_inconnus_liste_et_structures_malformees(self):
        self.task.get_return_value.return_value = {
            'portails': [{'portail': 'nr', 'nombre_offres': 4},
                         {'portail': 'SECRET', 'nombre_anomalies': 2}],
            'anomalies': [{'portail': ['SECRET'], 'etape': {'SECRET': 1}, 'motif': 'SECRET'}],
        }
        bilan = self.api.consulter_diagnostics_aws_historiques()[0]['bilan']
        self.assertEqual(bilan['portails'][0]['portail'], 'nr')
        self.assertEqual(bilan['portails'][1]['portail'], 'portail_non_reconnu')
        self.assertNotIn('SECRET', json.dumps(bilan))

    def enveloppe_papier(self, message):
        return ('Collecte AWS CPV incomplète : détail https://exemple.invalid/SECRET '
                ': Collecte AWS CPV incomplète : ' + message)

    def test_messages_exacts_et_suffixes_refuses(self):
        messages_vus = set()
        for categorie, messages in self.api.MESSAGES_PAR_CATEGORIE.items():
            for message in messages:
                with self.subTest(message=message):
                    self.assertNotIn(message, messages_vus)
                    messages_vus.add(message)
                    motif = self.enveloppe_papier(message)
                    self.assertEqual(self.api.classifier_motif_format(motif), categorie)
                    for variante in (motif + ' suffixe', motif + '\n', ' ' + motif,
                                     self.enveloppe_papier(message.upper())):
                        self.assertEqual(self.api.classifier_motif_format(variante), 'motif_non_classe')
        self.assertEqual(len(self.api.MESSAGES_PAR_CATEGORIE), 17)

    def test_refus_global_et_gabarits_variables(self):
        for protocole in ('http', 'https'):
            motif = f'Collecte AWS CPV incomplète : format de détail non pris en charge : {protocole}://exemple.invalid/SECRET'
            self.assertEqual(self.api.classifier_motif_format(motif), 'format_global_non_reconnu')
            self.assertEqual(self.api.classifier_motif_format(motif + ' suffixe'), 'motif_non_classe')
        motif = self.enveloppe_papier('champ flux papier absent ou contradictoire : SECRET personne@example.invalid')
        self.assertEqual(self.api.classifier_motif_format(motif), 'papier_champs_invalides')
        for lot in ('1', 'AB123', 'a0Z'):
            motif = self.enveloppe_papier(f'échéance dans le contexte du lot {lot} non prise en charge')
            self.assertEqual(self.api.classifier_motif_format(motif), 'papier_date_contexte_invalide')

    def test_inconnus_ambigus_et_enveloppes_malformees(self):
        message = 'échéance flux papier invalide'
        motif = self.enveloppe_papier(message)
        inconnus = (
            None, 42, True, [], {}, '', message,
            self.enveloppe_papier('structure de détail flux papier non reconnue'),
            self.enveloppe_papier('structure de lot CPV non reconnue'),
            motif.replace('https://', 'ftp://'), motif.replace('incomplète', 'incomplete'),
            motif.replace(' : Collecte', ': Collecte'),
            self.enveloppe_papier('champ flux papier absent ou contradictoire : '),
            self.enveloppe_papier('champ flux papier absent ou contradictoire : SECRET\nSUITE'),
            self.enveloppe_papier('échéance dans le contexte du lot A-1 non prise en charge'),
            self.enveloppe_papier('échéance dans le contexte du lot é1 non prise en charge'),
            self.enveloppe_papier('échéance dans le contexte du lot 1 non prise en charge suffixe'),
        )
        for valeur in inconnus:
            with self.subTest(valeur=valeur):
                self.assertEqual(self.api.classifier_motif_format(valeur), 'motif_non_classe')

    def test_classification_limitee_a_format(self):
        motif = self.enveloppe_papier('échéance flux papier invalide')
        with patch.object(self.api, 'classifier_motif_format', wraps=self.api.classifier_motif_format) as classer:
            for etape in ('cpv', 'recherche', 'FORMAT', None, [], {}):
                self.assertEqual(self.api._classer_motif(etape, motif), 'motif_non_classe')
            classer.assert_not_called()
            self.assertEqual(self.api._classer_motif('format', motif), 'papier_date_valeur_invalide')
            classer.assert_called_once_with(motif)

    def test_retour_complet_expurge_avec_categories_connues(self):
        motif = self.enveloppe_papier('champ flux papier absent ou contradictoire : SECRET personne@example.invalid')
        self.task.get_return_value.return_value = {
            'ok': True, 'statut_collecte': 'partielle', 'message_collecte': 'SECRET',
            'portails': {'ldm': {'nombre_offres': 0, 'nombre_anomalies': 2,
                                'candidats_parcourus': True, 'collecte_exploitable': False,
                                'url': 'https://exemple.invalid/SECRET'}},
            'anomalies': [{'portail': 'ldm', 'etape': 'format', 'motif': motif, 'cle': 'SECRET'}] * 2,
        }
        rapports = self.api.consulter_diagnostics_aws_historiques()
        self.assertEqual(rapports[0]['bilan']['anomalies_par_portail_et_categorie'], [{
            'portail': 'ldm', 'etape': 'format', 'categorie': 'papier_champs_invalides', 'nombre': 2}])
        rendu = json.dumps(rapports)
        for interdit in ('SECRET', 'https://', 'personne@', 'champ flux papier', 'motif"'):
            self.assertNotIn(interdit, rendu)


if __name__ == '__main__':
    unittest.main()
