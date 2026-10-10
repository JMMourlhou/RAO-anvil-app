"""Progression CARIF isolée, sans réseau ni navigateur."""
import unittest
from unittest.mock import Mock
import test_search_recherche_cpv as support


class TestsProgressionCarif(unittest.TestCase):
    def preparer(self, mode):
        preparation = support.TestsRechercheCPV()
        preparation.setUp()
        self.form = preparation.form
        self.form._ctx_recherche = {'mode_recherche': mode}
        self.form.label_jauge_globale = support.Composant()
        self.form._last_progress_role = None
        del self.form.afficher_progression_recherche
        self.form.regler_jauge = Mock()
        # La veille est hors de cette simulation de progression.
        self.form.actualiser_bouton_veille_cpv = Mock()

    def afficher(self, progress=None, current=None, total=None, message='', source='CARIF-OREF', **options):
        self.form.afficher_progression_recherche(source_nom=source, progress_source=progress,
            source_current=current, source_total=total, ligne_2=message, progress_global=45, **options)

    def test_none_compteurs_et_messages_deux_modes(self):
        for mode in ('classique', 'cpv'):
            for current, total, texte in ((None, None, 'Recherche CARIF-OREF en cours...'),
                    (3, 12, 'CARIF-OREF — 3/12 éléments traités'),
                    (3, None, 'CARIF-OREF — 3 éléments traités'),
                    (0, 12, 'CARIF-OREF — 0/12 éléments traités'),
                    (3, 0, 'CARIF-OREF — 3 éléments traités')):
                with self.subTest(mode=mode, current=current, total=total):
                    self.preparer(mode)
                    self.afficher(current=current, total=total)
                    self.assertEqual(self.form.label_jauge_globale.text, texte)
                    self.assertIn('progress-gauge-indeterminate', self.form.label_jauge_globale.role)
                    self.form.regler_jauge.assert_not_called()
                    self.assertNotIn('%', texte)
            for message in ('CARIF-OREF PACA — 3 avis examinés',
                            'CARIF-OREF Occitanie — 3/12 fiches récupérées',
                            'CARIF-OREF Occitanie — 3 consultations terminées'):
                self.preparer(mode)
                self.afficher(current=3, total=12, message=message)
                self.assertEqual(self.form.label_jauge_globale.text, message)

    def test_zero_et_cent_determines(self):
        for mode in ('classique', 'cpv'):
            self.preparer(mode)
            self.afficher()
            for progress in (0, 100):
                self.afficher(progress=progress)
                self.assertEqual(self.form.label_jauge_globale.role, 'progress-gauge-global')
                self.assertEqual(self.form.regler_jauge.call_args.args[1], progress)

    def test_transitions_et_etats_finaux(self):
        for mode in ('classique', 'cpv'):
            self.preparer(mode)
            for message, current in (('PACA — 12 avis examinés', 12),
                                     ('Occitanie — 0/20 fiches récupérées', 0),
                                     ('Occitanie — 2 consultations terminées', 2)):
                self.afficher(current=current, message=message)
                self.assertEqual(self.form.label_jauge_globale.text, message)
                self.form.regler_jauge.assert_not_called()
            self.afficher(source='TED', progress=37)
            self.assertEqual(self.form.label_jauge_globale.role, 'progress-gauge-global')
            self.assertEqual(self.form.regler_jauge.call_args.args[1], 37)
            for etat in ('success', 'error', 'stopping'):
                self.afficher()
                self.afficher(etat=etat, ligne_1='Fin', afficher_jauges=False)
                self.assertEqual(self.form.label_jauge_globale.role, 'progress-gauge-global')
            self.afficher()
            self.form.deverrouiller_recherche()
            self.assertEqual(self.form.label_jauge_globale.role, 'progress-gauge-global')
            self.assertEqual(self.form.timer_recherche_progress.interval, 0)
            self.afficher()
            self.form.f.revenir_menu_apres_arret = Mock()
            self.form.abandonner_recherche()
            self.assertEqual(self.form.label_jauge_globale.role, 'progress-gauge-global')
            self.assertEqual(self.form.timer_recherche_progress.interval, 0)
            self.form.f.revenir_menu_apres_arret.assert_called_once_with(self.form)

    def test_timer_conserve_none(self):
        self.preparer('cpv')
        self.form.task_recherche = Mock(spec=['get_state', 'is_completed'])
        self.form.task_recherche.get_state.return_value = dict(progress=45, source_progress=None,
            source_en_cours='CARIF-OREF', source_current=3, source_total=12,
            message='Occitanie — 3/12 fiches récupérées')
        self.form.task_recherche.is_completed.return_value = False
        self.form.afficher_progression_recherche = Mock(wraps=self.form.afficher_progression_recherche)
        self.form.timer_recherche_progress_tick()
        self.assertIsNone(self.form.afficher_progression_recherche.call_args.kwargs['progress_source'])
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs['progress_global'], 45)
        self.form.regler_jauge.assert_not_called()
        self.assertEqual(self.form.label_jauge_globale.text, 'Occitanie — 3/12 fiches récupérées')
