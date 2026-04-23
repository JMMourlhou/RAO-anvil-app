from anvil import *
import anvil.server
from datetime import datetime
from . import Variables_globales
import html
from anvil.tables import app_tables

@anvil.server.callable
def _send_contact_msg(name, email, tel, topic, message, activite):
    name = (name or "").strip()
    email = (email or "").strip().lower()
    tel = (tel or "").strip()
    topic = (topic or "").strip()
    message = (message or "").strip()

    # Variables globales
    dict_var_glob = Variables_globales.get_variable_names()
    mon_mail = dict_var_glob["mon_mail"]
    code_app1 = dict_var_glob["code_app1"]
    en_tete_address = code_app1 + "/_/theme/" + dict_var_glob["app_en_tete"]
    nom_app_pour_mail = dict_var_glob["nom_app_pour_mail"]

    # Heure côté serveur
    time = datetime.now().strftime("%d/%m/%Y à %H:%M")

    # Sécurisation pour le HTML
    name_html = html.escape(name)
    activite_html = html.escape(activite)
    email_html = html.escape(email)
    tel_html = html.escape(tel)
    topic_html = html.escape(topic)
    message_html = html.escape(message).replace("\n", "<br>")

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222;">
        <p>
          <img src="{en_tete_address}" width="263" height="263" alt="Logo">
        </p>

        <h2>Nouveau message de contact</h2>

        <p><b>Date :</b> {time}</p>
        <p><b>Nom :</b> {name_html}</p>
        <p><b>Activitée :</b> {activite_html}</p>
        
        <p><b>Email :</b> {email_html}</p>
        <p><b>Téléphone :</b> {tel_html}</p>
        <p><b>Sujet :</b> {topic_html}</p>

        <p><b>Message :</b></p>
        <div style="white-space: normal; line-height: 1.5;">
          {message_html}
        </div>

        <br>
        <hr>
        <p>
          <b><i>L'équipe {html.escape(nom_app_pour_mail)}</i></b><br>
          mail : {html.escape(mon_mail)}
        </p>
      </body>
    </html>
    """

    text_body = (
        f"Nouveau contact Web le {time}\n\n"
        f"Nom : {name}\n"
        f"Activitée : {activite}\n"
        f"Téléphone : {tel}\n"
        f"Email : {email}\n"
        f"Sujet : {topic}\n"
        f"Message :\n{message}\n\n"
        f"--------------------------------------------------\n"
        f"L'équipe de {nom_app_pour_mail}\n"
        f"mail : {mon_mail}\n"
    )
    try:
        result = anvil.server.call(
            "send_mail_general",
            to_address=mon_mail,
            subject="Message contact de AOS",
            text_body=text_body,
            html_body=html_body,
            from_address="jmarc@jmm-formation-et-services.fr",
            from_name="SAO-Surv. appels d'offres",
            reply_to=email if email else mon_mail,
        )
    except Exception as e:
        print(f"{e}")
    app_tables.contact.add_row(nom=name, tel=tel, mail=email, objet=topic, message=message, activite=activite, date=time)   
    return result