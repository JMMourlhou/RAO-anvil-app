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

        try:
            self.text_date_publication.text = str(self.item['date_publication'].strftime("%d/%m/%Y"))
        except Exception:
            self.text_date_publication.text = "-"

        self.text_titre.text = self.item_value('titre', "")
        self.link_lien.text = self.item_value('lien', "")
        self.text_departement.text = self.item_value('departement', "")
        try:
            self.text_date_limite_rep.text = str(self.item['date_limite_rep'].strftime("%d/%m/%Y"))
        except Exception:
            self.text_date_limite_rep.text = "-"

        self.checkbox_vu.checked = self.item_value('vu', False)
        
        # affichage du contenu du Bt 'vérification'
        self.button_generer_html.text = "Vérification"

    def form_show(self, **event_args):
        self.maj_libelle_bouton_verification()

    def item_value(self, key, default=None):
        try:
            value = self.item[key]
            if value is None:
                return default
            return value
        except Exception:
            return default

    def link_lien_click(self, **event_args):
        from anvil.js import window
        window.open(self.link_lien.text)
        self.checkbox_vu.checked = True
        self.checkbox_vu_change()

    def checkbox_vu_change(self, **event_args):                 # EVENEMENT levé/raised
        self.parent.raise_event(
            "x-checkbox-vu-changee",                                   # nom de l'Evenement raised
            checked=self.checkbox_vu.checked,                          # info: état du check box (True / False)
            item=self.item                                             # quelle est la row qui a été changée
        )
        with anvil.server.no_loading_indicator:
            result = anvil.server.call("check", self.item, self.checkbox_vu.checked)
        if not result:
            alert("Erreur en modification")

    def toggle_icon_button_1_click(self, **event_args):
        result = anvil.server.call("del_1", self.item)
        if not result:
            alert("Erreur en effacement")
        else:
            open_form('Main_large_screen', "check")

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

    def button_generer_html_click(self, **event_args):
        """Affiche le texte avec mots-clés surlignés en couleurs"""

        # Changement apparence du bouton:
        if self.column_panel_detail.visible is False:  # Le panneau n'est pas encore affiché
            # self.button_generer_html.text = "Retour"
            self.button_generer_html.icon = "mi:keyboard_double_arrow_up"
            # check du check_box 'vu'
            self.checkbox_vu.checked = True
            self.checkbox_vu_change()
            # le column_panel_detail sera rendu visible plus bas
        else:
            # self.button_generer_html.text = "Vérification"
            self.button_generer_html.icon = "mi:keyboard_double_arrow_down"
            self.column_panel_detail.visible = False
            return
    
        # contenu à afficher
        texte_source = self.get_texte_source_verification()
        texte = self.format_search_text_for_display(texte_source)
        mots_cles = self.extraire_mots_cles()
    
        if not texte:
            alert("Aucun texte disponible pour cette offre !")
            return
    
        if not mots_cles:
            alert("Aucun mot-clé saisi !")
            return
    
        # création du composant HTML si besoin
        if self.comp_html is None:
            self.comp_html = recherche_mk_html()
            self.column_panel_affichage.clear()
            self.column_panel_affichage.add_component(self.comp_html)
    
        # envoi du texte + mots-clés au composant
        self.comp_html.charger(texte, mots_cles)
    
        self.column_panel_detail.visible = True

    def format_search_text_for_display(self, texte):
        """
        Rend le texte plus lisible avant surbrillance :
        - garde les retours à la ligne existants
        - convertit les \n littéraux en vrais sauts de ligne
        - ajoute des sauts de ligne avant les libellés fréquents
        - supprime quelques lignes techniques parasites
        - compacte les espaces
        """
        texte = str(texte or "")
    
        # IMPORTANT : convertit les \n littéraux en vrais retours ligne
        texte = texte.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
    
        # normalisation des fins de ligne réelles
        texte = texte.replace("\r\n", "\n").replace("\r", "\n")
    
        # compacte les espaces, mais garde les \n
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

    """ ==============================================================================================
    Fonctions pour l'affichage du ou des mots clés dans le bouton 'Vérification'
    """
    
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
        texte = self.get_texte_source_verification()
        mots_clefs = self.extraire_mots_cles()
    
        trouves = self.mots_cles_presents(texte, mots_clefs)
    
        if trouves:
            self.button_generer_html.text = "Vérification : " + ", ".join(trouves)
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
