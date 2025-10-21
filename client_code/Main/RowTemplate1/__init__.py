from ._anvil_designer import RowTemplate1Template
from anvil import *
import anvil.server
import m3.components as m3
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class RowTemplate1(RowTemplate1Template):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Any code you write here will run before the form opens.
        self.text_date_publication.text = str(self.item['date_publication'].strftime("%d/%m/%Y"))
        self.text_titre.text = self.item['titre']
        self.link_lien.text = self.item['lien']
        self.text_departement.text = self.item['departement']
        self.text_date_limite_rep.text = str(self.item['date_limite_rep'].strftime("%d/%m/%Y"))
        self.checkbox_vu.checked = self.item['vu']

    def link_lien_click(self, **event_args):
        """This method is called clicked"""
        from anvil.js import window
        self.link_lien.checked = True
        window.open(self.link_lien.text)
        # marquage de l'offre
        self.checkbox_vu.checked = True
        self.checkbox_vu_change()
        

    def checkbox_vu_change(self, **event_args):
        """This method is called when the component is checked or unchecked"""
        with anvil.server.no_loading_indicator:
            result = anvil.server.call("check", self.item, self.checkbox_vu.checked)
        if not result:
            alert("Erreur en Modification")

    def toggle_icon_button_1_click(self, **event_args):  #Effact de la row offre 
        result = anvil.server.call("del_1", self.item)
        if not result:
            alert("Erreur en Effacement")
        else:
            open_form('Main', "check") # permet de réafficher
        
        
        