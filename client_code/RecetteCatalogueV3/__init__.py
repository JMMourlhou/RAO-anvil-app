from ._anvil_designer import RecetteCatalogueV3Template
from anvil import *
import anvil.server
import re
import time


_MESSAGES = {
    "caller_not_allowed": "Le Pi5 refuse l'origine de l'appel. Vérifier le passage direct par CatalogueRecetteV3.",
    "authentication_required": "Une session Anvil authentifiée est nécessaire.",
    "access_denied": "Accès refusé. Vérifier DEVELOPPEUR_USER_ID côté serveur et la liste locale autorisée du Pi5.",
    "invalid_parameters": "Paramètres refusés par le catalogue. Vérifier le CPV et les critères envoyés.",
    "catalogue_busy": "Le catalogue est occupé. Réessayer manuellement plus tard.",
    "pagination_changed": "Le catalogue a changé. Retour à la première page.",
    "catalogue_limit": "La limite de consultation du catalogue est atteinte.",
    "catalogue_unavailable": "Le catalogue PostgreSQL est indisponible. Vérifier le service V3 sur le Pi5.",
    "not_found": "L'annonce demandée est introuvable.",
}


class RecetteCatalogueV3(RecetteCatalogueV3Template):
    def __init__(self, **properties):
        self.init_components(**properties)
        self._page = None
        self._occupe = False
        self._appels_mesures = []
        self.repeating_panel_annonces.items = []
        self.repeating_panel_annonces.set_event_handler("x-detail", self.afficher_detail)

    def _actualiser_boutons(self):
        self.button_rechercher.enabled = not self._occupe
        self.text_box_cpv.enabled = not self._occupe
        suivante = False
        if self._page is not None and self._page["suite"]:
            suivante = self._page["decalage"] + self._page["limite"] <= 500
        self.button_suivante.visible = suivante
        self.button_suivante.enabled = suivante and not self._occupe

    def _appeler(self, nom, **parametres):
        """Affiche une panne technique sans intercepter ni masquer l'exception."""
        retour_recu = False
        resultat = None
        debut_appel = time.time()
        try:
            resultat = anvil.server.call(nom, **parametres)
            fin_appel = time.time()
            retour_recu = True
            return resultat
        finally:
            fin_mesure = fin_appel if retour_recu else time.time()
            if nom == "recette_catalogue_v3_rechercher":
                mesures = {"appel_formulaire_ms": (fin_mesure - debut_appel) * 1000,
                           "appel_termine": retour_recu, "uplink_ms": None,
                           "postgresql_duree_ms": None}
                if isinstance(resultat, dict):
                    serveur = resultat.get("_mesures_recette_v3")
                    valeur_uplink = serveur.get("uplink_ms") if isinstance(serveur, dict) else None
                    for cle, valeur in (("uplink_ms", valeur_uplink),
                                        ("postgresql_duree_ms", resultat.get("duree_ms"))):
                        if isinstance(valeur, (int, float)) and not isinstance(valeur, bool) and 0 <= valeur < float("inf"):
                            mesures[cle] = valeur
                self._appels_mesures.append(mesures)
            if not retour_recu:
                self.label_erreur.text = (
                    "L'appel serveur a échoué. Vérifier la session Anvil, la configuration "
                    "du développeur et la connexion Uplink V3. Le diagnostic reste dans la console Anvil."
                )

    def _code_erreur(self, resultat):
        erreur = resultat.get("error")
        if isinstance(erreur, dict):
            return erreur.get("code", "erreur_inconnue")
        return resultat.get("code") or resultat.get("error_code") or erreur or "erreur_inconnue"

    def _reponse_valide(self, resultat):
        if not isinstance(resultat, dict) or type(resultat.get("ok")) is not bool:
            self.label_erreur.text = "Réponse V3 incorrecte : dictionnaire avec ok booléen attendu."
            raise ValueError(self.label_erreur.text)
        if not resultat["ok"]:
            code = self._code_erreur(resultat)
            self.label_erreur.text = _MESSAGES.get(code, "Erreur retournée par le catalogue : " + str(code))
            return False
        return True

    @handle("button_rechercher", "click")
    def rechercher(self, **event_args):
        debut_clic = time.time()
        if self._occupe:
            return
        cpv = str(self.text_box_cpv.text or "").strip()
        if not re.fullmatch(r"[0-9]{8}", cpv):
            self.label_erreur.text = "Saisir un code CPV composé de huit chiffres."
            return
        self._page = None
        self.repeating_panel_annonces.items = []
        self.text_area_detail.text = ""
        self.label_page.text = "Recherche en cours…"
        self._executer_recherche({
            "cpv_selectionnes": [cpv], "departements": [], "filtre_jours": 30,
            "sources": ["TED"], "limite": 20, "decalage": 0,
        }, debut_clic=debut_clic)

    @handle("button_suivante", "click")
    def page_suivante(self, **event_args):
        debut_clic = time.time()
        if self._occupe or self._page is None or not self._page["suite"]:
            return
        page = self._page
        decalage = page["decalage"] + page["limite"]
        if decalage > 500:
            self.label_erreur.text = _MESSAGES["catalogue_limit"]
            return
        # Réutiliser exclusivement les critères effectivement retournés par V3.
        criteres = page["criteres"]
        self._executer_recherche({
            "cpv_selectionnes": criteres["cpv_selectionnes"],
            "departements": criteres["departements"], "filtre_jours": criteres["nb_jours"],
            "sources": criteres["sources"], "mots_obligatoires": criteres["mots_obligatoires"],
            "mots_exclus": criteres["mots_exclus"], "mots_ou": criteres["mots_ou"],
            "limite": page["limite"], "decalage": decalage,
            "empreinte": page["empreinte"], "date_reference": criteres["date_reference"],
        }, debut_clic=debut_clic)

    def _executer_recherche(self, parametres, debut_clic=None):
        if debut_clic is None:
            debut_clic = time.time()
        self._appels_mesures = []
        construction_ms = None
        resultats_affiches = False
        nombre_annonces = None
        code_erreur = None
        self._occupe = True
        self.label_erreur.text = ""
        self._actualiser_boutons()
        try:
            resultat = self._appeler("recette_catalogue_v3_rechercher", **parametres)
            if not self._reponse_valide(resultat):
                code_erreur = self._code_erreur(resultat)
                if self._code_erreur(resultat) != "pagination_changed":
                    return
                # Une seule reprise, sans ancien instantané ni lecture des champs UI.
                self._page = None
                self.repeating_panel_annonces.items = []
                parametres = dict(parametres)
                parametres.update(decalage=0, empreinte=None, date_reference=None)
                resultat = self._appeler("recette_catalogue_v3_rechercher", **parametres)
                if not self._reponse_valide(resultat):
                    code_erreur = self._code_erreur(resultat)
                    return
            debut_construction = time.time()
            try:
                self._afficher_page(resultat)
                resultats_affiches = True
                nombre_annonces = len(resultat["offres"])
            finally:
                construction_ms = (time.time() - debut_construction) * 1000
        finally:
            if self._page is None:
                self.label_page.text = "Aucune page valide reçue ; la recherche n'est pas déclarée complète."
            self._occupe = False
            self._actualiser_boutons()
            # Ces mesures s'arrêtent au retour des mises à jour des composants.
            # Elles ne prétendent pas mesurer la peinture des pixels du navigateur.
            code_public = code_erreur if isinstance(code_erreur, str) and code_erreur in _MESSAGES else None
            print("[RECETTE V3 FORMULAIRE]", {
                "nombre_annonces": nombre_annonces,
                "total_clic_mise_a_jour_ms": (time.time() - debut_clic) * 1000,
                "construction_resultats_ms": construction_ms,
                "resultats_affiches": resultats_affiches,
                "code_erreur": code_public,
                "appels": self._appels_mesures,
            })

    def _afficher_page(self, resultat):
        offres = resultat.get("offres")
        criteres = resultat.get("criteres")
        champs = ("cpv_selectionnes", "departements", "nb_jours", "sources", "mots_obligatoires",
                  "mots_exclus", "mots_ou", "date_reference")
        if (not isinstance(offres, list) or not all(isinstance(offre, dict) for offre in offres)
                or not isinstance(criteres, dict) or not all(champ in criteres for champ in champs)
                or type(resultat.get("suite")) is not bool
                or type(resultat.get("limite")) is not int or not 1 <= resultat["limite"] <= 100
                or type(resultat.get("decalage")) is not int or not 0 <= resultat["decalage"] <= 500
                or type(resultat.get("total")) is not int or resultat["total"] < 0
                or not isinstance(resultat.get("empreinte"), str)):
            self.label_erreur.text = "Réponse V3 incomplète : offres ou métadonnées de pagination invalides."
            raise ValueError(self.label_erreur.text)
        self._page = resultat
        self.repeating_panel_annonces.items = offres
        self.text_area_detail.text = ""
        self.label_page.text = (
            str(len(offres)) + " annonce(s) affichée(s) sur " + str(resultat["total"])
            + " — décalage " + str(resultat["decalage"])
        )
        if not offres:
            self.label_page.text += " — aucune annonce pour cette page."
        if resultat["suite"] and resultat["decalage"] + resultat["limite"] > 500:
            self.label_erreur.text = _MESSAGES["catalogue_limit"]

    def afficher_detail(self, offre_ids, **event_args):
        if self._occupe:
            return
        self._occupe = True
        self.label_erreur.text = ""
        self.text_area_detail.text = ""
        self._actualiser_boutons()
        try:
            resultat = self._appeler("recette_catalogue_v3_detail", offre_ids=offre_ids)
            if self._reponse_valide(resultat):
                # Le contrat de détail n'impose pas ici un champ unique « offre ».
                # Afficher le document entier comme texte, jamais comme HTML.
                self.text_area_detail.text = str(resultat)
        finally:
            self._occupe = False
            self._actualiser_boutons()
