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
        self.form._catalogue_v4_actif = True
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

    def test_pagination_au_dela_de_500(self):
        self.preparation.serveur.side_effect = self.moteur(701)
        resultat = self.form.charger_pages_catalogue(self.criteres())
        self.assertEqual(len(resultat["offres"]), 701)
        self.assertEqual(resultat["total_catalogue"], 701)
        self.assertEqual(resultat["statut_collecte"], "partielle")
        self.assertEqual(self.preparation.serveur.call_count, 8)

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

    def test_reprise_abandonne_les_pages_de_l_ancien_instantane(self):
        moteur = self.moteur(101)

        def transport(nom, **parametres):
            appel = self.preparation.serveur.call_count
            if appel == 2:
                return dict(ok=False, code="pagination_changed")
            page = moteur(nom, **parametres)
            if appel == 1:
                page["offres"][0]["titre"] = "Ancien instantané"
            return page

        self.preparation.serveur.side_effect = transport
        resultat = self.form.charger_pages_catalogue(self.criteres())
        appels = self.preparation.serveur.call_args_list
        self.assertEqual([appel.kwargs["decalage"] for appel in appels], [0, 100, 0, 100])
        self.assertEqual(appels[0], appels[2])
        self.assertEqual(len(resultat["offres"]), 101)
        self.assertEqual(resultat["offres"][0]["titre"], "Offre fictive")

    def test_erreurs_v4_et_rpc_ne_sauvegardent_pas(self):
        for code, texte in (
            ("catalogue_limit", "Trop de candidats"),
            ("response_limit", "trop volumineuse"),
            ("catalogue_busy", "occupé"),
            ("catalogue_unavailable", "indisponible"),
            ("rpc", "L'appel au catalogue a échoué"),
        ):
            with self.subTest(code=code):
                self.preparation.serveur.reset_mock(side_effect=True)
                if code == "rpc":
                    self.preparation.serveur.side_effect = self.preparation.espace["anvil"].server.TimeoutError
                else:
                    self.preparation.serveur.return_value = dict(ok=False, error={"code": code})
                self.form._ctx_recherche = dict(mode_recherche="cpv", **self.criteres())
                self.form.traiter_offres_cpv_apres_background = Mock()
                self.form.lancer_recherche_catalogue(self.criteres())
                self.form.traiter_offres_cpv_apres_background.assert_not_called()
                self.assertFalse(self.form._recherche_en_cours)
                self.assertEqual(self.preparation.serveur.call_count, 1)
                self.assertIn(texte, self.form.label_route_moteur.text)

    def test_fin_anticipee_signalee_partielle_meme_sans_ted(self):
        moteur = self.moteur(200)
        self.preparation.serveur.side_effect = lambda *a, **kw: dict(moteur(*a, **kw), suite=False)
        resultat = self.form.charger_pages_catalogue(self.criteres(["BOAMP"]))
        self.assertEqual(len(resultat["offres"]), 100)
        self.assertEqual(resultat["statut_collecte"], "partielle")
        self.assertIn("Collecte partielle", resultat["message_collecte"])

    def test_selecteur_pg_inoperant_quand_v4_fermee(self):
        self.form._catalogue_v4_actif = False
        self.assertFalse(self.form.utiliser_catalogue_postgresql(self.criteres(["BOAMP", "TED"])))

    def charger_facade(self):
        fixture = support.TestsMaintenanceRAO()
        fixture.setUp()
        espace = dict(fixture.espace, Maintenance_RAO=fixture.api)
        facade = support.charger("server_code/CatalogueRecetteV3.py", espace)
        return fixture, espace, facade

    def test_verrou_serveur_et_comptes_refuses_sur_les_trois_entrees(self):
        fixture, espace, facade = self.charger_facade()
        self.assertIs(espace["CATALOGUE_V4_ACTIVE"], False)
        for actif, compte, code in (
            (False, support.Row(role="C", enabled=True), "catalogue_unavailable"),
            (True, None, "authentication_required"),
            (True, support.Row(role="A", enabled=False), "access_denied"),
            (True, support.Row(role="C", enabled=1), "access_denied"),
            (True, support.Row(role="C"), "access_denied"),
        ):
            with self.subTest(actif=actif, compte=compte):
                espace["CATALOGUE_V4_ACTIVE"] = actif
                fixture.user = compte
                self.assertEqual(facade.recette_catalogue_v3_rechercher(**self.criteres())["error"], code)
                self.assertEqual(facade.rechercher_page_catalogue_search(**self.criteres())["error"], code)
                self.assertEqual(facade.recette_catalogue_v3_detail(["123"])["error"], code)
        fixture.server.call.assert_not_called()
        self.assertEqual(fixture.globales.writes, 0)

    def test_autorisation_native_critere_decalage_et_maintenance(self):
        fixture, espace, facade = self.charger_facade()
        espace["CATALOGUE_V4_ACTIVE"] = True
        fixture.server.call.side_effect = None
        for role in ("A", "C"):
            with self.subTest(role=role):
                fixture.user["role"] = role
                fixture.server.call.return_value = dict(ok=True, offres=[])
                reponse = facade.rechercher_page_catalogue_search(
                    **self.criteres(), decalage=600, empreinte="test", date_reference="2026-11-13")
                self.assertTrue(reponse["ok"])
                fixture.server.call.assert_called_once_with(
                    "rechercher_offres_catalogue_pg", ["80500000"], [], 30, ["TED"],
                    mots_obligatoires=[], mots_exclus=[], mots_ou=[], limite=100,
                    decalage=600, empreinte="test", date_reference="2026-11-13")
                fixture.server.call.reset_mock()
                self.assertTrue(facade.recette_catalogue_v3_detail(["123", "456"])["ok"])
                fixture.server.call.assert_called_once_with("obtenir_detail_offre_catalogue_pg", ["123", "456"])
                fixture.server.call.reset_mock()
        for valeurs in ({"limite": 101}, {"decalage": -1}, {"decalage": True},
                        {"decalage": 600}, {"date_reference": "2026-13-01"}):
            self.assertEqual(facade.recette_catalogue_v3_rechercher(**self.criteres(), **valeurs)["error"],
                             "invalid_parameters")
        with self.assertRaises(TypeError):
            facade.recette_catalogue_v3_rechercher(**self.criteres(), user_id="usurpe")
        with self.assertRaises(TypeError):
            facade.recette_catalogue_v3_detail(["123"], email="usurpe@example.invalid")
        fixture.user["role"] = "A"
        fixture.api.activer_maintenance_rao()
        self.assertEqual(facade.rechercher_page_catalogue_search(**self.criteres())["error"], "maintenance")
        fixture.server.call.assert_not_called()

    def test_frontiere_uplink_dans_le_code(self):
        # Ce contrôle local ne reproduit ni le routeur Anvil ni remote_caller.
        source = ROOT / "server_code/CatalogueRecetteV3.py"
        arbre = ast.parse(source.read_text())
        callables = {noeud.name: [ast.unparse(d) for d in noeud.decorator_list]
                     for noeud in arbre.body if isinstance(noeud, ast.FunctionDef) and noeud.decorator_list}
        self.assertEqual(callables, {
            "recette_catalogue_v3_rechercher": ["anvil.server.callable(require_user=True)"],
            "recette_catalogue_v3_detail": ["anvil.server.callable(require_user=True)"],
            "rechercher_page_catalogue_search": ["anvil.server.callable(require_user=True)"],
        })
        for fichier in (ROOT / "client_code").rglob("*.py"):
            contenu = fichier.read_text()
            self.assertNotIn("rechercher_offres_catalogue_pg", contenu)
            self.assertNotIn("obtenir_detail_offre_catalogue_pg", contenu)

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
        espace["CATALOGUE_V4_ACTIVE"] = True
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
        self.assertIn("16 retournées", self.form.text_nb_offres.text)
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
        arbre = ast.parse((ROOT / "client_code/search/RowTemplate1/__init__.py").read_text())
        classe = next(n for n in arbre.body if isinstance(n, ast.ClassDef))
        methodes = {"afficher_detail_catalogue", "presenter_detail_catalogue", "preparer_texte_complet_catalogue"}
        classe.body = [n for n in classe.body if isinstance(n, ast.FunctionDef) and n.name in methodes]
        classe.bases = []
        classe.decorator_list = []
        serveur = Mock(return_value=dict(ok=True, offres=[
            dict(offre_id="123", titre="Première fiche", description="Détail fictif <exemple>",
                 acheteur="Premier acheteur", liens=["https://test.invalid/123"],
                 cpv_lots=["80500000"], texte_integral=None, search_text="Corpus masqué"),
            dict(offre_id="456", titre="Seconde fiche", texte_integral="Texte attesté",
                 date_limite_reponse_horodatee="2026-12-01T09:00:00+01:00",
                 provenances=[{"lien": "https://test.invalid/456"}, {"lien": "javascript:invalide"}]),
        ]))
        espace = dict(anvil=SimpleNamespace(server=SimpleNamespace(call=serveur)),
                      Label=Mock(side_effect=lambda **kw: SimpleNamespace(**kw)),
                      Link=Mock(side_effect=lambda **kw: SimpleNamespace(**kw)),
                      ColumnPanel=Mock(side_effect=lambda **kw: Mock(**kw)), Button=Mock(), alert=Mock())
        exec(compile(ast.fix_missing_locations(ast.Module(body=[classe], type_ignores=[])),
                     "detail_catalogue", "exec"), espace)
        row = espace[classe.name]()
        row.item = dict(offre_ids=["123", "456"], acheteur="Acheteur carte", lien="https://test.invalid/carte")
        row.column_panel_detail = SimpleNamespace(visible=False)
        row.button_generer_html = SimpleNamespace(enabled=True)
        row.column_panel_affichage = Mock()
        row.parent = object()
        row.checkbox_vu = SimpleNamespace(checked=False)
        row.extraire_mots_et = Mock(return_value=["détail"])
        row.set_checkbox_vu_sans_event = Mock()
        row.checkbox_vu_change = Mock()
        row.afficher_detail_catalogue()
        serveur.assert_called_once_with("recette_catalogue_v3_detail", offre_ids=["123", "456"])
        self.assertTrue(row.column_panel_detail.visible)
        self.assertTrue(row.button_generer_html.enabled)
        premiere, seconde = [appel.args[0] for appel in row.column_panel_affichage.add_component.call_args_list]
        premiers_textes = [appel.args[0].text for appel in premiere.add_component.call_args_list]
        self.assertIn("Description : Détail fictif <exemple>", premiers_textes)
        self.assertTrue(any(getattr(appel.args[0], "bold", False) for appel in premiere.add_component.call_args_list))
        self.assertIn("CPV des lots : 80500000", premiers_textes)
        self.assertIn("Texte complet non disponible actuellement.", premiers_textes)
        self.assertNotIn("Corpus masqué", " ".join(premiers_textes))
        textes_seconde = [appel.args[0].text for appel in seconde.add_component.call_args_list
                          if isinstance(appel.args[0], SimpleNamespace)]
        self.assertIn("Date et heure limites de réponse : 2026-12-01T09:00:00+01:00", textes_seconde)
        self.assertFalse(any("acheteur" in t.lower() for t in textes_seconde))
        self.assertEqual([appel.kwargs["url"] for appel in espace["Link"].call_args_list],
                         ["https://test.invalid/123", "https://test.invalid/456"])
        espace["Button"].assert_called_once()
        espace["Button"].return_value.set_event_handler.call_args.args[1]()
        self.assertIn("Texte attesté", [appel.kwargs["text"] for appel in espace["Label"].call_args_list])
        row.set_checkbox_vu_sans_event.assert_called_once_with(True)
        row.checkbox_vu_change.assert_called_once_with()

        row.column_panel_detail.visible = False
        row.checkbox_vu_change.reset_mock()
        row.set_checkbox_vu_sans_event.reset_mock()
        serveur.return_value = dict(ok=False, code="catalogue_unavailable", message="Détail indisponible")
        row.afficher_detail_catalogue()
        espace["alert"].assert_called_once_with("Détail indisponible", title="Catalogue PostgreSQL")
        self.assertFalse(row.column_panel_detail.visible)
        self.assertTrue(row.button_generer_html.enabled)
        row.set_checkbox_vu_sans_event.assert_not_called()
        row.checkbox_vu_change.assert_not_called()



if __name__ == "__main__":
    unittest.main()
