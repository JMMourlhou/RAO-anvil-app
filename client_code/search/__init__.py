from ._anvil_designer import searchTemplate
from anvil import *
import anvil.server
from .. import Time
from datetime import date, datetime
import re
from anvil.js import get_dom_node, window    # pour écouteur JS sur le DropDown et conter tps d'éxéction
from .. import Context_ecran


# Alertes :
from ..Alertes import (
afficher_information,
afficher_reussite,
demander_choix,
afficher_avertissement
)


class search(searchTemplate):
    def __init__(
        self,
        origine="",
        checkbox_on_off=False,
        mk="",
        bt_mail_visible=False,
        **properties
    ):
        t_total = window.performance.now()

        def afficher_temps(libelle, debut):
            duree = (window.performance.now() - debut) / 1000
            print(f"[PERF search] {libelle} : {duree:.3f} s")

        # ================================================================
        # Création des composants
        # ================================================================

        t = window.performance.now()

        self.init_components(**properties)

        afficher_temps("init_components", t)

        # ================================================================
        # Détection du type d'écran
        # ================================================================

        t = window.performance.now()

        self.context = Context_ecran.context_screen()

        if self.context["screen_type"] == "phone":
            self.button_selection_mailed.text = "Mail"
        else:
            self.button_selection_mailed.text = (
                "Envoi de la sélection"
            )

        afficher_temps(
            "Context_ecran et adaptation affichage",
            t
        )

        # ================================================================
        # Form principale
        # ================================================================

        t = window.performance.now()

        self.f = get_open_form()

        afficher_temps("get_open_form", t)

        # ================================================================
        # Affichage de la progression
        # ================================================================

        t = window.performance.now()

        self.column_panel_progress_recherche.role = (
            "progress-search-box"
        )
        self.label_progress_recherche.role = (
            "progress-search-main"
        )
        self.label_jauge_globale.role = (
            "progress-gauge-global"
        )
        self.label_jauge_source.role = (
            "progress-gauge-source"
        )

        self.column_panel_progress_recherche.visible = False

        afficher_temps(
            "initialisation affichage progression",
            t
        )

        # ================================================================
        # Variables internes
        # ================================================================

        t = window.performance.now()

        self.user = None
        self.histo_id = None
        self.list_offres = []

        self.label_progress_recherche.visible = False
        self.timer_recherche_progress.interval = 0

        self.task_recherche = None
        self._ctx_recherche = {}
        self._recherche_en_cours = False
        self._annulation_recherche_demandee = False

        self.base_app = ""

        self._last_progress_global = None
        self._last_progress_source = None
        self._last_progress_role = None

        self.label_jauge_globale.visible = False
        self.label_jauge_source.visible = False
        self.text_param_summary.visible = False
        self.button_daily_survey_creation.visible = False
        self.button_daily_survey_creation.enabled = True

        # Évite les événements indésirables lors d'une modification par code
        self._ignore_checkbox_on_off_change = False

        afficher_temps(
            "initialisation variables internes",
            t
        )

        # ================================================================
        # Événements du RepeatingPanel
        # ================================================================

        t = window.performance.now()

        self.repeating_panel_offres.set_event_handler(
            "x-checkbox-vu-changee",
            self.modifier_offre_vu
        )

        self.repeating_panel_offres.set_event_handler(
            "x-del-offre",
            self.del_offre_affichee
        )

        self.repeating_panel_offres.set_event_handler(
            "x-icon_button_go_up",
            self.go_up
        )

        self.repeating_panel_offres.set_event_handler(
            "x-icon_button_go_down",
            self.go_down
        )

        afficher_temps(
            "installation handlers repeating_panel_offres",
            t
        )

        # ================================================================
        # Appel serveur unique
        # ================================================================

        inclure_offres = origine == "check"

        t = window.performance.now()

        try:
            with anvil.server.no_loading_indicator:
                donnees_initiales = anvil.server.call(
                    "initialiser_form_search",
                    inclure_offres
                )

        except Exception as e:
            print(
                "Erreur pendant l'initialisation de search :",
                e
            )

            afficher_avertissement(
                "Impossible d'initialiser la recherche.\n\n"
                f"{e}",
                titre="Erreur d’initialisation"
            )
            return

        afficher_temps(
            "appel initialiser_form_search",
            t
        )

        if not isinstance(donnees_initiales, dict):
            afficher_avertissement(
                "Le serveur n'a pas renvoyé les données "
                "d'initialisation attendues.",
                titre="Erreur d’initialisation"
            )
            return

        # ================================================================
        # Utilisateur et base_app
        # ================================================================

        self.user = donnees_initiales.get("user")

        self.base_app = (
            donnees_initiales.get("base_app") or ""
        )

        if not self.user:
            afficher_avertissement(
                "Vous n'êtes pas connecté.",
                titre="Connexion requise"
            )
            return

        # ================================================================
        # Configuration des plateformes
        # ================================================================

        t = window.performance.now()

        plateformes = (
            donnees_initiales.get("plateformes") or []
        )

        self.multi_select_drop_down_platformes.items = [
            {
                "key": plateforme_id,
                "value": plateforme_id
            }
            for plateforme_id in plateformes
        ]

        self.multi_select_drop_down_platformes.placeholder = (
            "Sélectionnez les plateformes"
        )
        self.multi_select_drop_down_platformes.multiple = True
        self.multi_select_drop_down_platformes.enable_filtering = False
        self.multi_select_drop_down_platformes.enable_select_all = True
        self.multi_select_drop_down_platformes.width = "100%"
        self.multi_select_drop_down_platformes.background = "#3CD9ED"
        self.multi_select_drop_down_platformes.spacing_above = "1"

        afficher_temps(
            "configuration plateformes",
            t
        )

        # ================================================================
        # Dernière recherche
        # ================================================================

        t = window.performance.now()

        derniere_ligne = donnees_initiales.get("histo")

        if derniere_ligne is None:
            # Nouvel utilisateur sans historique
            self.multi_select_drop_down_platformes.selected = (
                plateformes
            )

            self.text_box_mot_clef.text = (
                "Football et Ballon"
            )
            self.text_box_mot_ou.text = ""
            self.text_box_mots_exclus.text = ""
            self.text_box_nb_jours.text = "30"
            self.text_box_departements.text = None

            self.histo_id = None
            self.list_offres = []

        else:
            self.histo_id = derniere_ligne.get("histo_id")

            self.text_box_mot_clef.text = (
                derniere_ligne.get("mots_cles") or ""
            )

            self.text_box_mot_ou.text = (
                derniere_ligne.get("mots_ou") or ""
            )

            self.text_box_mots_exclus.text = (
                derniere_ligne.get("mots_exclus") or ""
            )

            self.text_box_nb_jours.text = (
                derniere_ligne.get("nb_jours") or "30"
            )

            self.text_box_departements.text = (
                derniere_ligne.get("departements")
            )

            sources = derniere_ligne.get("sources")

            if sources is not None:
                self.multi_select_drop_down_platformes.selected = (
                    sources
                )
            else:
                self.multi_select_drop_down_platformes.selected = (
                    plateformes
                )

        # ============================================================
        # Offres uniquement pour origine == "check"
        # ============================================================

        if inclure_offres and derniere_ligne is not None:
            t_offres = window.performance.now()

            offres_chargees = (
                self.normaliser_liste_offres_vu(
                    derniere_ligne.get("offres") or []
                )
            )

            mots_obligatoires = (
                self.extraire_liste_mots_saisie(
                    self.text_box_mot_clef.text or ""
                )
            )

            mots_ou = self.extraire_liste_mots_saisie(
                self.text_box_mot_ou.text or ""
            )

            mots_exclus = (
                self.extraire_liste_mots_saisie(
                    self.text_box_mots_exclus.text or ""
                )
            )

            offres_chargees = (
                self.filtrer_offres_criteres_positifs(
                    offres_chargees,
                    mots_obligatoires,
                    mots_ou
                )
            )

            offres_chargees = (
                self.filtrer_offres_exclues(
                    offres_chargees,
                    mots_exclus
                )
            )

            offres_chargees = (
                self.ajouter_correspondance_mots_ou(
                    offres_chargees,
                    mots_ou
                )
            )

            self.list_offres = (
                self.trier_offres_par_interet(
                    offres_chargees
                )
            )

            afficher_temps(
                "traitement offres mode check",
                t_offres
            )

        else:
            self.list_offres = []

        afficher_temps(
            "application dernière recherche",
            t
        )

        # ================================================================
        # Ouverture normale depuis le Menu
        # ================================================================

        t = window.performance.now()

        if origine == "":
            self.column_panel_params.visible = True
            self.maj_bouton_recherche_visible()

        afficher_temps(
            "traitement origine normale",
            t
        )

        # ================================================================
        # Ouverture en mode vérification
        # ================================================================

        t = window.performance.now()

        if origine == "check":
            self.column_panel_params.visible = False

            if mk != "":
                self.text_box_mot_clef.text = mk

            self.set_checkbox_on_off_sans_event(
                bool(checkbox_on_off)
            )

            if bt_mail_visible is True:
                self.button_selection_mailed.visible = True

            if derniere_ligne is not None:
                self.afficher_offres(self.list_offres)
            else:
                self.column_panel_select.visible = False

            self.f.navigation_link_search_go.visible = False

        afficher_temps(
            "traitement origine check",
            t
        )

        # ================================================================
        # Temps total
        # ================================================================

        afficher_temps(
            "TOTAL __init__",
            t_total
        )

    def verrouiller_recherche(self):
        """
        Verrouille l'interface pendant une recherche.
        Empêche un double clic ou un nouveau lancement.
        """

        self._recherche_en_cours = True

        try:
            self.f.navigation_link_search_go.visible = True
            self.f.navigation_link_search_go.enabled = False
            # Ne pas changer le texte ici : cela peut faire bouger le menu M3.
            # self.f.navigation_link_search_go.text = "Recherche en cours..."
        except Exception as e:
            print("Erreur verrouillage navigation_link_search_go :", e)

        self.afficher_progression_recherche(
            ligne_1="🔎 Lancement de la recherche",
            ligne_2="Préparation des plateformes...",
            etat="running",
            progress_global=0,
            progress_source=0
        )

    def deverrouiller_recherche(self, cacher_bouton=False):
        """
        Déverrouille l'interface après fin, erreur ou interruption de recherche.
        """
        self._recherche_en_cours = False
        self.timer_recherche_progress.interval = 0
        self.task_recherche = None

        try:
            self.f.navigation_link_search_go.visible = True

            if cacher_bouton:
                # On ne le cache pas : le masquer fait bouger le menu M3.
                self.f.navigation_link_search_go.enabled = False
            else:
                self.f.navigation_link_search_go.enabled = True

            # Ne pas changer le texte à chaque fin de recherche.
            self.f.navigation_link_search_go.text = "Rechercher"
        except Exception as e:
            print("Erreur réactivation navigation_link_search_go :", e)

        try:
            self.text_box_mot_clef.enabled = True
            self.text_box_mots_exclus.enabled = True
            self.text_box_nb_jours.enabled = True
            self.text_box_departements.enabled = True
            self.multi_select_drop_down_platformes.enabled = True
            self.text_box_mot_ou.enabled = True
        except Exception as e:
            print("Erreur déverrouillage UI :", e)

    def annuler_recherche_depuis_menu(self):
        """
        Appelée par la Form mère Menu avant de quitter la page search.
        Arrête le timer client et tue la background task si elle existe.
        """

        print("Demande d'annulation de la recherche depuis Menu")

        self._annulation_recherche_demandee = True

        # 1. Arrêter immédiatement le timer côté client
        try:
            self.timer_recherche_progress.interval = 0
        except Exception as e:
            print("Erreur arrêt timer_recherche_progress :", e)

        # 2. Récupérer la task avant de la remettre à None
        task = self.task_recherche

        if task is None:
            print("Aucune task_recherche à tuer")
            self.deverrouiller_recherche(cacher_bouton=False)
            return {
                "ok": True,
                "message": "Aucune recherche en cours"
            }

        # 3. Tuer la task côté serveur
        try:
            with anvil.server.no_loading_indicator:
                result = anvil.server.call("task_killer", task)

            print("Résultat task_killer :", result)

        except Exception as e:
            print("Erreur pendant task_killer :", e)
            result = {
                "ok": False,
                "message": str(e)
            }

        # 4. Nettoyer l'état local de search
        self.task_recherche = None
        self._recherche_en_cours = False

        try:
            self.afficher_progression_recherche(
                ligne_1="⛔ Recherche annulée",
                ligne_2="Retour au menu.",
                etat="error",
                progress_global=0,
                progress_source=0,
                afficher_jauges=False
            )
        except Exception as e:
            print("Erreur affichage annulation :", e)

        try:
            self.deverrouiller_recherche(cacher_bouton=False)
        except Exception as e:
            print("Erreur déverrouillage après annulation :", e)

        return result

    # =========================================================================
    # Recherche
    # =========================================================================
    def button_search_click(self, **event_args):
        if self._recherche_en_cours is True:
            Notification("Recherche déjà en cours...", timeout=2).show()
            return

        self.lancer_recherche()

    def lancer_recherche(self, **event_args):
        """
        Recherche les offres, applique les critères positifs et les exclusions,
        calcule la correspondance des mots OU, puis sauvegarde le résultat.
        """
        self.Titre_2.scroll_into_view(smooth=True, align="center")
        if self._recherche_en_cours:
            Notification("Recherche déjà en cours...", timeout=2).show()
            return

        # --- Lecture des champs ---
        mots_obligatoires_texte = self.text_box_mot_clef.text or ""
        mots_ou_texte = self.text_box_mot_ou.text or ""
        mots_exclus_texte = self.text_box_mots_exclus.text or ""
        deps_texte = self.text_box_departements.text or ""

        # --- Conversion en listes propres ---
        mots_obligatoires = self.extraire_liste_mots_saisie(mots_obligatoires_texte)

        mots_ou = self.extraire_liste_mots_saisie(mots_ou_texte)

        mots_exclus = self.extraire_liste_mots_saisie(mots_exclus_texte)

        depts = [d.strip() for d in deps_texte.split(",") if d.strip()]

        if not mots_obligatoires and not mots_ou:
            afficher_avertissement(
                "Vous devez saisir au moins un mot-clé.\n\n"
                "Exemple :\n"
                "- mots obligatoires : formation\n"
                "- au moins un de ces mots : sst, pse1",
                titre="Saisie requise"
            )
            self.text_box_mot_clef.focus()
            return

        try:
            periode = int(self.text_box_nb_jours.text)
        except Exception:
            afficher_information(
                "Le nombre de jours doit être un nombre entier.",
                titre="Valeur incorrecte"
            )
            self.text_box_nb_jours.focus()
            return

        if periode < 1:
            periode = 1
            self.text_box_nb_jours.text = "1"

        if periode > 365:
            periode = 365
            self.text_box_nb_jours.text = "365"
            Notification("La période a été limitée à 365 jours.", timeout=3).show()


        selected_platformes = self.multi_select_drop_down_platformes.selected

        if not selected_platformes:
            afficher_avertissement(
                "Sélectionnez au moins une plateforme.",
                titre="Plateforme requise"
            )
            return
            
        # --- L’ancienne recherche ne doit plus permettre
        #     la création d’une veille.
        self.button_daily_survey_creation.visible = False
        self.button_daily_survey_creation.enabled = True
  
        
        # --- Construction des requêtes envoyées aux sources ---
        # Important : cette fonction doit maintenant renvoyer large.
        # Exemple : formation + sst/mac/pse1/pse2 => ['formation']
        mots_clefs = self.construire_requetes_sources(
            mots_obligatoires=mots_obligatoires,
            mots_ou=mots_ou
        )

        # --- Lancement de la recherche brute en tâche de fond ---
        self._ctx_recherche = {
            "mots_obligatoires": mots_obligatoires,
            "mots_ou": mots_ou,
            "mots_exclus": mots_exclus,
            "periode": periode,
            "selected_platformes": selected_platformes,
        }

        self._annulation_recherche_demandee = False
        self.verrouiller_recherche()

        try:
            with anvil.server.no_loading_indicator:
                self.task_recherche = anvil.server.call(
                    "lancer_recherche_multi_sources_background",
                    mots=mots_clefs,
                    departements=depts,
                    rows=100,
                    pages=1,
                    filtre_jours=periode,
                    sources=selected_platformes,
                    operateur="ET",
                    mots_ou=mots_ou,
                    mots_exclus=mots_exclus
                )

        except Exception as e:
            print(f"Erreur au lancement de la recherche background sur Pi5 : {e}")
            self.label_progress_recherche.text = "Erreur au lancement de la recherche."
            self.deverrouiller_recherche(cacher_bouton=False)
            afficher_avertissement(
                f"Erreur pendant le lancement de la recherche :\n\n{e}",
                titre="Erreur de recherche"
            )
            return

        # afficher les paramètres 
        self.display_param_summary()

        self.afficher_progression_recherche(
            ligne_1="🔎 Recherche lancée",
            ligne_2="Lecture des offres en cours...",
            etat="running",
            progress_global=0,
            progress_source=0
        )

        self.data_grid_1.visible = False
        self.column_panel_select.visible = False
        self.text_nb_offres.visible = False
        self.checkbox_on_off.visible = False

        self.timer_recherche_progress.interval = 1
        return

    def traiter_offres_recuperees_apres_background(self, offres):
        """
        Suite du traitement après récupération des offres par Background Task :
        - filtre positif
        - exclusions
        - build_offres_list
        - correspondance des mots OU
        - sauvegarde histo
        - affichage
        """

        ctx = self._ctx_recherche or {}

        mots_obligatoires = ctx.get("mots_obligatoires", [])
        mots_ou = ctx.get("mots_ou", [])
        mots_exclus = ctx.get("mots_exclus", [])
        selected_platformes = ctx.get("selected_platformes", [])
        print(
            f"[CLIENT SEARCH] Offres reçues de l'Uplink : "
            f"{len(offres or [])}"
        )

        if not offres:
            self.data_grid_1.visible = False
            self.column_panel_select.visible = False
            self.text_nb_offres.visible = False

            self.label_progress_recherche.text = "Recherche terminée : aucune offre trouvée."

            self.deverrouiller_recherche(cacher_bouton=False)

            afficher_avertissement(
                "Désolé, aucune offre n’a été trouvée.",
                titre="Résultat de la recherche"
            )
            return

        self.label_progress_recherche.text = "Vérification des critères positifs..."
        
        # Les trois premiers mots obligatoires sont déjà contrôlés
        # par les modules sources sur le texte complet.
        #
        # On évite de refaire le même contrôle côté client sur les
        # descriptions raccourcies par lighten_offer_for_client().
        if len(mots_obligatoires) <= 3:
            offres = list(offres or [])
        
            print(
                "[CLIENT SEARCH] Filtre positif client ignoré : "
                "critères déjà contrôlés côté serveur"
            )
        
        else:
            # Sécurité provisoire pour les recherches comportant
            # plus de trois mots obligatoires.
            offres = self.filtrer_offres_criteres_positifs(
                offres,
                mots_obligatoires,
                mots_ou
            )
        
        print(
            f"[CLIENT SEARCH] Après contrôle positif : "
            f"{len(offres or [])}"
        )
        
        if not offres:
            self.data_grid_1.visible = False
            self.column_panel_select.visible = False
            self.text_nb_offres.visible = False

            self.label_progress_recherche.text = "Aucune offre après filtrage positif."

            self.deverrouiller_recherche(cacher_bouton=False)

            afficher_avertissement(
                "Des offres ont été récupérées, mais aucune ne respecte les critères :\n\n"
                f"Obligatoires : {', '.join(mots_obligatoires) or '-'}\n"
                f"Au moins un : {', '.join(mots_ou) or '-'}",
                titre="Résultat de la recherche"
            )
            return

        # =====================================================
        # 2. Filtrage local des mots exclus
        # =====================================================
        self.label_progress_recherche.text = "Application des mots exclus..."

        offres = self.filtrer_offres_exclues(offres, mots_exclus)
        print(
            f"[CLIENT SEARCH] Après mots exclus : "
            f"{len(offres or [])}"
        )
        
        if not offres:
            self.data_grid_1.visible = False
            self.column_panel_select.visible = False
            self.text_nb_offres.visible = False

            self.label_progress_recherche.text = "Aucune offre après exclusion."

            self.deverrouiller_recherche(cacher_bouton=False)
            afficher_avertissement(
                "Des offres correspondaient aux critères, mais elles contenaient "
                "toutes au moins un mot exclu.",
                titre="Résultat de la recherche"
            )
            return

        # --- Génération de la liste des offres ---
        self.label_progress_recherche.text = "Préparation des offres..."

        offres_preparees = self.build_offres_list(
            offres,
            dedoublonner=True
        )
        
        print(
            f"[CLIENT SEARCH] Après build_offres_list : "
            f"{len(offres_preparees or [])}"
        )
        
        # --- Calcul automatique de la correspondance des mots OU ---
        self.label_progress_recherche.text = "Évaluation de la correspondance des offres..."

        offres_finales = self.ajouter_correspondance_mots_ou(
            offres_preparees,
            mots_ou
        )

        offres_finales = self.normaliser_liste_offres_vu(offres_finales)

        # Tri final :
        # - par date si aucun mot OU
        # - par taux de mots OU trouvés puis date si mots OU présents
        offres_finales = self.trier_offres_par_interet(offres_finales)

        nb_offres = len(offres_finales)

        # --- Sauvegarde de la requête et des offres ---
        self.label_progress_recherche.text = "Sauvegarde de la recherche..."

        date_heure = Time.french_zone_time()

        try:
            with anvil.server.no_loading_indicator:
                result = anvil.server.call(
                    "backup_requete",
                    sources=selected_platformes,
                    mots_cles=self.get_mots_obligatoires_texte(),
                    mots_ou=self.get_mots_ou_texte(),
                    mots_exclus=self.get_mots_exclus_texte(),
                    nb_jours=self.text_box_nb_jours.text,
                    departements=self.text_box_departements.text,
                    date_heure=date_heure,
                    offres=offres_finales
                )

        except Exception as e:
            self.deverrouiller_recherche(cacher_bouton=False)
            afficher_avertissement(
                f"Erreur pendant la sauvegarde dans l’historique :\n\n{e}",
                titre="Erreur de sauvegarde"
            )
            return

        if not result or not result.get("ok"):
            message = result.get("message") if result else "Erreur inconnue"
            self.deverrouiller_recherche(cacher_bouton=False)
            afficher_avertissement(
                "La recherche a fonctionné, mais la sauvegarde dans "
                f"l’historique a échoué.\n\n{message}",
                titre="Erreur de sauvegarde"
            )
            return

        self.histo_id = result.get("histo_id")

        if not self.histo_id:
            self.deverrouiller_recherche(cacher_bouton=False)
            afficher_avertissement(
                "La sauvegarde dans l’historique a été effectuée, "
                "mais l’identifiant histo_id est manquant.",
                titre="Erreur de sauvegarde"
            )
            return

        print(f"Ligne histo sauvegardée : {self.histo_id}")
        print(f"Nombre d'offres sauvegardées dans histo : {result.get('nb_offres')}")

        self.list_offres = offres_finales

        self.afficher_offres(self.list_offres)
        
        # La veille journalière ne peut être créée qu’après une recherche ayant trouvé des offres.
        
        self.button_daily_survey_creation.enabled = True
        self.button_daily_survey_creation.visible = True

        
        self.f.navigation_link_search_go.enabled = False

        self.column_panel_params.visible = False

        # Affichage du résumé des paramètres de la requête
        self.display_param_summary()

        self.column_panel_progress_recherche.visible = True

        self.text_param_summary.visible = True

        self.afficher_progression_recherche(
            ligne_1="✅ Recherche terminée",
            ligne_2=self.format_nb_offres(
                nb_offres,
                "retenue",
                "retenues"
            ),
            etat="success",
            progress_global=100,
            progress_source=100,
            afficher_jauges=False
        )

        # Succès : on cache les boutons de recherche
        self.deverrouiller_recherche(cacher_bouton=True)

    def display_param_summary(self, **event_args):
        self.text_param_summary.text = (
            f"Plateformes : {self.multi_select_drop_down_platformes.selected} / "
            f"Obligatoires : {self.get_mots_obligatoires_texte() or '-'} / "
            f"Au moins un : {self.get_mots_ou_texte() or '-'} / "
            f"Exclus : {self.get_mots_exclus_texte() or '-'} / "
            f"sur les {self.text_box_nb_jours.text} derniers jours / "
            f"Départements : {self.text_box_departements.text or '-'}"
        )

    # =========================================================================
    # Champs Enter
    # =========================================================================

    def text_box_nb_jours_pressed_enter(self, **event_args):
        if self._recherche_en_cours is True:
            Notification("Recherche déjà en cours...", timeout=2).show()
            return

        self.lancer_recherche()

    def text_box_mot_clef_pressed_enter(self, **event_args):
        if self._recherche_en_cours is True:
            Notification("Recherche déjà en cours...", timeout=2).show()
            return

        self.lancer_recherche()

    def text_box_departements_pressed_enter(self, **event_args):
        if self._recherche_en_cours is True:
            Notification("Recherche déjà en cours...", timeout=2).show()
            return

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
        self.button_inverser_selection.visible = True

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
        self.button_inverser_selection.visible = True
        self.set_checkbox_on_off_sans_event(toutes_cochees)

    # =========================================================================
    # Effacement
    # =========================================================================

    def button_del_all_click(self, **event_args):
        """Efface toutes les offres affichées et met histo['offres'] à []."""

        r = demander_choix(
            titre="Changement des conditions de recherche",
            message="Repasser à la saisie des paramètres ? "
        )

        if not r:
            return

        self.list_offres = []

        if self.histo_id:
            self.sauver_offres_dans_histo()

        self.afficher_offres(self.list_offres)
        self.set_checkbox_on_off_sans_event(False)
        
        # Affichage du résumé des paramètres de la requête
        self.display_param_summary()
        
        
        self.checkbox_on_off.visible = False
        self.f.navigation_link_search_go.visible = True
        self.f.navigation_link_search_go.enabled = True
        self.button_daily_survey_creation.visible = False
        
    def button_del_before_modif_param(self, **event_args):
        """
        Vide l'affichage courant et les offres de la ligne d'historique.
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
            afficher_avertissement(
                "Offre introuvable.",
                titre="Information"
            )
            return

        r = demander_choix(
            titre="Suppression de l’offre",
            message="Effacer cette offre affichée ?"
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
            afficher_avertissement(
                "Impossible de sauvegarder : histo_id manquant.",
                titre="Erreur de sauvegarde"
            )
            return False

        try:
            with anvil.server.no_loading_indicator:
                result = anvil.server.call(
                    "update_histo_offres",
                    self.histo_id,
                    self.list_offres
                )
        except Exception as e:
            afficher_avertissement(
                f"Erreur pendant la sauvegarde des offres :\n\n{e}",
                titre="Erreur de sauvegarde"
            )
            return False

        if not result or not result.get("ok"):
            message = result.get("message") if result else "Erreur inconnue"
            afficher_avertissement(
                f"Erreur pendant la sauvegarde :\n\n{message}",
                titre="Erreur de sauvegarde"
            )
            return False

        self.list_offres = result.get("offres", self.list_offres)
        return True

    def valeur_int_pour_tri(self, valeur, defaut=0):
        """
        Convertit une valeur en entier pour le tri.
        """

        try:
            return int(valeur or defaut)
        except Exception:
            return defaut


    def date_iso_pour_tri(self, valeur):
        """
        Retourne une date triable au format YYYY-MM-DD.
        """

        if not valeur:
            return ""

        try:
            if isinstance(valeur, datetime):
                return valeur.date().isoformat()

            if isinstance(valeur, date):
                return valeur.isoformat()
        except Exception:
            pass

        try:
            texte = str(valeur).strip()

            if not texte:
                return ""

            texte = texte.split("T")[0]
            texte = texte.split(" ")[0]

            # Format ISO déjà correct
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texte):
                return texte

            # Format français DD/MM/YYYY
            if re.fullmatch(r"\d{2}/\d{2}/\d{4}", texte):
                jour, mois, annee = texte.split("/")
                return f"{annee}-{mois}-{jour}"

        except Exception:
            pass

        return ""


    def trier_offres_par_interet(self, offres):
        """
        Trie les offres selon les règles utilisateur :

        - si aucun mot OU n'a été saisi :
            tri par date de publication décroissante

        - si au moins un mot OU a été saisi :
            niveau 1 : taux de mots OU trouvés décroissant
            niveau 2 : date de publication décroissante
        """

        offres = list(offres or [])

        if not offres:
            return []

        avec_mots_ou = any(
            self.valeur_int_pour_tri(o.get("nb_mots_ou_total"), 0) > 0
            for o in offres
        )

        # Aucun mot OU : tri classique par date.
        if not avec_mots_ou:
            return sorted(
                offres,
                key=lambda o: self.date_iso_pour_tri(
                    o.get("date_publication")
                ),
                reverse=True
            )

        # Au moins un mot OU : tri par taux puis date.
        return sorted(
            offres,
            key=lambda o: (
                self.valeur_int_pour_tri(o.get("taux_mots_ou"), 0),
                self.date_iso_pour_tri(o.get("date_publication"))
            ),
            reverse=True
        )

    def afficher_offres(self, offres=None):
        """
        Réaffiche le repeating panel à partir de self.list_offres.
        """
    
        if offres is not None:
            self.list_offres = self.normaliser_liste_offres_vu(offres)
    
        nb = len(self.list_offres)
    
        # Important : remettre le tag après chaque réaffichage.
        # RowTemplate1 utilise les mots ET pour le bouton de vérification.
        self.repeating_panel_offres.tag.mots_et_saisis = self.get_mots_obligatoires_texte()
        
        items_affiches = []

        for index, offre in enumerate(self.list_offres, start=1):
            nouvelle_offre = dict(offre)
            nouvelle_offre["numero_offre"] = index
            nouvelle_offre["nb_offres_total"] = nb
            items_affiches.append(nouvelle_offre)
        
        self.repeating_panel_offres.items = items_affiches
    
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
    
        self.text_nb_offres.visible = False
        self.data_grid_1.visible = True
        self.column_panel_select.visible = True
        self.checkbox_on_off.visible = True
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

        try:
            self.checkbox_on_off.checked = bool(valeur)
        finally:
            self._ignore_checkbox_on_off_change = False

    # =========================================================================
    # Envoi mail
    # =========================================================================

    def button_selection_mailed_click(self, **event_args):
        """Envoi d'un mail contenant les offres cochées."""

    
        if not self.user:
            afficher_avertissement(
                "Vous devez être connecté pour recevoir les offres par mail.",
                titre="Connexion requise"
            )
            return
    
        email_user = self.user['email']

        if not email_user:
            afficher_information(
                "Aucune adresse e-mail n’est associée à votre compte.",
                titre="Adresse e-mail manquante"
            )
            return
    
        offres_selectionnees = self._get_offres_selectionnees_pour_mail()
    
        if not offres_selectionnees:
            afficher_information(
                "Aucune offre sélectionnée à envoyer par mail.",
                titre="Sélection requise"
            )
            return
    
        nb = len(offres_selectionnees)
    
        confirmation = demander_choix(
            titre="Confirmation de l’envoi",
            message=(
                f"... envoyer les {nb} offre(s) sélectionnée(s) à :\n\n"
                f"{email_user}\n\n"
                "Confirmer l’envoi ?"
            )
        )
    
        if not confirmation:
            return
    
        self.button_selection_mailed.enabled = False
        self.button_selection_mailed.text = "Envoi en cours..."
    
        try:
            result = anvil.server.call(
                "envoyer_mail_offres_selectionnees",
                offres_selectionnees,
                self._get_contexte_recherche_pour_mail()
            )
    
            if result and result.get("ok"):
                afficher_reussite(
                    f"Mail envoyé avec succès à {email_user}.\n\n"
                    f"{result.get('nb_offres', nb)} offre(s) envoyée(s)."
                )
            else:
                erreur = result.get("error") if isinstance(result, dict) else str(result)
                afficher_information(
                    f"Erreur pendant l’envoi du mail :\n\n{erreur}",
                    titre="Erreur d’envoi"
                )
    
        except Exception as e:
            afficher_information(
                f"Erreur pendant l’envoi du mail :\n\n{e}",
                titre="Erreur d’envoi"
            )
    
        finally:
            self.button_selection_mailed.enabled = True
            if self.context["screen_type"] == "phone":
                self.button_selection_mailed.text = "Mail"
            else:
                self.button_selection_mailed.text = (
                    "Envoi de la sélection"
                )

    def _get_contexte_recherche_pour_mail(self):
        """Prépare les infos de contexte pour le mail."""
    
        try:
            sources = self.multi_select_drop_down_platformes.selected
        except Exception:
            sources = []
    
        return {
            "mots_cles": self.text_box_mot_clef.text or "",
            "mots_ou": self.text_box_mot_ou.text or "",
            "mots_exclus": self.text_box_mots_exclus.text or "",
            "departements": self.text_box_departements.text or "",
            "nb_jours": self.text_box_nb_jours.text or "",
            "sources": sources,
        }

    def _get_offres_selectionnees_pour_mail(self):
        """
        Retourne une liste simple de dictionnaires sérialisables
        correspondant aux offres cliquées / vues.
        """
    
        champs_a_garder = [
            "titre",
            "acheteur",
            "nature",
            "procedure",
            "type_avis",
            "departement",
            "lieu",
            "date_publication",
            "date_limite_rep",
            "source",
            "reference",
            "resume_court",

            # Champs utiles pour le mail
            "description",
            "objet",
            "search_text",

            # Mots trouvés / intérêt déjà calculés dans search
            "mots_trouves",
            "mots_ou_trouves",
            "nb_mots_ou_total",
            "nb_mots_ou_trouves",
            "taux_mots_ou",
            "role_interet",

            # Liens
            "lien_source",
            "lien_app",
            "idweb",
            "vu",
        ]
    
        offres_selectionnees = []
    
        items = self.repeating_panel_offres.items or []
    
        for offre in items:
            # Ici on considère qu'une offre cliquée a vu == True
            if offre.get("vu") is True:
    
                offre_mail = {}
    
                for champ in champs_a_garder:
                    valeur = offre.get(champ)
    
                    # Sécurisation simple pour éviter d'envoyer des objets non sérialisables
                    if isinstance(valeur, (str, int, float, bool)) or valeur is None:
                        offre_mail[champ] = valeur
                    elif isinstance(valeur, list):
                        offre_mail[champ] = [str(x) for x in valeur]
                    else:
                        offre_mail[champ] = str(valeur)
    
                offres_selectionnees.append(offre_mail)
    
        return offres_selectionnees

    # =========================================================================
    # Recalcule visibilité du bouton mail
    # =========================================================================

    def recalculer_bouton_selection_mailed(self, sender=None, **event_args):
        au_moins_un_coche = any(
            bool(row.checkbox_vu.checked)
            for row in self.repeating_panel_offres.get_components()
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
        Construit une requête volontairement large pour les sources.

        Principe :
        - les plateformes servent seulement à récupérer un premier lot d'offres
        - le vrai filtrage ET / OU / intérêt est fait ensuite localement
        - on évite donc d'envoyer tous les mots ET aux plateformes, car cela peut
          bloquer une offre pertinente si une plateforme ne trouve pas un mot
          partiel comme ciment dans fibrociment.
        """

        mots_obligatoires = mots_obligatoires or []
        mots_ou = mots_ou or []

        # Cas normal : on envoie seulement les 3 premiers mots obligatoires.
        # Exemple : rénovation, toiture, facade, ciment
        # devient : rénovation et toiture et facade
        # puis le filtre local vérifie ensuite ciment dans fibrociment.
        if mots_obligatoires:
            mots_sources = mots_obligatoires[:3]
            return [" et ".join(mots_sources)]

        # Si aucun mot obligatoire, on envoie une requête OU large.
        if mots_ou:
            return [" ou ".join(mots_ou)]

        return []

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
    
        if len(mot_norm) <= 4:
            pattern = r"(?<![a-z0-9])" + re.escape(mot_norm) + r"(?![a-z0-9])"
            return re.search(pattern, texte_norm) is not None
    
        return mot_norm in texte_norm
    
    
    def offre_respecte_criteres_positifs(
        self,
        offre,
        mots_obligatoires,
        mots_ou
    ):
        """
        Règle :
        - avec des mots ET : tous doivent être présents ; les mots OU servent
          uniquement à mesurer le niveau d'intérêt ;
        - sans mot ET : au moins un mot OU doit être présent.
        """

        texte_norm = self.texte_offre_normalise(offre)

        if mots_obligatoires:
            return all(
                self.texte_contient_mot_filtre(texte_norm, mot)
                for mot in mots_obligatoires
            )

        if mots_ou:
            return any(
                self.texte_contient_mot_filtre(texte_norm, mot)
                for mot in mots_ou
            )

        return False

    def filtrer_offres_criteres_positifs(self, offres, mots_obligatoires, mots_ou):
        """
        Garde seulement les offres qui respectent les critères positifs.

        Règle :
        - avec mots ET : tous les mots ET doivent être présents ; les mots OU
          servent ensuite au niveau d'intérêt, y compris 0 %
        - sans mots ET : au moins un mot OU doit être présent
        """

        if not offres:
            return []

        offres_filtrees = []

        for offre in offres:
            if self.offre_respecte_criteres_positifs(offre, mots_obligatoires, mots_ou):
                offres_filtrees.append(offre)

        return offres_filtrees

    def trouver_mots_ou_dans_offre(self, offre, mots_ou):
        """
        Retourne la liste des mots OU trouvés dans une offre.
        Utilise la même logique de normalisation que le filtrage positif.
        """
    
        texte_norm = self.texte_offre_normalise(offre)
    
        mots_trouves = []
    
        for mot in mots_ou or []:
            if self.texte_contient_mot_filtre(texte_norm, mot):
                mots_trouves.append(mot)
    
        return mots_trouves
    
    
    def niveau_interet_mots_ou(self, nb_total, nb_trouves):
        """
        Détermine le niveau d'intérêt selon le pourcentage de mots OU trouvés.

        Règles :
        - aucun mot OU saisi : pas de niveau d'intérêt, tri par date
        - 0 %       : rouge pastel
        - 1-20 %    : orange pastel
        - 21-39 %   : jaune pastel
        - 40-59 %   : vert clair pastel
        - 60-79 %   : vert plus vif pastel
        - 80-99 %   : vert vif
        - 100 %     : vert très voyant
        """

        nb_total = int(nb_total or 0)
        nb_trouves = int(nb_trouves or 0)

        if nb_total == 0:
            return {
                "taux": 0,
                "rang": 0,
                "code": "sans_mots_ou",
                "libelle": "pas de mots facultatifs",
                "role": ""
            }

        taux = round((nb_trouves / nb_total) * 100)

        if taux == 0:
            return {
                "taux": taux,
                "rang": 0,
                "code": "interet_0",
                "libelle": "pas de mots facultatifs",
                "role": "bt-interet-0"
            }

        if taux <= 20:
            return {
                "taux": taux,
                "rang": 1,
                "code": "interet_20",
                "libelle": "",
                "role": "bt-interet-20"
            }

        if taux <= 39:
            return {
                "taux": taux,
                "rang": 2,
                "code": "interet_39",
                "libelle": "",
                "role": "bt-interet-39"
            }

        if taux <= 59:
            return {
                "taux": taux,
                "rang": 3,
                "code": "interet_59",
                "libelle": "",
                "role": "bt-interet-59"
            }

        if taux <= 79:
            return {
                "taux": taux,
                "rang": 4,
                "code": "interet_79",
                "libelle": "",
                "role": "bt-interet-79"
            }

        if taux < 100:
            return {
                "taux": taux,
                "rang": 5,
                "code": "interet_99",
                "libelle": "",
                "role": "bt-interet-99"
            }

        return {
            "taux": taux,
            "rang": 6,
            "code": "interet_100",
            "libelle": "",
            "role": "bt-interet-100"
        }

    def ajouter_correspondance_mots_ou(self, offres, mots_ou):
        """
        Ajoute dans chaque offre les informations de niveau d'intérêt :

        - mots_ou_trouves
        - nb_mots_ou_total
        - nb_mots_ou_trouves
        - taux_mots_ou
        - niveau_interet
        - libelle_interet
        - rang_interet
        - role_interet

        Si aucun mot OU n'est saisi, il n'y a pas de niveau d'intérêt :
        les offres seront triées par date.
        """

        mots_ou = mots_ou or []
        nb_total = len(mots_ou)

        offres_resultat = []

        for offre in offres or []:
            nouvelle_offre = dict(offre)

            mots_trouves = self.trouver_mots_ou_dans_offre(
                nouvelle_offre,
                mots_ou
            )

            nb_trouves = len(mots_trouves)

            infos_interet = self.niveau_interet_mots_ou(
                nb_total,
                nb_trouves
            )

            taux = infos_interet["taux"]

            nouvelle_offre["mots_ou_trouves"] = mots_trouves
            nouvelle_offre["nb_mots_ou_total"] = nb_total
            nouvelle_offre["nb_mots_ou_trouves"] = nb_trouves
            nouvelle_offre["taux_mots_ou"] = taux

            nouvelle_offre["niveau_interet"] = infos_interet["code"]
            nouvelle_offre["libelle_interet"] = infos_interet["libelle"]
            nouvelle_offre["rang_interet"] = infos_interet["rang"]
            nouvelle_offre["role_interet"] = infos_interet["role"]

            offres_resultat.append(nouvelle_offre)

        return offres_resultat

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
        if len(mot_norm) <= 4:
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

        base_app = self.base_app

        if not base_app:
            try:
                with anvil.server.no_loading_indicator:
                    base_app = anvil.server.call("get_variable_value", "code_app1")
                self.base_app = base_app
            except Exception as e:
                print("Impossible de récupérer code_app1 dans build_offres_list :", e)
                base_app = ""

        for item in resultats or []:
            uid = self._make_offer_uid(item)

            if dedoublonner and uid in vus:
                continue

            vus.add(uid)

            source = self._to_str(item.get("source"))
            idweb = self._to_str(item.get("idweb"))
            lien_app = f"{base_app}/analyse_offre?source={source}&idweb={idweb}"

            offre = {
                "idweb": self._to_str(item.get("idweb")),
                "source": self._to_str(item.get("source")),
                "source_originale": self._to_str(item.get("source_originale")),
                "sources_detectees": list(
                    item.get("sources_detectees") or []
                ),
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
                "resume_court": self._to_str(item.get("resume_court")),

                # Clé indispensable pour la sélection des offres
                "vu": False,
            }

            offres.append(offre)

        return offres

    # =========================================================================
    # Gestion des mots OU
    # =========================================================================
    
    def get_mots_ou(self):
        """
        Retourne les mots OU depuis le nouveau champ text_box_mot_ou.
        """
    
        return self.extraire_liste_mots_saisie(
            self.text_box_mot_ou.text or ""
        )
    
    
    def get_mots_ou_texte(self):
        """
        Retourne les mots OU sous forme texte pour affichage et sauvegarde.
        """
    
        return ", ".join(self.get_mots_ou())


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
        



    def text_box_mot_clef_change(self, **event_args):
        """This method is called when the text in this component is edited."""
        self.maj_bouton_recherche_visible()

   


       

    def text_box_mot_ou_pressed_enter(self, **event_args):
        if self._recherche_en_cours is True:
            Notification("Recherche déjà en cours...", timeout=2).show()
            return
        self.lancer_recherche()

    def text_box_mot_ou_change(self, **event_args):
        self.maj_bouton_recherche_visible()

    def text_box_mots_exclus_pressed_enter(self, **event_args):
        if self._recherche_en_cours is True:
            Notification("Recherche déjà en cours...", timeout=2).show()
            return
        self.lancer_recherche()


    def text_box_mots_exclus_change(self, **event_args):
        self.maj_bouton_recherche_visible()
    


    def timer_recherche_progress_tick(self, **event_args):
        """
        Suit la Background Task.
        Le bouton reste désactivé jusqu'à la fin complète :
        recherche + filtrage + classement + sauvegarde.
        """
        
        if self._annulation_recherche_demandee:
            self.timer_recherche_progress.interval = 0
            self.task_recherche = None
            self._recherche_en_cours = False
            return
            
        if self.task_recherche is None:
            self.deverrouiller_recherche(cacher_bouton=False)
            return
    
        try:
            with anvil.server.no_loading_indicator:
                state = self.task_recherche.get_state() or {}
                task_completed = self.task_recherche.is_completed()
        except Exception as e:
            print(f"Impossible de lire la progression : {e}")
    
            self.afficher_progression_recherche(
                ligne_1="⚠️ Erreur de lecture de la progression",
                ligne_2="Le bouton Rechercher est à nouveau disponible",
                etat="error",
                progress_global=0,
                progress_source=0,
                afficher_jauges=False
            )
    
            self.deverrouiller_recherche(cacher_bouton=False)
            afficher_information(
                f"Impossible de lire la progression :\n\n{e}",
                titre="Erreur de progression"
            )
            return
    
        progress = state.get("progress", 0)
        source_progress = state.get("source_progress", 0)
        source_en_cours = state.get("source_en_cours", "")
        source_current = state.get("source_current", None)
        source_total = state.get("source_total", None)
    
        self.afficher_progression_recherche(
            ligne_1="🔎 Recherche en cours",
            ligne_2="",
            etat="running",
            progress_global=progress,
            progress_source=source_progress,
            source_nom=source_en_cours,
            source_current=source_current,
            source_total=source_total,
            afficher_jauges=True
        )
    
        if not task_completed:
            return
    
        # La tâche Uplink est terminée.
        # On arrête le timer, mais on NE réactive PAS encore le bouton.
        # Il reste le filtrage, le classement et la sauvegarde.
        self.timer_recherche_progress.interval = 0
    
        try:
            with anvil.server.no_loading_indicator:
                result = self.task_recherche.get_return_value()
    
        except Exception as e:
            print(f"Erreur pendant la tâche background : {e}")
    
            self.afficher_progression_recherche(
                ligne_1="⚠️ Erreur pendant la recherche",
                ligne_2="Le bouton Rechercher est à nouveau disponible",
                etat="error",
                progress_global=0,
                progress_source=0,
                afficher_jauges=False
            )
    
            self.deverrouiller_recherche(cacher_bouton=False)
            afficher_information(
                f"Erreur pendant la recherche :\n\n{e}",
                titre="Erreur de recherche"
            )
            return
    
        if not result:
            self.afficher_progression_recherche(
                ligne_1="⚠️ Recherche terminée, mais résultat vide",
                ligne_2="0 offre récupérée",
                etat="error",
                progress_global=0,
                progress_source=0,
                afficher_jauges=False
            )
    
            self.deverrouiller_recherche(cacher_bouton=False)
            afficher_information(
                "La recherche est terminée, mais aucun résultat "
                "n’a été retourné.",
                titre="Résultat de la recherche"
            )
            return
    
        if not isinstance(result, dict):
            self.afficher_progression_recherche(
                ligne_1="⚠️ Réponse serveur incorrecte",
                ligne_2="Le résultat reçu n’est pas exploitable",
                etat="error",
                progress_global=0,
                progress_source=0,
                afficher_jauges=False
            )

            self.deverrouiller_recherche(cacher_bouton=False)
            afficher_information(
                "Le serveur n’a pas renvoyé le dictionnaire attendu.",
                titre="Erreur de recherche"
            )
            return

        errors = result.get("errors", [])
    
        if errors:
            print("Erreurs partielles pendant la recherche :", errors)
    
        offres = result.get("offres", [])

        if result.get("recherche_limitee"):
            message_limite = result.get("message_limite") or (
                "Recherche trop large : une partie seulement des offres est affichée."
            )
            afficher_information(
                message_limite,
                titre="Recherche limitée"
            )
            print("⚠️ Recherche limitée :", message_limite)
    
        self.afficher_progression_recherche(
            ligne_1="🔎 Préparation des résultats",
            ligne_2="Analyse et classement des offres en cours...",
            etat="running",
            progress_global=100,
            progress_source=100,
            source_nom="Traitement final",
            source_current=None,
            source_total=None,
            afficher_jauges=True
        )
    
        try:
            self.traiter_offres_recuperees_apres_background(offres)
    
        except Exception as e:
            print(f"Erreur pendant le traitement final des offres : {e}")
    
            self.afficher_progression_recherche(
                ligne_1="⚠️ Erreur pendant le traitement final",
                ligne_2="Le bouton Rechercher est à nouveau disponible",
                etat="error",
                progress_global=0,
                progress_source=0,
                afficher_jauges=False
            )
    
            self.deverrouiller_recherche(cacher_bouton=False)
            afficher_information(
                f"Erreur pendant le traitement final des offres :\n\n{e}",
                titre="Erreur de traitement"
            )
            return

    def maj_bouton_recherche_visible(self):
        """
        Active le bouton de recherche si au moins un critère positif existe :
        - mots obligatoires
        - ou mots OU
        """
    
        has_mots_obligatoires = bool((self.text_box_mot_clef.text or "").strip())
        has_mots_ou = bool((self.text_box_mot_ou.text or "").strip())
    
        actif = has_mots_obligatoires or has_mots_ou
    
        try:
            self.f.navigation_link_search_go.visible = True
            self.f.navigation_link_search_go.enabled = actif and not self._recherche_en_cours
        except Exception as e:
            print("Erreur maj navigation_link_search_go :", e)


    def format_nb_offres(self, nb, suffixe_singulier="", suffixe_pluriel=""):
        nb = int(nb or 0)

        if nb > 1:
            return f"{nb} offres {suffixe_pluriel}".strip()
    
        return f"{nb} offre {suffixe_singulier}".strip()


    def libelle_jauge_source(self, source_nom):
        """
        Texte affiché dans la jauge verte.
        """

        source = str(source_nom or "").strip().upper()

        if source == "TED":
            return "Lecture des offres TED"

        if source == "BOAMP":
            return "Lecture des offres BOAMP"

        if source == "AWS":
            return "Lecture des offres AWS"

        if source == "FUSION":
            return "Préparation des résultats"

        if source == "TERMINÉ":
            return "Recherche terminée"

        if source == "TRAITEMENT FINAL":
            return "Analyse des offres"

        if source:
            return f"Lecture des offres {source}"

        return "Lecture des offres"
    
    def afficher_progression_recherche(
        self,
        ligne_1="",
        ligne_2="",
        etat="running",
        progress_global=0,
        progress_source=0,
        source_nom="",
        source_current=None,
        source_total=None,
        afficher_jauges=True
    ):
        """
        Affiche la progression sur deux lignes
        + deux jauges.
        """
    
        if etat == "success":
            role = "progress-search-box-success"
        elif etat == "error":
            role = "progress-search-box-error"
        else:
            role = "progress-search-box"
    
        try:
            if not self.column_panel_progress_recherche.visible:
                self.column_panel_progress_recherche.visible = True
    
            if self._last_progress_role != role:
                self.column_panel_progress_recherche.role = role
                self._last_progress_role = role
        except Exception:
            pass
    
        if not self.label_progress_recherche.visible:
            self.label_progress_recherche.visible = True
    
        texte = ligne_1 or "Recherche en cours..."
    
        if ligne_2:
            texte = f"{texte}\n{ligne_2}"
    
        if self.label_progress_recherche.text != texte:
            self.label_progress_recherche.text = texte
    
        if not afficher_jauges:
            if self.label_jauge_globale.visible:
                self.label_jauge_globale.visible = False
            if self.label_jauge_source.visible:
                self.label_jauge_source.visible = False
            return
    
        if not self.label_jauge_globale.visible:
            self.label_jauge_globale.visible = True
        if not self.label_jauge_source.visible:
            self.label_jauge_source.visible = True
    
        try:
            progress_global = int(progress_global or 0)
        except Exception:
            progress_global = 0
    
        try:
            progress_source = int(progress_source or 0)
        except Exception:
            progress_source = 0
    
        progress_global = max(0, min(100, progress_global))
        progress_source = max(0, min(100, progress_source))
    
        texte_global = f"{progress_global} %"
    
        source_nom = str(source_nom or "").strip()
        libelle_source = self.libelle_jauge_source(source_nom)
        
        if source_current is not None and source_total:
            texte_source = f"{libelle_source} — {source_current}/{source_total}"
        else:
            texte_source = f"{libelle_source} — {progress_source} %"
            
        if self.label_jauge_globale.text != texte_global:
            self.label_jauge_globale.text = texte_global
    
        if self.label_jauge_source.text != texte_source:
            self.label_jauge_source.text = texte_source
    
        self.regler_jauge(self.label_jauge_globale, progress_global, "global")
        self.regler_jauge(self.label_jauge_source, progress_source, "source")
    
    
    def regler_jauge(self, composant, pourcentage, nom=""):
        """
        Met à jour une jauge CSS via la variable --progress-value.
        La jauge se remplit de gauche à droite.
        """
    
        try:
            p = int(pourcentage or 0)
        except Exception:
            p = 0
    
        p = max(0, min(100, p))
    
        if nom == "global":
            if self._last_progress_global == p:
                return
            self._last_progress_global = p
    
        elif nom == "source":
            if self._last_progress_source == p:
                return
            self._last_progress_source = p
    
        try:
            node = get_dom_node(composant)
            node.style.setProperty("--progress-value", f"{p}%")
        except Exception as e:
            print("Erreur réglage jauge :", e)

    def go_up(self, **event_args):
        self.scroll_into_view(smooth=True, align="start")

    def go_down(self, **event_args):
        self.scroll_into_view(smooth=True, align="end")


    def button_daily_survey_creation_click(self, **event_args):
        """
        Enregistre les critères de la recherche actuelle comme veille quotidienne.
        """
    
        if self._recherche_en_cours:
            Notification(
                "Attendez la fin de la recherche.",
                timeout=3
            ).show()
            return
    
        if not self.list_offres:
            self.button_daily_survey_creation.visible = False
    
            afficher_avertissement(
                "La veille quotidienne peut être créée uniquement "
                "après une recherche ayant trouvé au moins une offre.",
                titre="Veille quotidienne"
            )
            return
    
        try:
            sources = list(
                self.multi_select_drop_down_platformes.selected or []
            )
        except Exception:
            sources = []
    
        if not sources:
            afficher_avertissement(
                "Aucune plateforme n’est sélectionnée.",
                titre="Plateforme requise"
            )
            return
    
        confirmation = demander_choix(
            titre="Création d’une veille quotidienne",
            message=(
                " ... créer une veille quotidienne à partir des paramètres "
                "de cette recherche ?\n\n"
                "     Cette veille vérifiera <u><strong>chaque jour</strong></u> toutes les offres "
                "qui ont éventuellemnt été publiées la veille.\n\n"
                "Dans le cas où une ou plusieurs offres répondent aux critères, \n"
                "  un mail vous sera envoyé ! \n\n"
                "<span style=\"background-color:#FFF1A8;\">La première veille est offerte.</span>"
            ),
            autoriser_html=True
        )

        if confirmation is not True:
            return
    
        texte_bouton_initial = self.button_daily_survey_creation.text

        self.button_daily_survey_creation.enabled = False
        self.button_daily_survey_creation.text = (
            "Création de la veille..."
        )
        try:
            result = anvil.server.call(
                "enregistrer_daily_survey",
                sources=sources,
                mots_cles=self.get_mots_obligatoires_texte(),
                mots_ou=self.get_mots_ou_texte(),
                mots_exclus=self.get_mots_exclus_texte(),
                departements=(
                    self.text_box_departements.text or ""
                )
            )
    
        except Exception as e:
            print(
                "Erreur création de la veille quotidienne :",
                repr(e)
            )
    
            self.button_daily_survey_creation.enabled = True
            self.button_daily_survey_creation.text = texte_bouton_initial

            afficher_avertissement(
                "Impossible de créer la veille quotidienne.\n\n"
                f"{e}",
                titre="Erreur de création"
            )
            return
    
        if not isinstance(result, dict):
            self.button_daily_survey_creation.enabled = True
            self.button_daily_survey_creation.text = texte_bouton_initial

            afficher_avertissement(
                "Le serveur n’a pas renvoyé la réponse attendue.",
                titre="Erreur de création"
            )
            return
    
        if not result.get("ok"):
            self.button_daily_survey_creation.enabled = True
            self.button_daily_survey_creation.text = texte_bouton_initial

            afficher_avertissement(
                result.get("message")
                or "La veille quotidienne n’a pas pu être créée.",
                titre="Nouvelle veille non crée."
            )
            return
    
        # Ce traitement convient aux trois statuts :
        # creee, deja_active et reactivee.
        self.button_daily_survey_creation.text = (
            "Veille quotidienne active"
        )
        self.button_daily_survey_creation.background_color = "red"
        self.button_daily_survey_creation.foreground_color = "yellow"
        self.button_daily_survey_creation.enabled = False
    
        afficher_reussite(
            result.get("message")
            or "La veille quotidienne est maintenant active."
        )

