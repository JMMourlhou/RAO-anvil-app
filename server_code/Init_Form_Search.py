import anvil.users
import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables
from . import Variables_globales

@anvil.server.callable
def initialiser_form_search(inclure_offres=False):
    user = anvil.users.get_user()

    if not user:
        return {
            "user": None,
            "base_app": "",
            "plateformes": [],
            "histo": None
        }

    plateformes = [
        row["id"]
        for row in app_tables.platformes.search(
            tables.order_by("id", ascending=True)
        )
    ]

    rows_histo = app_tables.histo.search(
        tables.order_by("date_heure", ascending=False),
        email=user["email"]
    )

    row = next(iter(rows_histo), None)

    histo = None

    if row is not None:
        histo = {
            "histo_id": row.get_id(),
            "mots_cles": row["mots_cles"],
            "mots_ou": row["mots_ou"],
            "mots_score_obj": row["mots_score_obj"],
            "mots_exclus": row["mots_exclus"],
            "nb_jours": row["nb_jours"],
            "departements": row["departements"],
            "sources": row["sources"]
        }

        if inclure_offres:
            histo["offres"] = row["offres"] or []

    return {
        "user": user,
        "base_app": Variables_globales.get_variable_value("code_app1"),
        "plateformes": plateformes,
        "histo": histo
    }