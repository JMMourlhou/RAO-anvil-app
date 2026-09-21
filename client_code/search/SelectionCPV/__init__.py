from anvil import *
from ._anvil_designer import SelectionCPVTemplate


class SelectionCPV(SelectionCPVTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)

    @handle("button_retirer_cpv", "click")
    def button_retirer_cpv_click(self, **event_args):
        """Demande le retrait de ce seul code dans la sélection du parent.

        Paramètre : event_args (dict Anvil). Retour : None. Le code str vient
        de self.item ; aucun accès à une table ni appel serveur n'est effectué.
        """
        
        self.parent.raise_event("x-retirer-cpv", code_cpv=self.item["code"])
