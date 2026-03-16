from ._anvil_designer import MainTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import m3.components as m3
from .. import Time

class Main(MainTemplate):
    def __init__(self, origine="", sources="", mots="", nb_jours="1", departements="", **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        
        with anvil.server.no_loading_indicator:

            # init de la drop down plateforme multi sélectable depuis la table 'platformes'
            rows_platformes = app_tables.platformes.search(tables.order_by("id", ascending=True))
            # MultiSelectDropDown :
            # key   = texte affiché
            # value = valeur récupérée ensuite
            self.multi_select_drop_down_platformes.items = [
                {"key": r["id"], "value": r["id"]}
                for r in rows_platformes
            ]
            self.multi_select_drop_down_platformes.placeholder = "Sélectionnez au moins une plateforme"
            self.multi_select_drop_down_platformes.multiple = True
            self.multi_select_drop_down_platformes.enable_filtering = False
            self.multi_select_drop_down_platformes.enable_select_all = True
            self.multi_select_drop_down_platformes.width = "100%"
            #self.multi_select_drop_down_platformes.foreground = "#000000"  # dark
            self.multi_select_drop_down_platformes.background = "#00FF00"  # vert clair
            self.multi_select_drop_down_platformes.spacing_above = "1"
            
            if origine == "": # ouverture ou effact complet des offres, je lis les derniers params du user pour les afficher
                # Affichage des param à partir de la lecture du user dans table histo
                
                

                # pour l'instant, lecture du row 1 table histo du user
                try:
                    row = app_tables.histo.get(email="jmmourlhou@gmail.com")
                    if row:
                        #alert(f"lecture des param de {row['user_id']} !")
                        self.text_box_mot_clef.text       = row['mots_cles']
                        self.text_box_nb_jours.text       = row['nb_jours']
                        self.text_box_departements.text   = row['departements']
                        src = row['sources']
                        if src is not None:
                            self.multi_select_drop_down_platformes.selected = row['sources']
                        else:
                            # Cocher toutes les platformes si 1ere entrée
                            self.multi_select_drop_down_platformes.selected = [r["id"] for r in rows_platformes]
                        # =====================================
                        app_tables.appels_offres.delete_all_rows()   # effacer les offres précédentes en table appels_offres
                        # =====================================
                        self.button_search.visible = True
                        # =====================================
                except Exception as e:
                    alert(f"Vous n'êtes pas enregistré !, {e}")

            if origine=="check": # il y a eu un traitement de marquage sur les offres affichées par le user
                # Réaffichage des paramètres si il y a eu un effacement de toutes les offres par le user
                self.column_panel_params.visible = False
                
                
                #self.option = 0 # pour envoi en sélection(1), déselection(2), del(3)
                
                # Je réaffiche le contenu de la table "appels_offres"
                list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
                if len(list_offres)>0:
                    self.button_selection_mailed.visible = True
                    self.data_grid_offres.visible = True
                    self.repeating_panel_1.items = list_offres
                    if len(list_offres)==1:
                        self.text_nb_offres.text = f"{len(list_offres)} offre"
                    else:   
                        self.text_nb_offres.text = f"{len(list_offres)} offres"
                    self.text_nb_offres.visible = True
                    self.flow_panel_select.visible = True
                    # =====================================
                    self.button_search.visible = False
                    # =====================================
                else:
                    self.flow_panel_select.visible = False
                
                #alert(f"pas d'offres: {len(list_offres)}")
            
        # Any code you write here will run before the form opens.

    def button_search_click(self, **event_args):
        """This method is called when the component is clicked."""
        #offres = anvil.server.call("get_sst_offres",self.text_box_url.text, self.text_box_mot_clef.text)   # uplink sur Pi5
        # Effacement de la table appels offres
        app_tables.appels_offres.delete_all_rows()
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
        
        # Initialisation des platformes sources à partir de la dropdown
        selected_platformes = self.multi_select_drop_down_platformes.selected
        print(f"Sources: {selected_platformes}")

        try:
            # Appel du script "get_offres_multi_sources" en uplink sur Pi5
            #                                                           departements,  rows,  page,  nb de jours
            # offres = anvil.server.call("get_boamp_offres", mots_clefs , depts,         100,   1,     periode)
            offres = anvil.server.call("get_offres_multi_sources", mots_clefs , depts,         100,   1,     periode, sources=selected_platformes)
            if offres:
                for offre in offres:
                    print(offre)
                    result = anvil.server.call("sov_offres", offre)
                    if result != "ok":
                        self.flow_panel_select.visible = False
                        alert(result)
                    
                list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
                
                if len(list_offres)==1:
                    self.text_nb_offres.text = f"{len(list_offres)} offre"
                else:   
                    self.text_nb_offres.text = f"{len(list_offres)} offres"
                self.text_nb_offres.visible = True
                
                self.repeating_panel_1.items = list_offres
                self.data_grid_offres.visible = True
                self.flow_panel_select.visible = True
                self.button_selection_mailed.visible = True
                
                self.button_search.visible = False
                self.column_panel_params.visible = False
                
                # -------------------------------------------
                # Backup des paramètres
                self.param_backup(selected_platformes, self.text_box_mot_clef.text, self.text_box_nb_jours.text, self.text_box_departements.text)
                # -------------------------------------------
            else:
                self.data_grid_offres.visible = False
                alert("Désolé... pas d'offres trouvées !")
                with anvil.server.no_loading_indicator:
                    app_tables.appels_offres.delete_all_rows()
                    self.data_grid_offres.visible = False
        except Exception as e:
            alert(f"Erreur lors de la requête : {e}")

            
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
            #open_form('Main', self.text_box_url.text ,self.text_box_mot_clef.text, self.text_box_nb_jours.text, self.text_box_departements.text)
            open_form('Main', "")

    def traitement(self):
        #with anvil.server.no_loading_indicator:
        # self.option 1 = Tout sélectionner   /    2 = Tout déselectionner
        list = app_tables.appels_offres.search()
        result = anvil.server.call("treatment_on_all_checked", list, self.option)
        if not result:
            alert("Erreur !")
        else:
            open_form('Main', "check")
                    
                       
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
                open_form('Main', "check")

    def param_backup(self, sources, mots_clefs, nb_jours, departements):
        # Backup de la dernière recherche
        date_time = Time.french_zone_time()
        result = anvil.server.call("backup_param", sources, mots_clefs, nb_jours, departements, date_time)
        if not result:
            alert(f"Sauvegarde des paramètres non effectuée: {result}")

    
    def button_del_before_modif_param(self, **event_args):
        """This method is called when the component is clicked."""
        with anvil.server.no_loading_indicator:
            app_tables.appels_offres.delete_all_rows()
        #open_form('Main', self.text_box_url.text ,self.text_box_mot_clef.text, self.text_box_nb_jours.text, self.text_box_departements.text)
        #open_form('Main', "")
    
        
        
    



    
