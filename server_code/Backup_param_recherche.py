import anvil.users
import anvil.server
from anvil.tables import app_tables


def rendre_valeur_portable(valeur):
    """
    Transforme récursivement une valeur en objet stockable
    dans une colonne Simple Object Anvil.
    """

    if valeur is None:
        return ""

    if isinstance(valeur, (str, int, float, bool)):
        return valeur

    if isinstance(valeur, dict):
        return {
            str(cle): rendre_valeur_portable(sous_valeur)
            for cle, sous_valeur in valeur.items()
        }

    if isinstance(valeur, (list, tuple, set)):
        return [
            rendre_valeur_portable(element)
            for element in valeur
        ]

    return str(valeur)


def nettoyer_offres_pour_histo(offres):
    """
    Prépare les offres pour leur stockage dans histo['offres'].
    """

    offres_nettoyees = []

    for offre in offres or []:
        try:
            offre_dict = dict(offre)
        except Exception:
            continue

        offre_propre = {
            str(cle): rendre_valeur_portable(valeur)
            for cle, valeur in offre_dict.items()
        }

        offre_propre["vu"] = bool(
            offre_propre.get("vu", False)
        )

        offres_nettoyees.append(offre_propre)

    return offres_nettoyees


@anvil.server.callable(require_user=True)
def backup_requete(
    user_row=None,
    sources=None,
    mots_cles="",
    nb_jours=1,
    departements="",
    date_time=None,
    nb_offres=0,
    offres=None,
    dict_mots_score=None,
    mk_in_score=False,
    mots_ou="",
    mots_exclus=""
):
    """
    Sauvegarde une recherche dans la table histo.

    Les paramètres suivants sont encore acceptés temporairement
    pour rester compatible avec la Form search actuelle :

    - user_row
    - nb_offres
    - dict_mots_score
    - mk_in_score

    Ils ne sont plus utilisés ni enregistrés.
    """

    row = None

    try:
        # L'utilisateur est toujours déterminé côté serveur.
        user = anvil.users.get_user()

        if not user:
            return {
                "ok": False,
                "histo_id": None,
                "nb_offres": 0,
                "message": "Utilisateur non connecté."
            }

        email = str(user["email"] or "").strip()

        if not email:
            return {
                "ok": False,
                "histo_id": None,
                "nb_offres": 0,
                "message": "Adresse e-mail utilisateur introuvable."
            }

        # Normalisation des sources
        if isinstance(sources, str):
            sources = [sources]
        else:
            sources = list(sources or [])

        sources = [
            str(source).strip()
            for source in sources
            if str(source).strip()
        ]

        # Validation du nombre de jours
        try:
            nb_jours = int(nb_jours)
        except Exception:
            raise ValueError(
                "Le nombre de jours doit être un entier."
            )

        if nb_jours < 1:
            nb_jours = 1

        if nb_jours > 365:
            nb_jours = 365

        # Nettoyage des offres
        offres_nettoyees = nettoyer_offres_pour_histo(
            offres
        )

        # Création de la ligne d'historique
        row = app_tables.histo.add_row(
            email=email,
            sources=sources,
            mots_cles=str(mots_cles or "").strip(),
            mots_ou=str(mots_ou or "").strip(),
            mots_exclus=str(mots_exclus or "").strip(),
            nb_jours=nb_jours,
            departements=str(departements or "").strip(),
            date_heure=date_time,
            nb_offres=len(offres_nettoyees),
            offres=offres_nettoyees
        )

        return {
            "ok": True,
            "histo_id": row.get_id(),
            "nb_offres": len(offres_nettoyees),
            "message": (
                f"Requête sauvegardée pour {email}"
            )
        }

    except Exception as e:
        print("ERREUR backup_requete :", repr(e))

        # Suppression d'une éventuelle ligne partielle
        try:
            if row is not None:
                row.delete()
                print("Ligne histo partielle supprimée.")
        except Exception as erreur_suppression:
            print(
                "Impossible de supprimer la ligne partielle :",
                repr(erreur_suppression)
            )

        return {
            "ok": False,
            "histo_id": None,
            "nb_offres": 0,
            "message": (
                f"Erreur backup_requete : {repr(e)}"
            )
        }