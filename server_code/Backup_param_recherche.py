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

        print("===== BACKUP REQUETE DIAGNOSTIC 2 =====")
        print("email:", email)
        print("sources:", sources)
        print("mots_cles:", mots_cles)
        print("nb_jours:", nb_jours)
        print("departements:", departements)
        print("len offres:", len(offres))
        print("dict_mots_score:", dict_mots_score)
        print("mk_in_score:", mk_in_score)

        # =====================================================
        # 1. Création d'une ligne avec les colonnes de base
        #    On exclut volontairement :
        #    - offres
        #    - mots_score
        #    - mots_cles_in_score
        # =====================================================
        try:
            row = app_tables.histo.add_row(
                email=email,
                sources=sources,
                mots_cles=mots_cles or "",
                nb_jours=int(nb_jours),
                departements=departements or "",
                date_heure=date_time,
                nb_offres=len(offres)
            )
        except Exception as e:
            print("ERREUR création ligne de base :", repr(e))
            return {
                "ok": False,
                "histo_id": None,
                "nb_offres": 0,
                "message": f"Erreur création ligne de base histo : {repr(e)}"
            }

        print("Ligne de base créée :", row.get_id())

        # =====================================================
        # 2. Test écriture mots_score
        # =====================================================
        try:
            print("Test écriture mots_score")
            row["mots_score"] = dict_mots_score
        except Exception as e:
            print("ERREUR colonne mots_score :", repr(e))

            try:
                row.delete()
            except Exception:
                pass

            return {
                "ok": False,
                "histo_id": None,
                "nb_offres": 0,
                "message": f"Erreur sur colonne histo['mots_score'] : {repr(e)}"
            }

        # =====================================================
        # 3. Test écriture mots_cles_in_score
        # =====================================================
        try:
            print("Test écriture mots_cles_in_score")
            row["mots_cles_in_score"] = mk_in_score
        except Exception as e:
            print("ERREUR colonne mots_cles_in_score :", repr(e))

            try:
                row.delete()
            except Exception:
                pass

            return {
                "ok": False,
                "histo_id": None,
                "nb_offres": 0,
                "message": f"Erreur sur colonne histo['mots_cles_in_score'] : {repr(e)}"
            }

        # =====================================================
        # 4. Test écriture offres
        # =====================================================
        try:
            print("Test écriture offres")
            row["offres"] = offres
        except Exception as e:
            print("ERREUR colonne offres :", repr(e))

            try:
                row.delete()
            except Exception:
                pass

            return {
                "ok": False,
                "histo_id": None,
                "nb_offres": 0,
                "message": f"Erreur sur colonne histo['offres'] : {repr(e)}"
            }

        print("Sauvegarde diagnostic OK")

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