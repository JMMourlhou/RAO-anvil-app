import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server

# =========================================================================
@anvil.server.callable           # éffacements des offres sélectionnées (vu=True)
def backup_param(url, mots_cles, nb_jours, departements, date_time):
    # lecture de la 1ere ligne de la table
    try: # row1 existe ?
        row_1 = app_tables.histo.search()[0]   # pour l'instant 1ere ligne, plus tard recherher le user
        # modif
        row_1.update(
                    url          = url,
                    mots_cles    = mots_cles,
                    nb_jours     = int(nb_jours),
                    departements = departements,
                    date_heure   = date_time    
                    )
        return True
    except Exception as e:
        app_tables.histo.add_row(
                                user_id      = "jim34",                   # à modifier qd gestion des users
                                email        = "jmmourlhou@gmail.com",
                                url          = url,
                                mots_cles    = mots_cles,
                                nb_jours     = int(nb_jours),
                                departements = departements,
                                date_heure   = date_time    
                                )
        return e
    
