from ._anvil_designer import Form1Template
from anvil import *
from ..recherche_mk_html import recherche_mk_html

class Form1(Form1Template):
    def __init__(self, **properties):
        self.init_components(**properties)
        self.comp_html = None
        self.button_aller_mot.visible = False

    def button_charger_test_click(self, **event_args):
        html_genere = """
        <div id="zone_test_interne">
          ligne 1<br>
          ligne 2<br>
          ligne 3<br>
          ligne 4<br>
          ligne 5<br>
          ligne 6<br>
          ligne 7<br>
          ligne 8<br>
          <mark id="kw_hit_1">formation</mark><br>
          ligne 10<br>
          ligne 11<br>
          ligne 12<br>
          ligne 13<br>
          ligne 14<br>
          ligne 15<br>
        </div>
        """

        self.comp_html = recherche_mk_html(html_genere=html_genere)

        self.column_panel_affichage.clear()
        self.column_panel_affichage.add_component(self.comp_html)

        self.button_aller_mot.visible = True

    @handle("button_aller_mot", "click")
    def button_aller_mot_click(self, **event_args):
        if self.comp_html is not None:
            ok = self.comp_html.aller_a_occurrence("kw_hit_1")
            print("Scroll OK :", ok)