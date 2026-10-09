"""Caractérisation de l'alternance : méthodes réelles et composants simulés."""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid

import test_search_recherche_cpv as support


class TestsAlternance(unittest.TestCase):
    def setUp(self):
        preparation = support.TestsRechercheCPV()
        preparation.setUp()
        self.form = preparation.form
        self.espace = preparation.espace
        self.resultat = preparation.resultat
        self.espace['uuid'] = uuid
        self.espace['definir_titre_column_panel'] = Mock()
        for nom in ('column_panel_saisie_recherche column_panel_param_summary '
                    'label_summary_cpv label_summary_obligatoires label_summary_ou '
                    'label_summary_periode label_summary_departements label_summary_exclus').split():
            setattr(self.form, nom, support.Composant())
        self.form.actualiser_bouton_veille_cpv = Mock()
        self.form.sauvegarder_derniere_recherche = Mock(return_value=True)
        self.form.task_recherche = Mock()
        self.form.task_recherche.get_state.return_value = {}
        self.form.task_recherche.is_completed.return_value = False
        self.task = self.form.task_recherche
        self.espace['anvil'].server.call.side_effect = self.appel_serveur
        for nom in ('AppOfflineError', 'SessionExpiredError', 'UplinkDisconnectedError',
                    'TimeoutError', 'RuntimeUnavailableError', 'NoServerFunctionError'):
            setattr(self.espace['anvil'].server, nom, type(nom, (Exception,), {}))
        self.form.afficher_saisie_recherche()

    def appel_serveur(self, nom, *args, **kwargs):
        if nom == 'enregistrer_recherche_rao':
            return {'ok': True}
        return self.task

    def verifier_saisie(self, visible):
        self.assertEqual(self.form.column_panel_saisie_recherche.visible, visible)
        self.assertEqual(self.form.column_panel_param_summary.visible, not visible)
        if visible:
            self.assertTrue(self.form.column_panel_params.visible)
            self.assertTrue(self.form.bloc_selecteur_cpv_complet.visible)

    def classique(self):
        self.form.cpv_selectionnes = []
        self.form.text_box_mots_obligatoires_cpv.text = 'formation'

    def initialiser_affichage(self, origine):
        # Exécuter les branches réelles d'affichage de __init__, sans login/DOM.
        classe = next(n for n in ast.parse(support.SOURCE.read_text()).body
                      if isinstance(n, ast.ClassDef) and n.name == 'search')
        initialisation = next(n for n in classe.body if isinstance(n, ast.FunctionDef)
                              and n.name == '__init__')
        branches = [n for n in initialisation.body if isinstance(n, ast.If)
                    and isinstance(n.test, ast.Compare)
                    and isinstance(n.test.left, ast.Name) and n.test.left.id == 'origine']
        contexte = dict(self.espace, self=self.form, origine=origine, mk='',
                        checkbox_on_off=False, bt_mail_visible=False,
                        derniere_ligne={})
        module = ast.fix_missing_locations(ast.Module(body=branches, type_ignores=[]))
        exec(compile(module, str(support.SOURCE), 'exec'), contexte)

    def test_ouverture_normale(self):
        self.form.maj_bouton_recherche_visible = Mock()
        self.form.afficher_saisie_recherche(False)
        self.initialiser_affichage('')
        self.verifier_saisie(True)

    def test_lancement_cpv_et_classique_avant_reception_task(self):
        for mode in ('cpv', 'classique'):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == 'classique':
                    self.classique()
                def appel(nom, *args, **kwargs):
                    self.verifier_saisie(False)
                    return self.appel_serveur(nom, *args, **kwargs)
                self.espace['anvil'].server.call.side_effect = appel
                self.form.lancer_recherche()
                self.verifier_saisie(False)
                self.form.afficher_offres([])
                self.verifier_saisie(False)
                self.form.deverrouiller_recherche()
                self.verifier_saisie(False)

    def test_fin_avec_et_sans_offres_deux_modes(self):
        for mode in ('cpv', 'classique'):
            for offres in ([], [{'titre': 'Offre'}]):
                with self.subTest(mode=mode, offres=offres):
                    self.setUp()
                    if mode == 'classique':
                        self.classique()
                    self.form.lancer_recherche()
                    self.form.finaliser_recherche(offres)
                    self.verifier_saisie(not bool(offres))

    def test_erreurs_avant_task_deux_modes(self):
        for mode in ('cpv', 'classique'):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == 'classique':
                    self.classique()
                self.espace['anvil'].server.call.side_effect = RuntimeError('panne')
                with self.assertRaisesRegex(RuntimeError, 'panne'):
                    self.form.lancer_recherche()
                self.verifier_saisie(True)
                self.assertFalse(self.form._recherche_en_cours)

    def test_erreur_background_et_statut_inconnu(self):
        self.form.lancer_recherche()
        self.task.get_state.side_effect = RuntimeError('suivi')
        self.form.lire_statut_tache_recherche = Mock(return_value=None)
        self.form.timer_recherche_progress_tick()
        self.verifier_saisie(False)
        self.assertIs(self.form.task_recherche, self.task)
        self.form.lire_statut_tache_recherche.return_value = 'failed'
        self.form.timer_recherche_progress_tick()
        self.verifier_saisie(True)

    def test_erreur_lecture_resultat(self):
        self.form.lancer_recherche()
        self.task.is_completed.return_value = True
        self.task.get_return_value.side_effect = RuntimeError('résultat')
        self.form.timer_recherche_progress_tick()
        self.verifier_saisie(True)

    def test_erreur_cpv_et_reponse_mal_formee(self):
        for resultat in (self.resultat(ok=False), None):
            with self.subTest(resultat=resultat):
                self.setUp()
                self.form.lancer_recherche()
                if resultat is None:
                    with self.assertRaises(ValueError):
                        self.form.traiter_offres_cpv_apres_background(resultat)
                else:
                    self.form.traiter_offres_cpv_apres_background(resultat)
                self.verifier_saisie(True)

    def test_erreur_traitement_et_sauvegarde(self):
        for methode in ('sauvegarder_derniere_recherche', 'afficher_offres'):
            with self.subTest(methode=methode):
                self.setUp()
                self.form.lancer_recherche()
                setattr(self.form, methode, Mock(side_effect=RuntimeError('finalisation')))
                with self.assertRaises(RuntimeError):
                    self.form.finaliser_recherche([{'titre': 'Offre'}])
                self.verifier_saisie(True)

    def test_refus_sauvegarde_et_erreur_traitement_classique(self):
        self.classique()
        self.form.lancer_recherche()
        self.form.sauvegarder_derniere_recherche.return_value = False
        self.assertFalse(self.form.finaliser_recherche([{'titre': 'Offre'}]))
        self.verifier_saisie(True)
        self.form.lancer_recherche()
        self.task.is_completed.return_value = True
        self.task.get_return_value.return_value = {'offres': [{'titre': 'Offre'}]}
        self.form.traiter_offres_recuperees_apres_background = Mock(side_effect=RuntimeError('traitement'))
        self.form.timer_recherche_progress_tick()
        self.verifier_saisie(True)

    def test_tick_tardif_apres_succes_conserve_resume(self):
        self.form.lancer_recherche()
        self.form.finaliser_recherche([{'titre': 'Offre'}])
        self.form.timer_recherche_progress_tick()
        self.verifier_saisie(False)

    def test_retour_parametres_conserve_contexte_et_historique(self):
        self.form.lancer_recherche()
        self.form.finaliser_recherche([{'titre': 'Offre'}])
        avant = copy.deepcopy(self.form._ctx_recherche)
        identifiant = self.form.histo_id
        self.espace['demander_choix'] = Mock(return_value=True)
        self.form.text_box_recherche_cpv = support.Composant()
        self.form.button_del_all_click()
        self.verifier_saisie(True)
        self.assertEqual(self.form._ctx_recherche, avant)
        self.assertEqual(self.form.histo_id, identifiant)
        self.form.sauvegarder_derniere_recherche.assert_called_once()

    def test_derniere_recherche_avec_offres_et_resume_fige(self):
        self.form.lancer_recherche()
        self.form.list_offres = [{'titre': 'Sauvegardée'}]
        self.form.text_box_mots_obligatoires_cpv.text = 'Autre saisie'
        self.initialiser_affichage('check')
        self.verifier_saisie(False)
        self.assertNotIn('Autre saisie', self.form.label_summary_obligatoires.text)

    def test_annulation_en_attente_ne_change_pas_affichage(self):
        self.form.lancer_recherche()
        self.form._annulation_recherche_demandee = True
        self.form.timer_recherche_progress_tick()
        self.verifier_saisie(False)
        self.form.f.revenir_menu_apres_arret = Mock()
        self.form.abandonner_recherche()
        self.assertTrue(self.form._recherche_abandonnee)
        self.form.f.revenir_menu_apres_arret.assert_called_once_with(self.form)

    def test_resume_ne_modifie_pas_jauge(self):
        self.form.lancer_recherche()
        self.form.column_panel_progress_recherche.visible = False
        self.form.display_param_summary()
        self.assertFalse(self.form.column_panel_progress_recherche.visible)

    def test_composants_et_hierarchie(self):
        from xml.etree import ElementTree
        # Remplacer les préfixes XML de la syntaxe Anvil pour lire la structure.
        html = support.SOURCE.with_name('form_template.html').read_text()
        racine = ElementTree.fromstring(html.replace('prop:', 'prop_').replace('container:', 'container_').replace('on:', 'on_'))
        composants = {n.get('name'): n for n in racine.iter() if n.get('name')}
        parents = {enfant: parent for parent in racine.iter() for enfant in parent}
        saisie = composants['column_panel_saisie_recherche']
        resume = composants['column_panel_param_summary']
        self.assertIs(parents[saisie], parents[resume])
        for nom in ('column_panel_params', 'bloc_selecteur_cpv_complet', 'zone_resume_cpv'):
            self.assertIs(parents[composants[nom]], saisie)
        self.assertIs(parents[composants['column_panel_progress_recherche']], parents[saisie])


if __name__ == '__main__':
    unittest.main()
