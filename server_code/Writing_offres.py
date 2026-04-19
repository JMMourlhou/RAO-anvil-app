import anvil.email
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime


@anvil.server.callable           # écriture des offres
def sov_offres(offres):
    for offre in offres:
        # test num avis non existant
        avis_num         = offre.get("idweb", "")
        row = app_tables.appels_offres.get(avis_num=avis_num)
        if row:
            msg = f"Avis num {avis_num} existant."
            print(msg)
            return msg
            
        """Enregistre une offre dans la table appels_offres"""
        try:
            # Protection : toutes les clés existent
            titre            = offre.get("titre", "")
            lien             = offre.get("lien", "")
            acheteur         = offre.get("acheteur", "")
            source           = offre.get("source", "")
            date_scraping    = offre.get("date_scraping", datetime.now().isoformat())
            date_publication = offre.get("date_publication", None)
            date_limite_rep  = offre.get("date_limite_reponse", None)
            departement      = offre.get("departement", "")
            search_text      = offre.get("search_text", "")
            pertinence       = offre.get("pertinence", "")
            
            # Insertion
            app_tables.appels_offres.add_row(
                avis_num          = avis_num,
                titre             = titre,
                lien              = lien,
                acheteur          = acheteur,
                source            = source,
                date_scraping     = datetime.fromisoformat(date_scraping[:19]),
                date_publication  = date_publication,
                date_limite_rep   = date_limite_rep,
                departement       = departement,
                search_text       = search_text,
                pertinence        = pertinence,
            )
        except Exception as e:
            # 🔒 Toujours renvoyer du texte sérialisable
            msg = f"Erreur insertion : {type(e).__name__} - {e}"
            print(msg)
            return msg
    return "ok"
    
            