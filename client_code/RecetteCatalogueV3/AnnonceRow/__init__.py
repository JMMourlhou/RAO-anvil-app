from ._anvil_designer import AnnonceRowTemplate
from anvil import *


class AnnonceRow(AnnonceRowTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)

    @handle("button_detail", "click")
    def consulter_detail(self, **event_args):
        identifiants = self.item.get("offre_ids")
        if not identifiants:
            identifiant = self.item.get("offre_id")
            identifiants = [identifiant] if identifiant is not None else []
        # Le serveur impose à nouveau la forme décimale et la limite de dix IDs.
        self.parent.raise_event("x-detail", offre_ids=identifiants)
