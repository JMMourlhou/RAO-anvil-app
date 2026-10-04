import anvil.server
import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables

from . import Variables_globales, CPV_API


@anvil.server.callable
def initialiser_form_search(inclure_offres=False):
    """
    Renvoie au client les données nécessaires à l'ouverture de la Form Search :
    - l'utilisateur connecté ;
    - le code de l'application ;
    - la liste des plateformes ;
    - la dernière recherche de l'utilisateur.

    Les offres de la dernière recherche ne sont renvoyées que lorsque
    ``inclure_offres`` vaut True.
    """

    user = anvil.users.get_user()

    if not user:
        return {
            "user": None,
            "base_app": "",
            "plateformes": [],
            "histo": None
        }

    plateformes = [
        {
            "id": row["id"],
            "drop_down_display": row["drop_down_display"]
        }
        for row in app_tables.platformes.search(
            tables.order_by("id", ascending=True)
        )
    ]

    row = app_tables.histo.get(email=user["email"])
    histo = None

    if row is not None:
        histo = {
            "histo_id": row.get_id(),
            "mots_cles": row["mots_cles"] or "",
            "mots_ou": row["mots_ou"] or "",
            "mots_exclus": row["mots_exclus"] or "",
            "nb_jours": row["nb_jours"],
            "departements": row["departements"] or "",
            "sources": list(row["sources"] or []),
            "mode_recherche": row["mode_recherche"],
            "cpv_selectionnes": list(row["cpv_selectionnes"]),
            "revision_recherche": row["revision_recherche"],
            "prestations_cpv": []
        }

        # Résolution depuis la référence, sans stocker les libellés dans histo.
        if histo["mode_recherche"] == "cpv":
            resolution = CPV_API.obtenir_libelles_cpv(
                histo["cpv_selectionnes"]
            )
            if not resolution["ok"]:
                raise ValueError(resolution["message"])
            histo["prestations_cpv"] = resolution["resultats"]

        if inclure_offres:
            histo["offres"] = list(row["offres"] or [])

    return {
        "user": user,
        "base_app": Variables_globales.get_variable_value("code_app1"),
        "plateformes": plateformes,
        "histo": histo
    }
