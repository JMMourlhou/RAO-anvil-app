import anvil.server
from anvil.tables import app_tables

@anvil.server.callable
def update_histo_offres(histo_id, offres):
    """
    Mises à jour après clic sur les checkbox ou suppression d’une offre 
    Met à jour la colonne histo['offres'] avec la liste de dictionnaires reçue.
    Met aussi à jour nb_offres.
    """

    try:
        if not histo_id:
            return {
                "ok": False,
                "message": "histo_id manquant",
                "offres": []
            }

        row = app_tables.histo.get_by_id(histo_id)

        if row is None:
            return {
                "ok": False,
                "message": "Ligne histo introuvable",
                "offres": []
            }

        nouvelles_offres = []

        for offre in offres or []:
            nouvelle_offre = dict(offre)
            nouvelle_offre["vu"] = bool(nouvelle_offre.get("vu", False))
            nouvelles_offres.append(nouvelle_offre)

        row["offres"] = nouvelles_offres

        try:
            row["nb_offres"] = len(nouvelles_offres)
        except Exception:
            pass

        return {
            "ok": True,
            "message": "Offres mises à jour",
            "offres": nouvelles_offres,
            "nb_offres": len(nouvelles_offres)
        }

    except Exception as e:
        print(f"Erreur au module 'update_histo_offres' : {e}")
        return {
            "ok": False,
            "message": str(e),
            "offres": []
        }

