from anvil import *
from ._anvil_designer import SuggestionCPVTemplate


class SuggestionCPV(SuggestionCPVTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)

    @handle("button_ajouter_cpv", "click")
    def button_ajouter_cpv_click(self, **event_args):
        """Transmet la suggestion officielle au parent, sans appel serveur.

        Paramètre : event_args (dict Anvil). Retour : None. self.item contient
        code et libelle (str) issus des résultats de l'API CPV.
        """
        self.parent.raise_event("x-ajouter-cpv", cpv_propose=self.item)
