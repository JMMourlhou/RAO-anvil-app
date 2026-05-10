from ._anvil_designer import recherche_mk_htmlTemplate
from anvil import *


class recherche_mk_html(recherche_mk_htmlTemplate):

    def __init__(self, **properties):
        self.init_components(**properties)
        self._texte_html = ""
        self._mots_cles = []
        self._mots_score = []

    def _to_list(self, valeur):
        """
        Sécurise les valeurs reçues :
        - None -> []
        - dict -> liste des clés
        - list/tuple/set -> liste propre
        - str -> [str]
        """
        if not valeur:
            return []

        if isinstance(valeur, dict):
            valeur = list(valeur.keys())

        elif not isinstance(valeur, (list, tuple, set)):
            valeur = [valeur]

        return [
            str(v).strip()
            for v in valeur
            if str(v).strip()
        ]

    def charger(self, texte_html, mots_cles=None, mots_score=None):
        """
        Charge le texte HTML, les mots-clés de recherche
        et les mots utilisés pour le scoring.
        """
        self._texte_html = texte_html or ""
        self._mots_cles = self._to_list(mots_cles)
        self._mots_score = self._to_list(mots_score)

        # Si le composant est déjà affiché
        try:
            self.call_js(
                "render_keywords",
                self._texte_html,
                self._mots_cles,
                self._mots_score
            )
        except Exception:
            pass

    def form_show(self, **event_args):
        self.call_js(
            "render_keywords",
            self._texte_html,
            self._mots_cles,
            self._mots_score
        )