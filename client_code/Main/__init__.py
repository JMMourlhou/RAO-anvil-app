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
        
        self.option = 0 # pour envoi en sélection(1), déselection(2), del(3)
        with anvil.server.no_loading_indicator:
            list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
            if len(list_offres)>0:
                self.repeating_panel_1.items = list_offres
                if len(list_offres)==1:
                    self.text_nb_offres.text = f"{len(list_offres)} offre"
                else:   
                    self.text_nb_offres.text = f"{len(list_offres)} offres"
                self.column_panel_select.visible = True
                #alert(f"nb d'offres: {len(list_offres)}")
            else:
                self.column_panel_select.visible = False
                #alert(f"pas d'offres: {len(list_offres)}")
        
        # Any code you write here will run before the form opens.

    def button_search_click(self, **event_args):
        """This method is called when the component is clicked."""
        #offres = anvil.server.call("get_sst_offres",self.text_box_url.text, self.text_box_mot_clef.text)   # uplink sur Pi5
        offres = anvil.server.call("get_boamp_offres", self.text_box_mot_clef.text, int(self.text_box_nb_jours.text))
        if offres:
            for offre in offres:
                result = anvil.server.call("sov_offres", offre)
                if result == "ok":
                    #print(f"{offre['titre']} sauvée !")
                    list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
                    self.text_nb_offres.text = f"{len(list_offres)} offres"
                    self.repeating_panel_1.items = list_offres
                    self.column_panel_select.visible = True
                else:
                    self.column_panel_select.visible = False
                    alert(result)
        else:
            alert("Désolé... pas d'offres trouvées !")

    def text_box_nb_jours_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        self.button_search_click()

    def text_box_mot_clef_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        self.button_search_click()

    def text_box_departement_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        self.button_search_click()

    def button_tout_deselectionner_click(self, **event_args):
        """This method is called when the component is clicked."""
        self.option = 2
        self.column_panel_select.visible = False
        self.traitement()
        
        
    def button_tout_selection_click(self, **event_args):
        """This method is called when the component is clicked."""
        self.option = 1
        self.traitement()
        
    def button_del_checked_click(self, **event_args):
        """This method is called when the component is clicked."""
        self.option = 3
        self.traitement()

    def traitement(self):
        with anvil.server.no_loading_indicator:
            if self.option == 1 or self.option == 2: # Tout sélectionner(1) ou Tout délectionner(2) 
                list = app_tables.appels_offres.search()
                result = anvil.server.call("treatment_on_all_checked", list, self.option)
                if not result:
                    alert("Erreur !")
                else:
                    open_form('Main')
                    
        if self.option == 3:  # del offres selectionnées 
            list = app_tables.appels_offres.search(vu=True)
            result = anvil.server.call("treatment_on_all_checked", list, self.option)
            if not result:
                alert("Erreur en Effacement")
            else:
                open_form('Main')

        

    def button_selection_mailed_click(self, **event_args):
        """This method is called when the component is clicked."""
        pass

    
