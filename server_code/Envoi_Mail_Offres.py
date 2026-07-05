import anvil.server
import anvil.users

from datetime import datetime, date
from html import escape


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
        titre = _txt(offre.get("titre"), "Offre sans titre")
        acheteur = _txt(offre.get("acheteur"))
        lieu = _txt(offre.get("lieu") or offre.get("departement"))
        source = _txt(offre.get("source"))
        date_limite = _txt(offre.get("date_limite_rep"))
        resume = _txt(offre.get("resume_court"), "")
        mots_trouves = _format_mots_trouves(offre.get("mots_trouves"))
        lien_source = _txt(offre.get("lien_source"), "")
        lien_app = _txt(offre.get("lien_app"), "")
        correspondance = _calcul_correspondance(offre, contexte or {})
        score_brut = offre.get("score")

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
        titre = _html(offre.get("titre"), "Offre sans titre")
        acheteur = _html(offre.get("acheteur"))
        lieu = _html(offre.get("lieu") or offre.get("departement"))
        source = _html(offre.get("source"))
        date_limite = _html(offre.get("date_limite_rep"))
        resume = _html(offre.get("resume_court"), "")
        mots_trouves = _html(_format_mots_trouves(offre.get("mots_trouves")), "")
        correspondance = _calcul_correspondance(offre, contexte or {})
        score_brut = offre.get("score")
        lien_source = offre.get("lien_source") or ""
        lien_app = offre.get("lien_app") or ""

        bouton_source = ""
        if lien_source:
            bouton_source = f"""
            <a href="{escape(str(lien_source), quote=True)}"
               style="display:inline-block; background:#1a73e8; color:#ffffff; text-decoration:none; padding:10px 14px; border-radius:6px; font-weight:bold; margin-right:8px;  margin-top:6px;">
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

        bloc_resume = ""
        if resume:
            bloc_resume = f"""
            <p style="margin:12px 0 0 0;">
              <strong>Résumé :</strong><br>
              {resume}
            </p>
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

        html += f"""
    <div style="background:#ffffff; border:1px solid #dddddd; border-radius:8px; padding:14px; margin-bottom:12px;">
        <div style="background:#eef5df; border-left:6px solid #6b8e23; padding:12px 14px; border-radius:6px; margin-bottom:14px;">
            <h3 style="margin:0; color:#334400; font-size:19px; line-height:1.3;">
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

    # Tri recommandé : date limite puis score décroissant.
    # Ici on fait simple car les dates peuvent être de formats différents.
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



def _extraire_mots_depuis_texte(texte):
    """
    Transforme une chaîne en liste de mots simples.
    Séparateurs gérés : virgule, point-virgule, espaces, retours ligne.
    """
    if not texte:
        return []

    texte = str(texte)
    for sep in [",", ";", "\n", "\t"]:
        texte = texte.replace(sep, " ")

    mots = [x.strip() for x in texte.split(" ") if x.strip()]
    return mots


def _liste_mots_recherche(contexte):
    """
    Construit la liste des mots de recherche à partir du contexte.
    Ici on prend mots_cles + mots_ou.
    """
    if not contexte:
        return []

    mots_et = _extraire_mots_depuis_texte(contexte.get("mots_cles", ""))
    mots_ou = _extraire_mots_depuis_texte(contexte.get("mots_ou", ""))

    # dédoublonnage simple en conservant l'ordre
    resultat = []
    for mot in mots_et + mots_ou:
        mot_min = mot.lower()
        if mot_min not in [x.lower() for x in resultat]:
            resultat.append(mot)

    return resultat


def _calcul_correspondance(offre, contexte):
    """
    Retourne:
    - nb_trouves
    - nb_total
    - pourcentage
    - texte explicatif
    """
    mots_recherche = _liste_mots_recherche(contexte)

    mots_trouves = offre.get("mots_trouves") or []
    if not isinstance(mots_trouves, list):
        mots_trouves = [str(mots_trouves)]

    mots_trouves_norm = [str(x).strip().lower() for x in mots_trouves if str(x).strip()]

    nb_total = len(mots_recherche)
    nb_trouves = 0

    for mot in mots_recherche:
        if str(mot).strip().lower() in mots_trouves_norm:
            nb_trouves += 1

    if nb_total > 0:
        pourcentage = round((nb_trouves / nb_total) * 100)
        explication = f"{pourcentage}% ({nb_trouves} mot(s) trouvé(s) sur {nb_total})"
    else:
        pourcentage = 0
        explication = "Non calculable"

    return {
        "nb_trouves": nb_trouves,
        "nb_total": nb_total,
        "pourcentage": pourcentage,
        "explication": explication
    }    

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

def _score_int(offre):
    """
    Retourne le score sous forme d'entier.
    Si le score est vide, invalide ou non numérique, retourne 0.
    """

    try:
        return int(offre.get("score") or 0)
    except Exception:
        return 0

def _cle_tri_offre(offre):
    date_limite = _parse_date_limite(offre.get("date_limite_rep"))

    return (
        date_limite is None,
        date_limite or date.max,
        -_score_int(offre)
    )