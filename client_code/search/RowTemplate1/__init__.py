from ._anvil_designer import RowTemplate1Template
from anvil import *
import anvil.server
import re
from ...recherche_mk_html import recherche_mk_html
from .. import Context_ecran

class RowTemplate1(RowTemplate1Template):

    def __init__(self, **properties):
        self.init_components(**properties)
        # écran tel ?
        context = Context_ecran.context_screen()
        if context['screen_type']=="phone":
            self.icon_button_go_up.text = ''
            self.icon_button_go_down.text = ''
        else:
            self.icon_button_go_up.text = 'Début'
            self.icon_button_go_down.text = 'Fin'

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
        self.text_departement.text = self.item_value(
            "departement",
            ""
        )
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

        source = str(
            self.item_value("source", "") or ""
        ).strip()

        source_originale = str(
            self.item_value("source_originale", "") or ""
        ).strip()
        
        sources_detectees = self.item_value(
            "sources_detectees",
            []
        )
        
        # Certaines anciennes offres peuvent contenir
        # une chaîne simple.
        if isinstance(sources_detectees, str):
            sources_detectees = [sources_detectees]
        
        elif not isinstance(
            sources_detectees,
            (list, tuple, set)
        ):
            sources_detectees = []
        
        
        def normaliser_nom_source(valeur):
            return " ".join(
                str(valeur or "").strip().split()
            ).lower()
        
        
        # ---------------------------------------------------------
        # Source principale
        # ---------------------------------------------------------
        
        source_normalisee = normaliser_nom_source(
            source
        )
        
        source_affichee = self.nom_source_affiche(
            source
        )
        
        
        # ---------------------------------------------------------
        # Sources secondaires réellement différentes
        # ---------------------------------------------------------
        
        sources_secondaires = []
        sources_deja_ajoutees = set()
        
        if source_normalisee:
            sources_deja_ajoutees.add(
                source_normalisee
            )
        
        for valeur in sources_detectees:
        
            valeur = str(
                valeur or ""
            ).strip()
        
            valeur_normalisee = normaliser_nom_source(
                valeur
            )
        
            if not valeur_normalisee:
                continue
        
            # C'est la source principale :
            # ne pas l'afficher une deuxième fois.
            if valeur_normalisee in sources_deja_ajoutees:
                continue
        
            sources_deja_ajoutees.add(
                valeur_normalisee
            )
        
            sources_secondaires.append(
                self.nom_source_affiche(valeur)
            )
        
        
        # ---------------------------------------------------------
        # Construction du texte affiché
        # ---------------------------------------------------------
        
        if sources_secondaires:
        
            texte_source = (
                f"Source : {source_affichee}"
                " — également repérée par "
                + ", ".join(sources_secondaires)
            )
        
        elif (
            source_originale
            and normaliser_nom_source(source_originale)
            != source_normalisee
        ):
        
            texte_source = (
                f"Repérée par : {source_affichee} | "
                f"Publication : "
                f"{self.nom_source_affiche(source_originale)}"
            )
        
        else:
        
            texte_source = (
                f"Source : {source_affichee}"
                if source_affichee
                else ""
            )






        
        self.label_source.text = texte_source
        self.label_source.visible = bool(
            texte_source
        )       
        
        # Vu / non vu
        self.set_checkbox_vu_sans_event(
            bool(self.item_value("vu", False))
        )

        # Libellé du bouton Vérification :
        # couleur de correspondance + mots trouvés
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

    def nom_source_affiche(self, source):
        source = (source or "").strip()
        noms_aws = {
            "AWS-ML": "AWS / Midi-Libre",
            "AWS-DL": "AWS / Dauphiné Libéré",
            "AWS-GM": "AWS / Gazette de Montpellier",
            "AWS-NR": "AWS / Nouvelle République",
            "AWS-SO": "AWS / Sud Ouest",
            "AWS-LDM": "AWS / La Dépêche du Midi",
            "AWS-MP74": "AWS / Association des Maires 74",
        }
        return noms_aws.get(source.upper(), source)

    
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
    # Bouton Vérification
    # -------------------------------------------------------------------------
    def extraire_liste_depuis_parent_tag(self, nom_tag):
        """
        Récupère une liste de mots depuis self.parent.tag.
        Utilisé pour récupérer les mots ET saisis dans la Form search.
        """

        parent_tag = getattr(self.parent, "tag", None)
        brut = (getattr(parent_tag, nom_tag, "") or "").strip().lower()

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

    def extraire_mots_et(self):
        """
        Retourne une liste de termes de surlignage, éventuellement vide.

        Sans paramètre. En CPV, copie les expressions de l'instantané transmis
        par search ; sinon conserve l'extraction historique des mots ET.
        """
        parent_tag = getattr(self.parent, "tag", None)
        mots_obligatoires_cpv = getattr(parent_tag, "mots_obligatoires_cpv", None)
        if mots_obligatoires_cpv is not None:
            return list(mots_obligatoires_cpv)
        return self.extraire_liste_depuis_parent_tag("mots_et_saisis")

    def button_generer_html_click(self, **event_args):
        """Ouvre le détail catalogue ou le texte historique avec surlignage."""
        if self.item.get("moteur_recherche") == "catalogue_pg":
            self.afficher_detail_catalogue()
            return
        self.scroll_into_view(smooth=True, align="start")
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


        # Mots obligatoires de la recherche
        mots_cles = self.extraire_mots_et()

        # Mots OU réellement trouvés dans cette offre
        mots_ou_trouves = self.item_value("mots_ou_trouves", [])

        if mots_ou_trouves is None:
            mots_ou_trouves = []

        if isinstance(mots_ou_trouves, str):
            mots_ou_trouves = [mots_ou_trouves]

        mots_ou_a_surligner = list(mots_ou_trouves)

        # Le surlignage est facultatif : des listes vides permettent simplement
        # d'afficher le contenu sans remettre en cause la sélection du moteur.

        # Mise en forme simple du texte avant envoi au composant HTML
        texte = self.format_search_text_for_display(texte_source)

        # Création du composant HTML si besoin
        if self.comp_html is None:
            self.comp_html = recherche_mk_html()
            self.column_panel_affichage.clear()
            self.column_panel_affichage.add_component(self.comp_html)

        # Envoi des mots ET et des mots OU trouvés au composant HTML
        self.comp_html.charger(
            texte,
            mots_cles=mots_cles,
            mots_ou=mots_ou_a_surligner
        )

        self.column_panel_detail.visible = True

    def afficher_detail_catalogue(self):
        """Détail natif du catalogue dans le panneau existant ; parcours « vu » conservé.

        Seuls les champs métier sont présentés, sans HTML externe ni métadonnées.
        """
        if self.column_panel_detail.visible:
            self.column_panel_detail.visible = False
            self.button_generer_html.icon = "mi:keyboard_double_arrow_down"
            return
        ids = self.item.get("offre_ids") or [self.item.get("offre_id")]
        parent_initial = self.parent
        self.button_generer_html.enabled = False
        try:
            resultat = anvil.server.call("recette_catalogue_v3_detail", offre_ids=ids)
            if self.parent is not parent_initial or self.parent is None:
                return
            if not isinstance(resultat, dict) or type(resultat.get("ok")) is not bool:
                raise ValueError("Réponse de détail catalogue invalide.")
            if not resultat["ok"]:
                alert(resultat.get("message") or "Détail catalogue indisponible ou accès refusé.", title="Catalogue PostgreSQL")
                return
            self.presenter_detail_catalogue(resultat)
            self.column_panel_detail.visible = True
            self.button_generer_html.icon = "mi:keyboard_double_arrow_up"
            if self.checkbox_vu.checked is not True:
                self.set_checkbox_vu_sans_event(True)
                self.checkbox_vu_change()
        finally:
            self.button_generer_html.enabled = True

    def presenter_detail_catalogue(self, resultat):
        """Présente chaque fiche V4 avec ses propres champs et liens.

        Les identifiants restent dans les données ; aucun dictionnaire technique
        n'est converti en texte. Les valeurs absentes sont simplement omises.
        """
        def texte(valeur):
            if valeur is None:
                return ""
            if isinstance(valeur, (list, tuple)):
                return ", ".join(filter(None, [texte(element) for element in valeur]))
            if isinstance(valeur, dict):
                # CPV ou acheteur structurés : uniquement leurs champs publics.
                code = texte(valeur.get("code"))
                libelle = texte(valeur.get("libelle") or valeur.get("nom"))
                return " — ".join(filter(None, [code, libelle]))
            return str(valeur).strip()

        # Les mots proviennent de l'instantané de recherche, jamais des exclusions.
        mots = list(self.extraire_mots_et())
        mots_ou = self.item.get("mots_ou_trouves") or []
        if isinstance(mots_ou, str):
            mots_ou = [mots_ou]
        mots.extend(mots_ou)
        # Pour le futur texte intégral, inclure aussi les mots OU de l'instantané,
        # même s'ils n'étaient pas présents dans le résumé de cette annonce.
        parent = self.parent
        while parent is not None:
            contexte = getattr(parent, "_ctx_recherche", None)
            if isinstance(contexte, dict):
                mots.extend(contexte.get("mots_ou") or [])
                break
            parent = getattr(parent, "parent", None)

        def normaliser(valeur):
            accents = "àâäáãåçèéêëìíîïñòóôöõùúûüýÿ"
            simples = "aaaaaaceeeeiiiinooooouuuuyy"
            return "".join(simples[accents.index(c)] if c in accents else c for c in valeur.lower())

        termes = [normaliser(str(mot).strip()) for mot in mots if mot and str(mot).strip()]

        def ajouter_texte(panneau, contenu, surligner=False):
            if not surligner or not termes:
                panneau.add_component(Label(text=contenu, spacing_above="none", spacing_below="none"))
                return
            # Les lignes contenant une correspondance sont mises en gras
            # avec des Labels pour afficher les caractères de la source tels quels.
            for ligne in contenu.split("\n"):
                normalisee = normaliser(ligne)
                panneau.add_component(Label(
                    text=ligne, bold=any(terme in normalisee for terme in termes),
                    spacing_above="none", spacing_below="none"))

        def rubrique(panneau, libelle, valeur, surligner=False):
            contenu = texte(valeur)
            if contenu:
                ajouter_texte(panneau, libelle + " : " + contenu, surligner)

        def urls(entrees):
            """Extrait les URL des valeurs et des objets de provenance."""
            if isinstance(entrees, dict):
                return urls(entrees.get("lien") or entrees.get("url")) + urls(entrees.get("liens"))
            if isinstance(entrees, list):
                liens = []
                for entree in entrees:
                    liens.extend(urls(entree))
                return liens
            if isinstance(entrees, str) and entrees.lower().startswith(("https://", "http://")):
                return [entrees]
            return []

        documents = resultat.get("offres")
        if not isinstance(documents, list) or not documents:
            raise ValueError("Le détail catalogue ne contient aucune fiche exploitable.")
        if any(not isinstance(document, dict) for document in documents):
            raise ValueError("Format de fiche catalogue invalide.")

        self.column_panel_affichage.clear()
        for document in documents:
            fiche = ColumnPanel()
            rubrique(fiche, "Titre", document.get("titre"), surligner=True)
            rubrique(fiche, "Acheteur", document.get("acheteur"))
            rubrique(fiche, "Description", document.get("description"), surligner=True)
            rubrique(fiche, "Publication", document.get("date_publication"))
            rubrique(fiche, "Date limite de réponse", document.get("date_limite_reponse"))
            rubrique(fiche, "Date et heure limites de réponse", document.get("date_limite_reponse_horodatee"))
            rubrique(fiche, "Fin de diffusion", document.get("date_fin_diffusion"))
            rubrique(fiche, "CPV principal", document.get("cpv_principal"))
            rubrique(fiche, "CPV additionnels", document.get("cpv_additionnels"))
            rubrique(fiche, "CPV des lots", document.get("cpv_lots"))
            for numero, lot in enumerate(document.get("lots") or [], 1):
                if not isinstance(lot, dict):
                    continue
                reference = texte(lot.get("numero") or lot.get("numero_lot") or lot.get("lot_id")) or str(numero)
                description = " — ".join(filter(None, [
                    texte(lot.get("titre")), texte(lot.get("description")),
                ]))
                rubrique(fiche, "Lot " + reference, description or reference, surligner=True)
                rubrique(fiche, "CPV du lot", lot.get("cpv_principal") or lot.get("cpv"))
                rubrique(fiche, "CPV additionnels du lot", lot.get("cpv_additionnels"))
            rubrique(fiche, "Source", document.get("source"))

            liens = urls(document.get("liens")) + urls(document.get("provenances"))
            if not liens:
                liens = urls(document.get("lien"))
            for lien in dict.fromkeys(liens):
                fiche.add_component(Link(text=lien, url=lien, spacing_above="none", spacing_below="none"))

            integral = document.get("texte_integral")
            if isinstance(integral, str) and integral.strip():
                self.preparer_texte_complet_catalogue(fiche, integral, ajouter_texte)
            else:
                fiche.add_component(Label(
                    text="Texte complet non disponible actuellement.", italic=True,
                    font_size=12, spacing_above="none", spacing_below="none"))
            self.column_panel_affichage.add_component(fiche)

    def preparer_texte_complet_catalogue(self, fiche, integral, ajouter_texte):
        """Affiche sur demande le document intégral fourni, page par page."""
        bouton = Button(text="Afficher le texte complet", spacing_above="none", spacing_below="none")
        panneau = ColumnPanel(visible=False, spacing_above="none", spacing_below="none")
        etat = {"page": 0, "construit": False}
        # Découper entre les mots pour préserver les occurrences surlignées.
        pages = []
        debut = 0
        while debut < len(integral):
            fin = min(debut + 2500, len(integral))
            if fin < len(integral):
                coupure = integral.rfind(" ", debut, fin)
                if coupure > debut:
                    fin = coupure + 1
            pages.append(integral[debut:fin])
            debut = fin

        def afficher_page(**event_args):
            panneau.clear()
            ajouter_texte(panneau, pages[etat["page"]], True)
            if len(pages) > 1:
                panneau.add_component(Label(text="Page %s / %s" % (etat["page"] + 1, len(pages))))
                precedent = Button(text="Précédente", enabled=etat["page"] > 0)
                suivant = Button(text="Suivante", enabled=etat["page"] < len(pages) - 1)
                def changer(delta):
                    etat["page"] += delta
                    afficher_page()
                precedent.set_event_handler("click", lambda **e: changer(-1))
                suivant.set_event_handler("click", lambda **e: changer(1))
                panneau.add_component(precedent)
                panneau.add_component(suivant)

        def basculer(**event_args):
            if not etat["construit"]:
                afficher_page()
                etat["construit"] = True
            panneau.visible = not panneau.visible
            bouton.text = "Masquer le texte complet" if panneau.visible else "Afficher le texte complet"

        bouton.set_event_handler("click", basculer)
        fiche.add_component(bouton)
        fiche.add_component(panneau)

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
        """
        Retourne le texte réellement utile pour la vérification visuelle.
    
        Important :
        la correspondance des mots OU est calculée dans search sur plusieurs champs :
        titre, description, search_text, acheteur, lieu, nature, procedure.
    
        Donc l'affichage de vérification doit aussi reprendre ces champs,
        sinon un mot peut être considéré comme trouvé mais invisible au clic.
        """

        champs = [
            ("Titre", self.item_value("titre", "")),
            ("Acheteur", self.item_value("acheteur", "")),
            ("Lieu", self.item_value("lieu", "")),
            ("Département", self.item_value("departement", "")),
            ("Nature", self.item_value("nature", "")),
            ("Procédure", self.item_value("procedure", "")),
            ("Référence", self.item_value("reference", "")),
            ("Description", self.item_value("description", "")),
            ("Texte source", self.item_value("search_text", "")),
        ]

        blocs = []
        deja_vus = set()

        for libelle, valeur in champs:
            texte = str(valeur or "").strip()

            if not texte:
                continue

            if texte in ("-", "Non renseigné", "None"):
                continue

            # Evite d'afficher deux fois exactement le même bloc
            cle = self._normalize_text(
                re.sub(r"\s+", " ", texte)
            ).strip()

            if cle in deja_vus:
                continue

            deja_vus.add(cle)
            blocs.append(f"{libelle} : {texte}")

        return "\n\n".join(blocs)

    def maj_libelle_bouton_verification(self):
        """
        Met à jour le texte et la couleur du bouton Vérification.
    
        Affichage simple :
        Cliquez pour vérifier (mot_et_1, mot_et_2, mot_ou_trouvé_1, ...)
    
        - les mots ET sont affichés en premier
        - les mots OU trouvés dans l'offre sont affichés ensuite
        - on n'affiche pas les libellés ET / OU
        - l'intérêt reste porté par la couleur et le tri
        """

        self.button_generer_html.role = "bt-verification-base"

        nb_total = self.item_value("nb_mots_ou_total", 0)
        taux = self.item_value("taux_mots_ou", 0)

        mots_ou_trouves = self.item_value("mots_ou_trouves", [])
        role_interet = self.item_value("role_interet", "")

        try:
            nb_total = int(nb_total or 0)
        except Exception:
            nb_total = 0

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

        mots_et = self.extraire_mots_et()

        # ------------------------------------------------------------
        # Couleur du bouton
        # ------------------------------------------------------------
        # Aucun mot OU saisi OU aucun mot OU trouvé :
        # bouton gris pour signaler "critère ET seulement"
        if nb_total == 0 or taux == 0:
            self.button_generer_html.role = "bt-interet-0"

        # Mots OU trouvés : rôle calculé dans search
        elif role_interet:
            self.button_generer_html.role = role_interet

        # Sécurité pour anciennes offres sauvegardées sans role_interet
        else:
            if taux <= 20:
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
        # Texte simple du bouton
        # ------------------------------------------------------------
        mots_affiches = []

        for mot in mots_et + mots_ou_trouves:
            mot = str(mot or "").strip()

            if mot and mot not in mots_affiches:
                mots_affiches.append(mot)

        numero = self.item_value("numero_offre", "")
        total = self.item_value("nb_offres_total", "")

        numero_texte = ""

        if numero and total:
            numero_texte = f"{numero}/{total}"        


        if mots_affiches:
            if numero_texte:
                self.button_generer_html.text = (
                    f"{numero_texte} - Cliquez pour vérifier; "
                    + ", ".join(mots_affiches)
                )
            else:
                self.button_generer_html.text = (
                    "Cliquez pour vérifier; "
                    + ", ".join(mots_affiches)
                )
        else:
            if numero_texte:
                self.button_generer_html.text = f"{numero_texte} - Cliquez pour vérifier"
            else:
                self.button_generer_html.text = "Cliquez pour vérifier"

    def icon_button_go_up_click(self, **event_args):
        self.parent.raise_event(
            "x-icon_button_go_up",
        )

    def icon_button_go_down_click(self, **event_args):
        self.parent.raise_event(
            "x-icon_button_go_down",
        )
