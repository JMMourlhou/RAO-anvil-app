"""Compteur de résultats : méthodes de la Form, composants et transport simulés."""
import unittest
from unittest.mock import Mock
import test_search_recherche_cpv as support


class TestsCompteurOffres(unittest.TestCase):
    def setUp(self):
        self.p = support.TestsRechercheCPV()
        self.p.setUp()
        self.p.lancer()
        self.form = self.p.form

    def verifier_compteur(self, nb):
        self.assertEqual(self.form.text_nb_offres.visible, nb > 0)
        self.assertEqual(self.form.data_grid_1.visible, nb > 0)
        attendu = '0 offre' if nb == 0 else '1 offre retenue' if nb == 1 else f'{nb} offres retenues'
        self.assertEqual(self.form.text_nb_offres.text, attendu)
        self.assertEqual(len(self.form.repeating_panel_offres.items), nb)

    def test_cpv_complete_et_tick_tardif(self):
        for nb in (0, 1, 20):
            with self.subTest(nb=nb):
                self.setUp()
                self.form.traiter_offres_cpv_apres_background(self.p.resultat([{'titre':'Offre'}]*nb, statut_collecte='complete'))
                self.verifier_compteur(nb)
                message = self.form.afficher_progression_recherche.call_args.kwargs['ligne_1']
                self.assertEqual(message, 'Recherche terminée' if nb else "Pas d'offres correspondant aux critères")
                self.form.timer_recherche_progress_tick()
                self.verifier_compteur(nb)
                self.assertEqual(self.form.timer_recherche_progress.interval, 0)
                self.assertTrue(self.form.f.navigation_link_search_go.enabled)

    def test_cpv_partielle(self):
        for nb in (0, 20):
            with self.subTest(nb=nb):
                self.setUp()
                self.form.traiter_offres_cpv_apres_background(self.p.resultat([{'titre':'Offre'}]*nb, statut_collecte='partielle'))
                self.verifier_compteur(nb)
                message = self.form.afficher_progression_recherche.call_args.kwargs['ligne_1']
                self.assertIn("certaines annonces n'ont pas pu être analysées".lower(), message.lower())
                self.form.timer_recherche_progress_tick()
                self.verifier_compteur(nb)
                self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs['ligne_1'], message)

    def test_classique(self):
        self.form._ctx_recherche = dict(mode_recherche='classique', mots_obligatoires=[], mots_ou=[], mots_exclus=[], selected_platformes=['BOAMP'], periode=30, departements=[])
        self.form.finaliser_recherche([{'titre':'Offre'}]*20)
        self.verifier_compteur(20)
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs['ligne_1'], '20 offres retenues')

    def test_restaurer_offres_sans_task_ni_sauvegarde(self):
        self.form.deverrouiller_recherche()
        self.p.serveur.reset_mock()
        offres = [{'titre':'A', 'vu':True}, {'titre':'B', 'vu':False}]
        self.form.afficher_offres(offres)
        self.form.restaurer_avertissement_collecte(dict(mode_recherche='cpv', statut_collecte='partielle', message_collecte='Avertissement'))
        self.verifier_compteur(2)
        self.assertEqual([o['vu'] for o in self.form.list_offres], [True, False])
        self.p.serveur.assert_not_called()
        self.assertIsNone(self.form.task_recherche)

    def test_suppression_actualise_compteur(self):
        self.p.espace['demander_choix'] = Mock(return_value=True)
        self.form.sauver_offres_dans_histo = Mock(return_value=True)
        self.form.afficher_offres([{'titre':'A','lien':'a'}, {'titre':'B','lien':'b'}])
        self.form.del_offre_affichee(item=self.form.list_offres[0])
        self.verifier_compteur(1)
        self.form.del_offre_affichee(item=self.form.list_offres[0])
        self.verifier_compteur(0)

    def test_nouveau_lancement_masque_ancien_compteur(self):
        for mode in ('cpv', 'classique'):
            with self.subTest(mode=mode):
                self.setUp()
                self.form.traiter_offres_cpv_apres_background(self.p.resultat([{'titre':'Offre'}]))
                self.verifier_compteur(1)
                if mode == 'classique':
                    self.form.cpv_selectionnes = []
                self.p.lancer()
                self.assertFalse(self.form.text_nb_offres.visible)
