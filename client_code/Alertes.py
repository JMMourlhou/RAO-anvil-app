from anvil import *


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
    Affiche une alerte d'information standard.
    """

    message_html = _echapper_html(message)

    contenu = RichText(
        format="restricted_html",
        content=f"""
        <div style="
            color:#075985;
            font-size:16px;
            line-height:1.5;
            padding:10px 4px;
        ">
            {message_html}
        </div>
        """
    )

    alert(
        content=contenu,
        title=titre,
        large=True,
        dismissible=False,

        # Rôle CSS de l'alerte d'information
        role="alert-information",

        buttons=[
            ("Ok", True, "primary")
        ]
    )


def afficher_reussite(message):
    """
    Affiche une alerte après la réussite d'un traitement.
    """

    message_html = _echapper_html(message)

    contenu = RichText(
        format="restricted_html",
        content=f"""
        <div style="
            color:#166534;
            font-size:16px;
            font-weight:600;
            line-height:1.5;
            padding:10px 4px;
        ">
            {message_html}
        </div>
        """
    )

    alert(
        content=contenu,
        title="Réussite",
        large=True,
        dismissible=False,

        # Rôle CSS de l'alerte de réussite
        role="alert-reussite",

        buttons=[
            ("Ok", True, "primary")
        ]
    )


def demander_choix(titre, message):
    """
    Affiche une alerte avec les boutons Oui et Non.

    Retourne :
        True si l'utilisateur clique sur Oui
        False si l'utilisateur clique sur Non
    """

    message_html = _echapper_html(message)

    contenu = RichText(
        format="restricted_html",
        content=f"""
        <div style="
            color:#713f12;
            font-size:16px;
            line-height:1.5;
            padding:10px 4px;
        ">
            {message_html}
        </div>
        """
    )

    resultat = alert(
        content=contenu,
        title=titre,
        large=True,
        dismissible=False,

        # Rôle CSS de l'alerte de confirmation
        role="alert-choix",

        buttons=[
            ("Oui", True, "primary"),
            ("Non", False)
        ]
    )

    return resultat