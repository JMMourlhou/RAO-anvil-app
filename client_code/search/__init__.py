from ._anvil_designer import searchTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import m3.components as m3
from .. import Time
from datetime import date, datetime


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
                
                rows = app_tables.histo.search(tables.order_by("date_heure", ascending=False),
                                                email=self.user['email']
                                             ) 
                if len(rows)>0:
                    row = rows[0]
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
                    """  ==============================================================================
                    Je passe au composant repeat_panel_1 la propriété contenant les mots clefs par 'tag'
                    nécessaire quand on click sur le bouton 'verifier'
                        la form mère connaît les mots-clés saisis,
                        elle les stocke sur repeating_panel_1,
                        chaque row les lit depuis self.parent.
                    """
                    self.repeating_panel_1.tag.mots_cles_saisis = self.text_box_mot_clef.text or ""
                    # ===================================================================================
                    
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
            print(offres[0])
            
        except Exception as e:
            print(f"Erreur au module 'get_offres_multi_sources' sur Pi5: {e}")
            return
            
        if offres:
            # Ecriture de chaque offre en table appels_offres                   (à enlever)
            result = anvil.server.call("sov_offres", offres)
            if result != "ok":
                self.column_panel_select.visible = False
                alert(result)
                
            # Génération du dictionaire de listes des offres
            
            offres_preparees = self.build_offres_list(offres, dedoublonner=True)
            nb_offres = len(offres_preparees)
            
            # Backup de la requête (donc des paramètres)
            date_time = Time.french_zone_time()
            result = anvil.server.call("backup_requete", self.user, selected_platformes, self.text_box_mot_clef.text, self.text_box_nb_jours.text, self.text_box_departements.text, date_time, nb_offres, offres_preparees)
            print(f"Module 'param_backup':  {result}")
                # -------------------------------------------
            
            self.list_offres = app_tables.appels_offres.search(tables.order_by("date_publication", ascending=False))
                
            if len(self.list_offres)==1:
                self.text_nb_offres.text = f"{len(self.list_offres)} offre"
            else:
                self.text_nb_offres.text = f"{len(self.list_offres)} offres"
            self.text_nb_offres.visible = True

            self.repeating_panel_1.items = self.list_offres
            self.recalculer_bouton_selection_mailed()   # méthode qui vérifie si une row est checked
            
            """  ==============================================================================
            Je passe au composant repeat_panel_1 la propriété contenant les mots clefs par 'tag'
            nécessaire quand on click sur le bouton 'verifier'
                la form mère connaît les mots-clés saisis,
                elle les stocke sur repeating_panel_1,
                chaque row les lit depuis self.parent.
            """
            self.repeating_panel_1.tag.mots_cles_saisis = self.text_box_mot_clef.text or ""
            # ===================================================================================
            
            self.data_grid_1.visible = True
            self.column_panel_select.visible = True

            self.button_search.visible = False
            self.column_panel_params.visible = False
            self.text_param_summary.text = (f"Plateformes:{self.multi_select_drop_down_platformes.selected} / Mots clefs:{self.text_box_mot_clef.text} / sur les {self.text_box_nb_jours.text} derniers jours / {self.text_box_departements.text}")
            self.text_param_summary.visible = True
            
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


    """
    =================================================================================================
    Fonctions permettant la création du dict de liste des offres pour cette requete
    =================================================================================================
    """
    
    def _to_str(self, v):
        """None -> '', sinon str nettoyée."""
        if v is None:
            return ""
        return str(v).strip()
    
    
    def _to_iso_date(self, v):
        """
        Convertit une date/datetime en 'YYYY-MM-DD'.
        Si déjà texte, le renvoie tel quel nettoyé.
        Si vide, renvoie ''.
        """
        if v in (None, "", "-"):
            return ""
        if isinstance(v, datetime):
            return v.date().isoformat()
        if isinstance(v, date):
            return v.isoformat()
        return str(v).strip()
    
    
    def _make_offer_uid(self, item):
        """
        Clé technique pour éviter les doublons éventuels.
        """
        source = self._to_str(item.get("source"))
        idweb = self._to_str(item.get("idweb"))
        lien = self._to_str(item.get("lien"))
    
        if source and idweb:
            return f"{source}|{idweb}"
        if lien:
            return lien
        return f"{source}|{self._to_str(item.get('titre'))}|{self._to_iso_date(item.get('date_publication'))}"
    
    
    def build_offres_list(self, resultats, dedoublonner=True):
        """
        resultats : liste brute renvoyée par tes scrapers / multi_sources
        build_lien_app : fonction optionnelle qui reçoit item et renvoie le lien vers ton app
        dedoublonner : True pour éviter les doublons
        """
        offres = []
        vus = set()
        
        base_app = anvil.server.call('get_variable_value','code_app1')
            
        for item in resultats or []:
            uid = self._make_offer_uid(item)
            print(item.get("acheteur"))
            if dedoublonner and uid in vus:
                continue
            vus.add(uid)

            source = self._to_str(item.get("source"))
            idweb = self._to_str(item.get("idweb"))
            lien_app = f"{base_app}/analyse_offre?source={source}&idweb={idweb}"
    
            offre = {
                "idweb": self._to_str(item.get("idweb")),
                "source": self._to_str(item.get("source")),
                "titre": self._to_str(item.get("titre")),
                "date_publication": self._to_iso_date(item.get("date_publication")),
                "date_limite_rep": self._to_iso_date(item.get("date_limite_rep")),
                "departement": self._to_str(item.get("departement")),
                "lieu": self._to_str(item.get("lieu")),
                "acheteur": self._to_str(item.get("acheteur")),
                "lien_source": self._to_str(item.get("lien")),
                "lien_app": lien_app,
                "description": self._to_str(item.get("description")),
                "search_text": self._to_str(item.get("search_text")),
                "reference": self._to_str(item.get("reference")),
                "nature": self._to_str(item.get("nature")),
                "procedure": self._to_str(item.get("procedure")),
            }
    
            offres.append(offre)
    
        return offres
    
    
    """
    =================================================================================================
    FIN des fonctions permettant la création du dict de liste des offres pour cette requete
    =================================================================================================
    """