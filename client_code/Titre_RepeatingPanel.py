"""Fonctions d'affichage des RepeatingPanel encadrés."""

from anvil.js import get_dom_node


CLASSE_ROLE = "anvil-role-repeating-panel-rounded"
SELECTEUR_ROLE = ".anvil-role-repeating-panel-rounded"


def obtenir_noeud_cadre(repeating_panel):
    """Retourne le nœud DOM portant le rôle repeating-panel-rounded."""

    noeud = get_dom_node(repeating_panel)

    # Cas où le rôle est directement porté par le nœud Anvil.
    if noeud.classList.contains(CLASSE_ROLE):
        return noeud

    # Cas où Anvil place le rôle sur un conteneur parent.
    noeud_cadre = noeud.closest(SELECTEUR_ROLE)

    if noeud_cadre is not None:
        return noeud_cadre

    # Sécurité si le rôle se trouve sur un élément interne.
    noeud_cadre = noeud.querySelector(SELECTEUR_ROLE)

    return noeud_cadre


def definir_titre_repeating_panel(repeating_panel, titre):
    """Définit le titre intégré au cadre d'un RepeatingPanel."""

    noeud_cadre = obtenir_noeud_cadre(repeating_panel)

    if noeud_cadre is None:
        print("Rôle 'repeating-panel-rounded' introuvable.")
        return

    noeud_cadre.setAttribute("data-titre", str(titre or ""))


def supprimer_titre_repeating_panel(repeating_panel):
    """Supprime le titre intégré au cadre d'un RepeatingPanel."""

    noeud_cadre = obtenir_noeud_cadre(repeating_panel)

    if noeud_cadre is None:
        return

    noeud_cadre.removeAttribute("data-titre")