import anvil.tz
from datetime import datetime
# Calcul de l'heure en France

#Get the time now, local time FOR CLIENT SIDE (date from browser)
def french_zone_time():
    date_time = datetime.now(anvil.tz.tzlocal()) #recup browser time
    return date_time


# Calculate the difference beetween now time  and  't' (the str url time)
def time_over(t):
    bool=True #time is over

    #time now
    time_now=french_zone_time()
    t=t.replace("_"," ")
    date_url = datetime.fromisoformat(t)

    # difference in minutes
    diff_in_minutes = (time_now - date_url).total_seconds() / 60
    print(f"time now: {time_now}")
    print(f"Date de l'url: {date_url}")
    print(f"Diff in minutes: {diff_in_minutes}")
    # Lecture de la variable globale "timedelay_url_in_min" ds table variables_globales
    timedelay_url_in_min = int(anvil.server.call('get_variable_value', "timedelay_url_in_min"))
    print(f"Time delay_url_in_min en param globaux: {timedelay_url_in_min}")
    #to get the URL delay
    if diff_in_minutes < timedelay_url_in_min: 
        bool = False # time not over
    print(f"Module French_zone: Délai dépassé de l'URL: {bool}")
    return bool


# Returns the difference beetween now  and  a past date 
def time_diff(past_date):
    #time now
    time_now=french_zone_time()
    diff = time_now - past_date
    return diff