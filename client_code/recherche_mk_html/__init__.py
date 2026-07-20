from ._anvil_designer import recherche_mk_htmlTemplate
from anvil import *


class recherche_mk_html(recherche_mk_htmlTemplate):

    def __init__(self, **properties):
        self.init_components(**properties)

        self._texte_html = ""
        self._mots_cles = []
        self._mots_ou = []

    def _to_list(self, valeur):
        """
        Transforme une valeur en liste de textes propres.

        Accepte :
        - None
        - dictionnaire
        - liste, tuple ou ensemble
        - chaîne de caractères
        """

        if not valeur:
            return []

        if isinstance(valeur, dict):
            valeurs = list(valeur.keys())

        elif isinstance(valeur, (list, tuple, set)):
            valeurs = list(valeur)

        else:
            valeurs = [valeur]

        resultat = []
        deja_vus = set()

        for element in valeurs:
            texte = str(element or "").strip()

            if not texte:
                continue

            cle = texte.lower()

            if cle in deja_vus:
                continue

            deja_vus.add(cle)
            resultat.append(texte)

        return resultat

    def charger(
        self,
        texte_html,
        mots_cles=None,
        mots_ou=None,
        mots_score=None
    ):
        """
        Charge :

        - le texte à afficher ;
        - les mots obligatoires ;
        - les mots OU réellement trouvés.

        `mots_score` est conservé temporairement pour rester
        compatible avec l’ancienne version de RowTemplate1.
        """

        # Compatibilité temporaire avec RowTemplate1 actuel
        if mots_ou is None and mots_score is not None:
            mots_ou = mots_score

        self._texte_html = str(texte_html or "")
        self._mots_cles = self._to_list(mots_cles)
        self._mots_ou = self._to_list(mots_ou)

        # Si le composant est déjà visible, on actualise immédiatement.
        try:
            self.call_js(
                "render_keywords",
                self._texte_html,
                self._mots_cles,
                self._mots_ou
            )
        except Exception:
            pass

    def form_show(self, **event_args):
        """
        Affiche le texte et applique les surbrillances
        lorsque le composant devient visible.
        """

        self.call_js(
            "render_keywords",
            self._texte_html,
            self._mots_cles,
            self._mots_ou
        )