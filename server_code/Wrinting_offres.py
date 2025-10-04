import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime
# =========================================================================
@anvil.server.callable           # écriture des offres
def writing_offres(offre):
    result=""
    try:
        app_tables.appels_offres.add_row(
            titre=offre['titre'],
            lien=offre['lien'],
            organisme=offre['organisme'],
            source="e-marchespublics.com",
            date_scraping=datetime.now()
        )
        result = "ok"
    except Exception as e:
        result = e
    return result
    
            