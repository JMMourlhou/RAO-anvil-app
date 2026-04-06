from ._anvil_designer import RowTemplate1Template
from anvil import *
import anvil.server
import re
from ...recherche_mk_html import recherche_mk_html
import m3.components as m3

class RowTemplate1(RowTemplate1Template):
    def __init__(self, **properties):
        self.init_components(**properties)

        self.f = get_open_form()
        self.comp_html = None

        # plus besoin de hit_ids / hit_index / container_id
        # car on ne navigue plus entre les occurrences
        #self.button_aller_mot.visible = False

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

    def checkbox_vu_change(self, **event_args):
        with anvil.server.no_loading_indicator:
            result = anvil.server.call("check", self.item, self.checkbox_vu.checked)
        if not result:
            alert("Erreur en modification")

    def toggle_icon_button_1_click(self, **event_args):
        result = anvil.server.call("del_1", self.item)
        if not result:
            alert("Erreur en effacement")
        else:
            open_form('Main', "check")

    def extraire_mots_cles(self):
        brut = (self.f.text_box_mot_clef.text or "").strip().lower()
        if not brut:
            return []

        # normalisation simple
        texte = brut.replace(";", ",").replace("\n", ",")
        texte = texte.replace(" et ", ",")
        texte = texte.replace(" ou ", ",")

        morceaux = [m.strip() for m in texte.split(",") if m.strip()]

        # dédoublonnage en gardant l’ordre
        mots_uniques = []
        deja_vus = set()
        for mot in morceaux:
            if mot not in deja_vus:
                deja_vus.add(mot)
                mots_uniques.append(mot)

        return mots_uniques

    def button_generer_html_click(self, **event_args):
        """Affiche le texte avec mots-clés surlignés en couleurs"""

        # check du check_box 'vu'
        self.checkbox_vu.checked = True
        self.checkbox_vu_change()

        # masquer si déjà affiché
        if self.column_panel_detail.visible is True:
            self.column_panel_detail.visible = False
            return

        # contenu à afficher
        #texte = self.item_value("search_text", "")
        try:
            texte_source = self.item_value("search_text", "")
        except Exception:
            texte_source = ""
        
        if not texte_source:
            try:
                texte_source = self.item["titre"]
            except Exception:
                texte_source = ""
        
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
        - ajoute des sauts de ligne avant les libellés fréquents
        - supprime quelques lignes techniques parasites
        - compacte les espaces
        """
        texte = str(texte or "")
    
        # normalisation des fins de ligne
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
    
        # ajoute un saut de ligne avant chaque label
        for label in labels:
            texte = re.sub(
                rf"\s*{re.escape(label)}\s*",
                f"\n\n{label} ",
                texte
            )
    
        # met aussi les URL seules sur leur propre ligne
        texte = re.sub(r"\s+(https?://)", r"\n\1", texte)
    
        # supprime quelques lignes techniques fréquentes
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
    
        # évite les triples sauts de ligne
        texte = re.sub(r"\n{3,}", "\n\n", texte)
    
        return texte.strip()