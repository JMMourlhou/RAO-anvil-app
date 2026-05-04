import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server


@anvil.server.callable
def backup_requete(
    user_row,
    sources,
    mots_cles,
    nb_jours,
    departements,
    date_time,
    nb_offres,
    offres,
    dict_mots_score,
    mk_in_score
):
    """
    Sauvegarde la requête utilisateur dans histo.

    Retourne :
    {
        "ok": True,
        "histo_id": "...",
        "nb_offres": 12
    }
    """

    try:
        # Sécurité : on privilégie l'utilisateur connecté côté serveur
        user = anvil.users.get_user()

        if user:
            email = user["email"]
        else:
            email = user_row["email"]

        offres = list(offres or [])
        dict_mots_score = dict(dict_mots_score or {})

        row = app_tables.histo.add_row(
            email=email,
            sources=sources,
            mots_cles=mots_cles,
            nb_jours=int(nb_jours),
            departements=departements,
            date_heure=date_time,
            nb_offres=int(nb_offres),
            offres=offres,
            mots_score=dict_mots_score,
            mot_cles_in_score=mk_in_score
        )

        return {
            "ok": True,
            "histo_id": row.get_id(),
            "nb_offres": len(offres),
            "message": f"Requête sauvegardée pour {email}"
        }

    except Exception as e:
        return {
            "ok": False,
            "histo_id": None,
            "nb_offres": 0,
            "message": f"Erreur backup_requete : {e}"
        }