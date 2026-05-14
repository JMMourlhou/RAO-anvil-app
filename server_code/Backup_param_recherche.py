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


def dict_mots_score_to_list(dict_mots_score):
    """
    Transforme :
    {"secourisme": 10, "sst": 1}

    en :
    [
        {"mot": "secourisme", "valeur": 10},
        {"mot": "sst", "valeur": 1}
    ]
    """

    resultat = []

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

        resultat.append({
            "mot": mot,
            "valeur": valeur
        })

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
    mk_in_score=False,
    mots_ou="",
    mots_exclus=""
):
    row = None

    try:
        user = anvil.users.get_user()

        if user:
            email = user["email"]
        else:
            email = user_row["email"]

        sources = list(sources or [])
        offres = nettoyer_offres_pour_histo(offres)
        dict_mots_score = nettoyer_dict_mots_score(dict_mots_score)
        mots_score_obj = dict_mots_score_to_list(dict_mots_score)
        mk_in_score = bool(mk_in_score)

        print("===== BACKUP REQUETE =====")
        print("email:", email)
        print("sources:", sources)
        print("mots_cles:", mots_cles)
        print("mots_ou:", mots_ou)
        print("mots_exclus:", mots_exclus)
        print("nb_jours:", nb_jours)
        print("departements:", departements)
        print("len offres:", len(offres))
        print("dict_mots_score:", dict_mots_score)
        print("mots_score_obj:", mots_score_obj)
        print("mk_in_score:", mk_in_score)

        # Création minimale de la ligne.
        # On évite de tout mettre dans add_row pour identifier la colonne qui plante.
        row = app_tables.histo.add_row(
            email=email,
            date_heure=date_time
        )

        def set_col(cle, valeur):
            try:
                print(f"Ecriture histo['{cle}'] ...")
                row[cle] = valeur
                print(f"OK histo['{cle}']")
            except Exception as e:
                raise Exception(
                    f"Erreur sur colonne histo['{cle}'] : {repr(e)}"
                )

        # Recherche
        set_col("sources", sources)
        set_col("mots_cles", mots_cles or "")
        set_col("mots_ou", mots_ou or "")
        set_col("mots_exclus", mots_exclus or "")

        # Autres critères
        set_col("nb_jours", int(nb_jours))
        set_col("departements", departements or "")

        # Résultats
        set_col("nb_offres", len(offres))
        set_col("offres", offres)

        # Scoring
        set_col("mots_score_obj", mots_score_obj)
        set_col("mots_cles_in_score", bool(mk_in_score))

        return {
            "ok": True,
            "histo_id": row.get_id(),
            "nb_offres": len(offres),
            "message": f"Requête sauvegardée pour {email}"
        }

    except Exception as e:
        print("ERREUR backup_requete :", repr(e))

        # Si une ligne partielle a été créée, on la supprime pour ne pas polluer histo
        try:
            if row:
                row.delete()
                print("Ligne histo partielle supprimée.")
        except Exception as e_del:
            print("Impossible de supprimer la ligne partielle :", repr(e_del))

        return {
            "ok": False,
            "histo_id": None,
            "nb_offres": 0,
            "message": f"Erreur backup_requete : {repr(e)}"
        }