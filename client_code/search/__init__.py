from ._anvil_designer import searchTemplate
from anvil import *
import anvil.server
from .. import Time
from datetime import date, datetime
import re
from anvil.js import get_dom_node, window    # pour écouteur JS sur le DropDown et conter tps d'éxéction
from .. import Context_ecran

# Pour entrer le titre des repeating panel dans le cadre
import anvil.js  
from ..Titre_RepeatingPanel import definir_titre_repeating_panel

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

        self.data_grid_2.rows_per_page = 5

        t = window.performance.now()
        self.init_components(**properties)
        self.initialiser_selecteur_cpv()
        afficher_temps("init_components", t)

        # ================================================================
        # Personnalisation MultiSelect plateformes
        # ================================================================

        # Boutons en français
        self.multi_select_drop_down_platformes._dd.select_all_btn.text = "Tout sélectionner"
        self.multi_select_drop_down_platformes._dd.deselect_all_btn.text = "Tout désélectionner"

        # Couleurs boutons
        self.multi_select_drop_down_platformes._dd.select_all_btn.foreground = "theme:Dark"
        self.multi_select_drop_down_platformes._dd.deselect_all_btn.foreground = "theme:Dark"
        self.multi_select_drop_down_platformes._dd.select_all_btn.background = "theme:Light Green"
        self.multi_select_drop_down_platformes._dd.deselect_all_btn.background = "theme:Light Green"

        # ================================================================
        # Détection du type d'écran
        # ================================================================

        t = window.performance.now()
        self.context = Context_ecran.context_screen()

        if self.context["screen_type"] == "phone":

            self.button_selection_mailed.text = "Mail"

            # Largeur du menu ouvert du MultiSelect
            popover = self.multi_select_drop_down_platformes.popover
            popover.dom_popover.style.width = "calc(100vw - 10px)"
            popover.dom_popover.style.maxWidth = "calc(100vw - 10px)"

            # Le contenu interne prend toute la largeur disponible
            self.multi_select_drop_down_platformes._dd._dom_node.style.width = "100%"
            self.multi_select_drop_down_platformes._dd._dom_node.style.minWidth = "100%"

            # Afficher cadré à gauche du résumé des param
            self.text_param_summary.align = "left"
    
        else:
    
            self.button_selection_mailed.text = "Envoi de la sélection"
    
            # Largeur du menu ouvert du MultiSelect
            popover = self.multi_select_drop_down_platformes.popover
            popover.dom_popover.style.width = "calc(40vw - 50px)"
            popover.dom_popover.style.maxWidth = "calc(40vw - 50px)"
    
            self.multi_select_drop_down_platformes._dd._dom_node.style.width = "60%"
            self.multi_select_drop_down_platformes._dd._dom_node.style.minWidth = "60%"
    
        # afficher_temps("Context_ecran et adaptation affichage", t)
    
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
    
        self.column_panel_progress_recherche.role = "progress-search-box"
        self.label_jauge_globale.role = "progress-gauge-global"
    
        self.column_panel_progress_recherche.visible = False
    
        afficher_temps("initialisation affichage progression", t)
    
        # ================================================================
        # Variables internes
        # ================================================================
    
        t = window.performance.now()
    
        self.user = None
        self.histo_id = None
        self.revision_recherche = None
        self._offres_correspondent_histo = False
        self.list_offres = []
    
        self.timer_recherche_progress.interval = 0
    
        self.task_recherche = None
        self._ctx_recherche = {}
        self._recherche_en_cours = False
        self._nouvelle_recherche_cpv_en_attente = False
        self._annulation_recherche_demandee = False
    
        self.base_app = ""
    
        self._last_progress_global = None
        self._last_progress_source = None
        self._last_progress_role = None
    
        self.label_jauge_globale.visible = False
        self.text_param_summary.visible = False
    
        self.button_daily_survey_creation.visible = False
        self.button_daily_survey_creation.enabled = True
        self.button_creer_veille_cpv.text = "Créer une veille quotidienne"
    
        # Évite les événements indésirables lors d'une modification par code
        self._ignore_checkbox_on_off_change = False
    
        afficher_temps("initialisation variables internes", t)
    
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
    
        afficher_temps("installation handlers repeating_panel_offres", t)
    
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
            print("Erreur pendant l'initialisation de search :", e)
    
            afficher_avertissement(
                "Impossible d'initialiser la recherche.\n\n"
                f"{e}",
                titre="Erreur d’initialisation"
            )
            return
    
        afficher_temps("appel initialiser_form_search", t)
    
        if not isinstance(donnees_initiales, dict):
            afficher_avertissement(
                "Le serveur n'a pas renvoyé les données d'initialisation attendues.",
                titre="Erreur d’initialisation"
            )
            return
    
        # ================================================================
        # Utilisateur et base_app
        # ================================================================
    
        self.user = donnees_initiales.get("user")
        self.base_app = donnees_initiales.get("base_app") or ""
    
        if not self.user:
            afficher_avertissement(
                "Vous n'êtes pas connecté.",
                titre="Connexion requise"
            )
            return
    
        # ================================================================
        # Configuration de la DropDown plateformes
        # ================================================================
    
        t = window.performance.now()
    
        plateformes = donnees_initiales.get("plateformes") or []
    
        # ------------------------------------------------------------
        # key   = texte affiché dans la DropDown
        # value = ID utilisé par le programme
        # ------------------------------------------------------------
    
        liste_items = []
        liste_ids_plateformes = []
    
        for plateforme in plateformes:
    
            plateforme_id = plateforme["id"]
            texte_affiche = plateforme["drop_down_display"] or plateforme_id
    
            item = {
                "key": texte_affiche,
                "value": plateforme_id
            }
    
            liste_items.append(item)
            liste_ids_plateformes.append(plateforme_id)
    
        # Configuration du composant
        self.multi_select_drop_down_platformes.multiple = True
        self.multi_select_drop_down_platformes.enable_filtering = False
        self.multi_select_drop_down_platformes.enable_select_all = True
        self.multi_select_drop_down_platformes.items = liste_items
    
        self.multi_select_drop_down_platformes.placeholder = "Sélectionnez les plateformes"
        self.multi_select_drop_down_platformes.width = "100%"
        self.multi_select_drop_down_platformes.background = "#3CD9ED"
    
        # ------------------------------------------------------------
        # Texte affiché quand la DropDown est fermée :
        # AWS, BOAMP, TED...
        # ------------------------------------------------------------

        def format_selected_text(count, total):
    
            ids_selectionnes = self.multi_select_drop_down_platformes.selected or []
            textes = []
    
            for plateforme_id in ids_selectionnes:
                textes.append(str(plateforme_id))
    
            return ", ".join(textes)
    
        self.multi_select_drop_down_platformes.format_selected_text = format_selected_text
    
        afficher_temps("configuration plateformes", t)
    
        # ================================================================
        # Dernière recherche
        # ================================================================
    
        t = window.performance.now()
    
        derniere_ligne = donnees_initiales.get("histo")
    
        if derniere_ligne is None:
    
            # Nouvel utilisateur : toutes les plateformes sélectionnées
            self.multi_select_drop_down_platformes.selected = liste_ids_plateformes
    
            self.text_box_mots_obligatoires_cpv.text = "Formation"
            self.text_box_mot_ou.text = "sst, mac, psc, pse1, pse2, aipr, habilitation"
            self.text_box_mots_exclus.text = "Information, Déformation"
            self.text_box_nb_jours.text = "30"
            self.text_box_departements.text = None
    
            self.histo_id = None
            self.list_offres = []
    
        else:
    
            self.histo_id = derniere_ligne.get("histo_id")
    
            self.text_box_mots_obligatoires_cpv.text = derniere_ligne.get("mots_cles") or ""
            self.text_box_mot_ou.text = derniere_ligne.get("mots_ou") or ""
            self.text_box_mots_exclus.text = derniere_ligne.get("mots_exclus") or ""
            self.text_box_nb_jours.text = derniere_ligne.get("nb_jours") or "30"
            self.text_box_departements.text = derniere_ligne.get("departements")
    
            sources = derniere_ligne.get("sources")
    
            if sources is not None:
                self.multi_select_drop_down_platformes.selected = sources
            else:
                self.multi_select_drop_down_platformes.selected = liste_ids_plateformes
    
            self.revision_recherche = derniere_ligne["revision_recherche"]
            mode_recherche = derniere_ligne["mode_recherche"]

            if mode_recherche == "cpv":
                self.cpv_selectionnes = [
                    dict(prestation)
                    for prestation in derniere_ligne["prestations_cpv"]
                ]
                self._ctx_recherche = {
                    "mode_recherche": "cpv",
                    "cpv_selectionnes": list(derniere_ligne["cpv_selectionnes"]),
                    "prestations_cpv": [
                        dict(prestation)
                        for prestation in self.cpv_selectionnes
                    ],
                    "sources": list(derniere_ligne["sources"]),
                    "departements": self.decouper_saisie_recherche_cpv(
                        derniere_ligne["departements"]
                    ),
                    "filtre_jours": int(derniere_ligne["nb_jours"]),
                    "mots_obligatoires": self.decouper_saisie_recherche_cpv(
                        derniere_ligne["mots_cles"]
                    ),
                    "mots_ou": self.decouper_saisie_recherche_cpv(
                        derniere_ligne["mots_ou"]
                    ),
                    "mots_exclus": self.decouper_saisie_recherche_cpv(
                        derniere_ligne["mots_exclus"]
                    )
                }
            elif mode_recherche == "classique":
                self.cpv_selectionnes = []
                self._ctx_recherche = {
                    "mode_recherche": "classique",
                    "mots_obligatoires": self.extraire_liste_mots_saisie(
                        derniere_ligne["mots_cles"]
                    ),
                    "mots_ou": self.extraire_liste_mots_saisie(
                        derniere_ligne["mots_ou"]
                    ),
                    "mots_exclus": self.extraire_liste_mots_saisie(
                        derniere_ligne["mots_exclus"]
                    ),
                    "periode": int(derniere_ligne["nb_jours"]),
                    "selected_platformes": list(derniere_ligne["sources"]),
                    "departements": [
                        departement.strip()
                        for departement in derniere_ligne["departements"].split(",")
                        if departement.strip()
                    ]
                }
            else:
                raise ValueError("Mode de recherche sauvegardé invalide.")

            self.rafraichir_cpv_selectionnes()

        # ================================================================
        # Offres uniquement pour origine == "check"
        # ================================================================
    
        if inclure_offres and derniere_ligne is not None:
            t_offres = window.performance.now()

            # Les offres sauvegardées sont déjà finales.
            # Conserver leur ordre et leurs informations métier.
            self.list_offres = self.normaliser_liste_offres_vu(
                derniere_ligne.get("offres") or []
            )

            afficher_temps("chargement offres mode check", t_offres)
        else:
            self.list_offres = []

        # En ouverture normale, les offres sauvegardées ne sont pas chargées.
        self._offres_correspondent_histo = (
            inclure_offres and derniere_ligne is not None
        )

        afficher_temps("application dernière recherche", t)
    
        # ================================================================
        # Ouverture normale depuis le Menu
        # ================================================================
    
        t = window.performance.now()
    
        if origine == "":
            self.column_panel_params.visible = True
            self.maj_bouton_recherche_visible()
    
        afficher_temps("traitement origine normale", t)
    
        # ================================================================
        # Ouverture en mode vérification
        # ================================================================
    
        t = window.performance.now()
    
        if origine == "check":
    
            self.column_panel_params.visible = False
    
            if mk != "":
                self.text_box_mots_obligatoires_cpv.text = mk
    
            self.set_checkbox_on_off_sans_event(bool(checkbox_on_off))
    
            if bt_mail_visible is True:
                self.button_selection_mailed.visible = True
    
            if derniere_ligne is not None:
                self.afficher_offres(self.list_offres)
            else:
                self.column_panel_select.visible = False
    
            self.f.navigation_link_search_go.visible = False
    
        afficher_temps("traitement origine check", t)
    
        # ================================================================
        # Temps total
        # ================================================================
    
        self.actualiser_bouton_veille_cpv()
        afficher_temps("TOTAL __init__", t_total)

        # ================================================================
        # Définition du titre des repeating panels (à partir du module definir_titre_repeating_panel)
        # ================================================================
        #definir_titre_repeating_panel(self.repeating_panel_cpv_selectionnes, "Secteur sélectionné :", icone="factory")
        definir_titre_repeating_panel(self.repeating_panel_suggestions_cpv, "Secteurs à sélectionner :")

    # Pour Initialiser le curseur sur text_box_recherche_cpv
    @handle("", "show")
    def form_show(self, **event_args):
        """This method is called when the form is shown on the page"""
        self.text_box_recherche_cpv.focus()
        

    def verrouiller_recherche(self):
        """
        Verrouille l'interface pendant une recherche.
        Empêche un double clic ou un nouveau lancement.
        """

        self._recherche_en_cours = True
        self.actualiser_bouton_veille_cpv()

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
            self.text_box_mots_obligatoires_cpv.enabled = True
            self.text_box_mots_exclus.enabled = True
            self.text_box_nb_jours.enabled = True
            self.text_box_departements.enabled = True
            self.multi_select_drop_down_platformes.enabled = True
            self.text_box_mot_ou.enabled = True
        except Exception as e:
            print("Erreur déverrouillage UI :", e)

        self.actualiser_bouton_veille_cpv()

    def lire_statut_tache_recherche(self, task):
        """Lit le statut serveur ; les erreurs remontent à l'appelant."""
        with anvil.server.no_loading_indicator:
            return anvil.server.call("statut_tache_recherche", task)

    def annuler_recherche_depuis_menu(self):
        """Demande l'arrêt et conserve la Task jusqu'à confirmation.

        Retour : dict avec ok=True seulement si aucune Task ne reste
        à suivre. Les erreurs techniques remontent à Menu.
        """
        print("Demande d'annulation de la recherche depuis Menu")

        self._annulation_recherche_demandee = True
        self.timer_recherche_progress.interval = 0
        task = self.task_recherche

        if task is None:
            self.deverrouiller_recherche(cacher_bouton=False)
            return {
                "ok": True,
                "message": "Aucune recherche en cours"
            }

        self._recherche_en_cours = True

        try:
            with anvil.server.no_loading_indicator:
                result = anvil.server.call("task_killer", task)

            print("Résultat task_killer :", result)

            if not isinstance(result, dict):
                raise ValueError("Réponse de task_killer invalide.")

            if result.get("ok") is not True:
                return {
                    "ok": False,
                    "message": (
                        "Annulation non confirmée. "
                        "La référence est conservée ; vous pouvez réessayer."
                    )
                }

            # Vérifier aussi après kill_requested :
            # la réponse à la demande d'arrêt ne suffit pas.
            statut = self.lire_statut_tache_recherche(task)

            if statut not in ("completed", "failed", "killed"):
                return {
                    "ok": False,
                    "status": statut,
                    "message": (
                        "La recherche est encore en cours d'arrêt.  "
                        "Réessayez dans quelques instants."
                    )
                }

            self.deverrouiller_recherche(cacher_bouton=False)
            self.afficher_progression_recherche(
                ligne_1="⛔ Recherche arrêtée",
                ligne_2="Retour au menu.",
                etat="error",
                progress_global=0,
                progress_source=0,
                afficher_jauges=False
            )
            return {
                "ok": True,
                "status": statut,
                "message": "Terminaison confirmée par Anvil"
            }

        finally:
            # Si l'arrêt n'est pas confirmé, conserver la référence
            # et reprendre les vérifications, même après une exception.
            if self.task_recherche is task:
                self.timer_recherche_progress.interval = 1

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

        if bool(self.cpv_selectionnes):
            self.lancer_recherche_offres_cpv()
            return

        # --- Lecture des champs ---
        mots_obligatoires_texte = self.text_box_mots_obligatoires_cpv.text or ""
        mots_ou_texte = self.text_box_mot_ou.text or ""
        mots_exclus_texte = self.text_box_mots_exclus.text or ""
        deps_texte = str(self.text_box_departements.text or "")

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
            self.text_box_mots_obligatoires_cpv.focus()
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

        # Figer les critères du lancement pour le traitement, l'historique et le résumé.
        self._ctx_recherche = {
            "mode_recherche": "classique",
            "cpv_selectionnes": [],
            "mots_obligatoires": list(mots_obligatoires),
            "mots_ou": list(mots_ou),
            "mots_exclus": list(mots_exclus),
            "periode": periode,
            "selected_platformes": list(selected_platformes),
            "departements": list(depts),
        }

        self._offres_correspondent_histo = False
        self._annulation_recherche_demandee = False
        task_recue = None
        erreur_lancement = None

        try:
            self.verrouiller_recherche()

            try:
                with anvil.server.no_loading_indicator:
                    task_recue = anvil.server.call(
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
                    self.task_recherche = task_recue

            except (
                anvil.server.AppOfflineError,
                anvil.server.SessionExpiredError,
                anvil.server.UplinkDisconnectedError,
                anvil.server.TimeoutError,
                anvil.server.RuntimeUnavailableError,
                anvil.server.NoServerFunctionError,
            ) as erreur:
                # Présenter les échecs Anvil attendus sans masquer
                # les erreurs de programmation inattendues.
                if task_recue is not None:
                    raise

                erreur_lancement = erreur
                print(
                    "Erreur au lancement de la recherche background sur Pi5 :",
                    erreur
                )

            if erreur_lancement is None:
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
                self.bloc_selecteur_cpv_complet.visible = False

        finally:
            if task_recue is not None:
                # Préserver la référence reçue par ce lancement.
                self.task_recherche = task_recue
                self.timer_recherche_progress.interval = 1
            else:
                self.deverrouiller_recherche(cacher_bouton=False)

        if erreur_lancement is not None:
            # L'interface est déjà déverrouillée avant le message.
            self.afficher_progression_recherche(
                ligne_1="⚠️ Erreur au lancement de la recherche",
                ligne_2=str(erreur_lancement),
                etat="error",
                progress_global=0,
                progress_source=0,
                afficher_jauges=False
            )
            afficher_avertissement(
                "Erreur pendant le lancement de la recherche :\n\n"
                f"{erreur_lancement}",
                titre="Erreur de recherche"
            )

        return

    def decouper_saisie_recherche_cpv(self, saisie):
        """Adapte une saisie str en list[str] pour la frontière Uplink.

        Sépare uniquement virgules, points-virgules et retours à la ligne.
        Retourne les expressions non vides, sans déduplication, matching,
        changement de casse ou découpage des mots de liaison.
        """
        expressions = []
        for fragment in re.split(r"[,;\r\n]+", saisie or ""):
            expression = fragment.strip()
            if expression:
                expressions.append(expression)
        return expressions

    def preparer_criteres_recherche_cpv(self):
        """Collecte les critères manuels CPV sans validation métier officielle.

        Aucun paramètre. Retour : dict d'arguments pour le callable.
        Lève ValueError si CPV/sources absents ou période non entière.
        La période conserve les bornes manuelles 1 à 365 jours.
        """
        if not self.cpv_selectionnes:
            raise ValueError("Sélectionnez au moins une prestation CPV.")
        sources = list(self.multi_select_drop_down_platformes.selected or [])
        if not sources:
            raise ValueError("Sélectionnez au moins une plateforme.")
        try:
            periode = int(str(self.text_box_nb_jours.text).strip())
        except (ValueError, TypeError):
            raise ValueError("Le nombre de jours doit être un nombre entier.")
        periode = max(1, min(periode, 365))
        self.text_box_nb_jours.text = str(periode)
        codes_cpv = []
        for cpv_selectionne in self.cpv_selectionnes:
            codes_cpv.append(cpv_selectionne["code"])
        return {
            "cpv_selectionnes": codes_cpv,
            "departements": self.decouper_saisie_recherche_cpv(self.text_box_departements.text),
            "filtre_jours": periode,
            "sources": sources,
            "mots_obligatoires": self.decouper_saisie_recherche_cpv(self.text_box_mots_obligatoires_cpv.text),
            "mots_ou": self.decouper_saisie_recherche_cpv(self.text_box_mot_ou.text),
            "mots_exclus": self.decouper_saisie_recherche_cpv(self.text_box_mots_exclus.text),
        }

    def lancer_recherche_offres_cpv(self):
        """Lance la tâche CPV avec un instantané indépendant des composants.

        Aucun paramètre. Retour : None. Les erreurs de saisie sont présentées ;
        les exceptions techniques sont propagées après déverrouillage.
        Aucun appel d'historique ou de sauvegarde de veille.
        """
        try:
            criteres = self.preparer_criteres_recherche_cpv()
        except ValueError as erreur:
            afficher_avertissement(str(erreur), titre="Recherche CPV")
            return

        contexte_recherche: dict = {"mode_recherche": "cpv"}
        self._ctx_recherche = contexte_recherche
        for nom_critere, valeur in criteres.items():
            if isinstance(valeur, list):
                self._ctx_recherche[nom_critere] = list(valeur)
            else:
                self._ctx_recherche[nom_critere] = valeur
        # Les libellés servent seulement au résumé, jamais à la requête moteur.
        self._ctx_recherche["prestations_cpv"] = []
        for cpv_selectionne in self.cpv_selectionnes:
            self._ctx_recherche["prestations_cpv"].append(dict(cpv_selectionne))

        self.button_daily_survey_creation.visible = False

        # L'identifiant et la révision de la dernière sauvegarde sont conservés.
        # Les offres temporaires ne peuvent pas modifier cette sauvegarde.
        self._offres_correspondent_histo = False

        self.list_offres = []
        self.afficher_offres([])
        self.checkbox_on_off.visible = False
        self._annulation_recherche_demandee = False
        task_recue = None

        try:
            self.verrouiller_recherche()
            self.bloc_selecteur_cpv_complet.visible = False
            self.display_param_summary()

            with anvil.server.no_loading_indicator:
                task_recue = anvil.server.call(
                    "lancer_recherche_cpv_background",
                    cpv_selectionnes=criteres["cpv_selectionnes"],
                    departements=criteres["departements"],
                    filtre_jours=criteres["filtre_jours"],
                    sources=criteres["sources"],
                    mots_obligatoires=criteres["mots_obligatoires"],
                    mots_ou=criteres["mots_ou"],
                    mots_exclus=criteres["mots_exclus"],
                )
                self.task_recherche = task_recue

        finally:
            if task_recue is not None:
                # Préserver la référence reçue par ce lancement.
                self.task_recherche = task_recue
                self.timer_recherche_progress.interval = 1
            else:
                self.deverrouiller_recherche(cacher_bouton=False)
                self.bloc_selecteur_cpv_complet.visible = True
                self.afficher_progression_recherche(
                    ligne_1="Recherche CPV indisponible",
                    etat="error",
                    afficher_jauges=False
                )

    def traiter_offres_cpv_apres_background(self, resultat):
        """Affiche un résultat CPV dict déjà traité par le moteur.

        Retour : None. ok=False est une erreur contrôlée, jamais un résultat
        partiel. Une réponse mal formée lève ValueError ; zéro offre est un
        succès. Les champs métier sont copiés sans filtrage ni dédoublonnage.
        """
        self.button_daily_survey_creation.visible = False
        try:
            if not isinstance(resultat, dict) or type(resultat.get("ok")) is not bool:
                raise ValueError("Réponse de recherche CPV invalide.")
            if not resultat["ok"]:
                self.list_offres = []
                self.afficher_offres([])
                self.checkbox_on_off.visible = False
                self.display_param_summary()
                self.afficher_progression_recherche(
                    ligne_1="Échec de la recherche CPV",
                    ligne_2=resultat.get("message") or "La recherche CPV n’a pas abouti.",
                    etat="error", afficher_jauges=False,
                )
                print("Erreurs recherche CPV :", resultat.get("errors", []))
                return
            offres = resultat["offres"]
            if not isinstance(offres, list):
                raise ValueError("Liste d'offres CPV invalide.")
            offres_affichees = []
            for numero, offre in enumerate(offres, start=1):
                offre_affichee = dict(offre)
                offre_affichee["vu"] = False
                offre_affichee["numero_offre"] = numero
                offre_affichee["nb_offres_total"] = len(offres)
                if not offre_affichee.get("lien_source"):
                    offre_affichee["lien_source"] = offre_affichee.get("lien", "")
                offres_affichees.append(offre_affichee)
            if not self.sauvegarder_derniere_recherche(offres_affichees):
                return

            self.list_offres = offres_affichees
            self.afficher_offres(self.list_offres)
            self.checkbox_on_off.visible = bool(offres_affichees)
            self.display_param_summary()
            message_complementaire = ""
            nombre_metier = resultat.get("nb_resultats_metier")
            nombre_retour = resultat.get("nb_retour_client")
            if nombre_metier is not None and nombre_retour is not None:
                message_complementaire = f"{nombre_metier} offres correspondent aux critères ; {nombre_retour} retournées."
            if resultat.get("errors"):
                print("Erreurs partielles CPV :", resultat["errors"])
                message_complementaire += "\nCertaines sources ont signalé une erreur."
            self.afficher_progression_recherche(
                ligne_1=self.format_nb_offres(len(offres_affichees), "retenue", "retenues"),
                ligne_2=message_complementaire.strip(),
                etat="success", progress_global=100, progress_source=100,
                afficher_jauges=False,
            )
            if resultat.get("recherche_limitee") and resultat.get("message_limite"):
                afficher_information(resultat["message_limite"], titre="Recherche limitée")
            self.actualiser_bouton_veille_cpv()
        finally:
            self.deverrouiller_recherche(cacher_bouton=False)

    def construire_resume_recherche_cpv(self):
        """Retourne un résumé str borné des critères figés au lancement.

        Aucun paramètre. Les composants actuels ne sont pas relus.
        Au maximum dix prestations sont détaillées.
        """
        contexte = self._ctx_recherche
        prestations = contexte["prestations_cpv"]
        lignes = ["Secteurs :"]
        for prestation in prestations[:10]:
            lignes.append(prestation["code"] + " — " + prestation["libelle"])
        if len(prestations) > 10:
            lignes.append(f"Et {len(prestations) - 10} autre(s) prestation(s).")
        lignes.append("Mots obligatoires : " + (", ".join(contexte["mots_obligatoires"]) or "-"))
        lignes.append("Au moins un de ces mots : " + (", ".join(contexte["mots_ou"]) or "-"))
        lignes.append("Mots exclus : " + (", ".join(contexte["mots_exclus"]) or "-"))
        lignes.append("Plateformes : " + ", ".join(contexte["sources"]))
        lignes.append(f"Période : {contexte['filtre_jours']} jours")
        lignes.append("Départements : " + (", ".join(contexte["departements"]) or "-"))
        return "\n".join(lignes)

    def sauvegarder_derniere_recherche(self, offres):
        """Sauvegarde les critères figés et mémorise la nouvelle révision.

        Retourne True après succès, False après refus fonctionnel.
        Les références précédentes restent intactes si la sauvegarde échoue.
        Les erreurs techniques remontent après déverrouillage.
        """

        sauvegarde_terminee = False
        try:
            ctx = self._ctx_recherche
            mode_recherche = ctx["mode_recherche"]

            if mode_recherche == "cpv":
                sources = ctx["sources"]
                periode = ctx["filtre_jours"]
                codes_cpv = ctx["cpv_selectionnes"]
            elif mode_recherche == "classique":
                sources = ctx["selected_platformes"]
                periode = ctx["periode"]
                codes_cpv = []
            else:
                raise ValueError("Mode de recherche invalide.")

            with anvil.server.no_loading_indicator:
                result = anvil.server.call(
                    "backup_requete",
                    sources=list(sources),
                    mots_cles=", ".join(ctx["mots_obligatoires"]),
                    mots_ou=", ".join(ctx["mots_ou"]),
                    mots_exclus=", ".join(ctx["mots_exclus"]),
                    nb_jours=periode,
                    departements=", ".join(ctx["departements"]),
                    date_heure=Time.french_zone_time(),
                    offres=offres,
                    mode_recherche=mode_recherche,
                    cpv_selectionnes=list(codes_cpv)
                )

            if not result["ok"]:
                afficher_avertissement(
                    result["message"],
                    titre="Erreur de sauvegarde"
                )
                return False

            histo_id = result["histo_id"]
            revision = result["revision_recherche"]
            if not histo_id or revision is None or revision < 1:
                raise ValueError("Réponse de sauvegarde invalide.")

            # Remplacer les références uniquement après réponse de succès.
            self.histo_id = histo_id
            self.revision_recherche = revision
            self._offres_correspondent_histo = True
            sauvegarde_terminee = True
            return True
        finally:
            if not sauvegarde_terminee:
                self.deverrouiller_recherche(cacher_bouton=False)

    def terminer_recherche_classique_sans_offre(self, message):
        """Sauvegarde un résultat classique vide et termine son affichage."""

        try:
            if not self.sauvegarder_derniere_recherche([]):
                return

            self.list_offres = []
            self.afficher_offres([])
            self.set_checkbox_on_off_sans_event(False)
            self.checkbox_on_off.visible = False
            self.display_param_summary()
            self.bloc_selecteur_cpv_complet.visible = True

            self.afficher_progression_recherche(
                ligne_1="Recherche terminée",
                ligne_2=message,
                etat="success",
                progress_global=100,
                progress_source=100,
                afficher_jauges=False
            )
        finally:
            self.deverrouiller_recherche(cacher_bouton=False)

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
            self.terminer_recherche_classique_sans_offre(
                "Aucune offre trouvée"
            )
            return

        self.afficher_etape_traitement_final("Vérification des critères positifs...")
        
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
            self.terminer_recherche_classique_sans_offre(
                "Aucune offre ne contient les mots demandés"
            )
            return

        # =====================================================
        # 2. Filtrage local des mots exclus
        # =====================================================
        self.afficher_etape_traitement_final("Application des mots exclus...")

        offres = self.filtrer_offres_exclues(offres, mots_exclus)
        print(
            f"[CLIENT SEARCH] Après mots exclus : "
            f"{len(offres or [])}"
        )
        
        if not offres:
            self.terminer_recherche_classique_sans_offre(
                "Aucune offre ne correspond à tous vos critères"
            )
            return

        # --- Génération de la liste des offres ---
        self.afficher_etape_traitement_final("Préparation des offres...")

        offres_preparees = self.build_offres_list(
            offres,
            dedoublonner=True
        )
        
        print(
            f"[CLIENT SEARCH] Après build_offres_list : "
            f"{len(offres_preparees or [])}"
        )
        
        # --- Calcul automatique de la correspondance des mots OU ---
        self.afficher_etape_traitement_final("Évaluation de la correspondance des offres...")

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
        self.afficher_etape_traitement_final("Sauvegarde de la recherche...")

        if not self.sauvegarder_derniere_recherche(offres_finales):
            return

        self.list_offres = offres_finales

        self.afficher_offres(self.list_offres)
        

        
        self.f.navigation_link_search_go.enabled = False

        self.column_panel_params.visible = False

        # Affichage du résumé des paramètres de la requête
        self.display_param_summary()

        self.column_panel_progress_recherche.visible = True

        self.text_param_summary.visible = True

        self.afficher_progression_recherche(
            ligne_1="✔ Recherche terminée",
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
        if (self._ctx_recherche or {}).get("mode_recherche") == "cpv":
            self.text_param_summary.text = self.construire_resume_recherche_cpv()
            self.text_param_summary.visible = True
            self.column_panel_progress_recherche.visible = True
            return

        ctx = self._ctx_recherche or {}
        cles_requises = (
            "mots_obligatoires",
            "mots_ou",
            "mots_exclus",
            "periode",
            "selected_platformes",
            "departements",
        )
        for cle in cles_requises:
            if cle not in ctx:
                self.text_param_summary.text = ""
                return

        # Décrire la recherche lancée, sans relire les champs de saisie.
        mots_obligatoires = ", ".join(ctx["mots_obligatoires"])
        mots_ou = ", ".join(ctx["mots_ou"])
        mots_exclus = ", ".join(ctx["mots_exclus"])
        departements = ", ".join(ctx["departements"])

        self.text_param_summary.text = (
            f"Plateformes : {ctx['selected_platformes']} / "
            f"Obligatoires : {mots_obligatoires or '-'} / "
            f"Au moins un : {mots_ou or '-'} / "
            f"Exclus : {mots_exclus or '-'} / "
            f"sur les {ctx['periode']} derniers jours / "
            f"Départements : {departements or '-'}"
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
        self.button_creer_veille_cpv.visible = False
        self.text_box_recherche_cpv.focus()
        
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
        """Sauvegarde les offres de la recherche affichée et persistée.

        Refuse les résultats temporaires et les recherches devenues obsolètes.
        Les erreurs techniques remontent.
        """

        if (
            not self._offres_correspondent_histo
            or not self.histo_id
            or self.revision_recherche is None
        ):
            afficher_avertissement(
                "Cet affichage ne correspond pas à une recherche sauvegardée. "
                "Rechargez la page pour retrouver la dernière recherche.",
                titre="Sauvegarde refusée"
            )
            return False

        with anvil.server.no_loading_indicator:
            result = anvil.server.call(
                "update_histo_offres",
                self.histo_id,
                self.list_offres,
                self.revision_recherche
            )

        if not result["ok"]:
            afficher_avertissement(
                result["message"],
                titre="Sauvegarde refusée"
            )
            return False

        self.list_offres = result["offres"]
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
        self.actualiser_bouton_veille_cpv()
    
        # Important : remettre le tag après chaque réaffichage.
        # RowTemplate1 utilise les mots ET pour le bouton de vérification.
        if (self._ctx_recherche or {}).get("mode_recherche") == "cpv":
            self.repeating_panel_offres.tag.mots_et_saisis = ", ".join(self._ctx_recherche["mots_obligatoires"])
            # Le détail reçoit les expressions de la recherche terminée sans
            # les reparcourir avec les règles textuelles du legacy.
            self.repeating_panel_offres.tag.mots_obligatoires_cpv = list(self._ctx_recherche["mots_obligatoires"])
        else:
            self.repeating_panel_offres.tag.mots_et_saisis = self.get_mots_obligatoires_texte()
            self.repeating_panel_offres.tag.mots_obligatoires_cpv = None
        
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
            self.bloc_selecteur_cpv_complet.visible = True
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
            "mots_cles": self.text_box_mots_obligatoires_cpv.text or "",
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
            self.extraire_liste_mots_saisie(self.text_box_mots_obligatoires_cpv.text or "")
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
        self.actualiser_bouton_veille_cpv()

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
            task = self.task_recherche
            if task is None:
                self.deverrouiller_recherche(cacher_bouton=False)
                return

            try:
                statut = self.lire_statut_tache_recherche(task)
            except Exception as erreur:
                print("Statut d'annulation inconnu :", erreur)
                return

            # Un autre appel peut avoir nettoyé la tâche pendant la lecture.
            if self.task_recherche is not task:
                return

            if statut in ("completed", "failed", "killed"):
                self.deverrouiller_recherche(cacher_bouton=False)

            # None, missing ou statut inattendu : conserver le suivi.
            # Aucun résultat n'est traité dans cette branche.
            return

        if self.task_recherche is None:
            self.deverrouiller_recherche(cacher_bouton=False)
            return

        task = self.task_recherche

        try:
            with anvil.server.no_loading_indicator:
                state = task.get_state() or {}
                task_completed = task.is_completed()

        except Exception as erreur:
            print("Erreur de suivi de la recherche :", erreur)

            # is_completed() peut aussi lever si la tâche a échoué
            # ou a été tuée : vérifier son statut avant tout nettoyage.
            try:
                statut = self.lire_statut_tache_recherche(task)
            except Exception as erreur_statut:
                print("Statut de la tâche inconnu :", erreur_statut)
                return

            if self.task_recherche is not task:
                return

            # Une annulation demandée pendant la lecture sera suivie
            # par la branche d'annulation au prochain tick.
            if self._annulation_recherche_demandee:
                return

            if statut in ("failed", "killed"):
                self.deverrouiller_recherche(cacher_bouton=False)
                afficher_information(
                    f"La tâche est terminée avec le statut {statut}.\n\n"
                    f"{erreur}",
                    titre="Erreur de recherche"
                )

            # completed : retenter le parcours normal au prochain tick.
            # None ou missing : conserver référence et verrouillage.
            return

        if self.task_recherche is not task:
            return

        if self._annulation_recherche_demandee:
            return

        progress = state.get("progress", 0)
        source_progress = state.get("source_progress", 0)
        source_en_cours = state.get("source_en_cours", "")
        source_current = state.get("source_current", None)
        source_total = state.get("source_total", None)
        message_progression = state.get("message", "")
    
        self.afficher_progression_recherche(
            ligne_1="🔎 Recherche en cours",
            ligne_2=message_progression,
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
    
        if (self._ctx_recherche or {}).get("mode_recherche") == "cpv":
            self.traiter_offres_cpv_apres_background(result)
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
    
        has_mots_obligatoires = bool(str(self.text_box_mots_obligatoires_cpv.text or "").strip())
        has_mots_ou = bool(str(self.text_box_mot_ou.text or "").strip())
    
        actif = bool(getattr(self, "cpv_selectionnes", [])) or has_mots_obligatoires or has_mots_ou
    
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
        Affichage simplifié de la progression.
    
        Objectif :
        - une seule ligne visible ;
        - plus de redondance entre le message et la jauge source ;
        - conservation de la même signature pour ne pas modifier les appels existants.
    
        Affichage attendu :
        🔎 Recherche en cours — TED — 137/500 — 54 %
        """
    
        # =====================================================
        # 1. Rôle CSS du bloc
        # =====================================================
        if etat == "success":
            role = "progress-search-box-success"
        elif etat == "error":
            role = "progress-search-box-error"
        else:
            role = "progress-search-box"
    
        try:
            self.column_panel_progress_recherche.visible = True
    
            if self._last_progress_role != role:
                self.column_panel_progress_recherche.role = role
                self._last_progress_role = role
    
                # Force la prochaine mise à jour CSS de la jauge
                self._last_progress_global = None
    
        except Exception:
            pass
    
        # =====================================================
        # 2. Une seule ligne visible
        # =====================================================
            
        try:
            self.label_jauge_globale.visible = True
        except Exception:
            pass
    
        # =====================================================
        # 3. Sécurisation des pourcentages
        # =====================================================
        try:
            progress_global = int(progress_global or 0)
        except (TypeError, ValueError, OverflowError):
            progress_global = 0
    
        progress_global = max(0, min(100, progress_global))
        try:
            progress_source = int(progress_source or 0)
        except (TypeError, ValueError, OverflowError):
            progress_source = 0

        progress_source = max(0, min(100, progress_source))
    
        # =====================================================
        # 4. Construction du texte unique
        # =====================================================
        ligne_1 = str(ligne_1 or "").strip()
        ligne_2 = str(ligne_2 or "").strip()
        source_nom = str(source_nom or "").strip()
    
        progress_affiche = progress_global
        if afficher_jauges and source_nom:
            progress_affiche = progress_source
            libelle_etape = source_nom
            if source_current is not None and source_total is not None:
                libelle_etape += f" — {source_current}/{source_total}"
            elif ligne_2:
                libelle_etape += f" — {ligne_2}"
        elif source_nom:
            libelle_etape = self.libelle_jauge_source(source_nom)
        elif ligne_2:
            libelle_etape = ligne_2
        else:
            libelle_etape = ""
    
        if etat == "success":
            if ligne_2:
                texte = f"{ligne_1 or '✔ Recherche terminée'} — {ligne_2}"
            else:
                texte = ligne_1 or "✔ Recherche terminée"
        elif etat == "error":
            if ligne_2:
                texte = f"{ligne_1 or '⚠ Erreur'} — {ligne_2}"
            else:
                texte = ligne_1 or "⚠ Erreur"
    
        else:
            titre = ligne_1 or "🔎 Recherche en cours"
    
            if libelle_etape:
                texte = f"{titre} — {libelle_etape} — {progress_affiche} %"
            else:
                texte = f"{titre} — {progress_affiche} %"
    
        # =====================================================
        # 5. Mise à jour du texte
        # =====================================================
        if self.label_jauge_globale.text != texte:
            self.label_jauge_globale.text = texte
    
        # =====================================================
        # 6. Mise à jour visuelle de la barre
        # =====================================================
        if afficher_jauges:
            self.regler_jauge(self.label_jauge_globale, progress_affiche, "global")
        else:
            if etat == "success":
                self.regler_jauge(self.label_jauge_globale, 100, "global")
            else:
                self.regler_jauge(self.label_jauge_globale, progress_global, "global")

    def afficher_etape_traitement_final(self, message, progress=100):
        """
        Affiche une étape du traitement final dans la ligne unique de progression.
        """
    
        self.afficher_progression_recherche(
            ligne_1="🔎 Préparation des résultats",
            ligne_2=message,
            etat="running",
            progress_global=progress,
            progress_source=progress,
            source_nom="",
            afficher_jauges=True
        )
    
    
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

    def initialiser_selecteur_cpv(self):
        """Initialise le sélecteur CPV et ses événements, sans appel serveur."""
    
        self.cpv_selectionnes = []
        self._recherche_cpv_en_cours = False
    
        # Nombre maximal de suggestions récupérées depuis le serveur.
        # Le DataGrid se charge ensuite de les afficher par pages de 5.
        self.nombre_max_suggestions_cpv = 100
    
        self._sauvegarde_veille_cpv_en_cours = False
        self._criteres_veille_cpv_actifs = None
    
        self.repeating_panel_cpv_selectionnes.role = "repeating-panel-rounded"
    
        self.repeating_panel_suggestions_cpv.items = []
    
        self.bloc_selecteur_cpv_complet.visible = True
        self.zone_resume_cpv.visible = False
    
        # Une suggestion peut être ajoutée ou retirée directement.
        self.repeating_panel_suggestions_cpv.set_event_handler(
            "x-ajouter-cpv",
            self.ajouter_cpv
        )
        self.repeating_panel_suggestions_cpv.set_event_handler(
            "x-retirer-cpv",
            self.retirer_cpv
        )
    
        # La liste des CPV sélectionnés permet également leur retrait.
        self.repeating_panel_cpv_selectionnes.set_event_handler(
            "x-retirer-cpv",
            self.retirer_cpv
        )
    
        self.multi_select_drop_down_platformes.add_event_handler(
            "change",
            self.actualiser_bouton_veille_cpv
        )
        self.text_box_departements.add_event_handler(
            "change",
            self.actualiser_bouton_veille_cpv
        )
        self.text_box_mots_exclus.add_event_handler(
            "change",
            self.actualiser_bouton_veille_cpv
        )
        self.text_box_mots_obligatoires_cpv.add_event_handler(
            "change",
            self.actualiser_bouton_veille_cpv
        )
    
        self.rafraichir_cpv_selectionnes()


    @handle("timer_recherche_cpv", "tick")
    def timer_recherche_cpv_tick(self, **event_args):
        """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
        """Lance la recherche CPV après la pause de saisie.

        Paramètre : event_args (dict), événement Anvil.
        Retour : None.
        """

        # Arrête immédiatement le timer pour éviter des recherches répétées.
        self.timer_recherche_cpv.interval = 0

        # Lance la même recherche que le bouton actuel.
        self.rechercher_cpv_depuis_saisie()

    @handle("text_box_recherche_cpv", "pressed_enter")
    def text_box_recherche_cpv_pressed_enter(self, **event_args):
        """Recherche les CPV sur Entrée, sans lancer la recherche d'offres.

        Paramètre : event_args (dict), événement Anvil. Retour : None.
        Les erreurs inattendues restent propagées.
        """
        self.rechercher_cpv_depuis_saisie()

    @handle("text_box_recherche_cpv", "change")
    def text_box_recherche_cpv_change(self, **event_args):
        """Masque les suggestions sous deux caractères, sans changer la sélection."""
        self.timer_recherche_cpv.interval = 0
        terme_recherche = str(self.text_box_recherche_cpv.text or "").strip()

        if len(terme_recherche) < 2:
            self.panel_selecteur_cpv.visible = False
            self.repeating_panel_suggestions_cpv.items = []
            self.label_message_recherche_cpv.text = ""
            self._nouvelle_recherche_cpv_en_attente = False
            return

        if self._recherche_cpv_en_cours:
            self._nouvelle_recherche_cpv_en_attente = True
            return

        self.repeating_panel_suggestions_cpv.items = []
        self.label_message_recherche_cpv.text = ""
        self.timer_recherche_cpv.interval = 0.4


    @handle("button_cacher_cpv", "click")
    def button_cacher_cpv_click(self, **event_args):
        """Replie la recherche en gardant les sélections visibles. event_args : dict. Retour : None."""
        self.bloc_selecteur_cpv_complet.visible = False
        self.zone_resume_cpv.visible = True

    @handle("button_voir_bloc_cpv", "click")
    def button_voir_bloc_cpv_click(self, **event_args):
        """Restaure uniquement la visibilité du panneau. event_args : dict. Retour : None."""
        self.bloc_selecteur_cpv_complet.visible = True
        self.zone_resume_cpv.visible = False

    def rechercher_cpv_depuis_saisie(self):
        """Démarre une nouvelle recherche de suggestions CPV."""
    
        if self._recherche_cpv_en_cours:
            return
    
        terme_recherche = str(self.text_box_recherche_cpv.text or "").strip()
    
        self.repeating_panel_suggestions_cpv.items = []
        self.label_message_recherche_cpv.text = ""
    
        if len(terme_recherche) < 2:
            return
    
        if len(terme_recherche) > 200:
            self.label_message_recherche_cpv.text = (
                "La recherche est limitée à 200 caractères."
            )
            return

        # la recherche CPV.
        self.executer_recherche_cpv(terme_recherche)


    def executer_recherche_cpv(self, terme_recherche):
        """Recherche les CPV et transmet les résultats au DataGrid.
    
        terme_recherche : str
            Texte saisi par l'utilisateur.
    
        Retour : None.
    
        Le serveur renvoie au maximum nombre_max_suggestions_cpv résultats.
        Le DataGrid assure ensuite lui-même la pagination par pages de 5.
        """
    
        self._recherche_cpv_en_cours = True
        self.panel_selecteur_cpv.visible = True
        self.label_message_recherche_cpv.text = "Recherche des CPV…"
    
        recherche_terminee = False
    
        try:
            reponse_recherche = anvil.server.call(
                "rechercher_cpv",
                terme_recherche,
                self.nombre_max_suggestions_cpv
            )
    
            # Vérifie que l'utilisateur n'a pas changé la saisie
            # pendant l'appel serveur.
            terme_actuel = str(self.text_box_recherche_cpv.text or "").strip()
    
            if terme_actuel != terme_recherche:
                self.repeating_panel_suggestions_cpv.items = []
                self.label_message_recherche_cpv.text = ""
    
                self._nouvelle_recherche_cpv_en_attente = (
                    len(terme_actuel) >= 2
                )
    
                recherche_terminee = True
                return
    
            if not reponse_recherche["ok"]:
                self.repeating_panel_suggestions_cpv.items = []
                self.label_message_recherche_cpv.text = (
                    reponse_recherche["message"]
                )
    
            else:
                resultats_cpv = list(
                    reponse_recherche["resultats"] or []
                )
    
                total_resultats = int(
                    reponse_recherche["total_resultats"] or 0
                )
    
                self.repeating_panel_suggestions_cpv.items = (
                    self.preparer_suggestions_cpv(resultats_cpv)
                )
    
                nombre_resultats = len(resultats_cpv)
    
                if nombre_resultats == 0:
                    self.label_message_recherche_cpv.text = (
                        "Aucun CPV trouvé"
                    )
    
                elif nombre_resultats < total_resultats:
                    self.label_message_recherche_cpv.text = (
                        f"{nombre_resultats} premiers résultats "
                        f"sur {total_resultats}"
                    )
    
                else:
                    self.label_message_recherche_cpv.text = (
                        f"{nombre_resultats} résultats"
                    )
    
            recherche_terminee = True
    
        finally:
            self._recherche_cpv_en_cours = False
    
            if not recherche_terminee:
                self.repeating_panel_suggestions_cpv.items = []
                self.label_message_recherche_cpv.text = (
                    "La recherche CPV est indisponible. Réessayez."
                )
    
            # Si la saisie a changé pendant l'appel serveur,
            # une nouvelle recherche est programmée.
            if self._nouvelle_recherche_cpv_en_attente:
                self._nouvelle_recherche_cpv_en_attente = False
    
                terme_actuel = str(
                    self.text_box_recherche_cpv.text or ""
                ).strip()
    
                if len(terme_actuel) >= 2:
                    self.timer_recherche_cpv.interval = 0.4


    def preparer_suggestions_cpv(self, resultats_cpv):
        """Ajoute à chaque suggestion son état dérivé de la sélection courante.

        Paramètre : resultats_cpv (list[dict]), résultats officiels du serveur.
        Retour : list[dict], copies enrichies avec ``est_selectionne``. Cette
        information d'affichage est toujours recalculée depuis
        ``self.cpv_selectionnes``, qui reste l'unique source de vérité.
        """
        codes_cpv_selectionnes = set()
        for cpv_selectionne in self.cpv_selectionnes:
            codes_cpv_selectionnes.add(cpv_selectionne["code"])

        suggestions_preparees = []
        for resultat_cpv in resultats_cpv:
            suggestion_cpv = dict(resultat_cpv)
            code_cpv = suggestion_cpv["code"]
            suggestion_cpv["est_selectionne"] = code_cpv in codes_cpv_selectionnes
            suggestions_preparees.append(suggestion_cpv)

        return suggestions_preparees

    def rafraichir_etat_suggestions_cpv(self):
        """Actualise l'état des suggestions sans réinitialiser la pagination."""
    
        codes_cpv_selectionnes = {
            cpv_selectionne["code"]
            for cpv_selectionne in self.cpv_selectionnes
        }
    
        for ligne_suggestion in self.repeating_panel_suggestions_cpv.get_components():
            ligne_suggestion.item["est_selectionne"] = (
                ligne_suggestion.item["code"] in codes_cpv_selectionnes
            )
            ligne_suggestion.actualiser_etat_bouton()

    def ajouter_cpv(self, cpv_propose, **event_args):
        """Ajoute une suggestion officielle à la sélection locale, sans écriture.

        Paramètres : cpv_propose (dict contenant code et libelle, deux str),
        event_args (dict Anvil). Retour : None. Un doublon est ignoré ;
        au-delà de 100 codes, un message invite à réduire la sélection.
        """
        code_cpv = cpv_propose["code"]

        # Respecter la borne de résolution et de validation définie en 10C.
        if len(self.cpv_selectionnes) >= 5:
            alert("Vous pouvez sélectionner jusqu’à 5 CPV.")
            return

        self.cpv_selectionnes.append({
            "code": code_cpv,
            "libelle": cpv_propose["libelle"],
        })
        self.rafraichir_cpv_selectionnes()

    def retirer_cpv(self, code_cpv, **event_args):
        """Retire uniquement le code demandé de la sélection locale.

        Paramètres : code_cpv (str), event_args (dict Anvil). Retour : None.
        Un code absent ne change pas la sélection. Aucun appel serveur.
        """
        cpv_conserves = []
        for cpv_selectionne in self.cpv_selectionnes:
            if cpv_selectionne["code"] != code_cpv:
                cpv_conserves.append(cpv_selectionne)
        self.cpv_selectionnes = cpv_conserves
        self.rafraichir_cpv_selectionnes()
        #self.mettre_a_jour_affichage_selection_cpv()

    def mettre_a_jour_affichage_selection_cpv(self):
        """Met à jour l'affichage et le titre des CPV sélectionnés."""
    
        cpv_selectionnes = list(self.repeating_panel_cpv_selectionnes.items or [])
        nb_cpv_selectionnes = len(cpv_selectionnes)
    
        self.repeating_panel_cpv_selectionnes.visible = bool(cpv_selectionnes)
        self.button_cacher_cpv.visible = bool(cpv_selectionnes)
    
        if not cpv_selectionnes:
            return
    
        if nb_cpv_selectionnes == 1:
            titre = "Secteur sélectionné :"
        else:
            titre = "Secteurs sélectionnés :"
    
        definir_titre_repeating_panel(
            self.repeating_panel_cpv_selectionnes,
            titre,
            icone="factory"
        )
        

    def rafraichir_cpv_selectionnes(self):
        """Rafraîchit les CPV sélectionnés et synchronise les suggestions visibles.

        Aucun paramètre. Retour : None. L'ordre local est conservé et aucune
        transformation du libellé officiel n'est effectuée.
        """
        self.repeating_panel_cpv_selectionnes.items = list(self.cpv_selectionnes)
        # Recalculer les boutons depuis la sélection évite tout état parallèle
        # susceptible de se désynchroniser après un ajout ou un retrait.
        self.rafraichir_etat_suggestions_cpv()
        self.maj_bouton_recherche_visible()
        self.mettre_a_jour_affichage_selection_cpv()
        self.actualiser_bouton_veille_cpv()


    def preparer_criteres_veille_cpv(self):
        """Copie les six critères CPV, sans normalisation métier côté client.
    
        Aucun paramètre. Retour : dict contenant cpv_selectionnes (list[str]),
        sources (list[str]), departements, mots_exclus, mots_obligatoires
        et mots_ou.
        Les libellés restent dans la Form ; aucune valeur locale n'est modifiée.
        """
        codes_cpv = []
        for cpv_selectionne in self.cpv_selectionnes:
            codes_cpv.append(cpv_selectionne["code"])
    
        sources_selectionnees = list(self.multi_select_drop_down_platformes.selected or [])
        departements = str(self.text_box_departements.text or "").strip()
        mots_exclus = str(self.text_box_mots_exclus.text or "").strip()
    
        # Ces champs restent partagés avec la recherche manuelle ;
        # le serveur CPV normalise leur saisie.
        mots_obligatoires = self.text_box_mots_obligatoires_cpv.text or ""
        mots_ou = self.text_box_mot_ou.text or ""
    
        return {
            "cpv_selectionnes": codes_cpv,
            "sources": sources_selectionnees,
            "departements": departements,
            "mots_exclus": mots_exclus,
            "mots_obligatoires": mots_obligatoires,
            "mots_ou": mots_ou,
        }

    def valider_criteres_veille_cpv(self, criteres):
        """Vérifie les préconditions locales sans appeler le serveur.

        Paramètre : criteres (dict préparé par la Form). Retour : bool.
        Une sélection CPV ou des sources vides affichent un avertissement.
        La validation métier complète reste à la charge du serveur.
        """
        if not criteres["cpv_selectionnes"]:
            afficher_avertissement("Sélectionnez au moins une prestation CPV.", titre="Veille quotidienne CPV")
            return False
        if not criteres["sources"]:
            afficher_avertissement("Sélectionnez au moins une source.", titre="Veille quotidienne CPV")
            return False
        return True

    def construire_resume_veille_cpv(self, criteres):
        """Construit le résumé textuel des critères à confirmer.

        Paramètre : criteres (dict préparé). Retour : str, sans HTML.
        Au plus dix libellés sont détaillés pour garder le dialogue lisible ;
        le nombre total de CPV est toujours indiqué. Aucun terme legacy utilisé.
        """
        lignes_resume = [
            "Créer une veille quotidienne CPV ?",
            "Nombre de CPV sélectionnés : " + str(len(criteres["cpv_selectionnes"])),
        ]
        for cpv_selectionne in self.cpv_selectionnes[:10]:
            lignes_resume.append("- " + cpv_selectionne["libelle"])
        nombre_non_affiche = len(criteres["cpv_selectionnes"]) - 10
        if nombre_non_affiche > 0:
            lignes_resume.append("Et " + str(nombre_non_affiche) + " autre(s) prestation(s).")
        lignes_resume.append("Départements : " + (criteres["departements"] or "tous"))
        lignes_resume.append("Sources : " + ", ".join(criteres["sources"]))
        mots_obligatoires_affiches = criteres["mots_obligatoires"].strip() or "aucun"
        lignes_resume.append("Mots obligatoires : " + mots_obligatoires_affiches)
        mots_ou_affiches = criteres["mots_ou"].strip() or "aucun"
        lignes_resume.append("Au moins un de ces mots : " + mots_ou_affiches)
        lignes_resume.append("Mots exclus : " + (criteres["mots_exclus"] or "aucun"))
        lignes_resume.append("Fréquence : veille quotidienne, sur les publications du dernier jour.")
        return "\n".join(lignes_resume)

    def preparer_criteres_veille(self):
        """Copie les critères figés de la recherche ayant produit les offres."""
        ctx = getattr(self, "_ctx_recherche", {}) or {}
        mode = ctx.get("mode_recherche")

        if mode == "classique":
            sources = ctx["selected_platformes"]
            periode = ctx["periode"]
            codes_cpv = []
            prestations_cpv = []
        elif mode == "cpv":
            sources = ctx["sources"]
            periode = ctx["filtre_jours"]
            codes_cpv = list(ctx["cpv_selectionnes"])
            prestations_cpv = [
                dict(prestation)
                for prestation in ctx.get("prestations_cpv", [])
            ]
        else:
            return None

        return {
            "mode_recherche": mode,
            "sources": list(sources),
            "departements": list(ctx["departements"]),
            "mots_obligatoires": list(ctx["mots_obligatoires"]),
            "mots_ou": list(ctx["mots_ou"]),
            "mots_exclus": list(ctx["mots_exclus"]),
            "cpv_selectionnes": codes_cpv,
            "prestations_cpv": prestations_cpv,
            "periode": periode,
        }

    def construire_resume_veille(self, criteres):
        """Présente les critères de la recherche ayant réellement trouvé les offres."""
        message = (
            "Créer une veille quotidienne à partir des paramètres de cette recherche ?\n\n"
            "Cette veille vérifiera chaque jour les nouvelles offres publiées.\n\n"
            "Lorsqu'une ou plusieurs offres correspondent à vos critères,\n"
            "un mail vous sera envoyé.\n\n"
            "La première veille est offerte."
        )
        lignes = []
        if criteres["mode_recherche"] == "cpv":
            lignes.append("CPV sélectionnés : " + str(len(criteres["cpv_selectionnes"])))
            libelles = {}
            for prestation in criteres["prestations_cpv"]:
                libelles[prestation["code"]] = prestation["libelle"]
            # Limiter le détail du dialogue comme dans le résumé CPV existant.
            for code in criteres["cpv_selectionnes"][:10]:
                libelle = libelles.get(code)
                lignes.append("- " + code + (" — " + libelle if libelle else ""))
            nombre_non_affiche = len(criteres["cpv_selectionnes"]) - 10
            if nombre_non_affiche > 0:
                lignes.append("Et " + str(nombre_non_affiche) + " autre(s) prestation(s).")

        lignes.extend([
            "Mots obligatoires : " + (", ".join(criteres["mots_obligatoires"]) or "aucun"),
            "Au moins un de ces mots : " + (", ".join(criteres["mots_ou"]) or "aucun"),
            "Mots exclus : " + (", ".join(criteres["mots_exclus"]) or "aucun"),
            "Départements : " + (", ".join(criteres["departements"]) or "tous"),
            "Sources : " + ", ".join(criteres["sources"]),
            "Période de la recherche ayant validé les critères : " + str(criteres["periode"]) + " jour(s)",
            "La veille quotidienne vérifiera les publications du dernier jour.",
        ])
        return message + "\n\n" + "\n".join(lignes)

    def actualiser_bouton_veille_cpv(self, **event_args):
        """Actualise le bouton commun depuis la dernière recherche réussie."""
        self.button_daily_survey_creation.visible = False
        criteres = self.preparer_criteres_veille()
        sauvegarde_en_cours = getattr(self, "_sauvegarde_veille_cpv_en_cours", False)
        # Le sélecteur appelle ce helper avant l'initialisation de ces attributs.
        recherche_valide = (
            criteres is not None
            and bool(getattr(self, "list_offres", []))
            and getattr(self, "_offres_correspondent_histo", False)
            and not getattr(self, "_recherche_en_cours", False)
            and not sauvegarde_en_cours
        )
        veille_active = (
            criteres is not None
            and criteres == getattr(self, "_criteres_veille_cpv_actifs", None)
        )
        self.button_creer_veille_cpv.visible = recherche_valide
        self.button_creer_veille_cpv.enabled = recherche_valide and not veille_active
        self.button_creer_veille_cpv.bold = veille_active
        if not sauvegarde_en_cours:
            self.button_creer_veille_cpv.text = "Créer une veille quotidienne"

    def traiter_reponse_veille_cpv(self, reponse, criteres):
        """Interprète explicitement le statut serveur sans vider les critères.

        Paramètres : reponse (dict serveur), criteres (dict envoyé).
        Retour : tuple[str, bool] : message utilisateur et caractère informatif.
        'deja_active' est informatif même si ok=False. Une validation refusée
        est affichée ; une réponse malformée lève ValueError pour diagnostic.
        """
        if not isinstance(reponse, dict):
            raise ValueError("Réponse de sauvegarde CPV invalide.")
        statut = reponse.get("statut")
        if statut == "cree":
            message = "Veille quotidienne CPV créée."
        elif statut == "reactivee":
            message = "Cette veille existait déjà et a été réactivée."
        elif statut == "deja_active":
            message = "Cette veille quotidienne est déjà active."
        elif statut == "erreur":
            message = reponse.get("message")
            if not isinstance(message, str) or not message:
                raise ValueError("Message de validation CPV manquant.")
            return message, False
        else:
            raise ValueError("Statut de sauvegarde CPV inconnu.")
        self._criteres_veille_cpv_actifs = criteres
        return message, True

    @handle("button_creer_veille_cpv", "click")
    def button_creer_veille_cpv_click(self, **event_args):
        """Confirme puis crée une veille classique ou CPV depuis les critères figés.

        Les refus fonctionnels sont affichés. Les erreurs techniques remontent
        après restauration de l'état du bouton dans finally.
        """
        if not self.list_offres:
            afficher_avertissement(
                "La veille quotidienne peut être créée uniquement "
                "après une recherche ayant trouvé au moins une offre.\n\n"
                "Si aucun résultat n'est trouvé, essayez d'élargir temporairement "
                "la période de recherche, jusqu'à 365 jours, afin de vérifier que "
                "vos critères correspondent bien à des appels d'offres existants.",
                titre="Veille quotidienne",
            )
            return

        if self._sauvegarde_veille_cpv_en_cours:
            return
        if self._recherche_en_cours or not self._offres_correspondent_histo:
            afficher_avertissement(
                "Terminez une recherche avec succès avant de créer une veille.",
                titre="Veille quotidienne",
            )
            return

        criteres = self.preparer_criteres_veille()
        if criteres is None:
            raise ValueError("Mode de recherche invalide pour la veille.")

        self._sauvegarde_veille_cpv_en_cours = True
        self.actualiser_bouton_veille_cpv()
        try:
            confirmation = demander_choix(
                titre="Veille quotidienne",
                message=self.construire_resume_veille(criteres),
                autoriser_html=False,
            )
            if confirmation is not True:
                return

            # Ne jamais envoyer les critères d'une autre recherche que celle confirmée.
            if (
                self._recherche_en_cours
                or not self._offres_correspondent_histo
                or not self.list_offres
                or self.preparer_criteres_veille() != criteres
            ):
                afficher_avertissement(
                    "La recherche a changé. Vérifiez-la puis confirmez à nouveau.",
                    titre="Veille quotidienne",
                )
                return

            self.button_creer_veille_cpv.text = "Création de la veille…"
            if criteres["mode_recherche"] == "classique":
                reponse = anvil.server.call(
                    "enregistrer_daily_survey",
                    sources=criteres["sources"],
                    mots_cles=criteres["mots_obligatoires"],
                    mots_ou=criteres["mots_ou"],
                    mots_exclus=criteres["mots_exclus"],
                    departements=criteres["departements"],
                )
            else:
                reponse = anvil.server.call(
                    "enregistrer_daily_survey_cpv",
                    cpv_selectionnes=criteres["cpv_selectionnes"],
                    sources=criteres["sources"],
                    departements=criteres["departements"],
                    mots_exclus=criteres["mots_exclus"],
                    mots_obligatoires=criteres["mots_obligatoires"],
                    mots_ou=criteres["mots_ou"],
                )

            if not isinstance(reponse, dict):
                raise ValueError("Réponse de sauvegarde de veille invalide.")
            statut = reponse.get("statut")
            message = reponse.get("message")
            if not isinstance(message, str) or not message:
                raise ValueError("Message de sauvegarde de veille manquant.")

            # Un doublon actif est informatif même lorsque ok vaut False.
            if statut in ("creee", "cree", "reactivee", "deja_active"):
                self._criteres_veille_cpv_actifs = criteres
                afficher_information(message, titre="Veille quotidienne")
            elif statut == "erreur":
                afficher_avertissement(message, titre="Veille quotidienne")
            else:
                raise ValueError("Statut de sauvegarde de veille inconnu.")
        finally:
            self._sauvegarde_veille_cpv_en_cours = False
            self.actualiser_bouton_veille_cpv()

    def go_up(self, **event_args):
        self.scroll_into_view(smooth=True, align="start")

    def go_down(self, **event_args):
        self.scroll_into_view(smooth=True, align="end")


    def button_daily_survey_creation_click(self, **event_args):
        """Compatibilité temporaire avec l'ancien événement Designer."""
        self.button_creer_veille_cpv_click(**event_args)
