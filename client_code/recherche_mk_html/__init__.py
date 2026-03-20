from ._anvil_designer import recherche_mk_htmlTemplate
from anvil import *

class recherche_mk_html(recherche_mk_htmlTemplate):
    def __init__(self, html_genere="", **properties):
        self.init_components(**properties)
        self.dom_nodes["zone_desc"].innerHTML = html_genere or ""

