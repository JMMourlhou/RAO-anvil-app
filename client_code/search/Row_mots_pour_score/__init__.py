from ._anvil_designer import Row_mots_pour_scoreTemplate
from anvil import *
import anvil.server
import m3.components as m3
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Row_mots_pour_score(Row_mots_pour_scoreTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        # Any code you write here will run before the form opens.
        print(f"item: {self.item}")
        self.text_box_mot.text = self.item[0]     # mot, 1er élément ds la liste
        self.text_box_valeur.text = self.item[1]

    def icon_button_del_click(self, **event_args):
        self.parent.raise_event("x-del-mot",
                         mot=self.item[0]
                        )  # j'envoi le mot à la forme mère
        
