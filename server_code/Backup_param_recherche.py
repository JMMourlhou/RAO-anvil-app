import anvil.server
import anvil.users
from anvil.tables import app_tables


def nettoyer_valeur_pour_histo(valeur):
    """
    Convertit récursivement une valeur en donnée sérialisable par Anvil.
    """

    if valeur is None:
        return ""

    if isinstance(valeur, (str, int, float, bool)):
        return valeur

    if isinstance(valeur, dict):
        return {
            str(cle): nettoyer_valeur_pour_histo(sous_valeur)
            for cle, sous_valeur in valeur.items()
        }

    if isinstance(valeur, (list, tuple, set)):
        return [
            nettoyer_valeur_pour_histo(element)
            for element in valeur
        ]

    return str(valeur)


def nettoyer_offres_pour_histo(offres):
    """
    Garantit une liste de dictionnaires sérialisables contenant la clé ``vu``.
    """

    offres_nettoyees = []

    for offre in offres or []:
        try:
            offre_dict = dict(offre)
        except Exception:
            continue

        offre_propre = nettoyer_valeur_pour_histo(offre_dict)
        offre_propre["vu"] = bool(offre_propre.get("vu", False))
        offres_nettoyees.append(offre_propre)

    return offres_nettoyees


def nettoyer_sources(sources):
    """Retourne une liste propre d’identifiants de plateformes."""

    if sources is None:
        return []

    if not isinstance(sources, (list, tuple, set)):
        sources = [sources]

    resultat = []

    for source in sources:
        source = str(source or "").strip()
        if source and source not in resultat:
            resultat.append(source)

    return resultat


@anvil.server.callable(require_user=True)
def backup_requete(
    sources,
    mots_cles,
    mots_ou,
    mots_exclus,
    nb_jours,
    departements,
    date_heure,
    offres
):
    """
    Enregistre une recherche et ses offres dans la table ``histo``.

    L’adresse email provient toujours de l’utilisateur Anvil connecté.
    Le nombre d’offres est recalculé côté serveur.
    """

    row = None

    try:
        user = anvil.users.get_user()

        if not user or not user["email"]:
            return {
                "ok": False,
                "histo_id": None,
                "nb_offres": 0,
                "message": "Utilisateur non connecté."
            }

        sources = nettoyer_sources(sources)
        offres = nettoyer_offres_pour_histo(offres)

        try:
            nb_jours = int(nb_jours)
        except Exception:
            raise ValueError("Le nombre de jours doit être un entier.")

        if nb_jours < 1:
            raise ValueError("Le nombre de jours doit être supérieur à zéro.")

        if date_heure is None:
            raise ValueError("La date et l’heure de la recherche sont manquantes.")

        # Création minimale, puis écriture colonne par colonne. En cas de
        # problème de type ou de schéma, le message indique la colonne fautive
        # et la ligne partielle est supprimée dans le bloc except.
        row = app_tables.histo.add_row(
            email=user["email"],
            date_heure=date_heure
        )

        def definir_colonne(nom, valeur):
            try:
                row[nom] = valeur
            except Exception as erreur:
                raise ValueError(
                    f"Erreur sur la colonne histo['{nom}'] : {repr(erreur)}"
                )

        definir_colonne("sources", sources)
        definir_colonne("mots_cles", str(mots_cles or ""))
        definir_colonne("mots_ou", str(mots_ou or ""))
        definir_colonne("mots_exclus", str(mots_exclus or ""))
        definir_colonne("nb_jours", nb_jours)
        definir_colonne("departements", str(departements or ""))
        definir_colonne("nb_offres", len(offres))
        definir_colonne("offres", offres)

        return {
            "ok": True,
            "histo_id": row.get_id(),
            "nb_offres": len(offres),
            "message": f"Requête sauvegardée pour {user['email']}"
        }

    except Exception as e:
        print("Erreur backup_requete :", repr(e))

        try:
            if row is not None:
                row.delete()
        except Exception as erreur_suppression:
            print(
                "Impossible de supprimer la ligne histo partielle :",
                repr(erreur_suppression)
            )

        return {
            "ok": False,
            "histo_id": None,
            "nb_offres": 0,
            "message": f"Erreur backup_requete : {repr(e)}"
        }
