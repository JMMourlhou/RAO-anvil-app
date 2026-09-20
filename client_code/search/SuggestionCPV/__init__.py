from anvil import *
from ._anvil_designer import SuggestionCPVTemplate


class SuggestionCPV(SuggestionCPVTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self.actualiser_etat_bouton()

    def actualiser_etat_bouton(self):
        """Présente le bouton selon l'état calculé par la Form ``search``.

        Aucun paramètre. Retour : None. La méthode ne modifie ni la suggestion
        ni la sélection ; elle applique uniquement leur état visuel dérivé.
        """
        cpv_est_selectionne = bool(self.item.get("est_selectionne", False))
        if cpv_est_selectionne:
            self.button_ajouter_cpv.text = "Ajouté ✓"
            self.button_ajouter_cpv.icon = "fa:check"
            self.button_ajouter_cpv.background = "#2e7d32"
            self.button_ajouter_cpv.foreground = "white"
            self.button_ajouter_cpv.enabled = False
            return

        self.button_ajouter_cpv.text = "Ajouter"
        self.button_ajouter_cpv.icon = "fa:plus-square"
        self.button_ajouter_cpv.background = ""
        self.button_ajouter_cpv.foreground = ""
        self.button_ajouter_cpv.enabled = True

    @handle("button_ajouter_cpv", "click")
    def button_ajouter_cpv_click(self, **event_args):
        """Transmet la suggestion officielle au parent, sans appel serveur.

        Paramètre : event_args (dict Anvil). Retour : None. self.item contient
        code et libelle (str) issus des résultats de l'API CPV.
        """
        if self.item.get("est_selectionne", False):
            return
        self.parent.raise_event("x-ajouter-cpv", cpv_propose=self.item)
