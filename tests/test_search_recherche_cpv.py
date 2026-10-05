"""Tests isolés de search : aucun import Anvil réel, réseau ou Data Table."""
import ast
import copy
from contextlib import nullcontext
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / "client_code/search/__init__.py"


def charger_methodes():
    """Charge seulement les méthodes de la Form, sans son initialisation Anvil."""
    arbre = ast.parse(SOURCE.read_text())
    classe = next(element for element in arbre.body if isinstance(element, ast.ClassDef) and element.name == "search")
    methodes = []
    for methode in classe.body:
        if isinstance(methode, ast.FunctionDef) and methode.name != "__init__":
            methode.decorator_list = []
            methodes.append(methode)
    classe_test = ast.ClassDef(name="Search", bases=[], keywords=[], body=methodes, decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[classe_test], type_ignores=[]))
    espace = {
        "re": re,
        "anvil": SimpleNamespace(server=SimpleNamespace(call=Mock(), no_loading_indicator=nullcontext())),
        "afficher_information": Mock(),
        "afficher_avertissement": Mock(),
        "Notification": Mock(),
    }
    exec(compile(module, str(SOURCE), "exec"), espace)
    return espace


class Composant:
    def __init__(self, texte=""):
        self.text = texte
        self.visible = True
        self.enabled = True
        self.items = []
        self.tag = SimpleNamespace()
        self.interval = 0
        self.selected = []
        self.checked = False

    def focus(self):
        pass

    def scroll_into_view(self, **arguments):
        pass


class TestsRechercheCPV(unittest.TestCase):
    def setUp(self):
        self.espace = charger_methodes()
        self.form = self.espace["Search"]()
        self.serveur = self.espace["anvil"].server.call
        self.serveur.return_value = Mock()
        composants = (
            "Titre_2 text_box_mots_obligatoires_cpv text_box_mots_exclus text_box_mot_ou "
            "text_box_nb_jours text_box_departements multi_select_drop_down_platformes "
            "button_creer_veille_cpv timer_recherche_progress repeating_panel_offres "
            "checkbox_on_off text_nb_offres data_grid_1 column_panel_select "
            "button_selection_mailed column_panel_params text_param_summary "
            "column_panel_progress_recherche label_progress_recherche "
            "bloc_selecteur_cpv_complet zone_resume_cpv label_resume_cpv"
        )
        for nom in composants.split():
            setattr(self.form, nom, Composant())
        self.form.f = SimpleNamespace(navigation_link_search_go=Composant())
        self.form.cpv_selectionnes = [{"code": "80560000", "libelle": "Formation santé"}]
        self.form.multi_select_drop_down_platformes.selected = ["BOAMP", "CARIF-OREF"]
        self.form.text_box_nb_jours.text = "30"
        self.form.text_box_mot_ou.text = "ANCIENNE_VALEUR"
        self.form._recherche_en_cours = False
        self.form._annulation_recherche_demandee = False
        self.form._ctx_recherche = {}
        self.form.histo_id = "ancien-historique"
        self.form.task_recherche = None
        self.form.list_offres = []
        self.form.recalculer_bouton_selection_mailed = Mock()
        self.form.afficher_progression_recherche = Mock()
        for nom in ("filtrer_offres_criteres_positifs", "filtrer_offres_exclues",
                    "build_offres_list", "ajouter_correspondance_mots_ou", "trier_offres_par_interet"):
            setattr(self.form, nom, Mock(side_effect=AssertionError("pipeline legacy interdit")))

    def lancer(self):
        self.form.lancer_recherche()
        return self.serveur.call_args.kwargs

    def resultat(self, offres=None, **options):
        retour = dict(ok=True, offres=offres or [], errors=[], nb_resultats_metier=len(offres or []),
                      nb_retour_client=len(offres or []), recherche_limitee=False, message_limite="")
        retour.update(options)
        return retour

    def test_cpv_seul_et_arguments_exacts(self):
        criteres = self.lancer()
        self.assertEqual(self.serveur.call_args.args, ("lancer_recherche_cpv_background",))
        self.assertEqual(set(criteres), {"cpv_selectionnes", "departements", "filtre_jours", "sources", "mots_obligatoires", "mots_exclus"})
        self.assertEqual(criteres["cpv_selectionnes"], ["80560000"])
        self.assertEqual(criteres["mots_obligatoires"], [])
        self.assertEqual(criteres["sources"], ["BOAMP", "CARIF-OREF"])
        self.assertEqual(criteres["filtre_jours"], 30)

    def test_expressions_frontiere(self):
        for texte, attendu in [
            ("sst", ["sst"]), ("sst, recyclage", ["sst", "recyclage"]),
            ("formation sst", ["formation sst"]),
            ("formation et sécurité; réanimation\nSST", ["formation et sécurité", "réanimation", "SST"]),
            ("SST, sst", ["SST", "sst"]),
        ]:
            with self.subTest(texte=texte):
                self.form.text_box_mots_obligatoires_cpv.text = texte
                self.assertEqual(self.form.preparer_criteres_recherche_cpv()["mots_obligatoires"], attendu)

    def test_exclusions_et_departements(self):
        self.form.text_box_mots_exclus.text = "test; formation ou sécurité"
        self.form.text_box_departements.text = "34, 30\n2A"
        criteres = self.form.preparer_criteres_recherche_cpv()
        self.assertEqual(criteres["mots_exclus"], ["test", "formation ou sécurité"])
        self.assertEqual(criteres["departements"], ["34", "30", "2A"])

    def test_periode(self):
        for saisie, attendu in [("0", 1), ("400", 365), ("30", 30)]:
            self.form.text_box_nb_jours.text = saisie
            self.assertEqual(self.form.preparer_criteres_recherche_cpv()["filtre_jours"], attendu)
        self.form.text_box_nb_jours.text = "abc"
        self.form.lancer_recherche()
        self.serveur.assert_not_called()

    def test_sources_requises(self):
        self.form.multi_select_drop_down_platformes.selected = []
        self.form.lancer_recherche()
        self.serveur.assert_not_called()

    def test_legacy_sans_cpv_et_sst(self):
        self.form.cpv_selectionnes = []
        self.form.text_box_mots_obligatoires_cpv.text = "sst"
        self.form.lancer_recherche()
        self.assertEqual(self.serveur.call_args.args, ("lancer_recherche_multi_sources_background",))
        self.assertEqual(self.serveur.call_args.kwargs["mots"], ["sst"])
        self.assertIn("mots_ou", self.serveur.call_args.kwargs)

    def test_instantane_et_resume(self):
        self.form.text_box_mots_obligatoires_cpv.text = "formation sst"
        self.lancer()
        attendu = self.form.construire_resume_recherche_cpv()
        self.form.cpv_selectionnes[0]["libelle"] = "modifié"
        self.form.text_box_mots_obligatoires_cpv.text = "autre"
        self.form.multi_select_drop_down_platformes.selected.append("TED")
        self.assertEqual(self.form.construire_resume_recherche_cpv(), attendu)
        self.assertIn("80560000 — Formation santé", attendu)
        self.assertNotIn("ANCIENNE_VALEUR", attendu)
        self.assertNotIn("Au moins un", attendu)

    def test_zero_est_succes(self):
        self.lancer()
        self.form.traiter_offres_cpv_apres_background(self.resultat())
        self.assertEqual(self.form.list_offres, [])
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs["ligne_1"], "0 offre retenue")
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs["etat"], "success")
        self.assertFalse(self.form._recherche_en_cours)
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)

    def test_projection_conserve_metier_et_doublons(self):
        self.lancer()
        offre = dict(idweb="1", titre="Formation", cpv_principal="80560000", cpv_codes=["80560000"],
                     provenances=[{"source": "boamp"}], identifiants_officiels={"avis": "1"},
                     classifications_cpv_sources={"boamp": ["80560000"]}, lien="https://example.invalid")
        avant = copy.deepcopy(offre)
        self.form.traiter_offres_cpv_apres_background(self.resultat([offre, offre]))
        self.assertEqual(len(self.form.list_offres), 2)
        self.assertEqual(offre, avant)
        for champ, valeur in offre.items():
            self.assertEqual(self.form.list_offres[0][champ], valeur)
        self.assertFalse(self.form.list_offres[0]["vu"])
        self.assertEqual(self.form.list_offres[1]["numero_offre"], 2)
        self.assertEqual(self.form.list_offres[0]["nb_offres_total"], 2)
        self.assertEqual(self.form.list_offres[0]["lien_source"], offre["lien"])
        self.assertEqual(self.serveur.call_count, 1)

    def test_une_offre(self):
        self.lancer()
        self.form.traiter_offres_cpv_apres_background(self.resultat([{"titre": "Une offre"}]))
        self.assertEqual(self.form.text_nb_offres.text, "1 offre")

    def test_limitation_message_exact(self):
        self.lancer()
        self.form.traiter_offres_cpv_apres_background(self.resultat(
            [{"titre": "Offre"}], recherche_limitee=True, message_limite="Message exact moteur",
            nb_resultats_metier=501, nb_retour_client=500))
        self.espace["afficher_information"].assert_called_with("Message exact moteur", titre="Recherche limitée")
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs["ligne_2"], "")

    def test_erreur_sans_partiel(self):
        self.lancer()
        self.form.traiter_offres_cpv_apres_background(self.resultat([{"titre": "Ne pas afficher"}], ok=False))
        self.assertEqual(self.form.list_offres, [])
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs["etat"], "error")

    def test_timer_dispatch_cpv_et_none(self):
        self.lancer()
        self.form.task_recherche = Mock()
        self.form.task_recherche.get_state.return_value = {"source_current": None, "source_total": None}
        self.form.task_recherche.is_completed.return_value = True
        self.form.task_recherche.get_return_value.return_value = self.resultat()
        self.form.traiter_offres_recuperees_apres_background = Mock(side_effect=AssertionError("legacy"))
        self.form.timer_recherche_progress_tick()
        self.assertEqual(self.form.afficher_progression_recherche.call_args.kwargs["etat"], "success")

    def test_timer_dispatch_legacy(self):
        self.form._ctx_recherche = {}
        self.form.task_recherche = Mock()
        self.form.task_recherche.get_state.return_value = {}
        self.form.task_recherche.is_completed.return_value = True
        self.form.task_recherche.get_return_value.return_value = {"offres": [{"titre": "Legacy"}]}
        self.form.traiter_offres_recuperees_apres_background = Mock()
        self.form.timer_recherche_progress_tick()
        self.form.traiter_offres_recuperees_apres_background.assert_called_once_with([{"titre": "Legacy"}])

    def test_veille_et_historique_inactifs(self):
        self.lancer()
        self.form.traiter_offres_cpv_apres_background(self.resultat([{"titre": "Offre"}]))
        self.assertFalse(hasattr(self.form, "button_daily_survey_creation"))
        self.assertIsNone(self.form.histo_id)
        self.assertTrue(self.form.sauver_offres_dans_histo())
        self.assertEqual(self.serveur.call_count, 1)

    def test_repli_conserve_criteres(self):
        self.form.text_box_mots_obligatoires_cpv.text = "sst"
        avant = copy.deepcopy(self.form.cpv_selectionnes)
        self.form.button_cacher_cpv_click()
        self.form.button_voir_bloc_cpv_click()
        self.assertEqual(self.form.cpv_selectionnes, avant)
        self.assertEqual(self.form.text_box_mots_obligatoires_cpv.text, "sst")
        self.serveur.assert_not_called()

    def test_exception_lancement_deverrouille(self):
        self.serveur.side_effect = RuntimeError("indisponible")
        with self.assertRaises(RuntimeError):
            self.form.lancer_recherche()
        self.assertFalse(self.form._recherche_en_cours)
        self.assertEqual(self.form.timer_recherche_progress.interval, 0)

    def test_activation_cpv_sans_mots(self):
        self.form.text_box_mot_ou.text = ""
        self.form.maj_bouton_recherche_visible()
        self.assertTrue(self.form.f.navigation_link_search_go.enabled)


class TestsProgressionRecherche(unittest.TestCase):
    def setUp(self):
        self.form = charger_methodes()["Search"]()
        self.form._ctx_recherche = {"mode_recherche": "cpv"}
        self.form._last_progress_role = None
        self.form.column_panel_progress_recherche = Composant()
        self.form.label_jauge_globale = Composant()
        self.form.regler_jauge = Mock()

    def afficher(self, source="AWS", compteur=None, message="", **options):
        self.form.afficher_progression_recherche(
            source_nom=source, source_current=compteur, source_total=None,
            progress_source=0, ligne_2=message, **options
        )
        return self.form.label_jauge_globale.text

    def test_compteurs_sans_total_ni_pourcentage(self):
        for source in ("AWS", "BOAMP", "TED", "CARIF-OREF"):
            for compteur in (1, 2, 37):
                with self.subTest(source=source, compteur=compteur):
                    suffixe = "avis traité" if compteur == 1 else "avis traités"
                    attendu = f"{source} — {compteur} {suffixe}"
                    self.assertEqual(self.afficher(source, compteur), attendu)
                    self.assertNotIn("%", self.form.label_jauge_globale.text)
                    self.assertEqual(self.form._points_animation_recherche, 0)

    def test_message_utilisateur_prioritaire(self):
        self.assertEqual(self.afficher(compteur=37, message="AWS — 37 avis traités (collecte)"),
                         "AWS — 37 avis traités (collecte)")
        self.assertEqual(self.afficher(compteur=1, message="   "), "AWS — 1 avis traité")

    def test_cycle_sans_compteur_valide(self):
        for source in ("AWS", "BOAMP", "TED", "CARIF-OREF"):
            for compteur in (0, None, "37", -1, True):
                with self.subTest(source=source, compteur=compteur):
                    self.form._points_animation_recherche = 0
                    for points in (1, 2, 3, 1):
                        self.assertEqual(self.afficher(source, compteur, "Collecte"),
                                         f"Recherche {source} en cours" + "." * points)

    def test_transitions_compteur_et_source(self):
        self.assertEqual(self.afficher(), "Recherche AWS en cours.")
        self.assertEqual(self.afficher(compteur=2), "AWS — 2 avis traités")
        self.assertEqual(self.afficher("TED", 0), "Recherche TED en cours.")
        self.assertEqual(self.afficher("TED", 1), "TED — 1 avis traité")

    def test_alias_carif(self):
        self.assertEqual(self.afficher("CARIF", 1), "CARIF-OREF — 1 avis traité")
        self.assertEqual(self.afficher("CARIF", 2), "CARIF-OREF — 2 avis traités")
        self.assertEqual(self.afficher("CARIF", None), "Recherche CARIF-OREF en cours.")
        self.assertEqual(self.afficher("CARIF", 37, "CARIF-OREF — 37 avis traités"),
                         "CARIF-OREF — 37 avis traités")

    def test_mode_classique_inchange(self):
        self.form._ctx_recherche = {"mode_recherche": "classique"}
        for compteur in (None, 0, 37):
            self.assertEqual(self.afficher(compteur=compteur, message="AWS — 37 avis traités"),
                             "Recherche AWS en cours — 0 %")
        self.assertEqual(self.afficher("CARIF", 1), "Recherche CARIF en cours — 0 %")

    def test_etats_finaux_et_arret_inchanges(self):
        for etat, titre in (("success", "Terminé"), ("error", "Erreur"), ("stopping", "Arrêt")):
            with self.subTest(etat=etat):
                attendu = titre if etat == "stopping" else f"{titre} — Message"
                self.assertEqual(self.afficher(compteur=37, message="Message", etat=etat, ligne_1=titre), attendu)

    def test_timer_transmet_les_champs_et_affiche_le_message(self):
        self.form._annulation_recherche_demandee = False
        self.form.task_recherche = Mock()
        self.form.task_recherche.is_completed.return_value = False
        self.form.task_recherche.get_state.return_value = {
            "progress": 15, "source_progress": 0, "source_en_cours": "AWS",
            "source_current": 37, "source_total": None, "message": "AWS — 37 avis traités"
        }
        methode = self.form.afficher_progression_recherche
        self.form.afficher_progression_recherche = Mock(wraps=methode)
        self.form.timer_recherche_progress_tick()
        arguments = self.form.afficher_progression_recherche.call_args.kwargs
        self.assertEqual(arguments["ligne_2"], "AWS — 37 avis traités")
        self.assertEqual(arguments["source_nom"], "AWS")
        self.assertEqual(arguments["source_current"], 37)
        self.assertIsNone(arguments["source_total"])
        self.assertEqual(arguments["progress_source"], 0)
        self.assertEqual(self.form.label_jauge_globale.text, "AWS — 37 avis traités")


if __name__ == "__main__":
    unittest.main()
