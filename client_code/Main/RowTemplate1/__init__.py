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
        self.text_1.text = self.item['date_publication']
        self.text_2.text = self.item['titre']
        self.link_1.text = self.item['lien']

    def link_1_click(self, **event_args):
        """This method is called clicked"""
        from anvil.js import window
        window.open(self.link_1.text)

    def checkbox_1_change(self, **event_args):
        """This method is called when the component is checked or unchecked"""
        result = anvil.server.call("check", self.checkbox_1.checked)
        if not result:
            alert("Erreur en modif")
        
        