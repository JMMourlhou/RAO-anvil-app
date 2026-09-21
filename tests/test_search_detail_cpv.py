"""Détail CPV et legacy isolé : aucun appel Anvil ou serveur réel."""
import ast
import copy
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from test_search_recherche_cpv import charger_methodes, Composant


class TestsDetailCPV(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'client_code/search/RowTemplate1/__init__.py'
        arbre = ast.parse(source.read_text())
        classe = next(element for element in arbre.body if isinstance(element, ast.ClassDef))
        noms = ('extraire_mots_et', 'extraire_liste_depuis_parent_tag', 'button_generer_html_click')
        methodes = [element for element in classe.body if isinstance(element, ast.FunctionDef) and element.name in noms]
        for methode in methodes:
            methode.decorator_list = []
        module = ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name='Ligne', bases=[], keywords=[], body=methodes, decorator_list=[])], type_ignores=[]))
        self.alerte = Mock()
        self.composant_html = Mock()
        espace = {'alert': self.alerte, 'recherche_mk_html': Mock(return_value=self.composant_html), 're': re}
        exec(compile(module, str(source), 'exec'), espace)
        self.ligne = espace['Ligne']()
        self.ligne.parent = SimpleNamespace(tag=SimpleNamespace(mots_et_saisis='formation et secours'))
        self.ligne.item = {'cpv_codes': ['80560000'], 'provenances': [{'source': 'BOAMP'}], 'mots_ou_trouves': ['ancien']}
        self.original = copy.deepcopy(self.ligne.item)
        self.ligne.item_value = lambda nom, valeur: self.ligne.item.get(nom, valeur)
        self.ligne.scroll_into_view = Mock()
        self.ligne.column_panel_detail = SimpleNamespace(visible=False)
        self.ligne.button_generer_html = SimpleNamespace(icon='')
        self.ligne.checkbox_vu = SimpleNamespace(checked=True)
        self.ligne.column_panel_affichage = Mock()
        self.ligne.comp_html = None
        self.ligne.get_texte_source_verification = Mock(return_value='Formation SST recyclage')
        self.ligne.format_search_text_for_display = lambda texte: texte

    def ouvrir_cpv(self, termes):
        self.ligne.parent.tag.mots_obligatoires_cpv = termes
        self.ligne.button_generer_html_click()
        self.assertTrue(self.ligne.column_panel_detail.visible)
        self.composant_html.charger.assert_called_once_with('Formation SST recyclage', mots_cles=termes, mots_ou=[])
        self.alerte.assert_not_called()
        self.assertEqual(self.original, self.ligne.item)

    def test_cpv_sans_termes(self):
        self.ouvrir_cpv([])

    def test_cpv_un_terme(self):
        self.ouvrir_cpv(['sst'])

    def test_cpv_plusieurs_termes(self):
        self.ouvrir_cpv(['sst', 'recyclage'])

    def test_expression_conservee(self):
        self.ouvrir_cpv(['formation santé et sécurité'])

    def test_legacy_surlignage(self):
        self.ligne.button_generer_html_click()
        self.composant_html.charger.assert_called_once_with('Formation SST recyclage', mots_cles=['formation', 'secours'], mots_ou=['ancien'])
        self.assertTrue(self.ligne.column_panel_detail.visible)

    def test_legacy_sans_termes(self):
        self.ligne.parent.tag.mots_et_saisis = ''
        self.ligne.item['mots_ou_trouves'] = []
        self.ligne.button_generer_html_click()
        self.composant_html.charger.assert_called_once_with('Formation SST recyclage', mots_cles=[], mots_ou=[])
        self.alerte.assert_not_called()

    def test_contenu_absent(self):
        self.ligne.get_texte_source_verification.return_value = ''
        self.ligne.button_generer_html_click()
        self.assertFalse(self.ligne.column_panel_detail.visible)
        self.composant_html.charger.assert_not_called()
        self.alerte.assert_called_once_with('Aucun texte disponible pour cette offre !')

    def test_instantane_independant_du_champ_et_du_tag_legacy(self):
        espace = charger_methodes()
        form = espace['Search']()
        form._ctx_recherche = {'mode_recherche': 'cpv', 'mots_obligatoires': ['formation et sécurité']}
        form.list_offres = []
        for nom in ('repeating_panel_offres', 'text_nb_offres', 'data_grid_1', 'column_panel_select', 'button_selection_mailed', 'column_panel_params'):
            setattr(form, nom, Composant())
        form.text_box_mots_obligatoires_cpv = Composant('saisie modifiée')
        form.afficher_offres()
        self.ligne.parent = form.repeating_panel_offres
        self.ligne.parent.tag.mots_et_saisis = 'autres mots'
        self.assertEqual(self.ligne.extraire_mots_et(), ['formation et sécurité'])
        termes = self.ligne.extraire_mots_et()
        termes.append('nouveau')
        self.assertEqual(form._ctx_recherche['mots_obligatoires'], ['formation et sécurité'])


if __name__ == '__main__':
    unittest.main()
