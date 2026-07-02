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

        # Evite qu'une modification par code déclenche une sauvegarde inutile
        self._ignore_checkbox_vu_change = False

        # Dates
        self.text_date_publication.text = self.format_date_fr(
            self.item_value("date_publication", "")
        )

        self.text_date_limite_rep.text = self.format_date_fr(
            self.item_value("date_limite_rep", "")
        )

        # Champs principaux
        self.text_titre.text = self.item_value("titre", "")

        # Dans les résultats, la clé est souvent lien_source, pas lien
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
        self.set_checkbox_vu_sans_event(
            bool(self.item_value("vu", False))
        )
        
        
            
        # Libellé du bouton Vérification :
        # niveau de correspondance + mots OU trouvés
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

        try:
            return valeur.strftime("%d/%m/%Y")
        except Exception:
            pass

        try:
            valeur = str(valeur).strip()

            if not valeur:
                return "-"

            valeur = valeur.split("T")[0]
            valeur = valeur.split(" ")[0]

            if "/" in valeur:
                return valeur

            morceaux = valeur.split("-")

            if len(morceaux) == 3:
                annee, mois, jour = morceaux
                return f"{jour}/{mois}/{annee}"

        except Exception:
            pass

        return "-"

    def set_checkbox_vu_sans_event(self, valeur):
        """
        Modifie checkbox_vu.checked sans déclencher le traitement parent.
        """

        self._ignore_checkbox_vu_change = True
        self.checkbox_vu.checked = bool(valeur)
        self._ignore_checkbox_vu_change = False

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

        # On marque comme vu
        if self.checkbox_vu.checked is not True:
            self.set_checkbox_vu_sans_event(True)
            self.checkbox_vu_change()

    def checkbox_vu_change(self, **event_args):
        """
        Evènement levé vers la forme mère.
        La sauvegarde serveur est maintenant faite par le parent search,
        car la source officielle est histo['offres'].
        """

        if self._ignore_checkbox_vu_change:
            return

        checked = bool(self.checkbox_vu.checked)

        # On met aussi à jour le dictionnaire courant en mémoire
        try:
            self.item["vu"] = checked
        except Exception:
            pass

        self.parent.raise_event(
            "x-checkbox-vu-changee",
            checked=checked,
            item=self.item
        )

    def toggle_icon_button_del_click(self, **event_args):
        """
        Demande au parent de supprimer l'offre.
        La RowTemplate ne supprime rien directement.
        """

        self.parent.raise_event(
            "x-del-offre",
            item=self.item
        )

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
        Affiche le texte avec les mots-clés recherchés surlignés.
        """
    
        # Changement apparence du bouton
        if self.column_panel_detail.visible is False:
            self.button_generer_html.icon = "mi:keyboard_double_arrow_up"
    
            # On marque comme vu
            if self.checkbox_vu.checked is not True:
                self.set_checkbox_vu_sans_event(True)
                self.checkbox_vu_change()
    
        else:
            self.button_generer_html.icon = "mi:keyboard_double_arrow_down"
            self.column_panel_detail.visible = False
            return
    
        # Contenu brut à afficher
        texte_source = self.get_texte_source_verification()
    
        if not texte_source:
            alert("Aucun texte disponible pour cette offre !")
            return
    
  
        # Mots-clés de recherche :
        # obligatoires + mots OU saisis
        mots_cles = self.extraire_mots_cles()
        
        # Mots OU réellement trouvés dans cette offre
        mots_ou_trouves = self.item_value("mots_ou_trouves", [])
        
        if mots_ou_trouves is None:
            mots_ou_trouves = []
        
        if isinstance(mots_ou_trouves, str):
            mots_ou_trouves = [mots_ou_trouves]
        
        # Ancien nom conservé pour compatibilité avec recherche_mk_html.
        # Ici, mots_score ne signifie plus "score manuel".
        # Il contient les mots OU réellement trouvés dans l'offre.
        mots_score = list(mots_ou_trouves)
        
        # Sécurité : si aucun mot à mettre en évidence
        if not mots_cles and not mots_score:
            alert("Aucun mot-clé à mettre en évidence !")
            return
        
        print("===== DEBUG VERIFICATION ROW =====")
        print("mots_cles envoyés au HTML :", mots_cles)
        print("mots_ou_trouves :", mots_ou_trouves)
        print("mots_score envoyés au HTML :", mots_score)
        print("==================================")
    
        # Mise en forme simple du texte avant envoi au composant HTML
        texte = self.format_search_text_for_display(texte_source)
    
        # Création du composant HTML si besoin
        if self.comp_html is None:
            self.comp_html = recherche_mk_html()
            self.column_panel_affichage.clear()
            self.column_panel_affichage.add_component(self.comp_html)
    
        # Envoi du texte + mots-clés + mots de scoring au composant HTML
        self.comp_html.charger(
            texte,
            mots_cles,
            mots_score=mots_score
        )
    
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

        texte = texte.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
        texte = texte.replace("\r\n", "\n").replace("\r", "\n")

        lignes = [
            re.sub(r"[ \t]+", " ", ligne).strip()
            for ligne in texte.split("\n")
        ]

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

            if re.fullmatch(
                r"Heure\s*:\s*\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?",
                l,
                flags=re.I
            ):
                continue

            lignes.append(l)

        texte = "\n".join(lignes)
        texte = re.sub(r"\n{3,}", "\n\n", texte)

        return texte.strip()

    # -------------------------------------------------------------------------
    # Fonctions pour le bouton Vérification
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
        Met à jour le texte et la couleur du bouton Vérification
        selon le niveau d'intérêt calculé dans search.

        Nouvelle logique :
        - sans mots OU : pas de couleur d'intérêt, tri par date
        - avec mots OU : couleur selon le taux de mots OU trouvés
        """

        self.button_generer_html.role = ""

        nb_total = self.item_value("nb_mots_ou_total", 0)
        nb_trouves = self.item_value("nb_mots_ou_trouves", 0)
        taux = self.item_value("taux_mots_ou", 0)

        mots_ou_trouves = self.item_value("mots_ou_trouves", [])
        libelle_interet = self.item_value("libelle_interet", "")
        role_interet = self.item_value("role_interet", "")

        try:
            nb_total = int(nb_total or 0)
        except Exception:
            nb_total = 0

        try:
            nb_trouves = int(nb_trouves or 0)
        except Exception:
            nb_trouves = 0

        try:
            taux = int(taux or 0)
        except Exception:
            taux = 0

        if mots_ou_trouves is None:
            mots_ou_trouves = []

        if isinstance(mots_ou_trouves, str):
            mots_ou_trouves = [mots_ou_trouves]

        mots_ou_trouves = [
            str(m or "").strip()
            for m in mots_ou_trouves
            if str(m or "").strip()
        ]

        # ------------------------------------------------------------
        # Aucun mot OU : pas de niveau d'intérêt.
        # ------------------------------------------------------------
        if nb_total == 0:
            self.button_generer_html.role = ""
            self.button_generer_html.text = "Vérification"
            return

        # ------------------------------------------------------------
        # Avec mots OU : rôle CSS calculé dans search.
        # ------------------------------------------------------------
        if role_interet:
            self.button_generer_html.role = role_interet
        else:
            # Sécurité si ancienne offre sans role_interet.
            if taux == 0:
                self.button_generer_html.role = "bt-interet-0"
            elif taux <= 20:
                self.button_generer_html.role = "bt-interet-20"
            elif taux <= 39:
                self.button_generer_html.role = "bt-interet-39"
            elif taux <= 59:
                self.button_generer_html.role = "bt-interet-59"
            elif taux <= 79:
                self.button_generer_html.role = "bt-interet-79"
            elif taux < 100:
                self.button_generer_html.role = "bt-interet-99"
            else:
                self.button_generer_html.role = "bt-interet-100"

        # ------------------------------------------------------------
        # Libellé utilisateur.
        # ------------------------------------------------------------
        if taux == 100 and nb_trouves == nb_total:
            libelle = "Vérification · tous les mots trouvés"

            # Pas besoin d'afficher le pourcentage à 100 %.
            if mots_ou_trouves:
                libelle += " : " + ", ".join(mots_ou_trouves)

        elif taux == 0:
            libelle = "Vérification · aucun mot additionel trouvé"

        else:
            if not libelle_interet:
                libelle_interet = ""

            libelle = f"Vérification · {libelle_interet} ({taux} %) de mots trouvés"

            if mots_ou_trouves:
                libelle += " : " + ", ".join(mots_ou_trouves)

        self.button_generer_html.text = libelle

    def mots_cles_presents(self, texte, mots_clefs):
        texte_norm = self._normalize_text(texte)
        trouves = []
    
        for mot in mots_clefs:
            mot = (mot or "").strip()
    
            if not mot:
                continue
    
            mot_norm = self._normalize_text(mot)
    
            if not mot_norm:
                continue
    
            if len(mot_norm) <= 4:
                pattern = rf"(?<![a-z0-9]){re.escape(mot_norm)}(?![a-z0-9])"
                present = re.search(pattern, texte_norm) is not None
            else:
                present = mot_norm in texte_norm
    
            if present:
                trouves.append(mot)
    
        return trouves