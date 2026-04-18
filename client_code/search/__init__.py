from ._anvil_designer import searchTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import m3.components as m3
from .. import Time


class search(searchTemplate):
    def __init__(self, origine="", checkbox_on_off=False, mk="", bt_mail_visible=False, **properties):
        #def __init__(self, origine="", sources="", mots="", nb_jours="1", departements="", **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        
        self.repeating_panel_1.set_event_handler(
            "x-checkbox-vu-changee",                     # nom de l'évenement
            self.recalculer_bouton_selection_mailed      # méthode exécutéequand l'évenement est raised
        )
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
            self.multi_select_drop_down_platformes.background = "#3CD9ED"  # bleu clair
            self.multi_select_drop_down_platformes.spacing_above = "1"

            if origine == "": # ouverture ou effact complet des offres, je lis les derniers params du user pour les afficher
                # Affichage des param à partir de la lecture du user dans table histo
                try:
                    self.user=anvil.users.get_user()
                except Exception as e:
                    alert(f"Vous n'êtes pas enregistré !, {e}")
                
                row = app_tables.histo.get(email=self.user['email'])  
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
                    #app_tables.appels_offres.delete_all_rows()   # effacer les offres précédentes en table appels_offres
                else: # Pas encore d'historique pour un nouvel utilisateur
                    # Cocher toutes les platformes si 1ere entrée
                    self.multi_select_drop_down_platformes.selected = [r["id"] for r in rows_platformes]
                    self.text_box_mot_clef.text       = "Football et Ballon"
                    self.text_box_nb_jours.text       = "30"
                    self.text_box_departements.text   = None    # Tous les depts
                # =====================================
                self.button_search.visible = True
                
            if origine=="check": # il y a eu un traitement de marquage sur les offres affichées par le user
                # Réaffichage des paramètres si il y a eu un effacement de toutes les offres par le user
                self.column_panel_params.visible = False

                #self.option = 0 # pour envoi en sélection(1), déselection(2), del(3)
                
                # réaffichages des parametres, check box on_off, button mail: 
                if mk != "": # mots clefs
                    self.text_box_mot_clef.text = mk
                if checkbox_on_off is True:  # ckeck box check de toutes ou aucune offres affichées
                    self.checkbox_on_off.checked = True
                if  bt_mail_visible is True:  # Bouton envoi des mails checkés
                    self.button_selection_mailed.visible = True
                # Je réaffiche le contenu de la table "appels_offres"
                list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
                if len(list_offres)>0:
                    self.data_grid_1.visible = True
                    self.repeating_panel_1.items = list_offres
                    self.recalculer_bouton_selection_mailed()   # méthode qui vérifie si une row est checked
                   
                    if len(list_offres)==1:
                        self.text_nb_offres.text = f"{len(list_offres)} offre"
                    else:
                        self.text_nb_offres.text = f"{len(list_offres)} offres"
                    self.text_nb_offres.visible = True
                    self.column_panel_select.visible = True
                    # =====================================
                    self.button_search.visible = False
                    # =====================================
                else:
                    self.column_panel_select.visible = False

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
        """
        ================================================================================================
        Résultats 
        ================================================================================================
        """
        try:
            # Appel du script "get_offres_multi_sources" en uplink sur Pi5
            #                                                           departements,  rows,  page,  nb de jours
            # offres = anvil.server.call("get_boamp_offres", mots_clefs , depts,         100,   1,     periode)
            offres = anvil.server.call("get_offres_multi_sources", mots_clefs , depts,         100,   1,     periode, sources=selected_platformes)
        except Exception as e:
            print(f"Erreur au module 'get_offres_multi_sources' sur Pi5: {e}")
            return
            
        if offres:
            result = anvil.server.call("sov_offres", offres)
            if result != "ok":
                self.column_panel_select.visible = False
                alert(result)

            self.list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
                
            if len(self.list_offres)==1:
                self.text_nb_offres.text = f"{len(self.list_offres)} offre"
            else:
                self.text_nb_offres.text = f"{len(self.list_offres)} offres"
            self.text_nb_offres.visible = True

            self.repeating_panel_1.items = self.list_offres
            self.recalculer_bouton_selection_mailed()   # méthode qui vérifie si une row est checked
            
            self.data_grid_1.visible = True
            self.column_panel_select.visible = True

            self.button_search.visible = False
            self.column_panel_params.visible = False
            self.text_param_summary.text = (f"Plateformes:{self.multi_select_drop_down_platformes.selected} / Mots clefs:{self.text_box_mot_clef.text} / sur les {self.text_box_nb_jours.text} derniers jours / {self.text_box_departements.text}")
            self.text_param_summary.visible = True
            # -------------------------------------------
            # Backup des paramètres
            self.param_backup(selected_platformes, self.text_box_mot_clef.text, self.text_box_nb_jours.text, self.text_box_departements.text)
            # -------------------------------------------
        else:
            self.data_grid_1.visible = False
            alert("Désolé... pas d'offres trouvées !")
            with anvil.server.no_loading_indicator:
                app_tables.appels_offres.delete_all_rows()
                self.data_grid_1.visible = False
    


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
            open_form('search')

    # envoi d'un mail contenant les offres checkées
    def button_selection_mailed_click(self, **event_args):
        """This method is called when the component is clicked."""
        pass

    def param_backup(self, sources, mots_clefs, nb_jours, departements):
        # Backup de la dernière recherche
        date_time = Time.french_zone_time()
        # True: nouvelle row,  False = modif de la row histo
        result = anvil.server.call("backup_param", self.user, sources, mots_clefs, nb_jours, departements, date_time)
        
        #alert(f"Module 'param_backup': Sauvegarde des paramètres non effectuée: {result}, {e}")
        print(f"Module 'param_backup':  {result}")

    def button_del_before_modif_param(self, **event_args):
        """This method is called when the component is clicked."""
        with anvil.server.no_loading_indicator:
            app_tables.appels_offres.delete_all_rows()
        #open_form('Main', self.text_box_url.text ,self.text_box_mot_clef.text, self.text_box_nb_jours.text, self.text_box_departements.text)
        #open_form('Main', "")

    def button_retour_click(self, **event_args):
        """This method is called when the button is clicked"""
        #Retour_par_test_ecran.largeur_ecran()
        open_form('Main_large_screen')
        

    def checkbox_on_off_change(self, **event_args):
        """This method is called when the component is checked or unchecked"""
        if self.checkbox_on_off.checked is True:
            self.button_selection_mailed.visible = True
            self.option = 1
        else:
            self.button_selection_mailed.visible = False
            self.option = 2
        self.traitement()

    def traitement(self):
        #with anvil.server.no_loading_indicator:
        # self.option 1 = Tout sélectionner   /    2 = Tout déselectionner
        list = app_tables.appels_offres.search()
        result = anvil.server.call("treatment_on_all_checked", list, self.option)
        if not result:
            alert("Erreur !")
        else:
            open_form('search', "check", self.checkbox_on_off.checked, self.text_box_mot_clef.text, self.button_selection_mailed.visible)

    # ====================================================================================
    # TIMER 1 — keeps server session alive
    # ====================================================================================
    def timer_1_tick(self, **event_args):
        with anvil.server.no_loading_indicator:
            try:
                anvil.server.call("ping")  # Very light server call
            except Exception as e:
                print(e)

    # Méthode appelée:  quand un row du repeating panel a été changée (checked ou unchecked) 
    #                   quand le repeting panel est réaffiché
    def recalculer_bouton_selection_mailed(self, sender=None, **event_args):
        au_moins_un_coche = any(
            row.checkbox_vu.checked
            for row in self.repeating_panel_1.get_components()
        )
        self.button_selection_mailed.visible = au_moins_un_coche