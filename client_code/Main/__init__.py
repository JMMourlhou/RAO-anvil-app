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

        # Any code you write here will run before the form opens.

    def search_click(self, **event_args):
        """This method is called when the component is clicked."""
        #offres = anvil.server.call("get_sst_offres",self.text_box_url.text, self.text_box_mot_clef.text)   # uplink sur Pi5
        offres = anvil.server.call("get_sst_offres_emarches", self.text_box_mot_clef.text)
        if offres:
            for offre in offres:
                result = anvil.server.call("sov_offres", offre)
                if result == "ok":
                    alert(f"{offre['titre']} sauvée !")
                else:
                    alert(result)
        else:
            alert("Pas d'offres")