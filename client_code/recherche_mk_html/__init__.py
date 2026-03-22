from ._anvil_designer import recherche_mk_htmlTemplate
from anvil import *
from anvil.js import window

class recherche_mk_html(recherche_mk_htmlTemplate):
    def __init__(self, html_genere="", **properties):
        self.init_components(**properties)
        self.dom_nodes["zone_desc"].innerHTML = html_genere or ""

    def aller_a_occurrence(self, hit_id, container_id="zone_test_interne"):
        return window.scrollToKeywordHit(container_id, hit_id)