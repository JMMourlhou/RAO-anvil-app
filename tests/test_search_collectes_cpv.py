"""Résultats CPV partiels : méthodes réelles, sans serveur ou navigateur."""
import unittest
from unittest.mock import Mock
import test_search_recherche_cpv as support


class TestsCollectesCPV(unittest.TestCase):
    def setUp(self):
        self.preparation = support.TestsRechercheCPV()
        self.preparation.setUp()
        self.preparation.lancer()
        self.form = self.preparation.form
        self.form.label_jauge_globale = support.Composant()
        self.form._last_progress_role = None
        del self.form.afficher_progression_recherche
        self.form.regler_jauge = Mock()
        self.form.sauvegarder_derniere_recherche = Mock(return_value=True)

    def resultat(self, offres=None, **options):
        return self.preparation.resultat(offres, **options)

    def nettoyage(self):
        self.assertFalse(self.form._recherche_en_cours)
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)
        self.assertIsNone(self.form.task_recherche)
        self.assertTrue(self.form.f.navigation_link_search_go.enabled)
        self.assertNotIn('progress-gauge-indeterminate', self.form.label_jauge_globale.role)

    def test_complete_et_ancienne_reponse(self):
        for statut in ('complete', 'ancien'):
            for offres in ([], [{'titre': 'Offre'}]):
                with self.subTest(statut=statut, offres=offres):
                    self.setUp()
                    options = {} if statut == 'ancien' else dict(statut_collecte=statut)
                    self.form.traiter_offres_cpv_apres_background(self.resultat(offres, **options))
                    self.assertEqual(self.form.label_jauge_globale.text,
                                     'Recherche terminée' if offres else "Pas d'offres correspondant aux critères")
                    self.assertEqual(len(self.form.list_offres), len(offres))
                    self.nettoyage()

    def test_partielle_avertissement_persistant_et_offres_conservees(self):
        for offres in ([], [{'titre': 'Offre', 'champ_metier': 42}] * 2):
            with self.subTest(offres=offres):
                self.setUp()
                self.form.traiter_offres_cpv_apres_background(self.resultat(
                    offres, statut_collecte='partielle', message_collecte='Message moteur',
                    anomalies=['DETAIL TECHNIQUE'], portails=['PORTAIL TECHNIQUE']))
                attendu = ("Recherche partiellement terminée — certaines annonces n'ont pas pu être analysées."
                           if offres else "Recherche incomplète — aucune offre récupérée. Certaines annonces n'ont pas pu être analysées.")
                self.assertEqual(self.form.label_jauge_globale.text, attendu)
                self.assertEqual(len(self.form.list_offres), len(offres))
                for offre in self.form.list_offres:
                    self.assertEqual(offre['champ_metier'], 42)
                self.form.sauvegarder_derniere_recherche.assert_called_once_with(self.form.list_offres)
                self.assertFalse(any(call.args[1] == 100 for call in self.form.regler_jauge.call_args_list))
                self.nettoyage()
                self.form.timer_recherche_progress_tick()
                self.assertEqual(self.form.label_jauge_globale.text, attendu)
                self.nettoyage()

    def test_echec_et_contradictions(self):
        for ok, statut in ((False, 'echouee'), (True, 'echouee'), (False, 'complete'), (False, 'partielle')):
            with self.subTest(ok=ok, statut=statut):
                self.setUp()
                self.form.traiter_offres_cpv_apres_background(self.resultat(
                    [{'titre': 'Offre'}], ok=ok, statut_collecte=statut, message_collecte='Collecte impossible'))
                self.assertEqual(self.form.list_offres, [])
                self.assertIn('Collecte impossible', self.form.label_jauge_globale.text)
                self.assertEqual(self.form._last_progress_role, 'progress-search-box-error')
                self.form.sauvegarder_derniere_recherche.assert_not_called()
                self.nettoyage()

    def test_statuts_invalides(self):
        for statut in (None, '', 'inconnu', True, 1, [], {}):
            with self.subTest(statut=statut):
                self.setUp()
                with self.assertRaisesRegex(ValueError, 'Statut de collecte'):
                    self.form.traiter_offres_cpv_apres_background(self.resultat(statut_collecte=statut))
                self.form.sauvegarder_derniere_recherche.assert_not_called()
                self.nettoyage()

    def test_message_invalide(self):
        with self.assertRaisesRegex(ValueError, 'Message de collecte'):
            self.form.traiter_offres_cpv_apres_background(self.resultat(statut_collecte='partielle', message_collecte=[]))
        self.nettoyage()

    def test_sauvegarde_refusee_ou_exception(self):
        for exception in (False, True):
            with self.subTest(exception=exception):
                self.setUp()
                if exception:
                    self.form.sauvegarder_derniere_recherche.side_effect = RuntimeError('Sauvegarde impossible')
                    with self.assertRaisesRegex(RuntimeError, 'Sauvegarde impossible'):
                        self.form.traiter_offres_cpv_apres_background(self.resultat(statut_collecte='partielle'))
                else:
                    self.form.sauvegarder_derniere_recherche.return_value = False
                    self.form.traiter_offres_cpv_apres_background(self.resultat(statut_collecte='partielle'))
                self.assertNotIn('Recherche incomplète', self.form.label_jauge_globale.text)
                self.nettoyage()

    def test_form_abandonnee_ignore_resultat(self):
        self.form._recherche_abandonnee = True
        texte = self.form.label_jauge_globale.text
        self.form.traiter_offres_cpv_apres_background(self.resultat(statut_collecte='partielle'))
        self.form.sauvegarder_derniere_recherche.assert_not_called()
        self.assertEqual(self.form.label_jauge_globale.text, texte)
