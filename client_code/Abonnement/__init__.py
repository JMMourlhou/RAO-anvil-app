from ._anvil_designer import AbonnementTemplate
from anvil import *
import anvil.server
import m3.components as m3
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .. import Retour_par_test_ecran

class Abonnement(AbonnementTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Any code you write here will run before the form opens.

    def button_retour_click(self, **event_args):
        """This method is called when the button is clicked"""
        Retour_par_test_ecran.largeur_ecran()
