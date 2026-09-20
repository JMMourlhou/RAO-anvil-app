"""Tests de sauvegarde CPV sur doublures uniquement, sans exécution automatique.

L'utilisateur et l'objet app_tables du module testé sont remplacés avant chaque
appel. Aucune vraie table n'est consultée, même pour rechercher un doublon.
"""

import copy
import hashlib
import inspect
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from . import Daily_survey


class LigneVeilleSimulee(dict):
    """Ligne en mémoire avec identifiant fictif, indépendante d'Anvil."""

    def get_id(self):
        """Retourne un identifiant str de test ; aucun paramètre ni accès externe."""
        return "ligne-simulee"


class TestsSauvegardeVeilleCPV(unittest.TestCase):
    """Vérifie validation, écritures prévues et isolation sur objets simulés."""

    def setUp(self):
        self.utilisateur = {"email": "utilisateur@example.invalid"}
        self.lignes = []
        self.table = Mock()
        self.table.search.side_effect = self.rechercher_lignes_simulees
        self.table.add_row.side_effect = self.ajouter_ligne_simulee
        self.identite = patch.object(Daily_survey.anvil.users, "get_user", return_value=self.utilisateur)
        self.tables = patch.object(Daily_survey, "app_tables", SimpleNamespace(daily_survey=self.table))
        self.get_user = self.identite.start()
        self.tables.start()
        self.addCleanup(self.identite.stop)
        self.addCleanup(self.tables.stop)

    def rechercher_lignes_simulees(self, **criteres):
        """Filtre les lignes fictives selon criteres (dict) ; retourne list[dict]."""
        self.assertEqual(set(criteres), {"email", "cle_requete"})
        self.assertIs(criteres["email"], self.get_user.return_value)
        correspondances = []
        for ligne in self.lignes:
            if ligne["email"] is criteres["email"] and ligne["cle_requete"] == criteres["cle_requete"]:
                correspondances.append(ligne)
        return correspondances

    def ajouter_ligne_simulee(self, **colonnes):
        """Stocke colonnes (dict) en mémoire ; retourne une LigneVeilleSimulee."""
        ligne = LigneVeilleSimulee(colonnes)
        self.lignes.append(ligne)
        return ligne

    def enregistrer(self, **criteres):
        """Appelle le parcours CPV avec criteres (dict) fictifs ; retourne dict."""
        arguments = {"cpv_selectionnes": ["80530000"], "sources": ["BOAMP"]}
        arguments.update(criteres)
        return Daily_survey.enregistrer_daily_survey_cpv(**arguments)

    def verifier_refus_sans_table(self, **criteres):
        """Vérifie le refus de criteres (dict) sans accès table ; retourne None."""
        reponse = self.enregistrer(**criteres)
        self.assertFalse(reponse["ok"])
        self.assertEqual(reponse["statut"], "erreur")
        self.assertIsNone(reponse["daily_survey_id"])
        self.assertTrue(reponse["message"])
        self.table.search.assert_not_called()
        self.table.add_row.assert_not_called()

    def test_creation_un_cpv(self):
        reponse = self.enregistrer()
        self.assertEqual(reponse["statut"], "cree")
        self.assertTrue(reponse["ok"])
        self.assertEqual(reponse["daily_survey_id"], "ligne-simulee")
        self.assertEqual(self.lignes[0]["cpv_selectionnes"], ["80530000"])

    def test_plusieurs_cpv_ordre_stocke(self):
        self.enregistrer(cpv_selectionnes=["80530000", "80510000"])
        self.assertEqual(self.lignes[0]["cpv_selectionnes"], ["80530000", "80510000"])

    def test_ordre_cpv_meme_cle(self):
        self.enregistrer(cpv_selectionnes=["80530000", "80510000"])
        reponse = self.enregistrer(cpv_selectionnes=["80510000", "80530000"])
        self.assertEqual(reponse["statut"], "deja_active")
        self.assertEqual(self.table.add_row.call_count, 1)

    def test_doublons_cpv(self):
        self.enregistrer(cpv_selectionnes=["80530000", "80510000", "80530000"])
        self.assertEqual(self.lignes[0]["cpv_selectionnes"], ["80530000", "80510000"])

    def test_selection_vide(self):
        self.verifier_refus_sans_table(cpv_selectionnes=[])

    def test_code_inconnu(self):
        self.verifier_refus_sans_table(cpv_selectionnes=["99999999"])

    def test_types_cpv_invalides(self):
        for selection in (None, "80530000", ("80530000",), [80530000], [True], [{}]):
            with self.subTest(selection=selection):
                self.verifier_refus_sans_table(cpv_selectionnes=selection)

    def test_selection_trop_longue(self):
        self.verifier_refus_sans_table(cpv_selectionnes=["80530000"] * 101)

    def test_source_unique_texte(self):
        self.enregistrer(sources=" ted ")
        self.assertEqual(self.lignes[0]["sources"], ["TED"])

    def test_sources_multiples_et_doublons(self):
        self.enregistrer(sources=[" ted ", "CARIF", "aws", "BOAMP", "ted"])
        self.assertEqual(self.lignes[0]["sources"], ["AWS", "BOAMP", "CARIF", "TED"])

    def test_sources_inconnues_vides_et_types(self):
        for sources in (["INCONNUE"], ["TED", "INCONNUE"], [], None, "", 42, [42], {"TED": True}):
            with self.subTest(sources=sources):
                self.verifier_refus_sans_table(sources=sources)

    def test_departements_vides(self):
        for departements in (None, "", "  ", []):
            with self.subTest(departements=departements):
                self.assertEqual(Daily_survey.normaliser_departements_cpv(departements), "")
        self.enregistrer()
        self.assertEqual(self.lignes[0]["departements"], "")

    def test_departements_multiples(self):
        self.enregistrer(departements="34 ; 30\n34, 2a, 01")
        self.assertEqual(self.lignes[0]["departements"], "01, 2A, 30, 34")

    def test_departements_sans_validation_inventee(self):
        self.enregistrer(departements="code-non-verifie")
        self.assertEqual(self.lignes[0]["departements"], "CODE-NON-VERIFIE")

    def test_departements_types_invalides(self):
        for departements in (34, [34], {"34": True}):
            with self.subTest(departements=departements):
                self.verifier_refus_sans_table(departements=departements)

    def test_exclusions_vides(self):
        for exclusions in (None, "", []):
            with self.subTest(exclusions=exclusions):
                self.assertEqual(Daily_survey.normaliser_exclusions_cpv(exclusions), "")
        self.enregistrer()
        self.assertEqual(self.lignes[0]["mots_exclus"], "")

    def test_exclusions_multiples(self):
        self.enregistrer(mots_exclus=" Mot   1 ; mot 2\nMOT 1 ")
        self.assertEqual(self.lignes[0]["mots_exclus"], "Mot 1, mot 2")

    def test_exclusions_types_invalides(self):
        for exclusions in (3, [None], {"mot": True}):
            with self.subTest(exclusions=exclusions):
                self.verifier_refus_sans_table(mots_exclus=exclusions)

    def test_ordre_sources_departements_exclusions(self):
        self.enregistrer(sources=["TED", "BOAMP"], departements="34, 30", mots_exclus="alpha, beta")
        reponse = self.enregistrer(sources=["boamp", "ted"], departements=["30", "34"], mots_exclus=["BETA", "ALPHA"])
        self.assertEqual(reponse["statut"], "deja_active")
        self.assertEqual(len(self.lignes), 1)

    def test_non_connecte(self):
        self.get_user.return_value = None
        self.verifier_refus_sans_table()

    def test_email_inexploitable(self):
        for email in (None, "", "  ", 42, "sans-arobase", "@domaine", "nom@", "nom @domaine"):
            with self.subTest(email=email):
                self.get_user.return_value = {"email": email}
                self.verifier_refus_sans_table()

    def test_colonnes_et_constantes(self):
        self.enregistrer()
        ligne = self.lignes[0]
        self.assertEqual(set(ligne), {
            "email", "sources", "mots_cles", "mots_ou", "mots_exclus", "nb_jours",
            "departements", "active", "date_creation", "derniere_recherche",
            "dernier_statut", "derniere_erreur", "cle_requete",
            "nb_offres_derniere_recherche", "mode_recherche", "cpv_selectionnes", "mots_obligatoires"
        })
        self.assertIs(ligne["email"], self.utilisateur)
        self.assertEqual(ligne["mode_recherche"], "cpv")
        self.assertEqual(ligne["mots_cles"], "")
        self.assertEqual(ligne["mots_ou"], "")
        self.assertEqual(ligne["mots_obligatoires"], [])
        self.assertEqual(ligne["nb_jours"], 1)
        self.assertIs(ligne["active"], True)
        self.assertIsNone(ligne["derniere_recherche"])
        self.assertEqual(ligne["nb_offres_derniere_recherche"], 0)
        self.assertEqual(ligne["dernier_statut"], "jamais_lancee")
        self.assertEqual(ligne["derniere_erreur"], "")
        self.assertIsNotNone(ligne["date_creation"].tzinfo)
        self.assertEqual(ligne["date_creation"].utcoffset().total_seconds(), 0)

    def test_cle_version_deux(self):
        self.enregistrer()
        contenu_attendu = {
            "version": 2, "mode_recherche": "cpv", "email": self.utilisateur["email"],
            "cpv_selectionnes": ["80530000"], "sources": ["BOAMP"],
            "departements": [], "mots_exclus": [], "nb_jours": 1,
        }
        texte_attendu = json.dumps(contenu_attendu, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(self.lignes[0]["cle_requete"], hashlib.sha256(texte_attendu.encode("utf-8")).hexdigest())

    def test_doublon_actif_sans_mutation(self):
        self.enregistrer()
        avant = dict(self.lignes[0])
        reponse = self.enregistrer()
        self.assertFalse(reponse["ok"])
        self.assertEqual(reponse["statut"], "deja_active")
        self.assertEqual(self.lignes[0], avant)
        self.assertEqual(self.table.add_row.call_count, 1)

    def test_reactivation_limitee(self):
        self.enregistrer()
        ligne = self.lignes[0]
        ligne["active"] = False
        ligne["derniere_erreur"] = "ancienne erreur simulée"
        ligne["dernier_statut"] = "statut à conserver"
        avant = dict(ligne)
        reponse = self.enregistrer()
        attendu = dict(avant)
        attendu["active"] = True
        attendu["derniere_erreur"] = ""
        self.assertTrue(reponse["ok"])
        self.assertEqual(reponse["statut"], "reactivee")
        self.assertEqual(ligne, attendu)
        self.assertEqual(self.table.add_row.call_count, 1)

    def test_isolation_utilisateurs(self):
        self.enregistrer()
        premiere_ligne = self.lignes[0]
        self.get_user.return_value = {"email": "autre@example.invalid"}
        reponse = self.enregistrer()
        self.assertEqual(reponse["statut"], "cree")
        self.assertEqual(len(self.lignes), 2)
        self.assertIs(premiere_ligne["email"], self.utilisateur)
        self.assertNotEqual(premiere_ligne["cle_requete"], self.lignes[1]["cle_requete"])

    def test_isolation_meme_email_lignes_users_distinctes(self):
        self.enregistrer()
        self.get_user.return_value = {"email": self.utilisateur["email"]}
        reponse = self.enregistrer()
        self.assertEqual(reponse["statut"], "cree")
        self.assertEqual(len(self.lignes), 2)

    def test_arguments_non_mutes(self):
        arguments = {
            "cpv_selectionnes": ["80530000", "80510000", "80530000"],
            "sources": ["TED", "BOAMP", "ted"], "departements": ["34", "30"],
            "mots_exclus": ["Alpha", "Beta", "alpha"],
        }
        avant = copy.deepcopy(arguments)
        self.enregistrer(**arguments)
        self.assertEqual(arguments, avant)

    def test_criteres_differents_cle_differente(self):
        self.enregistrer()
        for criteres in ({"cpv_selectionnes": ["80510000"]}, {"sources": ["TED"]},
                         {"departements": "34"}, {"mots_exclus": "exclusion"}):
            self.assertEqual(self.enregistrer(**criteres)["statut"], "cree")
        self.assertEqual(len(self.lignes), 5)

    def test_erreurs_tables_propagees(self):
        self.table.search.side_effect = RuntimeError("panne simulée")
        with self.assertRaises(RuntimeError):
            self.enregistrer()
        self.table.add_row.assert_not_called()
        self.table.search.side_effect = self.rechercher_lignes_simulees
        self.table.add_row.side_effect = RuntimeError("écriture simulée refusée")
        with self.assertRaises(RuntimeError):
            self.enregistrer()

    def test_contrat_signature(self):
        signature = inspect.signature(Daily_survey.enregistrer_daily_survey_cpv)
        self.assertEqual(list(signature.parameters), ["cpv_selectionnes", "sources", "departements", "mots_exclus", "mots_obligatoires"])
        self.assertIsNone(signature.parameters["departements"].default)
        self.assertIsNone(signature.parameters["mots_exclus"].default)
        self.assertIsNone(signature.parameters["mots_obligatoires"].default)

    def test_separation_cle_legacy(self):
        cle_legacy = Daily_survey.creer_cle_requete(self.utilisateur["email"], ["BOAMP"], [], [], [], [])
        self.enregistrer()
        self.assertNotEqual(cle_legacy, self.lignes[0]["cle_requete"])

    def test_normalisation_obligatoires(self):
        cas = [
            (None, []), ("", []), ("   ", []), ([], []), ((), []),
            ("sst", ["sst"]), ("sst, recyclage", ["sst", "recyclage"]),
            ("sst; recyclage", ["sst", "recyclage"]),
            ("sst\nrecyclage", ["sst", "recyclage"]),
            ("formation sst", ["formation sst"]),
            ("formation santé et sécurité", ["formation santé et sécurité"]),
            ("et ou and or", ["et ou and or"]),
            ([" SST ", "recyclage", "sst", "formation   sst"],
             ["SST", "recyclage", "formation sst"]),
            (("réanimation", "RÉANIMATION"), ["réanimation"]),
        ]
        for valeur, attendu in cas:
            with self.subTest(valeur=valeur):
                avant = copy.deepcopy(valeur)
                resultat = Daily_survey.normaliser_mots_obligatoires_cpv(valeur)
                self.assertEqual(resultat, attendu)
                self.assertIsInstance(resultat, list)
                self.assertEqual(valeur, avant)
                self.assertIsNot(resultat, valeur)

    def test_obligatoires_invalides_avant_table(self):
        for valeur in (123, {"sst": True}, [1, 2], ["sst", 123],
                       ("sst", None), True, {"sst"}):
            with self.subTest(valeur=valeur):
                self.verifier_refus_sans_table(mots_obligatoires=valeur)

    def test_obligatoires_cle_v3_exacte(self):
        self.enregistrer(mots_obligatoires=["sst"])
        contenu = {
            "version": 3, "mode_recherche": "cpv",
            "email": self.utilisateur["email"],
            "cpv_selectionnes": ["80530000"], "sources": ["BOAMP"],
            "departements": [], "mots_exclus": [], "nb_jours": 1,
            "mots_obligatoires": ["sst"],
        }
        texte = json.dumps(contenu, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(self.lignes[0]["cle_requete"], hashlib.sha256(texte.encode("utf-8")).hexdigest())
        self.assertEqual(self.lignes[0]["mots_obligatoires"], ["sst"])

    def test_obligatoires_identite_et_stockage(self):
        self.enregistrer(mots_obligatoires=["réanimation", "SST"])
        avant = copy.deepcopy(self.lignes[0])
        reponse = self.enregistrer(mots_obligatoires=["sst", "REANIMATION", "Réanimation"])
        self.assertEqual(reponse["statut"], "deja_active")
        self.assertFalse(reponse["ok"])
        self.assertEqual(self.lignes[0], avant)
        self.assertEqual(self.lignes[0]["mots_obligatoires"], ["réanimation", "SST"])

    def test_obligatoires_ordre_doublons(self):
        self.enregistrer(mots_obligatoires="sst, recyclage")
        reponse = self.enregistrer(mots_obligatoires=["RECYCLAGE", "SST", "sst"])
        self.assertEqual(reponse["statut"], "deja_active")

    def test_obligatoires_expression_distincte(self):
        self.enregistrer(mots_obligatoires="formation sst")
        self.assertEqual(self.enregistrer(mots_obligatoires=["formation", "sst"])["statut"], "cree")
        self.assertNotEqual(self.lignes[0]["cle_requete"], self.lignes[1]["cle_requete"])

    def test_obligatoires_absence_distincte_et_ancienne_ligne(self):
        self.enregistrer()
        self.lignes[0]["mots_obligatoires"] = None
        for valeur in (None, "", " ; ", [], ()):
            self.assertEqual(self.enregistrer(mots_obligatoires=valeur)["statut"], "deja_active")
        self.assertIsNone(self.lignes[0]["mots_obligatoires"])
        self.lignes[0]["active"] = False
        self.assertEqual(self.enregistrer()["statut"], "reactivee")
        self.assertIsNone(self.lignes[0]["mots_obligatoires"])
        self.assertEqual(self.enregistrer(mots_obligatoires="sst")["statut"], "cree")
        self.assertEqual(len(self.lignes), 2)

    def test_obligatoires_reactivation_limitee(self):
        self.enregistrer(mots_obligatoires="réanimation")
        self.lignes[0]["active"] = False
        self.lignes[0]["derniere_erreur"] = "erreur simulée"
        attendu = dict(self.lignes[0])
        attendu.update(active=True, derniere_erreur="")
        self.assertEqual(self.enregistrer(mots_obligatoires="REANIMATION")["statut"], "reactivee")
        self.assertEqual(self.lignes[0], attendu)

    def test_obligatoires_isolation(self):
        self.enregistrer(mots_obligatoires="sst")
        self.get_user.return_value = {"email": "autre@example.invalid"}
        self.assertEqual(self.enregistrer(mots_obligatoires="sst")["statut"], "cree")

    def test_obligatoires_sans_legacy_et_sans_mutation(self):
        termes = [" SST ", "sst", "réanimation"]
        avant = list(termes)
        with patch.object(Daily_survey, "enregistrer_daily_survey", side_effect=AssertionError("legacy")), patch.object(
            Daily_survey, "creer_cle_requete", side_effect=AssertionError("legacy")
        ):
            self.enregistrer(mots_obligatoires=termes)
        self.assertEqual(termes, avant)
        self.assertEqual(self.lignes[0]["mots_cles"], "")
        self.assertEqual(self.lignes[0]["mots_ou"], "")

    def test_ancien_appel_positionnel(self):
        Daily_survey.enregistrer_daily_survey_cpv(["80530000"], ["BOAMP"], "34", "exclusion")
        self.assertEqual(self.lignes[0]["mots_exclus"], "exclusion")
        self.assertEqual(self.lignes[0]["mots_obligatoires"], [])
