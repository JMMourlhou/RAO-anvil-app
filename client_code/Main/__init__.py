from ._anvil_designer import MainTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import m3.components as m3


class Main(MainTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
        self.text_nb_offres.text = f"{len(list_offres)} offres"
        self.repeating_panel_1.items = list_offres
        # Any code you write here will run before the form opens.

    def search_click(self, **event_args):
        """This method is called when the component is clicked."""
        #offres = anvil.server.call("get_sst_offres",self.text_box_url.text, self.text_box_mot_clef.text)   # uplink sur Pi5
        offres = anvil.server.call("get_boamp_offres", self.text_box_mot_clef.text, int(self.text_box_nb_jours.text))
        if offres:
            for offre in offres:
                result = anvil.server.call("sov_offres", offre)
                if result == "ok":
                    print(f"{offre['titre']} sauvée !")
                    list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
                    self.text_nb_offres.text = f"{len(list_offres)} offres"
                    self.repeating_panel_1.items = list_offres
                else:
                    alert(result)
        else:
            alert("Pas d'offre trouvée !")

    def button_1_click(self, **event_args):
        """This method is called when the component is clicked."""
        result = anvil.server.call("del_all")
        if not result:
            alert("Erreur en Effacement")
        else:
            open_form('Main')

    def text_box_nb_jours_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        self.search_click()

    def text_box_mot_clef_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        self.search_click()
            
