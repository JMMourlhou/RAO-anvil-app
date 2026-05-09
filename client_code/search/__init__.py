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
        self.dict_mots_score = dict(dict_mots_score or {})

        # Evite les traitements indésirables quand on modifie la checkbox par code
        self._ignore_checkbox_on_off_change = False

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
        self.text_box_nb_jours.text = row["nb_jours"]
        self.text_box_departements.text = row["departements"]
        try:
            self.checkbox_mots_cles_dans_score.checked = bool(row["mots_cles_in_score"])
        except Exception:
            self.checkbox_mots_cles_dans_score.checked = False
        src = row["sources"]
        if src is not None:
            self.multi_select_drop_down_platformes.selected = src
        else:
            self.multi_select_drop_down_platformes.selected = [r["id"] for r in rows_platformes]

        try:
            self.dict_mots_score = dict(row["mots_score"] or {})
        except Exception:
            self.dict_mots_score = {}
        
        self.text_box_mots_pour_score.text = self.mots_score_to_text(self.dict_mots_score)
        self.list_offres = self.normaliser_liste_offres_vu(row["offres"] or [])

        return row

    # =========================================================================
    # Recherche
    # =========================================================================

    def button_search_click(self, **event_args):
        """Recherche les offres, les score, puis les sauvegarde dans histo['offres']."""

        # --- Lecture et nettoyage des champs texte ---
        mots_texte = self.text_box_mot_clef.text or ""
        deps_texte = self.text_box_departements.text or ""

        # --- Conversion en listes ---
        mots_clefs = [m.strip() for m in mots_texte.split(",") if m.strip()]
        depts = [d.strip() for d in deps_texte.split(",") if d.strip()]

        try:
            periode = int(self.text_box_nb_jours.text)
        except Exception:
            alert("Le nombre de jours doit être un nombre entier.")
            self.text_box_nb_jours.focus()
            return

        print(f"Recherche sur les {periode} derniers jours")
        print("🔍 Mots-clés saisis :", mots_clefs)
        print("🗺️ Départements saisis :", depts)

        selected_platformes = self.multi_select_drop_down_platformes.selected
        print(f"Sources: {selected_platformes}")
        
        # Construction du dictionnaire des mots pour le scoring
        dict_score = self.build_dict_mots_score()

        if dict_score is None:
            return
        
        self.dict_mots_score = dict_score
        print("dict_mots_score utilisé pour scoring :", self.dict_mots_score)
        
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

        # Génération de la liste des offres
        self.offres_preparees = self.build_offres_list(offres, dedoublonner=True)

        print(
            "offres_preparees avant score:",
            type(self.offres_preparees),
            len(self.offres_preparees)
        )

        # Calcul du score / pertinence côté serveur
        try:
            offres_scorees = anvil.server.call(
                "scorer_offres",
                self.offres_preparees,
                self.dict_mots_score or {}
            )
        except Exception as e:
            print(f"Erreur au module serveur 'scorer_offres': {e}")
            alert(f"Erreur pendant le calcul du score : {e}")
            offres_scorees = self.offres_preparees

        if offres_scorees is None:
            print("Attention : scorer_offres a renvoyé None")
            offres_scorees = self.offres_preparees

        # Ajout sécurité de la clé vu=False dans chaque offre
        offres_scorees = self.normaliser_liste_offres_vu(offres_scorees)

        nb_offres = len(offres_scorees)

        # Backup de la requête avec les offres scorées
        date_time = Time.french_zone_time()

        result = anvil.server.call(
            "backup_requete",
            self.user,
            selected_platformes,
            self.text_box_mot_clef.text,
            self.text_box_nb_jours.text,
            self.text_box_departements.text,
            date_time,
            nb_offres,
            offres_scorees,
            self.dict_mots_score,
            bool(self.checkbox_mots_cles_dans_score.checked)
        )
        
        if not result or not result.get("ok"):
            message = result.get("message") if result else "Erreur inconnue"
            alert(f"La recherche a fonctionné, mais la sauvegarde dans histo a échoué.\n\n{message}")
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
            f"Plateformes:{self.multi_select_drop_down_platformes.selected} / "
            f"Mots clefs:{self.text_box_mot_clef.text} / "
            f"sur les {self.text_box_nb_jours.text} derniers jours / "
            f"{self.text_box_departements.text}"
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
        self.repeating_panel_1.tag.mots_cles_saisis = self.text_box_mot_clef.text or ""

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

    def text_box_mot_change(self, **event_args):
        if self.text_box_valeur.text is not None:
            self.icon_button_valid_mot_score.visible = True

    def text_box_valeur_change(self, **event_args):
        valeur = self.text_box_valeur.text or 0
        if valeur != 0:
            self.icon_button_valid_mot_score.visible = True

    def icon_button_del_click(self, **event_args):
        self.text_box_mot.text = ""
        self.text_box_valeur.text = ""
        self.icon_button_valid_mot_score.visible = False
        self.column_panel_add.visible = False
        self.button_add_mot.visible = True
        self.data_grid_mots_pour_score.visible = True

    def button_add_mot_click(self, **event_args):
        self.column_panel_add.visible = True
        self.button_add_mot.visible = False
        self.text_box_mot.focus()
        self.data_grid_mots_pour_score.visible = False

    def icon_button_valid_mot_score_click(self, **event_args):
        cle = (self.text_box_mot.text or "").strip()
        valeur = self.text_box_valeur.text or 0

        if cle == "":
            alert("Entrez le mot à prendre en compte dans le scoring")
            self.text_box_mot.focus()
            return

        if valeur == 0:
            alert("Entrez la valeur")
            self.text_box_valeur.focus()
            return

        try:
            self.dict_mots_score[cle] = int(valeur)
        except Exception:
            alert("La valeur doit être un nombre entier.")
            self.text_box_valeur.focus()
            return

        self.display_mots_pour_score()

        print(self.dict_mots_score)

        self.text_box_mot.text = ""
        self.text_box_valeur.text = ""
        self.icon_button_valid_mot_score.visible = False
        self.data_grid_mots_pour_score.visible = True

    def del_mot_pour_score(self, sender, mot=None, **event_args):
        if mot in self.dict_mots_score:
            del self.dict_mots_score[mot]
        self.display_mots_pour_score()

    def modif_mot_pour_score(self, sender, item=None, cle=None, valeur=None, **event_args):
        if item and item[0] in self.dict_mots_score:
            del self.dict_mots_score[item[0]]

        try:
            self.dict_mots_score[cle] = int(valeur)
        except Exception:
            alert("La valeur doit être un nombre entier.")
            return

        n = Notification("Modification effectuée", timeout=1.5)
        n.show()

        self.display_mots_pour_score()

    def display_mots_pour_score(self, **event_args):
        list_keys = sorted(self.dict_mots_score.keys())

        list_display = []

        for mk in list_keys:
            list_display.append((mk, self.dict_mots_score[mk]))

        print(len(list_display))

        self.repeating_panel_mots_pour_score.items = list(list_display)
        self.data_grid_mots_pour_score.visible = True
        self.column_panel_add.visible = False
        self.button_add_mot.visible = True

    def build_dict_mots_score(self):
        """
        Construit le dictionnaire des mots pour le scoring.
    
        Format attendu :
        rénovation:10, restauration:5, bois:1
    
        Retourne :
        - un dictionnaire si tout est correct
        - None si erreur de saisie
        """
    
        dict_temp = {}
    
        # =====================================================
        # 1. Lecture du champ optionnel mots pour score
        # =====================================================
    
        texte_score = (self.text_box_mots_pour_score.text or "").strip()
    
        if texte_score:
            morceaux = texte_score.split(",")
    
            for morceau in morceaux:
                morceau = morceau.strip()
    
                if not morceau:
                    continue
    
                if ":" not in morceau:
                    alert(
                        f"Format incorrect pour : {morceau}\n\n"
                        "Format attendu : mot:valeur\n"
                        "Exemple : rénovation:10, restauration:5"
                    )
                    self.text_box_mots_pour_score.focus()
                    return None
    
                mot, valeur = morceau.split(":", 1)
    
                mot = mot.strip().lower()
                valeur = valeur.strip()
    
                if not mot:
                    alert(
                        "Un mot est vide dans les mots pour score.\n\n"
                        "Format attendu : rénovation:10, restauration:5"
                    )
                    self.text_box_mots_pour_score.focus()
                    return None
    
                if not valeur:
                    alert(
                        f"Valeur manquante pour : {mot}\n\n"
                        "Format attendu : mot:valeur\n"
                        "Exemple : rénovation:10"
                    )
                    self.text_box_mots_pour_score.focus()
                    return None
    
                try:
                    valeur = int(valeur)
                except Exception:
                    alert(
                        f"Valeur incorrecte pour : {mot}\n\n"
                        "La valeur doit être un nombre : 1, 5 ou 10."
                    )
                    self.text_box_mots_pour_score.focus()
                    return None
    
                if valeur not in [1, 5, 10]:
                    alert(
                        f"Valeur non autorisée pour : {mot}\n\n"
                        "Valeurs autorisées : 1, 5 ou 10."
                    )
                    self.text_box_mots_pour_score.focus()
                    return None
    
                dict_temp[mot] = valeur
    
        # =====================================================
        # 2. Ajouter aussi les mots-clés de recherche au score
        # =====================================================
    
        try:
            utiliser_mots_cles = bool(self.checkbox_mots_cles_dans_score.checked)
        except Exception:
            utiliser_mots_cles = False
    
        if utiliser_mots_cles:
            mots_cles = self.extraire_mots_cles_pour_score()
    
            for mot in mots_cles:
                if mot not in dict_temp:
                    dict_temp[mot] = 1
    
        return dict_temp

    def extraire_mots_cles_pour_score(self):
        """
        Extrait les mots-clés depuis self.text_box_mot_clef.text.
    
        Exemple :
        'porte ou fenêtre' devient ['porte', 'fenêtre']
        'porte, fenêtre, menuiserie' devient ['porte', 'fenêtre', 'menuiserie']
        """
    
        brut = (self.text_box_mot_clef.text or "").strip().lower()
    
        if not brut:
            return []
    
        texte = brut.replace(";", ",")
        texte = texte.replace("\n", ",")
        texte = texte.replace(" et ", ",")
        texte = texte.replace(" ou ", ",")
        texte = texte.replace(" and ", ",")
        texte = texte.replace(" or ", ",")
    
        morceaux = [m.strip() for m in texte.split(",") if m.strip()]
    
        mots_uniques = []
        deja_vus = set()
    
        for mot in morceaux:
            if mot not in deja_vus:
                deja_vus.add(mot)
                mots_uniques.append(mot)
    
        return mots_uniques
    
    def button_fin_mots_score_click(self, **event_args):
        self.column_panel_mots_pour_score.visible = False
        self.button_search.visible = True


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

