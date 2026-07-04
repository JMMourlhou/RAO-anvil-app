import anvil.server
import anvil.users

from datetime import datetime
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
        score = _txt(offre.get("score"), "")
        mots_trouves = _format_mots_trouves(offre.get("mots_trouves"))
        lien_source = _txt(offre.get("lien_source"), "")
        lien_app = _txt(offre.get("lien_app"), "")

        lignes.append("")
        lignes.append(f"{idx}. {titre}")
        lignes.append("")
        lignes.append(f"Acheteur : {acheteur}")
        lignes.append(f"Lieu / département : {lieu}")
        lignes.append(f"Source : {source}")
        lignes.append(f"Date limite de réponse : {date_limite}")

        if score:
            lignes.append(f"Score : {score}")

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
  <div style="max-width:900px; margin:0 auto; padding:24px;">

    <div style="background:#ffffff; border:1px solid #dddddd; border-radius:10px; padding:22px; margin-bottom:18px;">
      <h2 style="margin:0 0 10px 0; color:#111;">RAO — Offres sélectionnées</h2>
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
        score = _html(offre.get("score"), "")
        mots_trouves = _html(_format_mots_trouves(offre.get("mots_trouves")), "")

        lien_source = offre.get("lien_source") or ""
        lien_app = offre.get("lien_app") or ""

        bouton_source = ""
        if lien_source:
            bouton_source = f"""
            <a href="{escape(str(lien_source), quote=True)}"
               style="display:inline-block; background:#1a73e8; color:#ffffff; text-decoration:none; padding:10px 14px; border-radius:6px; font-weight:bold; margin-right:8px;">
               Voir l'annonce source
            </a>
            """

        bouton_app = ""
        if lien_app:
            bouton_app = f"""
            <a href="{escape(str(lien_app), quote=True)}"
               style="display:inline-block; background:#444444; color:#ffffff; text-decoration:none; padding:10px 14px; border-radius:6px; font-weight:bold;">
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
        if score:
            bloc_score = f"""
            <p style="margin:8px 0 0 0;">
              <strong>Score :</strong> {score}
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
    <div style="background:#ffffff; border:1px solid #dddddd; border-radius:10px; padding:20px; margin-bottom:16px;">
      <h3 style="margin:0 0 12px 0; color:#111;">
        {idx}. {titre}
      </h3>

      <table style="border-collapse:collapse; width:100%; font-size:14px;">
        <tr>
          <td style="padding:4px 8px 4px 0; font-weight:bold; width:180px;">Acheteur</td>
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
        key=lambda o: (
            str(o.get("date_limite_rep") or "9999-99-99"),
            -int(o.get("score") or 0) if str(o.get("score") or "0").isdigit() else 0
        )
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