import anvil.users
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
    mk_in_score=False
):
    try:
        user = anvil.users.get_user()

        if user:
            email = user["email"]
        else:
            email = user_row["email"]

        sources = list(sources or [])
        offres = list(offres or [])
        dict_mots_score = dict(dict_mots_score or {})
        mk_in_score = bool(mk_in_score)

        print("===== BACKUP REQUETE DIAGNOSTIC =====")
        print("email:", email)
        print("sources:", sources)
        print("mots_cles:", mots_cles)
        print("nb_jours:", nb_jours)
        print("departements:", departements)
        print("len offres:", len(offres))
        print("dict_mots_score:", dict_mots_score)
        print("mk_in_score:", mk_in_score)

        # Création minimale
        try:
            row = app_tables.histo.add_row(
                email=email
            )
        except Exception as e:
            return {
                "ok": False,
                "histo_id": None,
                "nb_offres": 0,
                "message": f"Erreur création ligne minimale histo : {repr(e)}"
            }

        # Mise à jour colonne par colonne
        tests = [
            ("sources", sources),
            ("mots_cles", mots_cles or ""),
            ("nb_jours", int(nb_jours)),
            ("departements", departements or ""),
            ("date_heure", date_time),
            ("nb_offres", len(offres)),
            ("mots_score", dict_mots_score),
            ("mots_cles_in_score", mk_in_score),
            ("offres", offres),
        ]

        for colonne, valeur in tests:
            try:
                print(f"Test écriture colonne : {colonne}")
                row[colonne] = valeur
            except Exception as e:
                print(f"ERREUR colonne {colonne} :", repr(e))

                try:
                    row.delete()
                except Exception:
                    pass

                return {
                    "ok": False,
                    "histo_id": None,
                    "nb_offres": 0,
                    "message": f"Erreur sur colonne histo['{colonne}'] : {repr(e)}"
                }

        return {
            "ok": True,
            "histo_id": row.get_id(),
            "nb_offres": len(offres),
            "message": f"Requête sauvegardée pour {email}"
        }

    except Exception as e:
        print("ERREUR backup_requete générale :", repr(e))

        return {
            "ok": False,
            "histo_id": None,
            "nb_offres": 0,
            "message": f"Erreur backup_requete générale : {repr(e)}"
        }