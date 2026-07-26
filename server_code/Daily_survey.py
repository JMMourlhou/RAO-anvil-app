import anvil.server
import anvil.users

from anvil.tables import app_tables

from datetime import datetime
import anvil.tz

import hashlib
import json
import re


def nettoyer_espace(valeur):
    """
    Supprime les espaces inutiles sans modifier le contenu.
    """

    return re.sub(
        r"\s+",
        " ",
        str(valeur or "").strip()
    )


def extraire_elements(valeur):
    """
    Transforme une chaîne ou une liste en éléments distincts.

    Séparateurs acceptés :
    - virgule
    - point-virgule
    - retour à la ligne
    """

    if valeur is None:
        return []

    if isinstance(valeur, (list, tuple, set)):
        valeurs = list(valeur)
    else:
        valeurs = [valeur]

    resultat = []
    deja_vus = set()

    for element in valeurs:
        morceaux = re.split(
            r"[,;\n]+",
            str(element or "")
        )

        for morceau in morceaux:
            texte = nettoyer_espace(morceau)

            if not texte:
                continue

            cle = texte.casefold()

            if cle in deja_vus:
                continue

            deja_vus.add(cle)
            resultat.append(texte)

    return resultat


def normaliser_sources(sources):
    """
    Retourne une liste de sources unique et triée.
    """

    if sources is None:
        return []

    if isinstance(sources, str):
        sources = [sources]

    resultat = []
    deja_vues = set()

    for source in sources:
        source_propre = nettoyer_espace(source).upper()

        if not source_propre:
            continue

        if source_propre in deja_vues:
            continue

        deja_vues.add(source_propre)
        resultat.append(source_propre)

    return sorted(resultat)


def texte_depuis_elements(elements):
    """
    Reconstitue une chaîne compatible avec les champs de Search.
    """

    return ", ".join(elements)


def elements_pour_cle(elements):
    """
    Prépare une liste triée utilisée uniquement pour détecter
    les veilles identiques.
    """

    return sorted(
        nettoyer_espace(element).casefold()
        for element in elements
        if nettoyer_espace(element)
    )


def creer_cle_requete(
    email,
    sources,
    mots_cles,
    mots_ou,
    mots_exclus,
    departements
):
    """
    Crée une signature stable de la veille.

    L’ordre de saisie des mots ou des départements
    ne crée pas artificiellement une nouvelle veille.
    """

    contenu = {
        "version": 1,
        "email": nettoyer_espace(email).casefold(),
        "sources": sorted(sources),
        "mots_cles": elements_pour_cle(mots_cles),
        "mots_ou": elements_pour_cle(mots_ou),
        "mots_exclus": elements_pour_cle(mots_exclus),
        "departements": elements_pour_cle(departements),
        "nb_jours": 1
    }

    texte = json.dumps(
        contenu,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        texte.encode("utf-8")
    ).hexdigest()


@anvil.server.callable(require_user=True)
def enregistrer_daily_survey(
    sources,
    mots_cles="",
    mots_ou="",
    mots_exclus="",
    departements=""
):
    """
    Enregistre une recherche devant être exécutée chaque nuit.

    Le nombre de jours est volontairement fixé à 1 côté serveur.
    """

    
    user = anvil.users.get_user()

    if not user:
        return {
            "ok": False,
            "statut": "erreur",
            "daily_survey_id": None,
            "message": "Utilisateur non connecté."
        }

    email_texte = user['email']
    print(email_texte)
    if not email_texte:
        return {
            "ok": False,
            "statut": "erreur",
            "daily_survey_id": None,
            "message": "Adresse e-mail introuvable."
        }

    sources_propres = normaliser_sources(sources)

    mots_cles_liste = extraire_elements(mots_cles)
    mots_ou_liste = extraire_elements(mots_ou)
    mots_exclus_liste = extraire_elements(mots_exclus)
    departements_liste = extraire_elements(departements)

    if not sources_propres:
        return {
            "ok": False,
            "statut": "erreur",
            "daily_survey_id": None,
            "message": "Sélectionnez au moins une source."
        }

    if not mots_cles_liste and not mots_ou_liste:
        return {
            "ok": False,
            "statut": "erreur",
            "daily_survey_id": None,
            "message": (
                "Saisissez au moins un mot obligatoire "
                "ou un mot OU."
            )
        }

    cle_requete = creer_cle_requete(
        email=email_texte,
        sources=sources_propres,
        mots_cles=mots_cles_liste,
        mots_ou=mots_ou_liste,
        mots_exclus=mots_exclus_liste,
        departements=departements_liste
    )

    lignes_existantes = app_tables.daily_survey.search(
        email=user,
        cle_requete=cle_requete
    )

    ligne_existante = next(
        iter(lignes_existantes),
        None
    )

    if ligne_existante is not None:

        if bool(ligne_existante["active"]):
            return {
                "ok": True,
                "statut": "deja_active",
                "daily_survey_id": ligne_existante.get_id(),
                "message": (
                    "Cette veille quotidienne est déjà active."
                )
            }

        # Une veille identique désactivée est réactivée.
        ligne_existante["active"] = True
        ligne_existante["derniere_erreur"] = ""

        return {
            "ok": True,
            "statut": "reactivee",
            "daily_survey_id": ligne_existante.get_id(),
            "message": (
                "Cette veille existait déjà et vient "
                "d’être réactivée."
            )
        }
    try:
        nouvelle_ligne = app_tables.daily_survey.add_row(
            email=user,
            sources=sources_propres,
            mots_cles=texte_depuis_elements(
                mots_cles_liste
            ),
            mots_ou=texte_depuis_elements(
                mots_ou_liste
            ),
            mots_exclus=texte_depuis_elements(
                mots_exclus_liste
            ),
            nb_jours=1,
            departements=texte_depuis_elements(
                departements_liste
            ),
            active=True,
            date_creation=datetime.now(anvil.tz.tzutc()),
            derniere_recherche=None,
            nb_offres_derniere_recherche=0,
            dernier_statut="jamais_lancee",
            derniere_erreur="",
            cle_requete=cle_requete
        )

        return {
            "ok": True,
            "statut": "creee",
            "daily_survey_id": nouvelle_ligne.get_id(),
            "message": "La veille quotidienne a été créée."
        }

    except Exception as e:
        print(
            "ERREUR enregistrer_daily_survey :",
            repr(e)
        )

        return {
            "ok": False,
            "statut": "erreur",
            "daily_survey_id": None,
            "message": (
                f"Erreur lors de la création de la veille : {repr(e)}"
            )
        }