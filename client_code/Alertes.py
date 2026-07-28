from anvil import *
import anvil.server


def _echapper_html(texte):
    """
    Empêche le texte reçu d'être interprété comme du HTML.
    Les retours à la ligne sont conservés.
    """
    return (
        str(texte)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
            .replace("\n", "<br>")
    )


def afficher_information(message, titre="Information"):
    """
    Affiche une information standard dans des tons bleu pastel.

    Exemple :
        afficher_information(
            "La recherche est terminée.",
            titre="Information"
        )
    """

    message_html = _echapper_html(message)

    # ==========================================================
    # Zone du message
    # ==========================================================

    texte = RichText(
        format="restricted_html",
        content=f"""
        <div style="
            width:100%;
            box-sizing:border-box;
            background-color:#E6F4FF;
            border:2px solid #8CC8F2;
            border-radius:12px;
            padding:20px;
        ">

            <h2 style="
                color:#174A6E;
                margin-top:0;
                margin-bottom:16px;
                font-size:22px;
                font-weight:700;
            ">
                Information
            </h2>

            <div style="
                color:#173F5F;
                font-size:16px;
                font-weight:500;
                line-height:1.6;
            ">
                {message_html}
            </div>

        </div>
        """
    )

    # ==========================================================
    # Bouton Ok bleu pastel
    # ==========================================================

    bouton_ok = Button(
        text="Ok",
        background="#A9D8F5",
        foreground="#123F5A",
        bold=True,
        font_size=16
    )

    zone_bouton = FlowPanel(
        align="right",
        spacing_above="medium",
        spacing_below="small"
    )

    zone_bouton.add_component(bouton_ok)

    # ==========================================================
    # Contenu complet
    # ==========================================================

    contenu = ColumnPanel()
    contenu.add_component(texte)
    contenu.add_component(zone_bouton)

    def fermer_alerte(**event_args):
        contenu.raise_event(
            "x-close-alert",
            value=True
        )

    bouton_ok.set_event_handler(
        "click",
        fermer_alerte
    )

    alert(
        content=contenu,
        title=titre,
        large=True,
        dismissible=False,
        buttons=[]
    )


def afficher_avertissement(
    message,
    titre="Traitement non effectué"
):
    """
    Affiche une information lorsqu'un traitement n'a pas été effectué.

    À utiliser notamment lorsque :
    - une donnée existe déjà ;
    - une action n'a pas pu être réalisée ;
    - le résultat n'est pas une erreur grave ;
    - l'utilisateur doit simplement être informé.

    Exemple :
        afficher_avertissement(
            "Cette recherche est déjà enregistrée "
            "comme veille quotidienne.",
            titre="Veille déjà enregistrée"
        )
    """

    message_html = _echapper_html(message)

    # ==========================================================
    # Zone du message
    # ==========================================================

    texte = RichText(
        format="restricted_html",
        content=f"""
        <div style="
            width:100%;
            box-sizing:border-box;
            background-color:#FFF4D6;
            border:2px solid #E0B45A;
            border-radius:12px;
            padding:20px;
        ">

            <h2 style="
                color:#765000;
                margin-top:0;
                margin-bottom:16px;
                font-size:22px;
                font-weight:700;
            ">
                Information
            </h2>

            <div style="
                color:#5C430C;
                font-size:16px;
                font-weight:500;
                line-height:1.6;
            ">
                {message_html}
            </div>

        </div>
        """
    )

    # ==========================================================
    # Bouton Ok jaune-orangé pastel
    # ==========================================================

    bouton_ok = Button(
        text="Ok",
        background="#F6D58A",
        foreground="#5A410B",
        bold=True,
        font_size=16
    )

    zone_bouton = FlowPanel(
        align="right",
        spacing_above="medium",
        spacing_below="small"
    )

    zone_bouton.add_component(bouton_ok)

    # ==========================================================
    # Contenu complet
    # ==========================================================

    contenu = ColumnPanel()
    contenu.add_component(texte)
    contenu.add_component(zone_bouton)

    def fermer_alerte(**event_args):
        contenu.raise_event(
            "x-close-alert",
            value=True
        )

    bouton_ok.set_event_handler(
        "click",
        fermer_alerte
    )

    alert(
        content=contenu,
        title=titre,
        large=True,
        dismissible=False,
        buttons=[]
    )




def afficher_reussite(message):
    """
    Affiche une alerte après la réussite d'un traitement.

    Le bouton Ok est personnalisé en vert pastel.
    """

    message_html = _echapper_html(message)

    # ==========================================================
    # Message de réussite
    # ==========================================================

    texte = RichText(
        format="restricted_html",
        content=f"""
        <div style="
            width:100%;
            box-sizing:border-box;
            background-color:#E2F8E7;
            border:2px solid #78C58C;
            border-radius:12px;
            padding:20px;
        ">

            <h2 style="
                color:#176B32;
                margin-top:0;
                margin-bottom:16px;
                font-size:22px;
                font-weight:700;
            ">
                Réussite
            </h2>

            <div style="
                color:#173D23;
                font-size:16px;
                font-weight:600;
                line-height:1.6;
            ">
                {message_html}
            </div>

        </div>
        """
    )

    # ==========================================================
    # Bouton Ok personnalisé
    # ==========================================================

    bouton_ok = Button(
        text="Ok",
        background="#A9DFB5",
        foreground="#123D20",
        bold=True,
        font_size=16
    )

    zone_bouton = FlowPanel(
        align="right",
        spacing_above="medium",
        spacing_below="small"
    )

    zone_bouton.add_component(bouton_ok)

    # ==========================================================
    # Contenu complet de l'alerte
    # ==========================================================

    contenu = ColumnPanel()
    contenu.add_component(texte)
    contenu.add_component(zone_bouton)

    # ==========================================================
    # Fermeture de l'alerte
    # ==========================================================

    def fermer_alerte(**event_args):
        contenu.raise_event(
            "x-close-alert",
            value=True
        )

    bouton_ok.set_event_handler(
        "click",
        fermer_alerte
    )

    alert(
        content=contenu,
        title="Réussite",
        large=True,
        dismissible=False,

        # Aucun bouton standard Anvil
        buttons=[]
    )





"""
Appel à la méthode demander_choix:

confirmation = demander_choix(
    titre="Création d’une veille quotidienne",
    message=(
        "Créer une veille quotidienne à partir des paramètres "
        "de cette recherche ?<br><br>"

        "<span style=\"background-color:#FFF1A8; "                  surbrillance
        "padding:3px 6px; border-radius:4px;\">"
        "Cette veille vérifiera chaque jour les nouvelles offres"
        "</span> "

        "éventuellement publiées la veille."
    ),
    autoriser_html=True
)

if confirmation is not True:
    return
-------------------------------------
autres possibilités:
"<strong>Texte en gras</strong>"                                     gras
"<span style=\"color:#176B32;\">Texte vert</span>"                   couleur
"<u><strong>Texte gras souligné</strong></u>"                        gras et souligné

"""
def demander_choix(
    titre,
    message,
    autoriser_html=False
):
    """
    Affiche une alerte avec les boutons Oui et Non.

    autoriser_html=False :
        le message est affiché comme du texte sécurisé.

    autoriser_html=True :
        certaines balises HTML peuvent être utilisées :
        <strong>, <b>, <i>, <span>, <br>, etc.

    Retourne :
        True si l'utilisateur clique sur Oui
        False si l'utilisateur clique sur Non
    """

    if autoriser_html:
        # Conserve le HTML et transforme les retours à la ligne.
        message_html = str(message).replace("\n", "<br>")
    else:
        # Fonctionnement sécurisé habituel.
        message_html = _echapper_html(message)

    texte = RichText(
        format="restricted_html",
        enable_slots=False,
        content=f"""
        <div style="
            width:100%;
            box-sizing:border-box;
            background-color:#E3F6E8;
            border:2px solid #78C58C;
            border-radius:12px;
            padding:20px;
        ">

            <h2 style="
                color:#185C2D;
                margin-top:0;
                margin-bottom:16px;
                font-size:22px;
                font-weight:700;
            ">
                Voulez-vous ...
            </h2>

            <div style="
                color:#173D23;
                font-size:16px;
                font-weight:500;
                line-height:1.6;
            ">
                {message_html}
            </div>

        </div>
        """
    )

    bouton_oui = Button(
        text="Oui",
        background="#A9DFB5",
        foreground="#123D20",
        bold=True,
        font_size=16
    )

    bouton_non = Button(
        text="Non",
        background="#D7EFDC",
        foreground="#23482D",
        bold=True,
        font_size=16
    )

    zone_boutons = FlowPanel(
        align="right",
        spacing_above="medium",
        spacing_below="small"
    )

    zone_boutons.add_component(bouton_oui)
    zone_boutons.add_component(bouton_non)

    contenu = ColumnPanel()
    contenu.add_component(texte)
    contenu.add_component(zone_boutons)

    def repondre_oui(**event_args):
        contenu.raise_event(
            "x-close-alert",
            value=True
        )

    def repondre_non(**event_args):
        contenu.raise_event(
            "x-close-alert",
            value=False
        )

    bouton_oui.set_event_handler(
        "click",
        repondre_oui
    )

    bouton_non.set_event_handler(
        "click",
        repondre_non
    )

    resultat = alert(
        content=contenu,
        title=titre,
        large=True,
        dismissible=False,
        buttons=[]
    )

    return resultat