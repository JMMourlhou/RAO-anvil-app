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
@anvil.server.callable           # éffacements des offres
def del_all():
    try:
        list = app_tables.appels_offres.search()
        for row in list:
            row.delete()
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