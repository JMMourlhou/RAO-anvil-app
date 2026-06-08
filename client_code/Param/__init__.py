from ._anvil_designer import ParamTemplate
from anvil import *
import anvil.server
import m3.components as m3
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .. import Mail_valideur
from .. import Mail_valideur  
from .. import Context_ecran

class Param(ParamTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        self.card_1.background_color = "theme:Background"
        context = Context_ecran.context_screen()
        if context['screen_type']=="phone":
            self.column_panel_tel_mail.wrap_on = 'mobile'
        else:
            self.column_panel_tel_mail.wrap_on = 'never'
