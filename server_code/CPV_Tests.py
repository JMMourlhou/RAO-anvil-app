"""Tests CPV sans Data Tables, réseau, utilisateur ou écriture persistante.

Ce module ne publie aucun callable et n'exécute pas les tests à l'import.
"""

import unittest
from unittest.mock import patch

from . import CPV_API, CPV_Metier
from .CPV_Catalogue import LIBELLES_PAR_CODE, NOMBRE_CODES


class TestsAPIRechercheCPV(unittest.TestCase):
    """Vérifie les contrats publics sur le catalogue officiel complet."""

    def test_catalogue_complet(self):
        self.assertEqual(len(LIBELLES_PAR_CODE), NOMBRE_CODES)
        self.assertEqual(NOMBRE_CODES, 9454)
        for code_cpv, libelle_officiel in LIBELLES_PAR_CODE.items():
            self.assertRegex(code_cpv, r"^[0-9]{8}$")
            self.assertTrue(libelle_officiel)

    def test_libelle_exact_prioritaire(self):
        reponse = CPV_API.rechercher_cpv("Services de formation professionnelle")
        self.assertTrue(reponse["ok"])
        self.assertEqual(reponse["resultats"][0], {
            "code": "80530000", "libelle": "Services de formation professionnelle"
        })

    def test_libelle_partiel(self):
        reponse = CPV_API.rechercher_cpv("formation professionnelle")
        self.assertIn("80530000", [resultat["code"] for resultat in reponse["resultats"]])

    def test_casse(self):
        self.assertEqual(CPV_API.rechercher_cpv("FORMATION"), CPV_API.rechercher_cpv("formation"))

    def test_accents(self):
        reponse = CPV_API.rechercher_cpv("électricité")
        self.assertTrue(reponse["resultats"])
        self.assertEqual(reponse, CPV_API.rechercher_cpv("ELECTRICITE"))

    def test_code_exact(self):
        reponse = CPV_API.rechercher_cpv("80530000")
        self.assertEqual(len(reponse["resultats"]), 1)
        self.assertEqual(reponse["resultats"][0]["code"], "80530000")

    def test_code_partiel(self):
        reponse = CPV_API.rechercher_cpv("8053")
        self.assertTrue(reponse["resultats"])
        for resultat in reponse["resultats"]:
            self.assertTrue(resultat["code"].startswith("8053"))

    def test_aucun_resultat(self):
        self.assertEqual(CPV_API.rechercher_cpv("zzzintrouvablezzz"), {
            "ok": True, "resultats": [], "total_resultats": 0, "message": ""
        })

    def test_recherche_vide(self):
        self.assertEqual(CPV_API.rechercher_cpv("  ")["resultats"], [])

    def test_limites_respectees(self):
        for limite in (1, 3, 10, 50, 60, 110):
            reponse = CPV_API.rechercher_cpv("services", limite)
            self.assertTrue(reponse["ok"])
            self.assertEqual(len(reponse["resultats"]), limite)
        self.assertEqual(len(CPV_API.rechercher_cpv("services")["resultats"]), 10)

    def test_limites_invalides(self):
        for limite in (0, -1, NOMBRE_CODES + 1, True, "10", 2.5, None):
            with self.subTest(limite=limite):
                self.assertFalse(CPV_API.rechercher_cpv("formation", limite)["ok"])

    def test_termes_invalides(self):
        for terme in (None, 80530000, [], {}, "a" * 201):
            with self.subTest(terme=terme):
                self.assertFalse(CPV_API.rechercher_cpv(terme)["ok"])

    def test_plusieurs_codes_et_ordre(self):
        reponse = CPV_API.obtenir_libelles_cpv(["80531000", "80530000"])
        self.assertTrue(reponse["ok"])
        self.assertEqual([resultat["code"] for resultat in reponse["resultats"]],
                         ["80531000", "80530000"])
        for resultat in reponse["resultats"]:
            self.assertEqual(resultat["libelle"], LIBELLES_PAR_CODE[resultat["code"]])

    def test_code_inconnu_sans_resultat_partiel(self):
        reponse = CPV_API.obtenir_libelles_cpv(["80530000", "99999999"])
        self.assertFalse(reponse["ok"])
        self.assertEqual(reponse["resultats"], [])

    def test_doublons_sans_mutation(self):
        codes = ["80531000", "80530000", "80531000"]
        reponse = CPV_API.valider_selection_cpv(codes)
        self.assertEqual(reponse["codes"], ["80531000", "80530000"])
        self.assertEqual(codes, ["80531000", "80530000", "80531000"])
        self.assertEqual(len(CPV_API.obtenir_libelles_cpv(codes)["resultats"]), 2)

    def test_selection_vide(self):
        self.assertFalse(CPV_API.valider_selection_cpv([])["ok"])
        self.assertFalse(CPV_API.obtenir_libelles_cpv([])["ok"])

    def test_types_et_formats_selection_invalides(self):
        selections_invalides = [None, "80530000", ("80530000",), {},
                                [80530000], [None], [True], ["80530000-8"],
                                [" 80530000"], ["８０５３００００"]]
        for codes in selections_invalides:
            with self.subTest(codes=codes):
                self.assertFalse(CPV_API.valider_selection_cpv(codes)["ok"])
                self.assertFalse(CPV_API.obtenir_libelles_cpv(codes)["ok"])

    def test_resolution_bornee(self):
        codes = list(LIBELLES_PAR_CODE)[:100]
        self.assertEqual(len(CPV_API.obtenir_libelles_cpv(codes)["resultats"]), 100)
        self.assertFalse(CPV_API.obtenir_libelles_cpv(codes + ["80530000"])["ok"])

    def test_resultats_independants_du_catalogue(self):
        reponse = CPV_API.rechercher_cpv("80530000")
        reponse["resultats"][0]["libelle"] = "Modification locale"
        self.assertEqual(LIBELLES_PAR_CODE["80530000"], "Services de formation professionnelle")

    def test_classement_prefixe_avant_inclusion(self):
        reponse = CPV_API.rechercher_cpv("services", 50)
        self.assertTrue(reponse["resultats"][0]["libelle"].lower().startswith("services"))
        self.assertEqual(reponse, CPV_API.rechercher_cpv("services", 50))

    def test_fibre_trouve_un_mot_au_milieu_du_libelle(self):
        reponse = CPV_API.rechercher_cpv("fibre", 50)
        self.assertTrue(reponse["resultats"])
        libelles_normalises = [
            CPV_Metier.normaliser_texte(resultat["libelle"])
            for resultat in reponse["resultats"]
        ]
        self.assertTrue(any("fibre" in libelle for libelle in libelles_normalises))
        self.assertIn("32562000", [resultat["code"] for resultat in reponse["resultats"]])

    def test_fragment_au_milieu_d_un_mot(self):
        reponse = CPV_API.rechercher_cpv("ibres", 50)
        self.assertTrue(reponse["resultats"])
        self.assertIn("32562000", [resultat["code"] for resultat in reponse["resultats"]])

    def test_secours_reste_recherche_partout(self):
        reponse = CPV_API.rechercher_cpv("secours", 50)
        self.assertTrue(reponse["resultats"])
        for resultat in reponse["resultats"]:
            self.assertIn("secours", CPV_Metier.normaliser_texte(resultat["libelle"]))

    def test_priorites_exact_debut_mot_inclusion(self):
        cas = (
            ("fibre", "fibre", 0),
            ("fibre", "fibres optiques", 1),
            ("fibre", "cables a fibres optiques", 2),
            ("fibre", "materiau multifibre optique", 3),
            ("fibre", "cables optiques", None),
        )
        for terme_normalise, libelle_normalise, priorite_attendue in cas:
            with self.subTest(libelle=libelle_normalise):
                priorite = CPV_Metier.calculer_priorite_libelle(
                    terme_normalise, libelle_normalise
                )
                self.assertEqual(priorite, priorite_attendue)

    def test_classement_complet_et_departage_deterministe(self):
        libelles_test = {
            "00000004": "Une multifibre optique",
            "00000003": "Câbles à fibres optiques",
            "00000002": "Fibres industrielles",
            "00000001": "Fibre",
            "00000005": "Câbles à fibres acoustiques",
        }
        libelles_normalises_test = {}
        for code_cpv, libelle_officiel in libelles_test.items():
            libelles_normalises_test[code_cpv] = CPV_Metier.normaliser_texte(libelle_officiel)

        with patch.object(CPV_Metier, "LIBELLES_NORMALISES", libelles_normalises_test):
            premier_resultat = CPV_Metier.rechercher_dans_catalogue("fibre", 5)
            second_resultat = CPV_Metier.rechercher_dans_catalogue("FIBRE", 5)

        self.assertEqual(premier_resultat, [
            "00000001",
            "00000002",
            "00000005",
            "00000003",
            "00000004",
        ])
        self.assertEqual(second_resultat, premier_resultat)

    def test_limite_appliquee_apres_classement(self):
        reponse_limitee = CPV_API.rechercher_cpv("fibre", 3)
        reponse_complete = CPV_API.rechercher_cpv("fibre", 50)
        self.assertEqual(reponse_limitee["resultats"], reponse_complete["resultats"][:3])

    def test_erreur_inattendue_propagee(self):
        with patch.object(CPV_Metier, "rechercher_dans_catalogue_avec_total", side_effect=RuntimeError("test")):
            with self.assertRaises(RuntimeError):
                CPV_API.rechercher_cpv("formation")


    def test_total_independant_de_la_limite(self):
        reponse_complete = CPV_API.rechercher_cpv("services", NOMBRE_CODES)
        total_attendu = len(reponse_complete["resultats"])
        self.assertGreater(total_attendu, 100)
        for limite in (10, 50, 60, 110):
            reponse = CPV_API.rechercher_cpv("services", limite)
            self.assertEqual(reponse["total_resultats"], total_attendu)
            self.assertEqual(reponse["resultats"], reponse_complete["resultats"][:limite])

    def test_total_code_exact_et_vide(self):
        self.assertEqual(CPV_API.rechercher_cpv("80530000")["total_resultats"], 1)
        self.assertEqual(CPV_API.rechercher_cpv("")["total_resultats"], 0)

    def test_contrat_metier_historique(self):
        codes = CPV_Metier.rechercher_dans_catalogue("services", 60)
        reponse = CPV_API.rechercher_cpv("services", 60)
        self.assertIsInstance(codes, list)
        self.assertEqual(codes, [resultat["code"] for resultat in reponse["resultats"]])
