import anvil.server
import anvil.users

from datetime import datetime, date
from html import escape


# ---------------------------------------------------------------------
# Import normalisation
# ---------------------------------------------------------------------
# Si Score_pertinence est un module serveur Anvil dans la même app,
# cet import devrait fonctionner dans beaucoup de cas.
# Si Anvil refuse, essaie la variante :
# from .Score_pertinence import normaliser_texte

try:
    from Score_pertinence import normaliser_texte
except Exception:
    try:
        from .Score_pertinence import normaliser_texte
    except Exception:
        # Fallback local minimal si l'import Anvil pose problème.
        # Normalement tu n'en auras pas besoin puisque normaliser_texte existe déjà.
        _ACCENTS = {
            "à": "a", "â": "a", "ä": "a", "á": "a", "ã": "a", "å": "a",
            "ç": "c",
            "é": "e", "è": "e", "ê": "e", "ë": "e",
            "î": "i", "ï": "i", "í": "i", "ì": "i",
            "ô": "o", "ö": "o", "ó": "o", "ò": "o", "õ": "o",
            "ù": "u", "û": "u", "ü": "u", "ú": "u",
            "ÿ": "y",
            "ñ": "n",
            "œ": "oe",
            "æ": "ae",
        }

        def normaliser_texte(texte):
            if texte is None:
                return ""

            texte = str(texte).lower()

            for accent, simple in _ACCENTS.items():
                texte = texte.replace(accent, simple)

            caracteres = []
            for c in texte:
                if c.isalnum():
                    caracteres.append(c)
                else:
                    caracteres.append(" ")

            texte = "".join(caracteres)
            texte = " ".join(texte.split())

            return texte


# ---------------------------------------------------------------------
# Outils généraux
# ---------------------------------------------------------------------

def _get_valeur(item, cle, defaut=None):
    """
    Récupère une valeur dans un dictionnaire ou dans une ligne Anvil.
    """
    if item is None:
        return defaut

    try:
        if isinstance(item, dict):
            return item.get(cle, defaut)
    except Exception:
        pass

    try:
        return item[cle]
    except Exception:
        return defaut


def _txt(value, default="Non renseigné"):
    """Retourne une chaîne propre pour le texte brut."""
    if value is None:
        return default

    value = str(value).strip()
    return value if value else default


def _html(value, default="Non renseigné"):
    """Retourne une chaîne échappée pour le HTML."""
    return escape(_txt(value, default))


def _format_liste(value):
    """
    Transforme une liste ou une chaîne en texte lisible.
    """
    if not value:
        return ""

    if isinstance(value, list):
        return ", ".join(str(x).strip() for x in value if str(x).strip())

    return str(value).strip()


def _format_mots_trouves(value):
    return _format_liste(value)


# ---------------------------------------------------------------------
# Extraction des termes de recherche
# ---------------------------------------------------------------------

def _extraire_termes_depuis_valeur(value):
    """
    Transforme une saisie en liste de termes.

    Important :
    - on découpe sur virgule, point-virgule, retour ligne ;
    - on ne découpe PAS sur les espaces ;
    - cela permet de conserver les expressions comme "mac sst".
    """

    if not value:
        return []

    if isinstance(value, list):
        termes = []
        for item in value:
            termes.extend(_extraire_termes_depuis_valeur(item))
        return termes

    texte = str(value)

    for sep in [";", "\n", "\t", "\r"]:
        texte = texte.replace(sep, ",")

    return [x.strip() for x in texte.split(",") if x.strip()]


def _liste_mots_recherche(contexte):
    """
    Construit la liste des termes recherchés.

    On accepte plusieurs clés possibles pour être robuste :
    - mots_cles
    - mots_obligatoires
    - obligatoires
    - mots_ou
    - au_moins_un
    - mots_au_moins_un
    """

    if not contexte:
        return []

    sources_termes = []

    for cle in [
        "mots_cles",
        "mots_obligatoires",
        "obligatoires",
        "mots_ou",
        "au_moins_un",
        "mots_au_moins_un",
    ]:
        valeur = contexte.get(cle)
        if valeur:
            sources_termes.extend(_extraire_termes_depuis_valeur(valeur))

    resultat = []
    deja_vus = set()

    for terme in sources_termes:
        terme_clean = str(terme).strip()
        terme_norm = normaliser_texte(terme_clean)

        if terme_norm and terme_norm not in deja_vus:
            resultat.append(terme_clean)
            deja_vus.add(terme_norm)

    return resultat


def _texte_offre_pour_correspondance(offre):
    """
    Construit le texte dans lequel vérifier la présence des mots-clés.
    """

    champs = [
        "titre",
        "resume_court",
        "description",
        "objet",
        "acheteur",
        "nature",
        "procedure",
        "type_avis",
        "departement",
        "lieu",
        "source",
        "reference",
        "search_text",
        "mots_score_trouves",
        "mots_trouves",
    ]

    morceaux = []

    for champ in champs:
        valeur = _get_valeur(offre, champ)

        if not valeur:
            continue

        if isinstance(valeur, list):
            morceaux.extend(str(x) for x in valeur if str(x).strip())
        else:
            morceaux.append(str(valeur))

    return " ".join(morceaux)


def _contient_terme(texte_normalise, terme_normalise):
    """
    Vérifie qu'un terme ou une expression est présent dans le texte normalisé.

    On ajoute des espaces autour pour éviter les faux positifs :
    - "sst" ne doit pas être trouvé dans un mot plus long.
    """

    if not texte_normalise or not terme_normalise:
        return False

    texte_prepare = " " + texte_normalise + " "
    terme_prepare = " " + terme_normalise + " "

    return terme_prepare in texte_prepare


def _mots_trouves_pour_mail(offre, contexte):
    """
    Retourne une liste simple de mots/termes trouvés dans l'offre.

    Priorité :
    1. on cherche les mots du contexte dans le texte réel de l'offre ;
    2. si aucun contexte exploitable, on utilise les champs déjà présents :
       - mots_trouves
       - mots_score_trouves
    """

    mots_recherche = _liste_mots_recherche(contexte)
    texte_offre = _texte_offre_pour_correspondance(offre)
    texte_normalise = normaliser_texte(texte_offre)

    trouves = []
    deja_vus = set()

    for mot in mots_recherche:
        mot_norm = normaliser_texte(mot)

        if not mot_norm:
            continue

        if _contient_terme(texte_normalise, mot_norm):
            if mot_norm not in deja_vus:
                trouves.append(mot)
                deja_vus.add(mot_norm)

    # Fallback si le contexte est vide ou incomplet
    if not trouves:
        for champ in ["mots_trouves", "mots_score_trouves"]:
            valeur = _get_valeur(offre, champ)

            if not valeur:
                continue

            if isinstance(valeur, list):
                candidats = valeur
            else:
                candidats = [valeur]

            for mot in candidats:
                mot_txt = str(mot).strip()
                mot_norm = normaliser_texte(mot_txt)

                if mot_txt and mot_norm not in deja_vus:
                    trouves.append(mot_txt)
                    deja_vus.add(mot_norm)

    return trouves


# ---------------------------------------------------------------------
# Tri des offres par date limite puis score
# ---------------------------------------------------------------------

def _parse_date_limite(value):
    """
    Convertit date_limite_rep en objet date pour permettre un tri fiable.

    Formats acceptés :
    - date Python
    - datetime Python
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SS
    - DD/MM/YYYY
    - DD-MM-YYYY
    - DD.MM.YYYY
    - DD/MM/YYYY HH:MM
    - DD/MM/YYYY à HH:MM
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    txt = str(value).strip()

    if not txt:
        return None

    txt = txt.replace(" à ", " ")
    txt = txt.replace("T", " ")

    if "+" in txt:
        txt = txt.split("+")[0].strip()

    if txt.endswith("Z"):
        txt = txt[:-1].strip()

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d.%m.%Y",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            pass

    return None


def _score_int(offre):
    """
    Retourne le score sous forme d'entier.
    """

    score = _get_valeur(offre, "score", 0)

    try:
        return int(score)
    except Exception:
        try:
            return int(float(str(score).replace(",", ".")))
        except Exception:
            return 0


def _cle_tri_offre(offre):
    """
    Tri :
    1. offres avec date connue en premier ;
    2. date limite la plus proche en premier ;
    3. score décroissant.
    """

    date_limite = _parse_date_limite(_get_valeur(offre, "date_limite_rep"))

    return (
        date_limite is None,
        date_limite or date.max,
        -_score_int(offre),
    )


# ---------------------------------------------------------------------
# Construction du mail texte
# ---------------------------------------------------------------------

def _build_text_body(offres, contexte, email_user):
    date_envoi = datetime.now().strftime("%d/%m/%Y à %H:%M")

    lignes = []
    lignes.append("Bonjour,")
    lignes.append("")
    lignes.append("Voici les offres que vous avez sélectionnées dans RAO.")
    lignes.append("")
    lignes.append(f"Date d'envoi : {date_envoi}")
    lignes.append(f"Destinataire : {email_user}")
    lignes.append(f"Nombre d'offres : {len(offres)}")

    if contexte:
        lignes.append("")
        lignes.append("Contexte de recherche :")
        lignes.append(f"- Mots clés : {_txt(contexte.get('mots_cles'), '')}")
        lignes.append(f"- Mots OU : {_txt(contexte.get('mots_ou'), '')}")
        lignes.append(f"- Mots exclus : {_txt(contexte.get('mots_exclus'), '')}")
        lignes.append(f"- Départements : {_txt(contexte.get('departements'), '')}")
        lignes.append(f"- Nombre de jours : {_txt(contexte.get('nb_jours'), '')}")

        sources = contexte.get("sources") or []
        if isinstance(sources, list):
            sources = ", ".join(str(x) for x in sources)
        lignes.append(f"- Sources : {_txt(sources, '')}")

    lignes.append("")
    lignes.append("------------------------------------------------------------")

    for idx, offre in enumerate(offres, start=1):
        titre = _txt(_get_valeur(offre, "titre"), "Offre sans titre")
        acheteur = _txt(_get_valeur(offre, "acheteur"))
        lieu = _txt(_get_valeur(offre, "lieu") or _get_valeur(offre, "departement"))
        source = _txt(_get_valeur(offre, "source"))
        date_limite = _txt(_get_valeur(offre, "date_limite_rep"))
        resume = _txt(_get_valeur(offre, "resume_court"), "")
        lien_source = _txt(_get_valeur(offre, "lien_source"), "")
        lien_app = _txt(_get_valeur(offre, "lien_app"), "")
        score_brut = _get_valeur(offre, "score")

        try:
            correspondance = _calcul_correspondance(offre, contexte or {})
        except Exception as e:
            print(f"Erreur calcul correspondance texte offre {idx}: {e}")
            correspondance = {
                "nb_total": 0,
                "explication": "",
                "mots_trouves": [],
            }

        mots_trouves = _format_mots_trouves(
            _get_valeur(offre, "mots_trouves")
            or correspondance.get("mots_trouves")
        )

        lignes.append("")
        lignes.append(f"{idx}. {titre}")
        lignes.append("")
        lignes.append(f"Acheteur : {acheteur}")
        lignes.append(f"Lieu / département : {lieu}")
        lignes.append(f"Source : {source}")
        lignes.append(f"Date limite de réponse : {date_limite}")

        if score_brut not in [None, ""]:
            lignes.append(f"Score de pertinence : {score_brut}")

        if correspondance.get("nb_total", 0) > 0:
            lignes.append(f"Correspondance mots-clés : {correspondance['explication']}")

        if mots_trouves:
            lignes.append(f"Mots trouvés : {mots_trouves}")

        if resume:
            lignes.append("")
            lignes.append("Résumé :")
            lignes.append(resume)

        if lien_source:
            lignes.append("")
            lignes.append(f"Lien vers l'annonce source : {lien_source}")

        if lien_app:
            lignes.append(f"Lien vers l'analyse RAO : {lien_app}")

        lignes.append("")
        lignes.append("------------------------------------------------------------")

    lignes.append("")
    lignes.append("Conseil : vérifiez toujours la date limite et le dossier de consultation directement sur la plateforme source avant toute réponse.")
    lignes.append("")
    lignes.append("Cordialement,")
    lignes.append("RAO — Recherche d'appels d'offres")

    return "\n".join(lignes)


# ---------------------------------------------------------------------
# Construction du mail HTML
# ---------------------------------------------------------------------

def _build_html_body(offres, contexte, email_user):
    date_envoi = datetime.now().strftime("%d/%m/%Y à %H:%M")

    mots_cles = _html(contexte.get("mots_cles"), "") if contexte else ""
    mots_ou = _html(contexte.get("mots_ou"), "") if contexte else ""
    mots_exclus = _html(contexte.get("mots_exclus"), "") if contexte else ""
    departements = _html(contexte.get("departements"), "") if contexte else ""
    nb_jours = _html(contexte.get("nb_jours"), "") if contexte else ""

    sources = ""
    if contexte:
        sources = contexte.get("sources") or ""
        if isinstance(sources, list):
            sources = ", ".join(str(x) for x in sources)
        sources = _html(sources, "")

    html = f"""
<!doctype html>
<html>
<body style="margin:0; padding:0; background:#f5f5f5; font-family:Arial, Helvetica, sans-serif; color:#222;">
  <div style="max-width:900px; margin:0 auto; padding:12px;">

    <div style="background:#ffffff; border:1px solid #dddddd; border-radius:10px; padding:22px; margin-bottom:18px;">
      <h2 style="margin:0 0 10px 0; color:#6b8e23;">RAO — Offres sélectionnées</h2>
      <p style="margin:0 0 8px 0;">Bonjour,</p>
      <p style="margin:0 0 14px 0;">Voici les offres que vous avez sélectionnées dans RAO.</p>

      <table style="border-collapse:collapse; width:100%; font-size:14px;">
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Date d'envoi</td>
          <td style="padding:4px 0;">{escape(date_envoi)}</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Destinataire</td>
          <td style="padding:4px 0;">{_html(email_user)}</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Nombre d'offres</td>
          <td style="padding:4px 0;">{len(offres)}</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Mots clés</td>
          <td style="padding:4px 0;">{mots_cles}</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Mots OU</td>
          <td style="padding:4px 0;">{mots_ou}</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Mots exclus</td>
          <td style="padding:4px 0;">{mots_exclus}</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Départements</td>
          <td style="padding:4px 0;">{departements}</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Période</td>
          <td style="padding:4px 0;">{nb_jours} jour(s)</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Sources</td>
          <td style="padding:4px 0;">{sources}</td>
        </tr>
      </table>
    </div>
"""

    for idx, offre in enumerate(offres, start=1):
        titre = _html(_get_valeur(offre, "titre"), "Offre sans titre")
        acheteur = _html(_get_valeur(offre, "acheteur"))
        lieu = _html(_get_valeur(offre, "lieu") or _get_valeur(offre, "departement"))
        source = _html(_get_valeur(offre, "source"))
        date_limite = _html(_get_valeur(offre, "date_limite_rep"))
        resume = _html(_get_valeur(offre, "resume_court"), "")
        score_brut = _get_valeur(offre, "score")
        lien_source = _get_valeur(offre, "lien_source") or ""
        lien_app = _get_valeur(offre, "lien_app") or ""
        mots_trouves_liste = _mots_trouves_pour_mail(offre, contexte or {})
        mots_trouves = _html(_format_mots_trouves(mots_trouves_liste), "")

        mots_trouves = _html(
            _format_mots_trouves(
                _get_valeur(offre, "mots_trouves")
                or correspondance.get("mots_trouves")
            ),
            ""
        )

        bouton_source = ""
        if lien_source:
            bouton_source = f"""
            <a href="{escape(str(lien_source), quote=True)}"
               style="display:inline-block; background:#1a73e8; color:#ffffff; text-decoration:none; padding:10px 14px; border-radius:6px; font-weight:bold; margin-right:8px; margin-top:6px;">
               Voir l'annonce source
            </a>
            """

        bouton_app = ""
        if lien_app:
            bouton_app = f"""
            <a href="{escape(str(lien_app), quote=True)}"
               style="display:inline-block; background:#6b8e23; color:#ffffff; text-decoration:none; padding:10px 14px; border-radius:6px; font-weight:bold; margin-top:6px;">
               Revoir dans RAO
            </a>
            """

        bloc_score = ""

        if score_brut not in [None, ""]:
            bloc_score += f"""
            <p style="margin:8px 0 0 0;">
              <strong>Score de pertinence :</strong> {_html(score_brut)}
            </p>
            """

        if correspondance.get("nb_total", 0) > 0:
            bloc_score += f"""
            <p style="margin:8px 0 0 0;">
              <strong>Correspondance mots-clés :</strong> {_html(correspondance['explication'])}
            </p>
            """

        bloc_mots = ""
        if mots_trouves:
            bloc_mots = f"""
            <p style="margin:8px 0 0 0;">
              <strong>Mots trouvés :</strong> {mots_trouves}
            </p>
            """

        bloc_resume = ""
        if resume:
            bloc_resume = f"""
            <p style="margin:12px 0 0 0;">
              <strong>Résumé :</strong><br>
              {resume}
            </p>
            """

        html += f"""
    <div style="background:#ffffff; border:1px solid #dddddd; border-radius:8px; padding:14px; margin-bottom:12px;">

      <div style="background:#eef5df; border-left:5px solid #6b8e23; padding:10px 12px; border-radius:5px; margin-bottom:12px;">
        <h3 style="margin:0; color:#334400; font-size:18px; line-height:1.3;">
          {idx}. {titre}
        </h3>
      </div>

      <table style="border-collapse:collapse; width:100%; font-size:14px;">
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold; width:120px;">Acheteur</td>
          <td style="padding:4px 0;">{acheteur}</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Lieu / département</td>
          <td style="padding:4px 0;">{lieu}</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Source</td>
          <td style="padding:4px 0;">{source}</td>
        </tr>
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold;">Date limite</td>
          <td style="padding:4px 0; color:#b00020; font-weight:bold;">{date_limite}</td>
        </tr>
      </table>

      {bloc_score}
      {bloc_mots}
      {bloc_resume}

      <div style="margin-top:16px;">
        {bouton_source}
        {bouton_app}
      </div>

    </div>
"""

    html += """
    <div style="background:#fff8e1; border:1px solid #e0c36a; border-radius:10px; padding:16px; font-size:14px;">
      <strong>Important :</strong>
      vérifiez toujours la date limite et le dossier de consultation directement sur la plateforme source avant toute réponse.
    </div>

    <p style="font-size:13px; color:#666; margin-top:18px;">
      Cordialement,<br>
      RAO — Recherche d'appels d'offres
    </p>

  </div>
</body>
</html>
"""

    return html


