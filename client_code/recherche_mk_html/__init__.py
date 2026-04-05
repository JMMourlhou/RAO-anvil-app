from ._anvil_designer import recherche_mk_htmlTemplate
from anvil import *

class recherche_mk_html(recherche_mk_htmlTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self._texte_html = ""
        self._mots_cles = []

    def charger(self, texte_html, mots_cles=None):
        self._texte_html = texte_html or ""
        self._mots_cles = mots_cles or []

        # si le composant est déjà affiché
        try:
            self.call_js("render_keywords", self._texte_html, self._mots_cles)
        except Exception:
            pass

    def form_show(self, **event_args):
        self.call_js("render_keywords", self._texte_html, self._mots_cles)