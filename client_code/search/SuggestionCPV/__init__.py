from anvil import *
from ._anvil_designer import SuggestionCPVTemplate


class SuggestionCPV(SuggestionCPVTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self.actualiser_etat_bouton()

    def actualiser_etat_bouton(self):
        """Présente le bouton selon l'état calculé par la Form search.

        Aucun paramètre. Retour : None.
        Le bouton reste actif dans les deux états :
        - non sélectionné : ajout ;
        - sélectionné : retrait.
        """
        self.button_ajouter_cpv.font_size = 12
        self.button_ajouter_cpv.spacing_below = "small"

        cpv_est_selectionne = bool(self.item.get("est_selectionne", False))

        if cpv_est_selectionne:
            self.button_ajouter_cpv.icon = "fa:check"
            self.button_ajouter_cpv.background = "#2e7d32"
            self.button_ajouter_cpv.enabled = True
            return

        self.button_ajouter_cpv.icon = "fa:plus-square"
        self.button_ajouter_cpv.background = "Transparent"
        self.button_ajouter_cpv.enabled = True

    @handle("button_ajouter_cpv", "click")
    def button_ajouter_cpv_click(self, **event_args):
        """Ajoute ou retire le CPV selon son état actuel."""

        if self.item.get("est_selectionne", False):
            self.parent.raise_event("x-retirer-cpv", code_cpv=self.item["code"])
        else:
            self.parent.raise_event("x-ajouter-cpv", cpv_propose=self.item)