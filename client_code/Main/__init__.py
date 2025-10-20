from ._anvil_designer import MainTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import m3.components as m3


class Main(MainTemplate):
    def __init__(self, mots="SST", nb_jours="10", departements="34", **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        
        self.option = 0 # pour envoi en sélection(1), déselection(2), del(3)
        with anvil.server.no_loading_indicator:
            # Réaffichage des paramètres si il y a eu un effacement de toutes les offres
            if mots != "SST":
                self.text_box_mot_clef.text=mots
            if nb_jours != "10":
                self.text_box_nb_jours.text=nb_jours
            if departements != "34":
                self.text_box_departements.text=departements
                
            list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
            if len(list_offres)>0:
                self.button_selection_mailed.visible = True
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
        # --- Lecture et nettoyage des champs texte ---
        mots_texte = self.text_box_mot_clef.text or ""
        deps_texte = self.text_box_departements.text or ""
    
        # --- Conversion en listes (séparateur = virgule) ---
        mots_clefs = [m.strip() for m in mots_texte.split(",") if m.strip()]
        depts = [d.strip() for d in deps_texte.split(",") if d.strip()]
        periode = int(self.text_box_nb_jours.text)
        print(f"Recherche sur les {periode} derniers jours")
        print("🔍 Mots-clés saisis :", mots_clefs)
        print("🗺️ Départements saisis :", depts)
        try:
            # Appel du script "get_boamp_offres" en uplink sur Pi5
            #                                                           departements,  rows,  page,  nb de jours
            offres = anvil.server.call("get_boamp_offres", mots_clefs , depts,         100,   1,     periode)
            if offres:
                for offre in offres:
                    print(offre)
                    result = anvil.server.call("sov_offres", offre)
                    if result != "ok":
                        self.column_panel_select.visible = False
                        alert(result)
                    
                list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
                self.text_nb_offres.text = f"{len(list_offres)} offres"
                self.repeating_panel_1.items = list_offres
                self.column_panel_select.visible = True
                self.button_selection_mailed.visible = True
            else:
                alert("Désolé... pas d'offres trouvées !")
        except Exception as e:
            alert(f"Erreur lors de la recherche : {e}")

            
    def text_box_nb_jours_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        self.button_search_click()

    def text_box_mot_clef_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        self.button_search_click()

    def text_box_departements_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        self.button_search_click()

    def button_tout_deselectionner_click(self, **event_args):
        """This method is called when the component is clicked."""
        self.option = 2
        self.traitement()
        
    def button_tout_selection_click(self, **event_args):
        """This method is called when the component is clicked."""
        self.option = 1
        self.traitement()

    def button_inverser_selection_click(self, **event_args):
        """This method is called when the component is clicked."""
        self.option = 4
        self.traitement()
        
    def button_del_all_click(self, **event_args):
        """This method is called when the component is clicked."""
        r=alert("Effacer toutes les offres affichées ?",dismissible=False,buttons=[("oui",True),("non",False)])
        if r :   # oui
            app_tables.appels_offres.delete_all_rows()
            open_form('Main',self.text_box_mot_clef.text, self.text_box_nb_jours.text, self.text_box_departements.text)

    def traitement(self):
        #with anvil.server.no_loading_indicator:
        # self.option 1 = Tout sélectionner   /    2 = Tout déselectionner
        list = app_tables.appels_offres.search()
        result = anvil.server.call("treatment_on_all_checked", list, self.option)
        if not result:
            alert("Erreur !")
        else:
            open_form('Main')
                    
                       
    def button_selection_mailed_click(self, **event_args):
        """This method is called when the component is clicked."""
        pass

    def button_del_checked_click(self, **event_args):
        """This method is called when the component is clicked."""
        r=alert("Effacer toutes les offres marquées ?",dismissible=False,buttons=[("oui",True),("non",False)])
        if r :   # oui
            list = app_tables.appels_offres.search(vu=True)
            self.option = 3 # On efface les offres marquées (vu=True)
            result = anvil.server.call("treatment_on_all_checked", list, self.option)
            if not result:
                alert("Erreur !")
            else:
                open_form('Main')

    



    
