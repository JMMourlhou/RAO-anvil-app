from anvil.js import window

# ==================================================================================================
#  Appel d'une form
# ==================================================================================================
def context_screen():
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
    #print(f"Ecran {ctx['screen_type']}, ({ctx['width']} x {ctx['height']})")

    return ctx
