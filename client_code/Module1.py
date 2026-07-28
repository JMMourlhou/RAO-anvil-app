from anvil import *
import anvil.server
from anvil.js import window

def context_ecran():
    w = int(window.innerWidth)
    h = int(window.innerHeight)
    landscape = bool(window.matchMedia("(orientation: landscape)").matches)

    # Seuils à adapter à l'interface
    if w < 768:
        screen_type = "phone"
    elif w < 1024:
        screen_type = "tablet"
    else:
        screen_type = "large"

    ctx = {
        "width": w,
        "height": h,
        "landscape": landscape,
        "screen_type": screen_type,
        "is_wide": w >= 768,
    }
    print(f"Ecran {ctx['screen_type']}, ({ctx['width']} x {ctx['height']})")
    
    open_form('Menu',True)   # first_entry True
    
    
# appel de la fonction (quand ce module est le start up module )
context_ecran()


# Ne pas mettre d'autres fonctions dessous,
#   car contexte_ecran ci-dessous est exécutée automatiquement dès que le module est chargé/importé d'une autre form