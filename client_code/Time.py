import anvil.tz
from datetime import datetime
# Calcul de l'heure en France

#Get the time now, local time FOR CLIENT SIDE (date from browser)
def french_zone_time():
    date_time = datetime.now(anvil.tz.tzlocal()) #recup browser time
    return date_time
