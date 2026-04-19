import anvil.email
import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server


# Sauvegarde de la requête du user

@anvil.server.callable          
def backup_requete(user_row, sources, mots_cles, nb_jours, departements, date_time, nb_offres, offres):

    app_tables.histo.add_row(
                            email        = user_row['email'],
                            sources      = sources,
                            mots_cles    = mots_cles,
                            nb_jours     = int(nb_jours),
                            departements = departements,
                            date_heure   = date_time,
                            nb_offres    = nb_offres,
                            offres=offres
                            )
    return f"Création row table 'histo' requete pour {user_row['email']}"
    
