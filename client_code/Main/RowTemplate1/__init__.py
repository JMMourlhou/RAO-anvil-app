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
        self.text_1.text = str(self.item['date_publication'].strftime("%d/%m/%Y"))
        self.text_2.text = self.item['titre']
        self.link_1.text = self.item['lien']
        self.text_3.text = self.item['departement']
        self.checkbox_1.checked = self.item['vu']

    def link_1_click(self, **event_args):
        """This method is called clicked"""
        from anvil.js import window
        self.checkbox_1.checked = True
        self.checkbox_1_change()
        window.open(self.link_1.text)
        

    def checkbox_1_change(self, **event_args):
        """This method is called when the component is checked or unchecked"""
        result = anvil.server.call("check", self.item, self.checkbox_1.checked)
        if not result:
            alert("Erreur en Modification")

    def toggle_icon_button_1_click(self, **event_args):
        result = anvil.server.call("del_1", self.item)
        if not result:
            alert("Erreur en Effacement")
        else:
            open_form('Main')
        
        
        