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
        self.DropDown_compact_valeur.items = [
            ("*", 1),
            ("* *", 5),
            ("* * *", 10)
        ]
        print(f"item: {self.item}")
        self.text_box_mot.text = self.item[0]     # mot, 1er élément ds la liste
        self.DropDown_compact_valeur.selected_value = self.item[1]

    def icon_button_del_click(self, **event_args):
        self.parent.raise_event("x-del-mot",
                         mot=self.item[0]
                        )  # j'envoi le mot à la forme mère

    #modif: je dois effecer l'ancienne cle/valeur et créer la nouvelle entrée modifiée    
    def icon_button_valid_mot_score_click(self, **event_args):
        cle = (self.text_box_mot.text or "").strip()
        valeur = (self.DropDown_compact_valeur.selected_value or 0)

        if cle == "" :
            alert("Entrez le mot à prendre en compte dans le scoring")
            self.text_box_mot.focus()
            return

        if valeur == 0:
            alert("Sélectionnez l'importance du mot.")
            return
            
        self.parent.raise_event("x-modif",
                                item=self.item,  # ancienne valeur à effacer
                                cle = cle,       # nouvelle cle (le mot)
                                valeur = valeur  # nouvelle valeur
                               )  # j'envoi le mot à la forme mère

    def text_box_mot_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        #self.icon_button_valid_mot_score.visible = True
        self.icon_button_valid_mot_score_click()


    def text_box_mot_change(self, **event_args):
        """This method is called when the text in this component is edited."""
        self.icon_button_valid_mot_score.visible = True
  
  




   
