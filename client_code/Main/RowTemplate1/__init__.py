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
        self.hit_ids = []
        self.hit_index = -1
        raw_uid = str(
            self.item_value("idweb")
            or self.item_value("lien")
            or id(self)
        )
        self.container_id = "zone_" + re.sub(r"[^A-Za-z0-9_-]", "_", raw_uid)
    
        self.button_aller_mot.visible = False
    
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
        return morceaux

    def button_generer_html_click(self, **event_args):
        """Affiche le texte avec mots-clés surlignés dans cette ligne"""
        
        # Ne plus afficher les détails
        if self.column_panel_detail.visible is True:
            self.column_panel_detail.visible = False
            return
            
        # prends le contenu de l'offre
        texte = (
            self.item["search_text"]
            or ""
        )
        mots_cles = self.extraire_mots_cles()
        
        if not texte:
            alert("Aucun texte disponible pour cette offre !")
            return

        if not mots_cles:
            alert("Aucun mot-clé saisi !")
            return

        html_genere, self.hit_ids = self.generer_html_mots_cles(
            texte=texte,
            mots_cles=mots_cles,
            container_id=self.container_id
        )

        self.hit_index = -1
        self.comp_html = recherche_mk_html(html_genere=html_genere)

        # IMPORTANT :
        # ce column_panel_affichage doit être dans RowTemplate1
        self.column_panel_affichage.clear()
        self.column_panel_affichage.add_component(self.comp_html)
        self.column_panel_detail.visible = True
        if len(self.hit_ids) > 0:
            self.button_aller_mot.visible = True

        if self.hit_ids:
            # va directement à la 1ère occurrence
            self.hit_index = 0
            self.comp_html.aller_a_occurrence(self.hit_ids[self.hit_index], self.container_id)

    def button_aller_mot_click(self, **event_args):
        """Va à l'occurrence suivante"""
        if self.comp_html is None:
            alert("Aucun texte affiché !")
            return

        if not self.hit_ids:
            alert("Aucune occurrence trouvée !")
            return

        self.hit_index = (self.hit_index + 1) % len(self.hit_ids)
        self.comp_html.aller_a_occurrence(self.hit_ids[self.hit_index], self.container_id)

    def generer_html_mots_cles(self, texte, mots_cles, container_id):
        texte = texte or ""
        mots_cles = [m.strip() for m in (mots_cles or []) if m and m.strip()]
    
        style_html = """
        <style>
        .kw-hit {
            background: #fff19c;
            padding: 0 1px;
            border-radius: 2px;
        }
        .kw-current {
            background: #ffb300 !important;
        }
        </style>
        """
    
        if not mots_cles:
            contenu = self.escape_html(texte).replace("\n", "<br>")
            html_genere = f"""
            {style_html}
            <div id="{container_id}">
            {contenu}
            </div>
            """
            return html_genere, []
    
        mots_uniques = sorted(set(mots_cles), key=len, reverse=True)
    
        pattern = re.compile(
            "|".join(re.escape(m) for m in mots_uniques),
            re.IGNORECASE
        )
    
        morceaux = []
        hit_ids = []
        last = 0
        num = 0
    
        for match in pattern.finditer(texte):
            morceaux.append(self.escape_html(texte[last:match.start()]))
    
            num += 1
            hit_id = f"{container_id}_kw_hit_{num}"
            hit_ids.append(hit_id)
    
            mot_trouve = self.escape_html(match.group(0))
            morceaux.append(f'<mark id="{hit_id}" class="kw-hit">{mot_trouve}</mark>')
    
            last = match.end()
    
        morceaux.append(self.escape_html(texte[last:]))
    
        contenu = "".join(morceaux).replace("\n", "<br>")
    
        html_genere = f"""
        {style_html}
        <div id="{container_id}">
        {contenu}
        </div>
        """
    
        return html_genere, hit_ids

    def escape_html(self, s):
        s = s or ""
        return (
        s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )    