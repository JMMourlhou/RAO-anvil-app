import anvil.users
import anvil.server
from anvil.tables import app_tables


def nettoyer_dict_mots_score(dict_mots_score):
    resultat = {}

    try:
        items = dict(dict_mots_score or {}).items()
    except Exception:
        return resultat

    for mot, valeur in items:
        mot = str(mot).strip().lower()
        mot = mot.replace("{", "").replace("}", "").replace('"', "").replace("'", "").strip()

        if not mot:
            continue

        try:
            valeur = int(valeur)
        except Exception:
            continue

        resultat[mot] = valeur

    return resultat


def nettoyer_offres_pour_histo(offres):
    offres_nettoyees = []

    for offre in offres or []:
        try:
            o = dict(offre)
        except Exception:
            continue

        for cle, valeur in list(o.items()):
            if valeur is None:
                o[cle] = ""
            elif isinstance(valeur, (str, int, float, bool, list, dict)):
                o[cle] = valeur
            else:
                o[cle] = str(valeur)

        o["vu"] = bool(o.get("vu", False))
        offres_nettoyees.append(o)

    return offres_nettoyees


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
        offres = nettoyer_offres_pour_histo(offres)
        dict_mots_score = nettoyer_dict_mots_score(dict_mots_score)
        mk_in_score = bool(mk_in_score)

        print("===== BACKUP REQUETE DIAGNOSTIC 3 =====")
        print("email:", email)
        print("sources:", sources)
        print("mots_cles:", mots_cles)
        print("nb_jours:", nb_jours)
        print("departements:", departements)
        print("len offres:", len(offres))
        print("dict_mots_score:", dict_mots_score)
        print("mk_in_score:", mk_in_score)

        # 1. Création ligne de base, sans les colonnes sensibles
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

        # 2. Test nouvelle colonne mots_score_obj
        try:
            print("Test écriture mots_score_obj")
            row["mots_score_obj"] = dict_mots_score
        except Exception as e:
            print("ERREUR colonne mots_score_obj :", repr(e))

            try:
                row.delete()
            except Exception:
                pass

            return {
                "ok": False,
                "histo_id": None,
                "nb_offres": 0,
                "message": f"Erreur sur colonne histo['mots_score_obj'] : {repr(e)}"
            }

        # 3. Test colonne booléenne
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

        # 4. Test colonne offres
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