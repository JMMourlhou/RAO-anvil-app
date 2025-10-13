import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

# =========================================================================
@anvil.server.callable           # écriture des offres
def check(row, checked):
    try:
        row.update(vu=checked)
        return True
    except Exception as e:
        return e
    
# =========================================================================
@anvil.server.callable           # éffacements des offres sélectionnées (vu=True)
def treatment_on_all_checked(list, option):
    try:
        for row in list:
            if option == 3:           # Del all checked
                row.delete()
            if option == 1:           # Select all offres
                row.update(vu=True) 
            if option == 2:           # Désecte all offres 
                row.update(vu=False)
        return True
    except Exception as e:
        return e

# =========================================================================
@anvil.server.callable           # éffacements d'1 offre
def del_1(row):
    try:
            row.delete()
            return True
    except Exception as e:
        return e