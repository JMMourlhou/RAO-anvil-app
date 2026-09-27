"""Fonctions d'affichage des RepeatingPanel encadrés."""
from anvil import app
import anvil.js
from anvil.js import get_dom_node, window


CLASSE_ROLE = "anvil-role-repeating-panel-rounded"
SELECTEUR_ROLE = ".anvil-role-repeating-panel-rounded"


def obtenir_noeud_cadre(repeating_panel):
    """Retourne le nœud DOM portant le rôle repeating-panel-rounded."""

    noeud = get_dom_node(repeating_panel)

    if noeud.classList.contains(CLASSE_ROLE):
        return noeud

    noeud_cadre = noeud.closest(SELECTEUR_ROLE)

    if noeud_cadre is not None:
        return noeud_cadre

    noeud_cadre = noeud.querySelector(SELECTEUR_ROLE)

    return noeud_cadre


def definir_titre_repeating_panel(repeating_panel, titre, icone=""):
    """Définit le titre et l'icône intégrés au cadre d'un RepeatingPanel."""

    noeud_cadre = obtenir_noeud_cadre(repeating_panel)

    if noeud_cadre is None:
        print("Rôle 'repeating-panel-rounded' introuvable.")
        return

    noeud_cadre.setAttribute("data-titre", str(titre or ""))
    noeud_cadre.setAttribute("data-icone", str(icone or ""))

    couleur_icone = app.theme_colors["Light Green"]
    noeud_cadre.style.setProperty("--couleur-icone-repeating-panel", str(couleur_icone))


def supprimer_titre_repeating_panel(repeating_panel):
    """Supprime le titre et l'icône intégrés au cadre d'un RepeatingPanel."""

    noeud_cadre = obtenir_noeud_cadre(repeating_panel)

    if noeud_cadre is None:
        return

    noeud_cadre.removeAttribute("data-titre")
    noeud_cadre.removeAttribute("data-icone")