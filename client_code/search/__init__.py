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

        # =====================================================================
        # Variables internes
        # =====================================================================
        self.user = None
        self.histo_id = None
        self.list_offres = []
        self.offres_preparees = []
        self.dict_mots_score = dict(dict_mots_score or {})    # mots type OU saisis par l'utilisateur + importance
        self.dict_score_recherche = {}                        # dictionnaire final utilisé pour scorer
        # Evite les traitements indésirables quand on modifie la checkbox par code
        self._ignore_checkbox_on_off_change = False
        self.dropdown_menu_valeur.items = [
            ("*", 1),
            ("* *", 5),
            ("* * *", 10)
        ]
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
                self.button_search.visible = True
                self.column_panel_params.visible = True

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

                if derniere_ligne:
                    self.afficher_offres(self.list_offres)
                    self.button_search.visible = False
                else:
                    self.column_panel_select.visible = False
                    self.button_search.visible = True

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

    # =========================================================================
    # Recherche
    # =========================================================================

    def button_search_click(self, **event_args):
        """Recherche les offres, applique les critères positifs/exclusions, score, puis sauvegarde dans histo['offres']."""
    
        # --- Lecture des champs ---
        mots_obligatoires_texte = self.text_box_mot_clef.text or ""
        mots_exclus_texte = self.text_box_mots_exclus.text or ""
        deps_texte = self.text_box_departements.text or ""
        
        # --- Conversion en listes propres ---
        mots_obligatoires = self.extraire_liste_mots_saisie(mots_obligatoires_texte)
        
        # Les mots OU viennent maintenant de la liste avec importance
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
    
        # --- Récupération brute des offres ---
        try:
            offres = anvil.server.call(
                "get_offres_multi_sources",
                mots_clefs,
                depts,
                100,
                1,
                periode,
                sources=selected_platformes
            )
        except Exception as e:
            print(f"Erreur au module 'get_offres_multi_sources' sur Pi5: {e}")
            alert(f"Erreur pendant la recherche : {e}")
            return
    
        if not offres:
            self.data_grid_1.visible = False
            self.column_panel_select.visible = False
            self.text_nb_offres.visible = False
            alert("Désolé... pas d'offres trouvées !")
            return
    
        nb_offres_brutes = len(offres)
        print(f"Offres brutes récupérées : {nb_offres_brutes}")
    
        # =====================================================
        # 1. Filtrage positif local
        # =====================================================
        # Règle :
        # - tous les mots obligatoires doivent être présents
        # - si des mots OU existent, au moins un doit être présent
    
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
            alert(
                "Des offres ont été récupérées, mais aucune ne respecte les critères :\n\n"
                f"Obligatoires : {', '.join(mots_obligatoires) or '-'}\n"
                f"Au moins un : {', '.join(mots_ou) or '-'}"
            )
            return
    
        # =====================================================
        # 2. Filtrage local des mots exclus
        # =====================================================
    
        offres = self.filtrer_offres_exclues(offres, mots_exclus)
    
        nb_apres_exclusion = len(offres)
        nb_exclues = nb_apres_filtre_positif - nb_apres_exclusion
    
        print(f"Offres exclues : {nb_exclues}")
        print(f"Offres conservées : {nb_apres_exclusion}")
    
        if not offres:
            self.data_grid_1.visible = False
            self.column_panel_select.visible = False
            self.text_nb_offres.visible = False
            alert(
                "Des offres correspondaient aux critères, mais elles contenaient toutes au moins un mot exclu."
            )
            return
    
        # --- Génération de la liste des offres ---
        self.offres_preparees = self.build_offres_list(offres, dedoublonner=True)
    
        print(
            "offres_preparees avant score:",
            type(self.offres_preparees),
            len(self.offres_preparees)
        )
    
        # --- Calcul du score / pertinence côté serveur ---
        try:
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
        date_time = Time.french_zone_time()
    
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
            self.dict_mots_score,     # On sauvegarde les mots OU + importance choisis par l'utilisateur
            True,                     # La checkbox disparaît : les mots obligatoires sont inclus automatiquement dans le scoring final         
            self.get_mots_ou_texte(),  # mots_ou généré depuis repeating_panel_mots_pour_score
            self.get_mots_exclus_texte()
        )
    
        if not result or not result.get("ok"):
            message = result.get("message") if result else "Erreur inconnue"
            alert(
                f"La recherche a fonctionné, mais la sauvegarde dans histo a échoué.\n\n{message}"
            )
            return
    
        self.histo_id = result.get("histo_id")
    
        if not self.histo_id:
            alert("Sauvegarde histo effectuée, mais histo_id manquant.")
            return
    
        print(f"Ligne histo sauvegardée : {self.histo_id}")
        print(f"Nombre d'offres sauvegardées dans histo : {result.get('nb_offres')}")
    
        self.list_offres = offres_scorees
    
        self.afficher_offres(self.list_offres)
    
        self.button_search.visible = False
        self.column_panel_params.visible = False
    
        self.text_param_summary.text = (
            f"Plateformes : {self.multi_select_drop_down_platformes.selected} / "
            f"Obligatoires : {self.get_mots_obligatoires_texte() or '-'} / "
            f"Au moins un : {self.text_box_mots_ou.text or '-'} / "
            f"Exclus : {self.get_mots_exclus_texte() or '-'} / "
            f"sur les {self.text_box_nb_jours.text} derniers jours / "
            f"Départements : {self.text_box_departements.text or '-'}"
        )
    
        self.text_param_summary.visible = True

    # =========================================================================
    # Champs Enter
    # =========================================================================

    def text_box_nb_jours_pressed_enter(self, **event_args):
        self.button_search_click()

    def text_box_mot_clef_pressed_enter(self, **event_args):
        self.button_search_click()

    def text_box_departements_pressed_enter(self, **event_args):
        self.button_search_click()

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
    # Navigation
    # =========================================================================

    def button_retour_click(self, **event_args):
        open_form("Main_large_screen")

    # =========================================================================
    # Timer
    # =========================================================================

    def timer_1_tick(self, **event_args):
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
    """
    def button_gestion_score_click(self, **event_args):
        if self.column_panel_mots_pour_score.visible is False:
            self.column_panel_mots_pour_score.visible = True
            self.column_panel_add_mot_pour_score.visible = True
            self.button_search.visible = False
            self.scroll_into_view(smooth=self.text_box_mot_clef)

            try:
                if len(self.repeating_panel_mots_pour_score.items) > 0:
                    self.repeating_panel_mots_pour_score.visible = True
            except Exception:
                pass
        else:
            self.column_panel_mots_pour_score.visible = False
            self.button_search.visible = True
    """
    def text_box_mot_change(self, **event_args):
        if self.dropdown_menu_valeur.selected_value is not None:
            self.icon_button_valid_mot_score.visible = True


    def dropdown_menu_valeur_change(self, **event_args):
        valeur = self.dropdown_menu_valeur.selected_value or 0
        if valeur != 0:
            self.icon_button_valid_mot_score.visible = True

    def icon_button_del_click(self, **event_args):
        self.text_box_mot.text = ""
        self.dropdown_menu_valeur.selected_value = None
        self.icon_button_valid_mot_score.visible = False
        self.column_panel_add.visible = False
        self.button_add_mot.visible = True
        self.data_grid_mots_pour_score.visible = True

    def button_add_mot_click(self, **event_args):
        self.column_panel_add.visible = True
        self.button_add_mot.visible = False
        self.text_box_mot.focus()
        #self.data_grid_mots_pour_score.visible = False

    def icon_button_valid_mot_score_click(self, **event_args):
        cle = (self.text_box_mot.text or "").strip().lower()
        valeur = self.dropdown_menu_valeur.selected_value or 0
    
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
            alert("La valeur doit être 1, 5 ou 10.")
            return
    
        if valeur not in [1, 5, 10]:
            alert("Valeurs autorisées : 1, 5 ou 10.")
            return
    
        # Ajout ou remplacement du mot
        self.dict_mots_score[cle] = valeur
    
        self.display_mots_pour_score()
    
        print("dict_mots_score utilisateur :", self.dict_mots_score)
    
        self.text_box_mot.text = ""
        self.dropdown_menu_valeur.selected_value = None
        self.icon_button_valid_mot_score.visible = False
        self.data_grid_mots_pour_score.visible = True

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
        self.column_panel_add.visible = False
        self.button_add_mot.visible = True
    
        # Compatibilité temporaire si text_box_mots_ou existe encore dans l'IDE.
        # Quand le composant sera supprimé, ce try évitera de casser.
        try:
            self.text_box_mots_ou.text = self.get_mots_ou_texte()
        except Exception:
            pass
    
        # Compatibilité temporaire si text_box_mots_pour_score existe encore.
        try:
            self.text_box_mots_pour_score.text = self.mots_score_to_text(self.dict_mots_score)
        except Exception:
            pass
    
        self.button_search.visible = True

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
        self.button_search.visible = True

   
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
        self.button_search.visible = True


    def text_box_mots_ou_pressed_enter(self, **event_args):
        self.button_search_click()


    def text_box_mots_exclus_pressed_enter(self, **event_args):
        self.button_search_click()

    def text_box_mots_ou_change(self, **event_args):
        self.button_search.visible = True

    def text_box_mots_exclus_change(self, **event_args):
        self.button_search.visible = True

