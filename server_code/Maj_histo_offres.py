import anvil.users
import anvil.server
import anvil.tables as tables
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
@tables.in_transaction
def update_histo_offres(histo_id, offres, revision_recherche):
    """Modifie les offres si utilisateur et révision correspondent.

    Retourne un refus explicite ou les offres enregistrées.
    Ne change jamais la révision de la recherche complète.
    Les erreurs techniques annulent la transaction et remontent.
    """

    def refuser(message):
        return {"ok": False, "message": message}

    user = anvil.users.get_user()
    if not user or not user["email"]:
        return refuser("Utilisateur non connecté.")

    if not histo_id:
        return refuser("Identifiant de recherche manquant.")

    if (
        isinstance(revision_recherche, bool)
        or not isinstance(revision_recherche, (int, float))
        or revision_recherche < 1
        or int(revision_recherche) != revision_recherche
    ):
        return refuser("Révision de recherche invalide.")

    revision_recherche = int(revision_recherche)

    row = app_tables.histo.get_by_id(histo_id)
    if row is None:
        return refuser("Recherche introuvable.")

    if row["email"] != user["email"]:
        return refuser("Cette recherche ne vous appartient pas.")

    if row["revision_recherche"] != revision_recherche:
        return refuser(
            "Une recherche plus récente a été sauvegardée. "
            "Rechargez la page avant de modifier les offres."
        )

    # Contrôle et écriture sont protégés par la même transaction.
    offres_nettoyees = nettoyer_offres_pour_histo(offres)
    row.update(
        offres=offres_nettoyees,
        nb_offres=len(offres_nettoyees)
    )

    return {
        "ok": True,
        "message": "Offres mises à jour.",
        "offres": offres_nettoyees,
        "nb_offres": len(offres_nettoyees),
        "revision_recherche": row["revision_recherche"]
    }
