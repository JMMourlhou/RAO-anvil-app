from ._anvil_designer import RowTemplate1Template
from anvil import *
import anvil.users
import anvil.server
import re
from ...recherche_mk_html import recherche_mk_html
import m3.components as m3


class RowTemplate1(RowTemplate1Template):

    def __init__(self, **properties):
        self.init_components(**properties)

        self.comp_html = None

        # Dates
        self.text_date_publication.text = self.format_date_fr(
            self.item_value("date_publication", "")
        )

        self.text_date_limite_rep.text = self.format_date_fr(
            self.item_value("date_limite_rep", "")
        )

        # Champs principaux
        self.text_titre.text = self.item_value("titre", "")

        # Dans tes résultats, la clé est souvent lien_source, pas lien
        lien = (
            self.item_value("lien_source", "")
            or self.item_value("lien", "")
            or self.item_value("lien_app", "")
        )

        self.link_lien.text = lien

        try:
            self.link_lien.url = lien
        except Exception:
            pass

        self.text_departement.text = self.item_value("departement", "")

        # Vu / non vu
        self.checkbox_vu.checked = self.item_value("vu", False)

        # Libellé du bouton Vérification :
        # score + mots_score trouvés + mots-clés classiques si besoin
        self.maj_libelle_bouton_verification()

    def form_show(self, **event_args):
        self.maj_libelle_bouton_verification()

    # -------------------------------------------------------------------------
    # Fonctions utilitaires item / date
    # -------------------------------------------------------------------------

    def item_value(self, cle, defaut=None):
        """
        Récupère une valeur dans self.item,
        que self.item soit un dictionnaire ou une row Anvil.
        """
        try:
            valeur = self.item.get(cle, defaut)
            if valeur is None:
                return defaut
            return valeur
        except Exception:
            try:
                valeur = self.item[cle]
                if valeur is None:
                    return defaut
                return valeur
            except Exception:
                return defaut

    def format_date_fr(self, valeur):
        """
        Accepte :
        - une date Python avec strftime()
        - une string '2026-04-24'
        - une string ISO '2026-04-24T10:30:00'
        Retourne '24/04/2026'
        """

        if not valeur:
            return "-"

        # Cas date/datetime Python
        try:
            return valeur.strftime("%d/%m/%Y")
        except Exception:
            pass

        # Cas string
        try:
            valeur = str(valeur).strip()

            if not valeur:
                return "-"

            # Si format ISO avec heure
            valeur = valeur.split("T")[0]
            valeur = valeur.split(" ")[0]

            # Cas déjà au format français
            if "/" in valeur:
                return valeur

            morceaux = valeur.split("-")
            if len(morceaux) == 3:
                annee, mois, jour = morceaux
                return f"{jour}/{mois}/{annee}"

        except Exception:
            pass

        return "-"

    # -------------------------------------------------------------------------
    # Actions principales row
    # -------------------------------------------------------------------------

    def link_lien_click(self, **event_args):
        from anvil.js import window

        lien = (
            self.item_value("lien_source", "")
            or self.item_value("lien", "")
            or self.item_value("lien_app", "")
            or self.link_lien.text
        )

        if lien:
            window.open(lien)

        self.checkbox_vu.checked = True
        self.checkbox_vu_change()

    def checkbox_vu_change(self, **event_args):
        """
        Evènement levé vers la forme mère + sauvegarde côté serveur.
        """

        self.parent.raise_event(
            "x-checkbox-vu-changee",
            checked=self.checkbox_vu.checked,
            item=self.item
        )

        with anvil.server.no_loading_indicator:
            result = anvil.server.call("check", self.item, self.checkbox_vu.checked)

        if not result:
            alert("Erreur en modification")

    def toggle_icon_button_del_click(self, **event_args):
        result = anvil.server.call("del_1", self.item)
        if result:
            open_form("search", "check")
        else:
            alert("Erreur en effacement !")

    # -------------------------------------------------------------------------
    # Extraction des mots-clés classiques saisis par l'utilisateur
    # -------------------------------------------------------------------------

    def extraire_mots_cles(self):
        parent_tag = getattr(self.parent, "tag", None)
        brut = (getattr(parent_tag, "mots_cles_saisis", "") or "").strip().lower()

        if not brut:
            return []

        texte = brut.replace(";", ",").replace("\n", ",")
        texte = texte.replace(" et ", ",")
        texte = texte.replace(" ou ", ",")

        morceaux = [m.strip() for m in texte.split(",") if m.strip()]

        mots_uniques = []
        deja_vus = set()

        for mot in morceaux:
            if mot not in deja_vus:
                deja_vus.add(mot)
                mots_uniques.append(mot)

        return mots_uniques

    # -------------------------------------------------------------------------
    # Bouton Vérification
    # -------------------------------------------------------------------------

    def button_generer_html_click(self, **event_args):
        """
        Affiche le texte avec mots-clés surlignés en couleurs.
        """

        # Changement apparence du bouton
        if self.column_panel_detail.visible is False:
            self.button_generer_html.icon = "mi:keyboard_double_arrow_up"

            # Check du check_box 'vu'
            self.checkbox_vu.checked = True
            self.checkbox_vu_change()

        else:
            self.button_generer_html.icon = "mi:keyboard_double_arrow_down"
            self.column_panel_detail.visible = False
            return

        # Contenu à afficher
        texte_source = self.get_texte_source_verification()
        texte = self.format_search_text_for_display(texte_source)
        mots_cles = self.extraire_mots_cles()

        if not texte:
            alert("Aucun texte disponible pour cette offre !")
            return

        if not mots_cles:
            alert("Aucun mot-clé saisi !")
            return

        # Création du composant HTML si besoin
        if self.comp_html is None:
            self.comp_html = recherche_mk_html()
            self.column_panel_affichage.clear()
            self.column_panel_affichage.add_component(self.comp_html)

        # Envoi du texte + mots-clés au composant
        self.comp_html.charger(texte, mots_cles)

        self.column_panel_detail.visible = True

    def format_search_text_for_display(self, texte):
        """
        Rend le texte plus lisible avant surbrillance :
        - garde les retours à la ligne existants
        - convertit les \\n littéraux en vrais sauts de ligne
        - ajoute des sauts de ligne avant les libellés fréquents
        - supprime quelques lignes techniques parasites
        - compacte les espaces
        """

        texte = str(texte or "")

        # Convertit les \n littéraux en vrais retours ligne
        texte = texte.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")

        # Normalisation des fins de ligne réelles
        texte = texte.replace("\r\n", "\n").replace("\r", "\n")

        # Compacte les espaces, mais garde les \n
        lignes = [re.sub(r"[ \t]+", " ", ligne).strip() for ligne in texte.split("\n")]
        texte = "\n".join(lignes)

        labels = [
            "Titre :",
            "Acheteur :",
            "Date de publication :",
            "Date limite :",
            "Date limite de réception des offres :",
            "Référence :",
            "Nature :",
            "Procédure :",
            "Lieu :",
            "Nom :",
            "Nom officiel :",
            "Adresse :",
            "Ville :",
            "Code postal :",
            "Email :",
            "Téléphone :",
            "Site web :",
            "Lien :",
            "Note :",
            "Description :",
            "Informations complémentaires :",
            "Eléments de preuve :",
            "Eléments de jugement :",
            "Critère :",
            "Type :",
            "Arrangement financier :",
            "Type d'avis :",
        ]

        for label in labels:
            texte = re.sub(
                rf"\s*{re.escape(label)}\s*",
                f"\n\n{label} ",
                texte
            )

        # URL seule sur sa propre ligne
        texte = re.sub(r"\s+(https?://)", r"\n\1", texte)

        lignes = []
        a_supprimer = {
            "epo-procurement-document",
            "non-restricted-document",
        }

        for ligne in texte.split("\n"):
            l = ligne.strip()

            if not l:
                lignes.append("")
                continue

            l_norm = l.lower()

            if l_norm in a_supprimer:
                continue

            if re.fullmatch(r"Heure\s*:\s*\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?", l, flags=re.I):
                continue

            lignes.append(l)

        texte = "\n".join(lignes)
        texte = re.sub(r"\n{3,}", "\n\n", texte)

        return texte.strip()

    # -------------------------------------------------------------------------
    # Fonctions pour le bouton Vérification :
    # mots-clés classiques + score + mots_score
    # -------------------------------------------------------------------------

    def _normalize_text(self, s):
        s = (s or "").lower()

        remplacements = {
            "à": "a", "á": "a", "â": "a", "ä": "a",
            "ç": "c",
            "è": "e", "é": "e", "ê": "e", "ë": "e",
            "ì": "i", "í": "i", "î": "i", "ï": "i",
            "ñ": "n",
            "ò": "o", "ó": "o", "ô": "o", "ö": "o",
            "ù": "u", "ú": "u", "û": "u", "ü": "u",
            "ý": "y", "ÿ": "y",
            "œ": "oe",
            "æ": "ae",
        }

        for src, dst in remplacements.items():
            s = s.replace(src, dst)

        return s

    def get_texte_source_verification(self):
        texte_source = self.item_value("search_text", "")

        if not texte_source:
            texte_source = self.item_value("description", "")

        if not texte_source:
            texte_source = self.item_value("titre", "")

        return texte_source or ""

    def maj_libelle_bouton_verification(self):
        """
        Met à jour le texte du bouton Vérification.

        Affichage voulu :
        - si score présent :
          Vérification | score 10 | rénovation

        - si pas de score mais mots-clés classiques trouvés :
          Vérification : porte, fenêtre

        - sinon :
          Vérification
        """

        score = self.item_value("score", 0)
        mots_score_trouves = self.item_value("mots_score_trouves", [])

        try:
            score = int(score or 0)
        except Exception:
            score = 0

        if mots_score_trouves is None:
            mots_score_trouves = []

        if isinstance(mots_score_trouves, str):
            mots_score_trouves = [mots_score_trouves]

        texte = self.get_texte_source_verification()
        mots_clefs = self.extraire_mots_cles()
        mots_clefs_trouves = self.mots_cles_presents(texte, mots_clefs)

        # Priorité : afficher le score quand il existe
        if score > 0:
            libelle = f"Vérification | score {score}"

            if mots_score_trouves:
                libelle += " | " + ", ".join(mots_score_trouves)

            self.button_generer_html.text = libelle
            return

        # Sinon, on garde ton ancien comportement :
        # affichage des mots-clés de recherche trouvés
        if mots_clefs_trouves:
            self.button_generer_html.text = "Vérification : " + ", ".join(mots_clefs_trouves)
        else:
            self.button_generer_html.text = "Vérification"

    def mots_cles_presents(self, texte, mots_clefs):
        texte_norm = self._normalize_text(texte)
        trouves = []

        for mot in mots_clefs:
            mot = (mot or "").strip()

            if not mot:
                continue

            mot_norm = self._normalize_text(mot)

            pattern = rf"(?<!\w){re.escape(mot_norm)}\w*"

            if re.search(pattern, texte_norm):
                trouves.append(mot)

        return trouves