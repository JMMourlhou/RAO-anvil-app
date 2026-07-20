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
    Prépare les offres avant leur stockage dans histo['offres'].
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
def update_histo_offres(histo_id, offres):
    """
    Met à jour les offres de la recherche courante.

    La fonction vérifie que la ligne histo appartient bien
    à l’utilisateur connecté.
    """

    try:
        user = anvil.users.get_user()

        if not user:
            return {
                "ok": False,
                "message": "Utilisateur non connecté.",
                "offres": [],
                "nb_offres": 0
            }

        email_user = str(user["email"] or "").strip().lower()

        if not email_user:
            return {
                "ok": False,
                "message": "Adresse e-mail utilisateur introuvable.",
                "offres": [],
                "nb_offres": 0
            }

        if not histo_id:
            return {
                "ok": False,
                "message": "histo_id manquant.",
                "offres": [],
                "nb_offres": 0
            }

        row = app_tables.histo.get_by_id(histo_id)

        if row is None:
            return {
                "ok": False,
                "message": "Ligne histo introuvable.",
                "offres": [],
                "nb_offres": 0
            }

        email_histo = str(
            row["email"] or ""
        ).strip().lower()

        if not email_histo or email_histo != email_user:
            return {
                "ok": False,
                "message": (
                    "Accès refusé : cette recherche n’appartient "
                    "pas à l’utilisateur connecté."
                ),
                "offres": [],
                "nb_offres": 0
            }

        offres_nettoyees = nettoyer_offres_pour_histo(
            offres
        )

        row["offres"] = offres_nettoyees
        row["nb_offres"] = len(offres_nettoyees)

        return {
            "ok": True,
            "message": "Offres mises à jour.",
            "offres": offres_nettoyees,
            "nb_offres": len(offres_nettoyees)
        }

    except Exception as e:
        print(
            "ERREUR update_histo_offres :",
            repr(e)
        )

        return {
            "ok": False,
            "message": (
                f"Erreur update_histo_offres : {repr(e)}"
            ),
            "offres": [],
            "nb_offres": 0
        }