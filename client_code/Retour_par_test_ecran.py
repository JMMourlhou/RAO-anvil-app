from anvil import *
from anvil.js import window

def largeur_ecran():
    w = int(window.innerWidth)
    h = int(window.innerHeight)
    landscape = bool(window.matchMedia("(orientation: landscape)").matches)

    # Seuils à adapter à TON interface
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
    print(ctx["screen_type"])
    if (ctx["screen_type"] == "phone" and ctx["landscape"]) or ctx["screen_type"] == "tablet" or ctx['screen_type'] == "large":
        open_form('Main_large_screen')
    else:
        open_form('Main_small_screen')
