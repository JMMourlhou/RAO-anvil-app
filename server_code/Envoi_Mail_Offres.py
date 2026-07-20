import anvil.server
import anvil.users

from datetime import datetime, date
from html import escape

# ---------------------------------------------------------------------
# Normalisation texte
# ---------------------------------------------------------------------

_ACCENTS = {
    "à": "a", "â": "a", "ä": "a",
    "á": "a", "ã": "a", "å": "a",

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


def sans_accents(texte):
    """Remplace les accents courants."""
    if texte is None:
        return ""

    texte = str(texte).lower()

    for accent, simple in _ACCENTS.items():
        texte = texte.replace(accent, simple)

    return texte


def normaliser_texte(texte):
    """
    Normalise un texte :
    - minuscules
    - accents supprimés
    - ponctuation remplacée par espaces
    - espaces multiples supprimés
    """
    if texte is None:
        return ""

    texte = sans_accents(texte)

    caracteres = []

    for c in texte:
        if c.isalnum():
            caracteres.append(c)
        else:
            caracteres.append(" ")

    texte = "".join(caracteres)
    texte = " ".join(texte.split())

    return texte

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
        valeur = item[cle]
        if valeur is None:
            return defaut
        return valeur
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


def _format_mots_trouves(value):
    if not value:
        return ""

    if isinstance(value, list):
        return ", ".join(str(x) for x in value if str(x).strip())

    return str(value)


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

        mots_trouves_liste = _mots_trouves_affichage_mail(offre, contexte or {})
        mots_trouves = _format_mots_trouves(mots_trouves_liste)

        lignes.append("")
        lignes.append(f"{idx}. {titre}")
        lignes.append("")
        lignes.append(f"Acheteur : {acheteur}")
        lignes.append(f"Lieu / département : {lieu}")
        lignes.append(f"Source : {source}")
        lignes.append(f"Date limite de réponse : {date_limite}")

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
        lien_source = _get_valeur(offre, "lien_source") or ""
        lien_app = _get_valeur(offre, "lien_app") or ""

        mots_trouves_liste = _mots_trouves_affichage_mail(offre, contexte or {})
        mots_trouves = _html(_format_mots_trouves(mots_trouves_liste), "")

        ligne_mots = ""

        if mots_trouves:
            ligne_mots = f"""
                <tr>
                <td style="padding:4px 8px 4px 0; font-weight:bold;">Mots trouvés</td>
                <td style="padding:4px 0;">{mots_trouves}</td>
                </tr>
            """

        bloc_resume = ""
        if resume:
            bloc_resume = f"""
            <p style="margin:12px 0 0 0;">
            <strong>Résumé :</strong><br>
            {resume}
            </p>
            """

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
            {ligne_mots}
        </table>
    
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


@anvil.server.callable(require_user=True)
def envoyer_mail_offres_selectionnees(offres_selectionnees, contexte=None):
    """
    Fonction appelée par le bouton client.
    Elle récupère l'utilisateur connecté, construit le mail,
    puis appelle l'uplink send_mail_general().
    """

    user = anvil.users.get_user()

    if not user:
        return {
            "ok": False,
            "error": "Utilisateur non connecté."
        }

    email_user = user['email']

    if not email_user:
        return {
            "ok": False,
            "error": "Adresse email utilisateur introuvable."
        }

    if not offres_selectionnees:
        return {
            "ok": False,
            "error": "Aucune offre sélectionnée."
        }

    # Sécurité : limite raisonnable pour éviter un mail énorme
    if len(offres_selectionnees) > 50:
        return {
            "ok": False,
            "error": "Trop d'offres sélectionnées. Limite actuelle : 50 offres par mail."
        }

    # Les échéances les plus proches apparaissent en premier.
    # Les offres sans date reconnue sont placées à la fin.
    # Le tri Python étant stable, l'ordre d'affichage de Search est conservé
    # lorsque plusieurs offres ont la même date limite.
    offres = sorted(
        offres_selectionnees,
        key=_cle_tri_offre
    )

    nb = len(offres)
    date_sujet = datetime.now().strftime("%d/%m/%Y")

    mots_cles = ""
    if contexte:
        mots_cles = str(contexte.get("mots_cles") or "").strip()

    if mots_cles:
        subject = f"RAO — {nb} offre(s) sélectionnée(s) pour « {mots_cles} » — {date_sujet}"
    else:
        subject = f"RAO — {nb} offre(s) sélectionnée(s) — {date_sujet}"

    text_body = _build_text_body(offres, contexte or {}, email_user)
    html_body = _build_html_body(offres, contexte or {}, email_user)

    try:
        result = anvil.server.call(
            "send_mail_general",
            to_address=email_user,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            from_address="jmarc@jmm-formation-et-services.fr",
            from_name="RAO - JM-Web34",
            reply_to="jmarc@jmm-formation-et-services.fr"
        )
    except Exception as e:
        return {
            "ok": False,
            "error": f"Erreur pendant l'appel à l'uplink mail : {str(e)}"
        }

    if result and result.get("ok"):
        return {
            "ok": True,
            "message": "Mail envoyé.",
            "email": email_user,
            "nb_offres": nb,
            "subject": subject
        }

    return {
        "ok": False,
        "error": result.get("error") if isinstance(result, dict) else str(result)
    }

def _mots_trouves_affichage_mail(offre, contexte):
    """
    Retourne les mots à afficher dans le mail.

    Logique :
    - les mots obligatoires sont considérés comme trouvés,
      car l'offre a déjà passé le filtre positif ;
    - les mots OU trouvés viennent du champ mots_ou_trouves,
      déjà calculé dans search ;
    - aucun calcul supplémentaire n'est effectué dans ce module.
    """

    mots_affiches = []
    deja_vus = set()

    # 1. Mots obligatoires de la requête
    mots_obligatoires = _extraire_termes_depuis_valeur(
        contexte.get("mots_cles", "")
    )

    for mot in mots_obligatoires:
        mot_txt = str(mot or "").strip()
        mot_norm = normaliser_texte(mot_txt)

        if mot_txt and mot_norm not in deja_vus:
            mots_affiches.append(mot_txt)
            deja_vus.add(mot_norm)

    # 2. Mots OU réellement trouvés dans l'offre
    mots_ou_trouves = _get_valeur(offre, "mots_ou_trouves", [])

    if mots_ou_trouves is None:
        mots_ou_trouves = []

    if isinstance(mots_ou_trouves, str):
        mots_ou_trouves = [mots_ou_trouves]

    for mot in mots_ou_trouves:
        mot_txt = str(mot or "").strip()
        mot_norm = normaliser_texte(mot_txt)

        if mot_txt and mot_norm not in deja_vus:
            mots_affiches.append(mot_txt)
            deja_vus.add(mot_norm)

    return mots_affiches

def _extraire_termes_depuis_valeur(value):
    """
    Transforme une valeur en liste de termes.

    Accepte :
    - une chaîne : "sst, mac sst, psc1"
    - une liste : ["sst", "mac sst", "psc1"]

    Important :
    - on découpe sur virgule, point-virgule, retour ligne ;
    - on ne découpe pas sur les espaces ;
    - donc "mac sst" reste un seul terme.
    """

    if not value:
        return []

    if isinstance(value, list):
        termes = []

        for item in value:
            termes.extend(_extraire_termes_depuis_valeur(item))

        return termes

    texte = str(value)

    for sep in [";", "\n", "\t", "\r", "|"]:
        texte = texte.replace(sep, ",")

    termes = []

    for morceau in texte.split(","):
        mot = morceau.strip()
        mot = mot.strip("()[]{}")
        mot = mot.strip('"')
        mot = mot.strip("'")
        mot = mot.strip()

        if mot:
            termes.append(mot)

    # Suppression des doublons en conservant l'ordre
    resultat = []
    deja_vus = set()

    for mot in termes:
        mot_norm = normaliser_texte(mot)

        if mot_norm and mot_norm not in deja_vus:
            resultat.append(mot)
            deja_vus.add(mot_norm)

    return resultat

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

    Retourne None si la date est vide ou non reconnue.
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

    # Nettoyage léger
    txt = txt.replace(" à ", " ")
    txt = txt.replace("T", " ")

    # On enlève une éventuelle timezone simple en fin de chaîne
    # Exemple : 2026-07-15 12:00:00+02:00 -> 2026-07-15 12:00:00
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

def _cle_tri_offre(offre):
    """
    Clé de tri par date limite croissante.
    Les dates absentes ou non reconnues sont placées à la fin.
    """

    date_limite = _parse_date_limite(
        _get_valeur(offre, "date_limite_rep")
    )

    return (
        date_limite is None,
        date_limite or date.max
    )
