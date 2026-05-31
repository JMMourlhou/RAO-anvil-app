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
import re
import anvil.js   # pour la détection d'un click sur le DropDown dropdown_menu_valeur
from anvil.js import get_dom_node    # pour écouteur JS sur le DropDown

class search(searchTemplate):

    def __init__(
        self,
        origine="",
        checkbox_on_off=False,
        mk="",
        bt_mail_visible=False,
        dict_mots_score=None,
        **properties
    ):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        
        self.f = get_open_form()
  
        #self.button_search.visible = False
        #self.f.navigation_link_search_go.visible = False

        # =====================================================================
        # Variables internes
        # =====================================================================
        
        self.user = None
        self.histo_id = None
        self.list_offres = []
        self.offres_preparees = []
        self.dict_mots_score = dict(dict_mots_score or {})    # mots type OU saisis par l'utilisateur + importance
        self.dict_score_recherche = {}                        # dictionnaire final utilisé pour scorer
        
        # Pour l'affichage de la progression de la requête
        self.label_progress_recherche.visible = False
        self.label_nb_offres_progress.visible = False
        self.timer_recherche_progress.interval = 0
        self.task_recherche = None
        self._ctx_recherche = {}
        self._recherche_en_cours = False
        
        # Evite les traitements indésirables quand on modifie la checkbox par code
        self._ignore_checkbox_on_off_change = False
        
        # Sert à savoir si text_box_mot a perdu le focus
        # parce que l'utilisateur a cliqué sur dropdown_menu_valeur
        self._dropdown_menu_valeur_clicked = False
        
        self.dropdown_menu_valeur.items = [
            ("*", 1),
            ("* *", 5),
            ("* * *", 10)
        ]
        
        # Détection du clic sur le DropDown AVANT le lost_focus du TextBox
        try:
            get_dom_node(self.dropdown_menu_valeur).addEventListener(
                "mousedown",
                self._dropdown_menu_valeur_mouse_down
            )
        except Exception as e:
            print("Impossible d'ajouter l'écouteur JS sur dropdown_menu_valeur :", e)
        # =====================================================================
        # Events du repeating panel des mots pour score
        # =====================================================================
        self.repeating_panel_mots_pour_score.set_event_handler(
            "x-del-mot",
            self.del_mot_pour_score
        )

        self.repeating_panel_mots_pour_score.set_event_handler(
            "x-modif",
            self.modif_mot_pour_score
        )

        # =====================================================================
        # Events du repeating panel des offres
        # =====================================================================
        self.repeating_panel_1.set_event_handler(
            "x-checkbox-vu-changee",
            self.modifier_offre_vu
        )

        self.repeating_panel_1.set_event_handler(
            "x-del-offre",
            self.del_offre_affichee
        )

        with anvil.server.no_loading_indicator:
            # =================================================================
            # Utilisateur connecté
            # =================================================================
            try:
                self.user = anvil.users.get_user()
            except Exception as e:
                alert(f"Vous n'êtes pas enregistré ! {e}")
                return

            if not self.user:
                alert("Vous n'êtes pas connecté.")
                return

            # =================================================================
            # Init de la drop down plateforme multi-sélectable
            # =================================================================
            rows_platformes = app_tables.platformes.search(
                tables.order_by("id", ascending=True)
            )

            self.multi_select_drop_down_platformes.items = [
                {"key": r["id"], "value": r["id"]}
                for r in rows_platformes
            ]

            self.multi_select_drop_down_platformes.placeholder = "Sélectionnez au moins une plateforme"
            self.multi_select_drop_down_platformes.multiple = True
            self.multi_select_drop_down_platformes.enable_filtering = False
            self.multi_select_drop_down_platformes.enable_select_all = True
            self.multi_select_drop_down_platformes.width = "100%"
            self.multi_select_drop_down_platformes.background = "#3CD9ED"
            self.multi_select_drop_down_platformes.spacing_above = "1"

            # =================================================================
            # Lecture de la dernière ligne histo du user
            # =================================================================
            derniere_ligne = self.charger_derniere_ligne_histo(rows_platformes)
            self.display_mots_pour_score()
            
            # =================================================================
            # Ouverture normale : on affiche seulement les derniers paramètres
            # =================================================================
            if origine == "":
                self.column_panel_params.visible = True

                self.maj_bouton_recherche_visible()
                    
            # =================================================================
            # Réaffichage après traitement éventuel
            # Aujourd'hui, on évite open_form("search", "check") autant que possible.
            # Mais on garde ce cas pour compatibilité.
            # =================================================================
            if origine == "check":
                self.column_panel_params.visible = False

                if mk != "":
                    self.text_box_mot_clef.text = mk

                self.set_checkbox_on_off_sans_event(bool(checkbox_on_off))

                if bt_mail_visible is True:
                    self.button_selection_mailed.visible = True

                if dict_mots_score:
                    self.dict_mots_score = dict(dict_mots_score)
                    self.text_box_mots_pour_score.text = self.mots_score_to_text(self.dict_mots_score)

                if derniere_ligne : 
                    self.afficher_offres(self.list_offres)
                else:
                    self.column_panel_select.visible = False

                self.f.navigation_link_search_go.visible = False
                self.button_search.visible = False
                
                 
    # =========================================================================
    # Chargement de la dernière ligne histo
    # =========================================================================

    def charger_derniere_ligne_histo(self, rows_platformes):
        """
        Charge la dernière ligne histo de l'utilisateur :
        - paramètres de recherche
        - histo_id
        - liste d'offres sauvegardée dans histo['offres']
        """

        rows = app_tables.histo.search(
            tables.order_by("date_heure", ascending=False),
            email=self.user["email"]
        )

        if len(rows) == 0:
            # Pas encore d'historique pour un nouvel utilisateur
            self.multi_select_drop_down_platformes.selected = [r["id"] for r in rows_platformes]
            self.text_box_mot_clef.text = "Football et Ballon"
            #self.text_box_mots_ou.text = ""
            self.text_box_mots_exclus.text = ""
            self.text_box_nb_jours.text = "30"
            self.text_box_departements.text = None
            self.histo_id = None
            self.list_offres = []
            return None

        row = rows[0]

        if not row:
            return None

        self.histo_id = row.get_id()

        self.text_box_mot_clef.text = row["mots_cles"]
        
        try:
            self.text_box_mots_exclus.text = row["mots_exclus"] or ""
        except Exception:
            self.text_box_mots_exclus.text = ""
            
        self.text_box_nb_jours.text = row["nb_jours"]
        self.text_box_departements.text = row["departements"]
            
        src = row["sources"]
        if src is not None:
            self.multi_select_drop_down_platformes.selected = src
        else:
            self.multi_select_drop_down_platformes.selected = [r["id"] for r in rows_platformes]

        try:
            self.dict_mots_score = self.mots_score_obj_to_dict(row["mots_score_obj"])
        except Exception:
            self.dict_mots_score = {}
        
        self.list_offres = self.normaliser_liste_offres_vu(row["offres"] or [])

        return row

    
    def verrouiller_recherche(self, message="Recherche en cours..."):
        """
        Verrouille l'interface pendant une recherche.
        Empêche un double clic ou un nouveau lancement.
        """
    
        self._recherche_en_cours = True
    
        self.button_search.enabled = False
        self.button_search.text = "Recherche en cours..."
        
        self.f.navigation_link_search_go.enabled = False
        self.f.navigation_link_search_go.text = "Recherche en cours..."
    
        self.label_progress_recherche.visible = True
        self.label_nb_offres_progress.visible = True
    
        self.label_progress_recherche.text = message
        self.label_nb_offres_progress.text = ""
    
        # Optionnel mais conseillé :
        # éviter que l'utilisateur change les paramètres pendant la recherche
        try:
            self.text_box_mot_clef.enabled = False
            self.text_box_mots_exclus.enabled = False
            self.text_box_nb_jours.enabled = False
            self.text_box_departements.enabled = False
            self.multi_select_drop_down_platformes.enabled = False
            self.button_add_mot.enabled = False
        except Exception as e:
            print("Erreur verrouillage UI :", e)
    
    
    def deverrouiller_recherche(self, cacher_bouton=False):
        """
        Déverrouille l'interface après fin, erreur ou interruption de recherche.
        """
    
        self._recherche_en_cours = False
    
        self.timer_recherche_progress.interval = 0
        self.task_recherche = None
    
        self.button_search.enabled = True
        self.button_search.text = "Rechercher"
        
        self.f.navigation_link_search_go.enabled = True
        self.f.navigation_link_search_go.text = "Rechercher"

        if cacher_bouton:
            self.f.navigation_link_search_go.visible = False
        else:
            self.f.navigation_link_search_go.visible = True
            
        try:
            self.text_box_mot_clef.enabled = True
            self.text_box_mots_exclus.enabled = True
            self.text_box_nb_jours.enabled = True
            self.text_box_departements.enabled = True
            self.multi_select_drop_down_platformes.enabled = True
            self.button_add_mot.enabled = True
        except Exception as e:
            print("Erreur déverrouillage UI :", e)


    
    # =========================================================================
    # Recherche
    # =========================================================================
    def button_search_click(self, **event_args):
        self.lancer_recherche()

    def lancer_recherche(self, **event_args):
        """Recherche les offres, applique les critères positifs/exclusions, score, puis sauvegarde dans histo['offres']."""

        if self._recherche_en_cours:
            Notification("Recherche déjà en cours...", timeout=2).show()
            return
            
        # --- Lecture des champs ---
        mots_obligatoires_texte = self.text_box_mot_clef.text or ""
        mots_exclus_texte = self.text_box_mots_exclus.text or ""
        deps_texte = self.text_box_departements.text or ""
        
        # --- Conversion en listes propres ---
        mots_obligatoires = self.extraire_liste_mots_saisie(mots_obligatoires_texte)
        
        # Les mots OU viennent de la liste avec importance
        mots_ou = self.get_mots_ou_depuis_score()
        
        mots_exclus = self.extraire_liste_mots_saisie(mots_exclus_texte)
        
        print("===== DEBUG CHAMPS BRUTS =====")
        print("text_box_mot_clef =", repr(self.text_box_mot_clef.text))
        print("mots_ou depuis dict_mots_score =", mots_ou)
        print("text_box_mots_exclus =", repr(self.text_box_mots_exclus.text))
        print("dict_mots_score utilisateur =", self.dict_mots_score)
        print("==============================")
    
        depts = [d.strip() for d in deps_texte.split(",") if d.strip()]
    
        if not mots_obligatoires and not mots_ou:
            alert(
                "Vous devez saisir au moins un mot-clé.\n\n"
                "Exemple :\n"
                "- mots obligatoires : formation\n"
                "- au moins un de ces mots : sst, pse1"
            )
            self.text_box_mot_clef.focus()
            return
    
        try:
            periode = int(self.text_box_nb_jours.text)
        except Exception:
            alert("Le nombre de jours doit être un nombre entier.")
            self.text_box_nb_jours.focus()
            return
    
        selected_platformes = self.multi_select_drop_down_platformes.selected
    
        if not selected_platformes:
            alert("Sélectionnez au moins une plateforme.")
            return
    
        # --- Construction des requêtes envoyées aux sources ---
        # Important : cette fonction doit maintenant renvoyer large.
        # Exemple : formation + sst/mac/pse1/pse2 => ['formation']
        mots_clefs = self.construire_requetes_sources(
            mots_obligatoires=mots_obligatoires,
            mots_ou=mots_ou
        )
    
        print(f"Recherche sur les {periode} derniers jours")
        print("🔍 Mots obligatoires :", mots_obligatoires)
        print("🔍 Mots OU :", mots_ou)
        print("🚫 Mots exclus :", mots_exclus)
        print("🔎 Requêtes envoyées aux sources :", mots_clefs)
        print("🗺️ Départements saisis :", depts)
        print(f"Sources: {selected_platformes}")

        # --- Construction du dictionnaire final utilisé pour le scoring ---
        dict_score = self.build_dict_mots_score()
        
        if dict_score is None:
            return
        
        self.dict_score_recherche = dict_score
        
        print("dict_mots_score utilisateur :", self.dict_mots_score)
        print("dict_score_recherche utilisé pour scoring :", self.dict_score_recherche)
    
        if dict_score is None:
            return
    
        # --- Lancement de la recherche brute en tâche de fond ---
        self._ctx_recherche = {
            "mots_obligatoires": mots_obligatoires,
            "mots_ou": mots_ou,
            "mots_exclus": mots_exclus,
            "periode": periode,
            "selected_platformes": selected_platformes,
        }
        
        self.verrouiller_recherche("Lancement de la recherche...")

        try:
            with anvil.server.no_loading_indicator:
                self.task_recherche = anvil.server.call(
                    "lancer_recherche_multi_sources_background",
                    mots_clefs,
                    depts,
                    100,
                    1,
                    periode,
                    sources=selected_platformes
                )
        
        except Exception as e:
            print(f"Erreur au lancement de la recherche background sur Pi5 : {e}")
            self.label_progress_recherche.text = "Erreur au lancement de la recherche."
            self.label_nb_offres_progress.text = ""
            self.deverrouiller_recherche(cacher_bouton=False)
            alert(f"Erreur pendant le lancement de la recherche : {e}")
            return
        
        self.label_progress_recherche.text = "0% - Recherche lancée..."
        self.label_nb_offres_progress.text = "Recherche des offres provisoires..."
        
        self.data_grid_1.visible = False
        self.column_panel_select.visible = False
        self.text_nb_offres.visible = False
        
        self.timer_recherche_progress.interval = 1
        return
    
    def traiter_offres_recuperees_apres_background(self, offres):
        """
        Suite du traitement après récupération des offres par Background Task :
        - filtre positif
        - exclusions
        - build_offres_list
        - scoring
        - sauvegarde histo
        - affichage
        """
    
        ctx = self._ctx_recherche or {}
    
        mots_obligatoires = ctx.get("mots_obligatoires", [])
        mots_ou = ctx.get("mots_ou", [])
        mots_exclus = ctx.get("mots_exclus", [])
        selected_platformes = ctx.get("selected_platformes", [])
    
        if not offres:
            self.data_grid_1.visible = False
            self.column_panel_select.visible = False
            self.text_nb_offres.visible = False
    
            self.label_progress_recherche.text = "Recherche terminée : aucune offre trouvée."
            self.label_nb_offres_progress.text = "0 offre"

            self.deverrouiller_recherche(cacher_bouton=False)
    
            alert("Désolé... pas d'offres trouvées !")
            return
    
        nb_offres_brutes = len(offres)
        print(f"Offres brutes récupérées : {nb_offres_brutes}")
    
        self.label_progress_recherche.text = "Filtrage des critères positifs..."
        self.label_nb_offres_progress.text = f"{nb_offres_brutes} offre(s) brutes récupérée(s)"
    
        # =====================================================
        # 1. Filtrage positif local
        # =====================================================
        offres = self.filtrer_offres_criteres_positifs(
            offres,
            mots_obligatoires,
            mots_ou
        )
    
        nb_apres_filtre_positif = len(offres)
        print(f"Offres après filtre positif : {nb_apres_filtre_positif}")
    
        if not offres:
            self.data_grid_1.visible = False
            self.column_panel_select.visible = False
            self.text_nb_offres.visible = False
    
            self.label_progress_recherche.text = "Aucune offre après filtrage positif."
            self.label_nb_offres_progress.text = "0 offre conservée"

            self.deverrouiller_recherche(cacher_bouton=False)
    
            alert(
                "Des offres ont été récupérées, mais aucune ne respecte les critères :\n\n"
                f"Obligatoires : {', '.join(mots_obligatoires) or '-'}\n"
                f"Au moins un : {', '.join(mots_ou) or '-'}"
            )
            return
    
        # =====================================================
        # 2. Filtrage local des mots exclus
        # =====================================================
        self.label_progress_recherche.text = "Application des mots exclus..."
    
        offres = self.filtrer_offres_exclues(offres, mots_exclus)
    
        nb_apres_exclusion = len(offres)
        nb_exclues = nb_apres_filtre_positif - nb_apres_exclusion
    
        print(f"Offres exclues : {nb_exclues}")
        print(f"Offres conservées : {nb_apres_exclusion}")
    
        if not offres:
            self.data_grid_1.visible = False
            self.column_panel_select.visible = False
            self.text_nb_offres.visible = False
    
            self.label_progress_recherche.text = "Aucune offre après exclusion."
            self.label_nb_offres_progress.text = "0 offre conservée"

            self.deverrouiller_recherche(cacher_bouton=False)
            alert("Des offres correspondaient aux critères, mais elles contenaient toutes au moins un mot exclu.")
            return
    
        # --- Génération de la liste des offres ---
        self.label_progress_recherche.text = "Préparation des offres..."
    
        self.offres_preparees = self.build_offres_list(offres, dedoublonner=True)
    
        print(
            "offres_preparees avant score:",
            type(self.offres_preparees),
            len(self.offres_preparees)
        )
    
        # --- Calcul du score / pertinence côté serveur ---
        self.label_progress_recherche.text = "Calcul du score des offres..."
        self.label_nb_offres_progress.text = f"{len(self.offres_preparees)} offre(s) à scorer"
    
        try:
            with anvil.server.no_loading_indicator:
                offres_scorees = anvil.server.call(
                    "scorer_offres",
                    self.offres_preparees,
                    self.dict_score_recherche or {}
                )
    
        except Exception as e:
            print(f"Erreur au module serveur 'scorer_offres': {e}")
            alert(f"Erreur pendant le calcul du score : {e}")
            offres_scorees = self.offres_preparees
    
        if offres_scorees is None:
            print("Attention : scorer_offres a renvoyé None")
            offres_scorees = self.offres_preparees
    
        # --- Ajout sécurité de la clé vu=False dans chaque offre ---
        offres_scorees = self.normaliser_liste_offres_vu(offres_scorees)
    
        print("===== DEBUG SCORES =====")
        for o in offres_scorees:
            print(
                "titre:", o.get("titre"),
                "| score:", o.get("score"),
                "| type:", type(o.get("score"))
            )
        print("========================")
    
        nb_offres = len(offres_scorees)
    
        # --- Backup de la requête avec les offres scorées ---
        self.label_progress_recherche.text = "Sauvegarde de la recherche..."
        self.label_nb_offres_progress.text = f"{nb_offres} offre(s) à sauvegarder"
    
        date_time = Time.french_zone_time()
    
        try:
            with anvil.server.no_loading_indicator:
                result = anvil.server.call(
                    "backup_requete",
                    self.user,
                    selected_platformes,
                    self.get_mots_obligatoires_texte(),
                    self.text_box_nb_jours.text,
                    self.text_box_departements.text,
                    date_time,
                    nb_offres,
                    offres_scorees,
                    self.dict_mots_score,
                    True,
                    self.get_mots_ou_texte(),
                    self.get_mots_exclus_texte()
                )
    
        except Exception as e:
            self.deverrouiller_recherche(cacher_bouton=False)
            alert(f"Erreur pendant la sauvegarde dans histo : {e}")
            return
    
        if not result or not result.get("ok"):
            message = result.get("message") if result else "Erreur inconnue"
            self.deverrouiller_recherche(cacher_bouton=False)
            alert(
                f"La recherche a fonctionné, mais la sauvegarde dans histo a échoué.\n\n{message}"
            )
            return
    
        self.histo_id = result.get("histo_id")
    
        if not self.histo_id:
            self.deverrouiller_recherche(cacher_bouton=False)
            alert("Sauvegarde histo effectuée, mais histo_id manquant.")
            return
    
        print(f"Ligne histo sauvegardée : {self.histo_id}")
        print(f"Nombre d'offres sauvegardées dans histo : {result.get('nb_offres')}")
    
        self.list_offres = offres_scorees
    
        self.afficher_offres(self.list_offres)
    
        self.button_search.visible = False
        self.f.navigation_link_search_go.enabled = False
        
        self.column_panel_params.visible = False
    
        self.text_param_summary.text = (
            f"Plateformes : {self.multi_select_drop_down_platformes.selected} / "
            f"Obligatoires : {self.get_mots_obligatoires_texte() or '-'} / "
            f"Au moins un : {mots_ou or '-'} / "
            f"Exclus : {self.get_mots_exclus_texte() or '-'} / "
            f"sur les {self.text_box_nb_jours.text} derniers jours / "
            f"Départements : {self.text_box_departements.text or '-'}"
        )
    
        self.text_param_summary.visible = True
    
        self.label_progress_recherche.text = "Recherche terminée."

        if nb_offres > 1:
            self.label_nb_offres_progress.text = f"{nb_offres} offres retenues après filtrage final"
        else:
            self.label_nb_offres_progress.text = f"{nb_offres} offre retenue après filtrage final"
        
        # Succès, cacher le bouton
        self.deverrouiller_recherche(cacher_bouton=True)

    # =========================================================================
    # Champs Enter
    # =========================================================================

    def text_box_nb_jours_pressed_enter(self, **event_args):
        self.lancer_recherche()

    def text_box_mot_clef_pressed_enter(self, **event_args):
        self.lancer_recherche()

    def text_box_departements_pressed_enter(self, **event_args):
        self.lancer_recherche()

    # =========================================================================
    # Sélection / désélection / inversion
    # =========================================================================

    def checkbox_on_off_change(self, **event_args):
        """
        Coche ou décoche toutes les offres.
        Maintenant, on travaille sur self.list_offres puis histo['offres'].
        """

        if self._ignore_checkbox_on_off_change:
            return

        checked = bool(self.checkbox_on_off.checked)
        self.traitement_tout_vu(checked)

    def button_tout_deselectionner_click(self, **event_args):
        """Tout désélectionner."""
        self.set_checkbox_on_off_sans_event(False)
        self.traitement_tout_vu(False)

    def button_inverser_selection_click(self, **event_args):
        """Inverse la sélection de toutes les offres affichées."""

        if not self.list_offres:
            return

        nouvelles_offres = []

        for offre in self.list_offres:
            nouvelle_offre = dict(offre)
            nouvelle_offre["vu"] = not bool(nouvelle_offre.get("vu", False))
            nouvelles_offres.append(nouvelle_offre)

        self.list_offres = nouvelles_offres

        if not self.sauver_offres_dans_histo():
            return

        self.afficher_offres(self.list_offres)

        # Si toutes les offres sont cochées après inversion, on coche aussi checkbox_on_off
        toutes_cochees = all(bool(o.get("vu", False)) for o in self.list_offres)
        self.set_checkbox_on_off_sans_event(toutes_cochees)

    def traitement_tout_vu(self, checked):
        """
        Met toutes les offres affichées à vu=True ou vu=False.
        """

        if not self.list_offres:
            self.button_selection_mailed.visible = False
            return

        nouvelles_offres = []

        for offre in self.list_offres:
            nouvelle_offre = dict(offre)
            nouvelle_offre["vu"] = bool(checked)
            nouvelles_offres.append(nouvelle_offre)

        self.list_offres = nouvelles_offres

        if not self.sauver_offres_dans_histo():
            return

        self.afficher_offres(self.list_offres)

        self.button_selection_mailed.visible = bool(checked) and len(self.list_offres) > 0

    def modifier_offre_vu(self, sender=None, checked=False, item=None, **event_args):
        """
        Appelé par une RowTemplate quand la checkbox d'une offre change.
        Met à jour l'offre correspondante dans self.list_offres puis sauvegarde histo['offres'].
        """

        if not item:
            return

        uid = self._make_offer_uid(item)
        nouvelles_offres = []
        trouve = False

        for offre in self.list_offres:
            nouvelle_offre = dict(offre)

            if self._make_offer_uid(nouvelle_offre) == uid:
                nouvelle_offre["vu"] = bool(checked)
                trouve = True

            nouvelles_offres.append(nouvelle_offre)

        if not trouve:
            print("Offre non trouvée dans self.list_offres")
            return

        self.list_offres = nouvelles_offres

        if not self.sauver_offres_dans_histo():
            return

        self.recalculer_bouton_selection_mailed()

        toutes_cochees = (
            len(self.list_offres) > 0
            and all(bool(o.get("vu", False)) for o in self.list_offres)
        )

        self.set_checkbox_on_off_sans_event(toutes_cochees)

    # =========================================================================
    # Effacement
    # =========================================================================

    def button_del_all_click(self, **event_args):
        """Efface toutes les offres affichées et met histo['offres'] à []."""

        r = alert(
            "Effacer toutes les offres affichées ?",
            dismissible=False,
            buttons=[("oui", True), ("non", False)]
        )

        if not r:
            return

        self.list_offres = []

        if self.histo_id:
            self.sauver_offres_dans_histo()

        self.afficher_offres(self.list_offres)
        self.set_checkbox_on_off_sans_event(False)
        self.column_panel_add_mot_pour_score.visible = False
        
        self.button_search.visible = True
        self.f.navigation_link_search_go.visible = True

    def button_del_before_modif_param(self, **event_args):
        """
        Anciennement : effacement de app_tables.appels_offres.
        Maintenant : on vide seulement l'affichage courant.
        """

        self.list_offres = []

        if self.histo_id:
            self.sauver_offres_dans_histo()

        self.afficher_offres(self.list_offres)
        self.set_checkbox_on_off_sans_event(False)

    def del_offre_affichee(self, sender=None, item=None, **event_args):
        """
        Efface une offre affichée dans le repeating panel.
        Comme les items sont des dictionnaires, on supprime l'entrée de self.list_offres,
        puis on sauvegarde histo['offres'].
        """

        if not item:
            alert("Offre introuvable.")
            return

        r = alert(
            "Effacer cette offre affichée ?",
            dismissible=False,
            buttons=[("oui", True), ("non", False)]
        )

        if not r:
            return

        uid_a_supprimer = self._make_offer_uid(item)

        ancienne_liste = self.list_offres or []

        self.list_offres = [
            offre for offre in ancienne_liste
            if self._make_offer_uid(offre) != uid_a_supprimer
        ]

        if not self.sauver_offres_dans_histo():
            return

        self.afficher_offres(self.list_offres)

        toutes_cochees = (
            len(self.list_offres) > 0
            and all(bool(o.get("vu", False)) for o in self.list_offres)
        )

        self.set_checkbox_on_off_sans_event(toutes_cochees)

    # =========================================================================
    # Sauvegarde histo['offres'] + affichage
    # =========================================================================

    def sauver_offres_dans_histo(self):
        """
        Sauvegarde self.list_offres dans histo['offres'].
        La fonction serveur update_histo_offres est obligatoire.
        """

        if not self.histo_id:
            alert("Impossible de sauvegarder : histo_id manquant.")
            return False

        try:
            with anvil.server.no_loading_indicator:
                result = anvil.server.call(
                    "update_histo_offres",
                    self.histo_id,
                    self.list_offres
                )
        except Exception as e:
            alert(f"Erreur pendant la sauvegarde des offres : {e}")
            return False

        if not result or not result.get("ok"):
            message = result.get("message") if result else "Erreur inconnue"
            alert(f"Erreur pendant la sauvegarde : {message}")
            return False

        self.list_offres = result.get("offres", self.list_offres)
        return True

    def afficher_offres(self, offres=None):
        """
        Réaffiche le repeating panel à partir de self.list_offres.
        """
    
        if offres is not None:
            self.list_offres = self.normaliser_liste_offres_vu(offres)
    
        nb = len(self.list_offres)
    
        # Important : remettre le tag après chaque réaffichage
        self.repeating_panel_1.tag.mots_cles_saisis = self.get_texte_mots_positifs_pour_highlight()
    
        # Important aussi : transmettre les mots de scoring aux rows
        self.repeating_panel_1.tag.dict_mots_score = self.dict_mots_score or {}
    
        self.repeating_panel_1.items = list(self.list_offres)
    
        if nb == 0:
            self.text_nb_offres.text = "0 offre"
            self.text_nb_offres.visible = False
            self.data_grid_1.visible = False
            self.column_panel_select.visible = False
            self.button_selection_mailed.visible = False
            self.column_panel_params.visible = True
            return
    
        if nb == 1:
            self.text_nb_offres.text = "1 offre"
        else:
            self.text_nb_offres.text = f"{nb} offres"
    
        self.text_nb_offres.visible = True
        self.data_grid_1.visible = True
        self.column_panel_select.visible = True
    
        self.recalculer_bouton_selection_mailed()

    def normaliser_liste_offres_vu(self, offres):
        """
        Garantit que chaque offre possède une clé 'vu'.
        """

        nouvelles_offres = []

        for offre in offres or []:
            nouvelle_offre = dict(offre)
            nouvelle_offre["vu"] = bool(nouvelle_offre.get("vu", False))
            nouvelles_offres.append(nouvelle_offre)

        return nouvelles_offres

    def set_checkbox_on_off_sans_event(self, valeur):
        """
        Modifie checkbox_on_off.checked sans déclencher le traitement global.
        """

        self._ignore_checkbox_on_off_change = True
        self.checkbox_on_off.checked = bool(valeur)
        self._ignore_checkbox_on_off_change = False

    # =========================================================================
    # Envoi mail
    # =========================================================================

    def button_selection_mailed_click(self, **event_args):
        """Envoi d'un mail contenant les offres cochées."""
        pass


    # =========================================================================
    # Timer
    # =========================================================================

    def timer_ping_tick(self, **event_args):
        with anvil.server.no_loading_indicator:
            try:
                anvil.server.call("ping")
            except Exception as e:
                print(e)

    # =========================================================================
    # Recalcule visibilité du bouton mail
    # =========================================================================

    def recalculer_bouton_selection_mailed(self, sender=None, **event_args):
        au_moins_un_coche = any(
            bool(row.checkbox_vu.checked)
            for row in self.repeating_panel_1.get_components()
        )

        self.button_selection_mailed.visible = au_moins_un_coche

    # =========================================================================
    # Fonctions permettant la création de la liste des offres
    # =========================================================================

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

    def extraire_liste_mots_saisie(self, texte):
        """
        Transforme une saisie utilisateur en liste propre.
    
        Accepte :
        - virgules
        - points-virgules
        - retours ligne
        - et / ou / and / or
    
        Exemple :
        'sst, pse1 ou pse2' devient ['sst', 'pse1', 'pse2']
        """
    
        texte = (texte or "").strip().lower()
    
        if not texte:
            return []
    
        texte = texte.replace("\n", ",")
        texte = texte.replace(";", ",")
        texte = texte.replace("|", ",")
    
        # Compatibilité avec anciennes saisies du type "formation et sst"
        texte = re.sub(r"\s+(et|ou|and|or)\s+", ",", texte, flags=re.IGNORECASE)
    
        morceaux = []
    
        for morceau in texte.split(","):
            mot = morceau.strip()
            mot = mot.strip("()[]{}")
            mot = mot.strip('"')
            mot = mot.strip("'")
            mot = mot.strip()
    
            if mot:
                morceaux.append(mot)
    
        # Suppression des doublons en gardant l'ordre
        resultat = []
        deja_vus = set()
    
        for mot in morceaux:
            if mot not in deja_vus:
                deja_vus.add(mot)
                resultat.append(mot)
    
        return resultat
    
    
    def construire_requetes_sources(self, mots_obligatoires, mots_ou):
        """
        Construit une requête large pour les sources.
    
        Important :
        On évite d'envoyer plusieurs requêtes du type :
        ['formation et sst', 'formation et mac']
    
        On récupère large, puis on filtre localement.
        """
    
        mots_obligatoires = mots_obligatoires or []
        mots_ou = mots_ou or []
    
        # Cas normal : on envoie les mots obligatoires seulement
        if mots_obligatoires:
            return [" et ".join(mots_obligatoires)]
    
        # Si aucun mot obligatoire, on envoie une requête OU large
        if mots_ou:
            return [" ou ".join(mots_ou)]
    
        return []
    
    
    def get_texte_mots_positifs_pour_highlight(self):
        """
        Renvoie les mots à surligner dans les résultats.
    
        On surligne :
        - les mots obligatoires
        - les mots OU issus de dict_mots_score
    
        On ne surligne pas les mots exclus.
        """
    
        mots = []
    
        mots.extend(
            self.extraire_liste_mots_saisie(self.text_box_mot_clef.text or "")
        )
    
        mots.extend(
            self.get_mots_ou_depuis_score()
        )
    
        resultat = []
        deja_vus = set()
    
        for mot in mots:
            mot = str(mot or "").strip().lower()
    
            if mot and mot not in deja_vus:
                deja_vus.add(mot)
                resultat.append(mot)
    
        return ", ".join(resultat)

    def normaliser_texte_filtre(self, texte):
        """
        Normalise un texte côté client Anvil :
        - minuscules
        - suppression simple des accents
        - espaces multiples
        """
    
        texte = str(texte or "").lower()
    
        remplacements = {
            "à": "a", "â": "a", "ä": "a", "á": "a", "ã": "a", "å": "a",
            "ç": "c",
            "é": "e", "è": "e", "ê": "e", "ë": "e",
            "î": "i", "ï": "i", "í": "i", "ì": "i",
            "ô": "o", "ö": "o", "ó": "o", "ò": "o", "õ": "o",
            "ù": "u", "û": "u", "ü": "u", "ú": "u",
            "ÿ": "y",
            "ñ": "n",
            "œ": "oe",
            "æ": "ae",
        }
    
        for accent, simple in remplacements.items():
            texte = texte.replace(accent, simple)
    
        texte = re.sub(r"\s+", " ", texte)
    
        return texte.strip()

    def texte_offre_normalise(self, offre):
        """
        Construit un texte complet normalisé pour filtrer localement une offre.
        """
    
        texte_offre = " ".join([
            str(offre.get("titre", "") or ""),
            str(offre.get("description", "") or ""),
            str(offre.get("search_text", "") or ""),
            str(offre.get("acheteur", "") or ""),
            str(offre.get("lieu", "") or ""),
            str(offre.get("nature", "") or ""),
            str(offre.get("procedure", "") or "")
        ])
    
        return self.normaliser_texte_filtre(texte_offre)
    
    
    def texte_contient_mot_filtre(self, texte_norm, mot):
        """
        Vérifie si un texte normalisé contient un mot.
        Pour les mots longs, recherche partielle :
        renovation trouve rénovations.
        """
    
        mot_norm = self.normaliser_texte_filtre(mot)
    
        if not mot_norm:
            return False
    
        if len(mot_norm) <= 3:
            pattern = r"(?<![a-z0-9])" + re.escape(mot_norm) + r"(?![a-z0-9])"
            return re.search(pattern, texte_norm) is not None
    
        return mot_norm in texte_norm
    
    
    def offre_respecte_criteres_positifs(self, offre, mots_obligatoires, mots_ou):
        """
        Vérifie :
        - tous les mots obligatoires doivent être présents
        - si mots_ou existe, au moins un doit être présent
        """
    
        texte_norm = self.texte_offre_normalise(offre)
    
        # Tous les mots obligatoires doivent être présents
        for mot in mots_obligatoires or []:
            if not self.texte_contient_mot_filtre(texte_norm, mot):
                return False
    
        # Au moins un mot OU doit être présent
        if mots_ou:
            trouve_un_mot_ou = False
    
            for mot in mots_ou:
                if self.texte_contient_mot_filtre(texte_norm, mot):
                    trouve_un_mot_ou = True
                    break
    
            if not trouve_un_mot_ou:
                return False
    
        return True
    
    
    def filtrer_offres_criteres_positifs(self, offres, mots_obligatoires, mots_ou):
        """
        Garde seulement les offres qui respectent :
        mots obligatoires ET au moins un mot OU.
        """
    
        if not offres:
            return []
    
        offres_filtrees = []
    
        for offre in offres:
            if self.offre_respecte_criteres_positifs(offre, mots_obligatoires, mots_ou):
                offres_filtrees.append(offre)
    
        return offres_filtrees
    
    def offre_contient_mot_exclu(self, offre, mot_exclu):
        """
        Vérifie si une offre contient un mot exclu.
    
        Pour les mots courts, on évite les faux positifs avec des limites de mot.
        Pour les mots longs, on accepte une recherche partielle :
        - construction trouve constructions
        - renovation trouve renovations
        """
    
        if not offre or not mot_exclu:
            return False
    
        texte_offre = " ".join([
            str(offre.get("titre", "") or ""),
            str(offre.get("description", "") or ""),
            str(offre.get("search_text", "") or ""),
            str(offre.get("acheteur", "") or ""),
            str(offre.get("lieu", "") or ""),
            str(offre.get("nature", "") or ""),
            str(offre.get("procedure", "") or "")
        ])
    
        texte_norm = self.normaliser_texte_filtre(texte_offre)
        mot_norm = self.normaliser_texte_filtre(mot_exclu)
    
        if not mot_norm:
            return False
    
        # Mot court : recherche stricte
        if len(mot_norm) <= 3:
            pattern = r"(?<![a-z0-9])" + re.escape(mot_norm) + r"(?![a-z0-9])"
            return re.search(pattern, texte_norm) is not None
    
        # Mot long : recherche partielle volontaire
        return mot_norm in texte_norm
    
    
    def filtrer_offres_exclues(self, offres, mots_exclus):
        """
        Supprime les offres contenant au moins un mot exclu.
        """
    
        if not offres:
            return []
    
        if not mots_exclus:
            return list(offres)
    
        offres_filtrees = []
    
        for offre in offres:
            exclure = False
    
            for mot_exclu in mots_exclus:
                if self.offre_contient_mot_exclu(offre, mot_exclu):
                    exclure = True
                    print(
                        "Offre exclue :",
                        offre.get("titre", ""),
                        "| mot exclu :",
                        mot_exclu
                    )
                    break
    
            if not exclure:
                offres_filtrees.append(offre)
    
        return offres_filtrees
        
    def _make_offer_uid(self, item):
        """
        Clé technique pour identifier une offre affichée et éviter les doublons.
        Fonctionne avec les dictionnaires issus de self.list_offres.
        """

        if not item:
            return ""

        source = self._to_str(item.get("source"))
        idweb = self._to_str(item.get("idweb"))

        lien = (
            self._to_str(item.get("lien"))
            or self._to_str(item.get("lien_source"))
            or self._to_str(item.get("lien_app"))
        )

        if source and idweb:
            return f"{source}|{idweb}"

        if lien:
            return lien

        return (
            f"{source}|"
            f"{self._to_str(item.get('titre'))}|"
            f"{self._to_iso_date(item.get('date_publication'))}"
        )

    def build_offres_list(self, resultats, dedoublonner=True):
        """
        resultats : liste brute renvoyée par tes scrapers / multi_sources.
        dedoublonner : True pour éviter les doublons.
        """

        offres = []
        vus = set()

        base_app = anvil.server.call("get_variable_value", "code_app1")

        for item in resultats or []:
            uid = self._make_offer_uid(item)

            try:
                print(item.get("acheteur"))
            except Exception:
                pass

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
                "pertinence": self._to_str(item.get("pertinence")),
                "resume_court": self._to_str(item.get("resume_court")),
                "score": self._to_str(item.get("score")),

                # Nouvelle clé indispensable
                "vu": False,
            }

            offres.append(offre)

        return offres

    # =========================================================================
    # Gestion du dictionnaire des mots pour scoring
    # =========================================================================
    @anvil.js.report_exceptions   # Détection du clicksur dropdown (initialisé ds l'init)
    def _dropdown_menu_valeur_mouse_down(self, event):
        """
        Se déclenche dès que l'utilisateur appuie sur le DropDown.
        Important : mousedown arrive avant le lost_focus du TextBox.
        """
        self._dropdown_menu_valeur_clicked = True


    def text_box_mot_lost_focus(self, **event_args):
        """This method is called when the component loses focus."""
        """
        Quand text_box_mot perd le focus, on vérifie si c'est parce que
        l'utilisateur vient de cliquer sur dropdown_menu_valeur.
        """
    
        if self._dropdown_menu_valeur_clicked:
            # ici, le TextBox a perdu le focus parce qu'on a cliqué sur le DropDown dropdown_menu_valeur
            self._dropdown_menu_valeur_clicked = False
    
            # Exemple : on ne cache pas la zone d'ajout, on ne valide pas encore.
            return
    
        # Ici, le TextBox a perdu le focus pour une autre raison.
        # Tu peux mettre ton traitement normal ici si besoin.
        self._dropdown_menu_valeur_clicked = False
        self.icon_button_del_click()

    def dropdown_menu_valeur_change(self, **event_args):
        valeur = self.dropdown_menu_valeur.selected_value or 0
        if valeur != 0:
            cle = (self.text_box_mot.text or "").strip().lower()
            #valeur = self.dropdown_menu_valeur.selected_value or 0
    
            if cle == "":
                alert("Entrez le mot à rechercher.")
                self.text_box_mot.focus()
                return
    
            if valeur == 0:
                alert("Sélectionnez l'importance du mot.")
                return
    
            try:
                valeur = int(valeur)
            except Exception:
                alert("La valeur doit être *")
                return
    
            if valeur not in [1, 5, 10]:
                alert("Valeurs autorisées : 1, 2 ou 3 étoiles.")
                return
    
            # Ajout ou remplacement du mot
            self.dict_mots_score[cle] = valeur
    
            self.display_mots_pour_score()
    
            print("dict_mots_score utilisateur :", self.dict_mots_score)
    
            self.text_box_mot.text = ""
            self.dropdown_menu_valeur.selected_value = None
            self.data_grid_mots_pour_score.visible = True
            
    def icon_button_del_click(self, **event_args):
        self.text_box_mot.text = ""
        self.dropdown_menu_valeur.selected_value = None
        self.column_panel_add_mot_pour_score.visible = False
        self.button_add_mot.visible = True
        self.data_grid_mots_pour_score.visible = True

    def button_add_mot_click(self, **event_args):
        self.maj_cadre_mots_ou_bleu()
        self.column_panel_add_mot_pour_score.visible = True
        self.button_add_mot.visible = False
        self.text_box_mot.focus()


    def del_mot_pour_score(self, sender, mot=None, **event_args):
        mot = str(mot or "").strip().lower()
        if mot in self.dict_mots_score:
            del self.dict_mots_score[mot]
  
        self.display_mots_pour_score()

    def modif_mot_pour_score(self, sender, item=None, cle=None, valeur=None, **event_args):
        # Ancienne clé à supprimer
        if item and item[0]:
            ancienne_cle = str(item[0]).strip().lower()
    
            if ancienne_cle in self.dict_mots_score:
                del self.dict_mots_score[ancienne_cle]
    
        cle = str(cle or "").strip().lower()
    
        if not cle:
            alert("Le mot ne peut pas être vide.")
            return
    
        try:
            valeur = int(valeur)
        except Exception:
            alert("La valeur doit être un nombre entier.")
            return
    
        if valeur not in [1, 5, 10]:
            alert("Valeurs autorisées : 1, 5 ou 10.")
            return
    
        self.dict_mots_score[cle] = valeur
    
        #n = Notification("Modification effectuée", timeout=1.5)
        #n.show()
    
        self.display_mots_pour_score()

    def display_mots_pour_score(self, **event_args):
        """
        Affiche les mots OU + importance dans le repeating panel.
        """
    
        list_keys = sorted(self.dict_mots_score.keys())
    
        list_display = []
    
        for mk in list_keys:
            list_display.append((mk, self.dict_mots_score[mk]))
    
        print("Nb mots OU avec importance :", len(list_display))
    
        self.repeating_panel_mots_pour_score.items = list(list_display)
    
        self.data_grid_mots_pour_score.visible = True
        self.column_panel_add_mot_pour_score.visible = False
        self.button_add_mot.visible = True
        
        self.maj_bouton_recherche_visible()

    def get_mots_ou_depuis_score(self):
        """
        Les mots OU viennent maintenant de self.dict_mots_score.
    
        Exemple :
        self.dict_mots_score = {"sst": 10, "mac": 10, "pse1": 5}
    
        Retour :
        ["sst", "mac", "pse1"]
        """
    
        mots = []
    
        try:
            items = self.dict_mots_score.items()
        except Exception:
            return mots
    
        deja_vus = set()
    
        for mot, valeur in items:
            mot = str(mot or "").strip().lower()
    
            if not mot:
                continue
    
            if mot not in deja_vus:
                deja_vus.add(mot)
                mots.append(mot)
    
        return mots


    def get_mots_ou_texte(self):
        """
        Retourne les mots OU sous forme texte pour :
        - affichage résumé
        - sauvegarde histo['mots_ou']
        """
    
        return ", ".join(self.get_mots_ou_depuis_score())

    def get_mots_obligatoires_texte(self):
        """
        Retourne les mots obligatoires nettoyés pour sauvegarde/affichage.
        """
        return ", ".join(
            self.extraire_liste_mots_saisie(self.text_box_mot_clef.text or "")
        )


    def get_mots_exclus_texte(self):
        """
        Retourne les mots exclus nettoyés pour sauvegarde/affichage.
        """
        return ", ".join(
            self.extraire_liste_mots_saisie(self.text_box_mots_exclus.text or "")
        )
        
    def build_dict_mots_score(self):
        """
        Construit le dictionnaire final utilisé pour le scoring.
    
        Source principale :
        - self.dict_mots_score : mots OU + importance choisis par l'utilisateur
    
        Ajout automatique :
        - les mots obligatoires sont ajoutés avec une valeur 1
        sans apparaître dans la liste des mots OU.
        """
    
        dict_temp = {}
    
        # =====================================================
        # 1. Mots OU + importance
        # =====================================================
    
        try:
            items = self.dict_mots_score.items()
        except Exception:
            items = []
    
        for mot, valeur in items:
            mot = str(mot or "").strip().lower()
    
            if not mot:
                continue
    
            try:
                valeur = int(valeur)
            except Exception:
                alert(f"Valeur incorrecte pour : {mot}")
                return None
    
            if valeur not in [1, 5, 10]:
                alert(
                    f"Valeur non autorisée pour : {mot}\n\n"
                    "Valeurs autorisées : 1, 5 ou 10."
                )
                return None
    
            dict_temp[mot] = valeur
    
        # =====================================================
        # 2. Ajout automatique des mots obligatoires au score
        # =====================================================
        # Ils ne servent pas à faire le OU.
        # Ils ajoutent seulement un petit score de base.
    
        mots_obligatoires = self.extraire_liste_mots_saisie(
            self.text_box_mot_clef.text or ""
        )
    
        for mot in mots_obligatoires:
            mot = str(mot or "").strip().lower()
    
            if mot and mot not in dict_temp:
                dict_temp[mot] = 1
    
        return dict_temp

    def extraire_mots_cles_pour_score(self):
        """
        Extrait les mots-clés positifs pour le scoring.
    
        On prend :
        - les mots obligatoires
        - les mots OU
    
        On ne prend pas les mots exclus.
        """
    
        mots = []
    
        mots.extend(
            self.extraire_liste_mots_saisie(self.text_box_mot_clef.text or "")
        )
    
        mots.extend(
            self.extraire_liste_mots_saisie(self.text_box_mots_ou.text or "")
        )
    
        mots_uniques = []
        deja_vus = set()
    
        for mot in mots:
            mot = mot.strip().lower()
    
            if mot and mot not in deja_vus:
                deja_vus.add(mot)
                mots_uniques.append(mot)
    
        return mots_uniques


    def text_box_mot_clef_change(self, **event_args):
        """This method is called when the text in this component is edited."""
        self.maj_bouton_recherche_visible()
        self.maj_cadre_mots_ou_blanc()

   
    def text_box_mots_pour_score_focus(self, **event_args):
        """This method is called when the component gets focus."""
        return

    def mots_score_to_text(self, mots_score):
        """
        Transforme le dictionnaire histo['mots_score'] en texte affichable.
    
        Exemple :
        {
        "{'sst'": 1,
        "'stage'": 5,
        "'travail'": 10,
        "'formation'": 1
        }
    
        devient :
        sst:1, stage:5, travail:10, formation:1
        """
    
        if not mots_score:
            return ""
    
        morceaux = []
    
        try:
            items = mots_score.items()
        except Exception:
            return ""
    
        for mot, valeur in items:
            mot = str(mot).strip()
    
            # Nettoyage des caractères parasites
            mot = mot.replace("{", "")
            mot = mot.replace("}", "")
            mot = mot.replace('"', "")
            mot = mot.replace("'", "")
            mot = mot.strip()
    
            if not mot:
                continue
    
            try:
                valeur = int(valeur)
            except Exception:
                valeur = str(valeur).strip()
    
            morceaux.append(f"{mot}:{valeur}")
    
        return ", ".join(morceaux)

    def mots_score_obj_to_dict(self, mots_score_obj):
        """
        Accepte :
        - ancien format dict : {"sst": 1, "formation": 10}
        - nouveau format liste : [{"mot": "sst", "valeur": 1}]
        """
    
        resultat = {}
    
        if not mots_score_obj:
            return resultat
    
        # Ancien format : dict direct
        if isinstance(mots_score_obj, dict):
            for mot, valeur in mots_score_obj.items():
                mot = str(mot).strip()
    
                mot = mot.replace("{", "")
                mot = mot.replace("}", "")
                mot = mot.replace('"', "")
                mot = mot.replace("'", "")
                mot = mot.strip().lower()
    
                if not mot:
                    continue
    
                try:
                    valeur = int(valeur)
                except Exception:
                    continue
    
                resultat[mot] = valeur
    
            return resultat
    
        # Nouveau format : liste de dicts
        if isinstance(mots_score_obj, list):
            for item in mots_score_obj:
                try:
                    mot = str(item.get("mot", "")).strip().lower()
                    valeur = int(item.get("valeur", 0))
                except Exception:
                    continue
    
                if mot:
                    resultat[mot] = valeur
    
        return resultat


    def checkbox_mots_cles_dans_score_change(self, **event_args):
        """This method is called when the component is checked or unchecked"""
        self.maj_bouton_recherche_visible()
       

    def text_box_mots_ou_pressed_enter(self, **event_args):
        self.lancer_recherche()


    def text_box_mots_exclus_pressed_enter(self, **event_args):
        self.lancer_recherche()

    def text_box_mots_ou_change(self, **event_args):
        self.maj_bouton_recherche_visible()

    def text_box_mots_exclus_change(self, **event_args):
        self.maj_bouton_recherche_visible()
    

    def maj_cadre_mots_ou_blanc(self, **event_args):
        # mise en blanc du border quand un champ autre que les mots ou est saisi
        self.column_panel_mots_pour_score.border = "1px solid #BFC8CA"  # Blanc
        
    def maj_cadre_mots_ou_bleu(self, **event_args):
        # mise en blanc du border quand un champ autre que les mots ou est saisi
        self.column_panel_mots_pour_score.border = "1px solid #3CD9ED"  # Bleu


    def timer_recherche_progress_tick(self, **event_args):
        """
        Suit la Background Task.
        Le bouton reste désactivé jusqu'à la fin complète :
        recherche + filtrage + scoring + sauvegarde.
        """
    
        if self.task_recherche is None:
            self.deverrouiller_recherche(cacher_bouton=False)
            return
    
        try:
            with anvil.server.no_loading_indicator:
                state = self.task_recherche.get_state() or {}
    
        except Exception as e:
            print(f"Impossible de lire la progression : {e}")
            self.label_progress_recherche.text = "Erreur de lecture de la progression."
            self.label_nb_offres_progress.text = ""
            self.deverrouiller_recherche(cacher_bouton=False)
            alert(f"Impossible de lire la progression : {e}")
            return
    
        progress = state.get("progress", 0)
        message = state.get("message", "Recherche en cours...")
        nb_offres = state.get("nb_offres", 0)
    
        self.label_progress_recherche.text = f"{progress}% - {message}"
    
        if nb_offres > 1:
            self.label_nb_offres_progress.text = (
                f"{nb_offres} offres provisoires récupérées avant filtrage final"
            )
        else:
            self.label_nb_offres_progress.text = (
                f"{nb_offres} offre provisoire récupérée avant filtrage final"
            )
    
        if not self.task_recherche.is_completed():
            return
    
        # La tâche Uplink est terminée.
        # On arrête le timer, mais on NE réactive PAS encore le bouton.
        # Il reste le filtrage, le scoring et la sauvegarde.
        self.timer_recherche_progress.interval = 0
    
        try:
            with anvil.server.no_loading_indicator:
                result = self.task_recherche.get_return_value()
    
        except Exception as e:
            print(f"Erreur pendant la tâche background : {e}")
            self.label_progress_recherche.text = "Erreur pendant la recherche."
            self.label_nb_offres_progress.text = ""
            self.deverrouiller_recherche(cacher_bouton=False)
            alert(f"Erreur pendant la recherche : {e}")
            return
    
        if not result:
            self.label_progress_recherche.text = "Recherche terminée, mais résultat vide."
            self.label_nb_offres_progress.text = "0 offre récupérée"
            self.deverrouiller_recherche(cacher_bouton=False)
            alert("La recherche est terminée, mais aucun résultat n'a été retourné.")
            return
    
        errors = result.get("errors", [])
        if errors:
            print("Erreurs partielles pendant la recherche :", errors)
    
        offres = result.get("offres", [])
    
        self.label_progress_recherche.text = "Recherche terminée. Traitement des offres..."
        self.label_nb_offres_progress.text = (
            f"{len(offres)} offres provisoires récupérées avant filtrage final"
            if len(offres) > 1
            else f"{len(offres)} offre provisoire récupérée avant filtrage final"
        )
    
        try:
            self.traiter_offres_recuperees_apres_background(offres)
    
        except Exception as e:
            print(f"Erreur pendant le traitement final des offres : {e}")
            self.label_progress_recherche.text = "Erreur pendant le traitement final."
            self.deverrouiller_recherche(cacher_bouton=False)
            alert(f"Erreur pendant le traitement final des offres : {e}")
            return

    def texte_nb_offres(self, nb, mot_apres_singulier="", mot_apres_pluriel=""):
        nb = int(nb or 0)
    
        if nb > 1:
            return f"{nb} offres {mot_apres_pluriel}".strip()
    
        return f"{nb} offre {mot_apres_singulier}".strip()

    def maj_bouton_recherche_visible(self):
        """
        Affiche le bouton de recherche si au moins un critère positif existe :
        - mots obligatoires
        - ou mots OU avec importance
        """
    
        has_mots_obligatoires = bool((self.text_box_mot_clef.text or "").strip())
        has_mots_ou = len(self.dict_mots_score or {}) > 0
    
        visible = has_mots_obligatoires or has_mots_ou
    
        self.button_search.visible = visible
        self.f.navigation_link_search_go.visible = visible



