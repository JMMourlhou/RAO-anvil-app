"""Reset et historique : méthodes réelles, composants et Data Tables simulés."""
import ast
import copy
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_search_recherche_cpv as support
from test_search_annulation import charger_menu


def charger_initialisation(anvil, app_tables):
    """Charge les fonctions serveur réelles sans imports ni décorateurs Anvil."""
    source = Path(__file__).resolve().parents[1] / "server_code/Init_Form_Search.py"
    arbre = ast.parse(source.read_text())
    fonctions = [element for element in arbre.body if isinstance(element, ast.FunctionDef)]
    for fonction in fonctions:
        fonction.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=fonctions, type_ignores=[]))
    espace = {
        "anvil": anvil, "app_tables": app_tables,
        "tables": SimpleNamespace(order_by=Mock()),
        "Variables_globales": SimpleNamespace(get_variable_value=Mock(return_value="app")),
    }
    exec(compile(module, str(source), "exec"), espace)
    return espace


class Ligne(dict):
    def get_id(self):
        return "historique-1"


class TestsResetHistorique(unittest.TestCase):
    def setUp(self):
        preparation = support.TestsRechercheCPV()
        preparation.setUp()
        self.form = preparation.form
        self.espace_search = preparation.espace
        self.espace_search["demander_choix"] = Mock(return_value=True)
        self.form.text_box_recherche_cpv = support.Composant()
        self.form.actualiser_bouton_veille_cpv = Mock()
        self.form.histo_id = "historique-1"
        self.form.revision_recherche = 7
        self.form._offres_correspondent_histo = True
        self.form.list_offres = [{"titre": "Offre originale", "vu": True}]
        self.form.sauver_offres_dans_histo = Mock(side_effect=AssertionError("écriture interdite"))
        self.form._ctx_recherche = dict(
            mode_recherche="classique", mots_obligatoires=["formation"],
            mots_ou=[], mots_exclus=[], periode=30,
            selected_platformes=["BOAMP"], departements=[]
        )
        self.ligne = Ligne(
            offres=copy.deepcopy(self.form.list_offres), nb_offres=1,
            revision_recherche=7, mots_cles="formation", mots_ou="",
            mots_exclus="", nb_jours=30, departements="", sources=["BOAMP"],
            mode_recherche="classique", cpv_selectionnes=[]
        )
        self.original = copy.deepcopy(self.ligne)
        self.table = Mock()
        self.table.get.return_value = self.ligne
        self.anvil = SimpleNamespace(
            users=SimpleNamespace(get_user=Mock(return_value={"email": "test@example.com"})),
            server=SimpleNamespace(call=Mock(), no_loading_indicator=nullcontext())
        )
        self.serveur = charger_initialisation(
            self.anvil, SimpleNamespace(
                histo=self.table,
                platformes=SimpleNamespace(search=Mock(return_value=[]))
            )
        )
        self.anvil.server.call.side_effect = lambda nom: self.serveur[nom]()
        self.espace_menu = charger_menu()
        self.espace_menu["anvil"] = self.anvil
        self.menu = self.espace_menu["Menu"]()
        for nom in ("navigation_link_user_derniere_recherche navigation_link_user_contact "
                    "navigation_link_user_parametres navigation_link_user_appels_offres "
                    "navigation_link_fermer Titre bt_user_mail navigation_link_retour "
                    "navigation_link_search_go").split():
            setattr(self.menu, nom, support.Composant())
        self.menu.content_panel = Mock()
        self.menu.activer_bouton_arret = Mock()
        self.menu.form_search = self.form

    def verifier_reset(self, methode):
        contexte = copy.deepcopy(self.form._ctx_recherche)
        getattr(self.form, methode)()
        self.assertEqual(self.form.list_offres, [])
        self.assertEqual(self.form.repeating_panel_offres.items, [])
        self.assertFalse(self.form._offres_correspondent_histo)
        self.assertEqual(self.form.histo_id, "historique-1")
        self.assertEqual(self.form.revision_recherche, 7)
        self.assertEqual(self.form._ctx_recherche, contexte)
        self.form.sauver_offres_dans_histo.assert_not_called()
        self.espace_search["anvil"].server.call.assert_not_called()
        self.assertEqual(self.ligne, self.original)

    def test_reset_apres_chargement_historique(self):
        self.verifier_reset("button_del_all_click")

    def test_reset_avant_modification_parametres(self):
        self.verifier_reset("button_del_before_modif_param")

    def test_reset_annule_conserve_affichage_et_correspondance(self):
        self.espace_search["demander_choix"].return_value = False
        self.form.button_del_all_click()
        self.assertEqual(self.form.list_offres, self.original["offres"])
        self.assertTrue(self.form._offres_correspondent_histo)
        self.espace_search["anvil"].server.call.assert_not_called()

    def test_retour_menu_selon_existence_historique(self):
        for compteur, existe in ((3, True), (0, True), (None, False)):
            with self.subTest(nb_offres=compteur):
                self.table.get.return_value = None if not existe else Ligne(nb_offres=compteur)
                self.menu.form_search = self.form
                self.menu.revenir_menu_apres_arret(self.form)
                self.assertIsNone(self.menu.form_search)
                self.assertIs(self.menu.navigation_link_user_derniere_recherche.visible, existe)
                self.anvil.server.call.assert_called_with("existe_derniere_recherche")
                self.table.get.assert_called_with(email="test@example.com")

    def test_utilisateur_deconnecte_lien_masque_sans_appel_serveur(self):
        self.anvil.users.get_user.return_value = None
        self.menu.actualiser_visibilite_derniere_recherche()
        self.assertFalse(self.menu.navigation_link_user_derniere_recherche.visible)
        self.anvil.server.call.assert_not_called()

    def test_recharge_apres_reset_retrouve_offres_persistees(self):
        for methode in ("button_del_all_click", "button_del_before_modif_param"):
            with self.subTest(methode=methode):
                self.setUp()
                self.verifier_reset(methode)
                self.menu.revenir_menu_apres_arret(self.form)
                self.assertTrue(self.menu.navigation_link_user_derniere_recherche.visible)
                donnees = self.serveur["initialiser_form_search"](inclure_offres=True)
                self.form.list_offres = self.form.normaliser_liste_offres_vu(donnees["histo"]["offres"])
                self.form.afficher_offres(self.form.list_offres)
                self.assertEqual(self.form.list_offres, self.original["offres"])
                self.assertEqual(donnees["histo"]["revision_recherche"], 7)
                self.assertEqual(self.ligne, self.original)


if __name__ == "__main__":
    unittest.main()
