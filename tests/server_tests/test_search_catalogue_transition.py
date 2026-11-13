"""Vérifications ciblées de transition : aucun réseau, collecteur ou base réelle."""
import sys
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
import test_search_recherche_cpv as client
import test_maintenance_rao as support


class TestsTransitionCatalogue(unittest.TestCase):
    def setUp(self):
        self.preparation = client.TestsRechercheCPV()
        self.preparation.setUp()
        self.form = self.preparation.form
        self.form.drop_down_moteur_catalogue = SimpleNamespace(selected_value="postgresql")
        self.form.label_route_moteur = client.Composant()
        self.form.actualiser_bouton_veille_cpv = Mock()
        self.form.f.revenir_menu_apres_arret = Mock()
        self.form.f.activer_bouton_arret = Mock()

    def criteres(self, sources=None):
        return dict(cpv_selectionnes=["80500000"], departements=[], filtre_jours=30,
                    sources=sources or ["TED"], mots_obligatoires=[], mots_exclus=[], mots_ou=[])

    def moteur(self, total):
        def transport(nom, **parametres):
            self.assertEqual(nom, "rechercher_page_catalogue_search")
            offset = parametres["decalage"]
            self.assertEqual(parametres["filtre_jours"], 30)
            if offset:
                self.assertEqual(parametres["empreinte"], "empreinte-test")
                self.assertEqual(parametres["date_reference"], "2026-11-13")
            return dict(ok=True, offres=[dict(offre_id=str(n), titre="Offre fictive") for n in range(offset, min(offset+100, total))],
                        total=total, decalage=offset, limite=100, suite=offset+100 < total,
                        empreinte="empreinte-test", couverture_ted_complete=False,
                        criteres=dict(cpv_selectionnes=["80500000"], departements=[], nb_jours=30,
                                      sources=parametres["sources"], mots_obligatoires=[], mots_exclus=[], mots_ou=[], date_reference="2026-11-13"))
        return transport

    def test_routage_pg_par_defaut_et_secours_sans_perte_criteres(self):
        for sources in (["BOAMP"], ["TED"], ["BOAMP", "TED"]):
            self.assertTrue(self.form.utiliser_catalogue_postgresql(self.criteres(sources)))
        for sources in (["AWS"], ["CARIF-OREF"], ["TED", "AWS"], ["BOAMP", "CARIF-OREF"]):
            self.assertFalse(self.form.utiliser_catalogue_postgresql(self.criteres(sources)))
        self.assertFalse(self.form.utiliser_catalogue_postgresql(dict(self.criteres(), cpv_selectionnes=[])))
        self.form.text_box_mot_ou.text = "critère conservé"
        self.form.drop_down_moteur_catalogue.selected_value = "historique"
        self.assertFalse(self.form.utiliser_catalogue_postgresql(self.criteres()))
        self.assertEqual(self.form.text_box_mot_ou.text, "critère conservé")

    def test_ted_16_et_boamp_150_avec_criteres_figes(self):
        for sources, total, statut in ((["TED"],16,"partielle"), (["BOAMP"],150,"complete")):
            self.preparation.serveur.reset_mock()
            self.preparation.serveur.side_effect = self.moteur(total)
            resultat = self.form.charger_pages_catalogue(self.criteres(sources))
            self.assertEqual(len(resultat["offres"]), total)
            self.assertEqual(resultat["total_catalogue"], total)
            self.assertEqual(resultat["statut_collecte"], statut)
            self.assertEqual(self.preparation.serveur.call_count, (total+99)//100)
            if sources == ["TED"]:
                self.assertIn("incomplète", resultat["message_collecte"])

    def test_limite_contractuelle_600_explicitement_partielle(self):
        self.preparation.serveur.side_effect = self.moteur(701)
        resultat = self.form.charger_pages_catalogue(self.criteres())
        self.assertEqual(len(resultat["offres"]), 600)
        self.assertEqual(resultat["total_catalogue"], 701)
        self.assertEqual(resultat["statut_collecte"], "partielle")
        self.assertIn("Pagination limitée", resultat["message_collecte"])
        self.assertEqual(self.preparation.serveur.call_count, 6)

    def test_arret_pendant_page_interdit_suite_et_finalisation(self):
        def transport(*args, **kwargs):
            self.assertTrue(self.form.annuler_recherche_depuis_menu()["ok"])
            return self.moteur(200)(*args, **kwargs)
        self.preparation.serveur.side_effect = transport
        self.form._ctx_recherche = dict(mode_recherche="cpv", **self.criteres())
        self.form.traiter_offres_cpv_apres_background = Mock()
        self.form.lancer_recherche_catalogue(self.criteres())
        self.assertEqual(self.preparation.serveur.call_count, 1)
        self.form.traiter_offres_cpv_apres_background.assert_not_called()
        self.assertTrue(self.form._recherche_abandonnee)
        self.assertIsNone(self.form.task_recherche)
        self.assertFalse(self.form._recherche_en_cours)

    def test_erreur_pagination_ne_finalise_pas_de_resultat(self):
        self.preparation.serveur.side_effect = lambda *args, **kwargs: dict(ok=False, error="pagination_changed")
        self.form._ctx_recherche = dict(mode_recherche="cpv", **self.criteres())
        self.form.traiter_offres_cpv_apres_background = Mock()
        self.form.lancer_recherche_catalogue(self.criteres())
        self.form.traiter_offres_cpv_apres_background.assert_not_called()
        self.assertFalse(self.form._recherche_en_cours)
        self.assertIn("Aucun résultat sauvegardé", self.form.label_route_moteur.text)

    def test_reouverture_recherches_preserve_veille_et_nouveau_gel(self):
        fixture = support.TestsMaintenanceRAO()
        fixture.setUp()
        api = fixture.api
        api.activer_maintenance_rao()
        self.assertIsNotNone(api.refus_si_maintenance("recherche_cpv"))
        api.rouvrir_recherches_rao()
        self.assertIsNone(api.refus_si_maintenance("recherche_cpv"))
        self.assertIsNone(api._admettre("recherche_classique")[1])
        self.assertIsNone(api._admettre("recherche_catalogue")[1])
        self.assertEqual(api._admettre("veille_cpv")[1]["error"], "maintenance")
        self.assertEqual(api._admettre("veille_classique")[1]["error"], "maintenance")
        api.activer_maintenance_rao()
        self.assertEqual(api._admettre("recherche_catalogue")[1]["error"], "maintenance")

    def test_projection_et_detail_ids_sans_identite_transmise(self):
        fixture = support.TestsMaintenanceRAO()
        fixture.setUp()
        espace = dict(fixture.espace, Maintenance_RAO=fixture.api)
        api = support.charger("server_code/CatalogueRecetteV3.py", espace)
        espace["DEVELOPPEUR_USER_ID"] = "test-row"
        fixture.server.call.side_effect = None
        fixture.server.call.return_value = dict(ok=True, offres=[dict(offre_id="123", offre_ids=["123","456"],
            date_limite_reponse="2026-12-01", titre="Fictive", source="TED", reference="REF")])
        reponse = api.rechercher_page_catalogue_search(**self.criteres())
        self.assertEqual(reponse["offres"][0]["offre_ids"], ["123","456"])
        self.assertEqual(reponse["offres"][0]["date_limite_rep"], "2026-12-01")
        self.assertEqual(reponse["offres"][0]["moteur_recherche"], "catalogue_pg")
        self.assertNotIn("user_id", fixture.server.call.call_args.kwargs)
        api.recette_catalogue_v3_detail(["123","456"])
        fixture.server.call.assert_called_with("obtenir_detail_offre_catalogue_pg", ["123","456"])

    def test_parcours_principal_sauvegarde_partielle_reset_et_nouvelle_recherche(self):
        self.form.cpv_selectionnes = [{"code": "80500000", "libelle": "Formation"}]
        self.form.multi_select_drop_down_platformes.selected = ["TED"]
        self.form.text_box_mot_ou.text = ""
        self.form.text_box_recherche_cpv = client.Composant()
        self.preparation.espace["demander_choix"] = Mock(return_value=True)
        sauvegardes = []

        def transport(nom, *args, **kwargs):
            if nom == "rechercher_page_catalogue_search":
                return self.moteur(16)(nom, **kwargs)
            if nom == "backup_requete":
                sauvegardes.append(kwargs)
                return dict(ok=True, histo_id="histo-simule", revision_recherche=len(sauvegardes))
            raise AssertionError("Appel externe non prévu : " + nom)

        self.preparation.serveur.side_effect = transport
        self.form.lancer_recherche()
        self.assertEqual(len(self.form.list_offres), 16)
        self.assertEqual(sauvegardes[0]["statut_collecte"], "partielle")
        self.assertIn("Couverture TED", sauvegardes[0]["message_collecte"])
        self.assertIn("16 trouvées", self.form.text_nb_offres.text)
        self.form.button_del_all_click()
        self.assertEqual(self.form.list_offres, [])
        self.assertEqual(len(sauvegardes), 1)
        self.form.lancer_recherche()
        self.assertEqual(len(self.form.list_offres), 16)
        self.assertEqual(len(sauvegardes), 2)

    def test_mixte_garde_un_seul_lancement_historique_et_tous_les_criteres(self):
        self.form.multi_select_drop_down_platformes.selected = ["TED", "AWS"]
        task = Mock()

        def transport(nom, *args, **kwargs):
            if nom == "enregistrer_recherche_rao":
                return dict(ok=True)
            if nom == "lancer_recherche_cpv_rao":
                self.assertEqual(kwargs["sources"], ["TED", "AWS"])
                self.assertEqual(kwargs["mots_ou"], ["ANCIENNE_VALEUR"])
                return dict(ok=True, task=task)
            raise AssertionError("Aucune fusion ni page PostgreSQL attendue")

        self.preparation.serveur.side_effect = transport
        self.form.lancer_recherche()
        self.assertIs(self.form.task_recherche, task)
        self.assertEqual(self.preparation.serveur.call_count, 2)
        self.assertIn("historique", self.form.label_route_moteur.text)

    def test_detail_dans_panneau_existant_et_marque_vu_preservee(self):
        arbre = ast.parse((ROOT / 'client_code/search/RowTemplate1/__init__.py').read_text())
        classe = next(n for n in arbre.body if isinstance(n, ast.ClassDef))
        methode = next(n for n in classe.body if isinstance(n, ast.FunctionDef) and n.name == 'afficher_detail_catalogue')
        serveur = Mock(return_value=dict(ok=True, offres=[dict(offre_id="123", description="Détail fictif")]))
        texte = Mock()
        espace = dict(anvil=SimpleNamespace(server=SimpleNamespace(call=serveur)), TextArea=texte, alert=Mock())
        exec(compile(ast.fix_missing_locations(ast.Module(body=[methode], type_ignores=[])), 'detail_catalogue', 'exec'), espace)
        row = SimpleNamespace(item=dict(offre_ids=["123","456"]), column_panel_detail=SimpleNamespace(visible=False),
                              button_generer_html=SimpleNamespace(enabled=True), column_panel_affichage=Mock(),
                              parent=object(), checkbox_vu=SimpleNamespace(checked=False),
                              set_checkbox_vu_sans_event=Mock(), checkbox_vu_change=Mock())
        espace['afficher_detail_catalogue'](row)
        serveur.assert_called_once_with('recette_catalogue_v3_detail', offre_ids=["123","456"])
        self.assertTrue(row.column_panel_detail.visible)
        self.assertTrue(row.button_generer_html.enabled)
        self.assertIn("Détail fictif", texte.call_args.kwargs['text'])
        row.set_checkbox_vu_sans_event.assert_called_once_with(True)
        row.checkbox_vu_change.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
