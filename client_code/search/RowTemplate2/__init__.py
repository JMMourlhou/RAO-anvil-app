from ._anvil_designer import RowTemplate2Template
import anvil.server
import m3.components as m3
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class RowTemplate2(RowTemplate2Template):
    def __init__(self, **properties):
        super().__init__(**properties)
