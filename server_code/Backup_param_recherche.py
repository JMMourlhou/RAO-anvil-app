import anvil.email
import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server

# =========================================================================
@anvil.server.callable          
def backup_param(user_row, sources, mots_cles, nb_jours, departements, date_time):
    # lecture des derniers params du user
    
    row = app_tables.histo.get(email=user_row['email'])
    if row is not None:
        # modif
        row.update(
                    sources      = sources,
                    mots_cles    = mots_cles,
                    nb_jours     = int(nb_jours),
                    departements = departements,
                    date_heure   = date_time    
                    )
        return f"MAJ table 'histo' pour {user_row['email']}"
    else:
        app_tables.histo.add_row(
                                email        = user_row['email'],
                                sources      = sources,
                                mots_cles    = mots_cles,
                                nb_jours     = int(nb_jours),
                                departements = departements,
                                date_heure   = date_time    
                                )
        return f"Création row table 'histo' pour {user_row['email']}"
    
