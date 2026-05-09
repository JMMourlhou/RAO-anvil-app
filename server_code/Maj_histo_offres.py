import anvil.server
from anvil.tables import app_tables


def nettoyer_offres_pour_histo(offres):
    """
    Nettoie les offres avant stockage dans histo['offres'].

    Objectif :
    - garantir une liste de dictionnaires simples
    - garantir la clé 'vu'
    - éviter les valeurs non sérialisables
    """

    nouvelles_offres = []

    for offre in offres or []:
        try:
            nouvelle_offre = dict(offre)
        except Exception:
            continue

        for cle, valeur in list(nouvelle_offre.items()):
            if valeur is None:
                nouvelle_offre[cle] = ""
            elif isinstance(valeur, (str, int, float, bool, list, dict)):
                nouvelle_offre[cle] = valeur
            else:
                nouvelle_offre[cle] = str(valeur)

        nouvelle_offre["vu"] = bool(nouvelle_offre.get("vu", False))
        nouvelles_offres.append(nouvelle_offre)

    return nouvelles_offres


@anvil.server.callable
def update_histo_offres(histo_id, offres):
    """
    Mises à jour après clic sur les checkbox ou suppression d’une offre.

    Met à jour :
    - histo['offres']
    - histo['nb_offres']
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

        nouvelles_offres = nettoyer_offres_pour_histo(offres)

        row["offres"] = nouvelles_offres
        row["nb_offres"] = len(nouvelles_offres)

        return {
            "ok": True,
            "message": "Offres mises à jour",
            "offres": nouvelles_offres,
            "nb_offres": len(nouvelles_offres)
        }

    except Exception as e:
        print("Erreur au module 'update_histo_offres' :", repr(e))

        return {
            "ok": False,
            "message": f"Erreur update_histo_offres : {repr(e)}",
            "offres": []
        }