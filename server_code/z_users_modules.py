from anvil import *
import anvil.files
from anvil.files import data_files
#import anvil.email

from anvil.tables import app_tables
import anvil.users
import anvil.server
from anvil.http import url_encode
import bcrypt
import uuid   # this library generates codes (API keys for exemple)
import sys
from . import Time # importation du module pour le calcul du jour / heure du sign in

from datetime import datetime
from . import Variables_globales # importation du module de lecture des variables globales (de la table Variables_globales) 
import hmac  #compare deux valeurs sensibles d’une façon conçue pour réduire les fuites d’information par le temps d’exécution.

# Forcer login de l'utilisateur qui se connecte    
@anvil.server.callable
def force_log(user_row):
    user=anvil.users.force_login(user_row,remember=True)
    user["last_login"]=Time.french_zone_time()  # Update the login time
    return user


"""Envoi du mail de confirmation: le mail du new user doit être confirmé"""
@anvil.server.callable
def _send_email_confirm_link(email):
    email = (email or "").strip().lower()

    # Récupération des variables globales utilisées ici
    dict_var_glob = Variables_globales.get_variable_names()
    mon_mail = dict_var_glob["mon_mail"]
    code_app1 = dict_var_glob["code_app1"]
    en_tete_address = code_app1 + "/_/theme/" + dict_var_glob["app_en_tete"]
    nom_app_pour_mail = dict_var_glob["nom_app_pour_mail"]

    user = app_tables.users.get(email=email)

    if user is None:
        print(f"_send_email_confirm_link: utilisateur introuvable : {email}")
        return False

    if user["confirmed_email"]:
        print(f"_send_email_confirm_link: utilisateur déjà confirmé : {email}")
        return False

    # sécurité : toujours recréer la clé et remettre à jour date et heure de l'envoi du lien de confirmation
    user["api_key"] = mk_api_key()
    user["api_key_created_at"] = Time.french_zone_time()

    # pas de time dans le lien, la verif de la validité se fera à paartir de la colonne "api_key_created_at", coté serveur
    confirm_link = (
        f"{code_app1}/#?a=confirm"
        f"&email={url_encode(user['email'])}"
        f"&api_key={url_encode(user['api_key'])}"
    )

    html_body = f"""
        <p><img src="{en_tete_address}" width="263" height="263"></p> 
        <b>Mme/Mr {user["nom"]},</b><br>
        <br>
        Merci de votre enregistrement sur {nom_app_pour_mail} !<br>
        Afin de confirmer votre adresse mail, <b>cliquez sur le lien ci-dessous :</b><br>
        <br>
        <a href="{confirm_link}">{confirm_link}</a><br>
        <br><br>
        <b><i>L'équipe S.A.O Surveillance des Appels d'offres</i></b><br>
        mail : {mon_mail}<br>
    """

    text_body = (
        f"Mme/Mr {user['nom']},\n\n"
        f"Merci de votre enregistrement sur {nom_app_pour_mail} !\n"
        f"Afin de confirmer votre adresse mail, cliquez sur le lien ci-dessous :\n\n"
        f"{confirm_link}\n\n"
        f"L'équipe de S.A.O. - Surveillance d'appels d'offres\n"
        f"mail : {mon_mail}\n"
    )

    result = anvil.server.call(
        "send_mail_general",
        to_address=user["email"],
        subject="Confirmation de votre adresse email",
        text_body=text_body,
        html_body=html_body,
        from_address="jmarc@jmm-formation-et-services.fr",
        from_name="SAO-Surv. appels d'offres",
        reply_to=mon_mail,
    )

    return result

""" Création de la clef API si non déjà créée"""
def mk_api_key():
    user_api_key = str(uuid.uuid4())   # Création de l'identifiant unique et transformation en chaîne
    #print(f"UUID  généré: {user_api_key}")
    return user_api_key


# Nouvel utilisateur, création du user en base avec son API temporaire
@anvil.server.callable
@anvil.tables.in_transaction
def do_signup(email, name, entreprise, password):
    email = (email or "").strip().lower()
    print(f"Module 'z_user_modules / do_sign_up': création du user:{email}, nom: {name}, entreprise: {entreprise}")

    pwhash = hash_password(password, bcrypt.gensalt())
    user = app_tables.users.get(email=email)

    if user is None:
        api = mk_api_key()
        date_heure = Time.french_zone_time()
        role_user = "C"   # New client par défaut
        
        try:
            user = app_tables.users.add_row(
                email=email,
                role=role_user,
                enabled=True,
                confirmed_email=False,
                nom=name,
                entreprise=entreprise,
                password_hash=pwhash,
                api_key=api,
                api_key_created_at=date_heure,
                signed_up=date_heure,
            )
            print("création user ok:", user['email'])
            err = None

        except Exception as e:
            return e
    else:
        print(f"Module 'z_user_modules / do_sign_up', en création du user, son adresse mail {user['email']} déjà existante !")
        err = "Cette adresse mail est déjà enregistrée... Essayez de vous connecter."
    return err


# for Pw reset or confirmation après sign_up
# does the api key in URL match the table api key
# and is the key still within the allowed delay
def get_user_if_key_correct(email, api_key):
    email = (email or "").strip().lower()
    api_key = (api_key or "").strip()

    user_row = app_tables.users.get(email=email)

    if user_row is None:
        print("Utilisateur introuvable.")
        return False, None

    stored_key = user_row["api_key"]
    key_created_at = user_row["api_key_created_at"]

    if not stored_key:
        print("Aucune api_key enregistrée pour cet utilisateur.")
        return False, None

    if key_created_at is None:
        print("Aucune date de création de api_key enregistrée.")
        return False, None

    # 1) contrôle de la clé
    if not hmac.compare_digest(str(api_key), str(stored_key)):
        print("api_key invalide.")
        return False, None

    # 2) contrôle du délai
    timedelay_url_in_min = int(anvil.server.call("get_variable_value", "timedelay_url_in_min"))
    time_now = Time.french_zone_time()

    diff_in_minutes = (time_now - key_created_at).total_seconds() / 60

    print(f"time now: {time_now}")
    print(f"Date de création api_key: {key_created_at}")
    print(f"Diff in minutes: {diff_in_minutes}")
    print(f"Time delay_url_in_min en param globaux: {timedelay_url_in_min}")

    if diff_in_minutes > timedelay_url_in_min:
        print("Lien expiré.")
        return False, None

    return True, user_row


@anvil.server.callable
def confirm_email_address(email, api_key):
    ok, user_row = get_user_if_key_correct(email, api_key)

    if not ok or user_row is None:
        return False, "Lien invalide ou expiré."

    if user_row["confirmed_email"]:
        return True, "Adresse mail déjà confirmée."

    user_row["confirmed_email"] = True
    user_row["api_key"] = None
    user_row["api_key_created_at"] = None

    return True, "Adresse mail confirmée ! \n Vous pouvez vous connecter."



"""
# is the Api key in URL matches the table API
@anvil.server.callable
def _is_password_key_correct(email, api_key):
  test_2api_identical = False  
  test_2api_identical = get_user_if_key_correct(email, api_key)
  return test_2api_identical  #True if 2 apis identicals
"""

def hash_password(password, salt):
    """Hash the password using bcrypt in a way that is compatible with Python 2 and 3."""
    if not isinstance(password, bytes):
        password = password.encode()
    if not isinstance(salt, bytes):
        salt = salt.encode()

    result = bcrypt.hashpw(password, salt)

    if isinstance(result, bytes):
        return result.decode('utf-8')


""" ************************************************************************** """
"""         NEW USER: MAIL CONFIRMATION                                         """    
""" ************************************************************************** """
@anvil.server.callable
def _confirm_email_address(email, api_key):
  """Confirm a user's email address if the api key matches; return True if it did."""
  bool=False  
  bool, user_row = get_user_if_key_correct(email, api_key)
  if bool:
    user=anvil.users.get_user()  
    user['confirmed_email'] = True
    #user['api_key'] = None
    anvil.users.force_login(user)
  return bool

def recup_time(): 
    time=Time.french_zone_time()
    time_str=""
    time_str=str(time)
    time_str=time_str.replace(" ","_")
    return(time_str)

""" ************************************************************************** """
"""     PASS WORD RESET demande de chgt de Password, confirmation après click sur le lien                                                       """    
""" ************************************************************************** """

# Récupération des variables globales utilisées ici
@anvil.server.callable
def _send_password_reset(email):
    """Send a password reset email to the specified user"""
    # Récupération des variables globales utilisées ici
    dict_var_glob = Variables_globales.get_variable_names()   # var_globale du mail d'AMS, stockées ds table 
    mon_mail = dict_var_glob["mon_mail"]   # var globale Mail AMS
    code_app1 = dict_var_glob["code_app1"]      # var_globale de l'app
    en_tete_address = code_app1+"/_/theme/"+ dict_var_glob["app_en_tete"]  #Logo_F_S_small.png
    #nom_app_pour_mail = dict_var_glob["nom_app_pour_mail"]

    user = app_tables.users.get(email=email)
    #t=recup_time() # t will be text form (module at the end of this server code module)
    # sécurité : toujours recréer la clé et remettre à jour date et heure de l'envoi du lien de confirmation
    user["api_key"] = mk_api_key()
    user["api_key_created_at"] = Time.french_zone_time()

    # pas de time dans le lien, la verif de la validité se fera à paartir de la colonne "api_key_created_at", coté serveur
    reset_link = (
        f"{code_app1}/#?a=pwreset"
        f"&email={url_encode(user['email'])}"
        f"&api_key={url_encode(user['api_key'])}"
    )
    
    html_body = f"""
        <p><img src="{en_tete_address}" width="263" height="263"></p> 
        <b>Mme/Mr {user["nom"]},</b><br>
        <br>
        Avez-vous bien demandé une modification du mot de passe de votre compte ?
        Si ce n'est pas vous, supprimez cet email !<br>
        <br>
        Si vous désirez poursuivre et ré-initialiser votre mot de passe,
        <b>cliquez sur le lien ci-dessous :</b><br>
        <br>
        <a href="{reset_link}">{reset_link}</a><br>
        <br><br>
        <b><i>L'équipe S.A.O Surveillance des Appels d'offres</i></b><br>
        mail : {mon_mail}<br>
        """

    text_body = (
        f"Mme/Mr {user['nom']},\n\n"
        f"Avez-vous bien demandé une modification du mot de passe de votre compte ? "
        f"Si ce n'est pas vous, supprimez cet email !\n\n"
        f"Si vous désirez poursuivre et ré-initialiser votre mot de passe, "
        f"cliquez sur le lien ci-dessous :\n\n"
        f"{reset_link}\n\n"
        f"L'équipe S.A.O Surveillance des Appels d'offres\n"
        f"mail : {mon_mail}\n"
    )
        
    result = anvil.server.call(
        "send_mail_general",
        to_address=user["email"],
        subject="Ré-initialisation de Mot de Passe.",
        text_body=text_body,
        html_body=html_body,
        from_address="jmarc@jmm-formation-et-services.fr",
        from_name="SAO-Surv. appels d'offres",
        reply_to=mon_mail,
    )
    return result

""" ************************************************************************** """
"""     PASS WORD RESET confirmation après click sur le lien                   """    
""" ************************************************************************** """
@anvil.server.callable
def _perform_password_reset(email, api_key, new_password):
    """Perform a password reset if the key matches; return True if it did."""
    ok, user_row = get_user_if_key_correct(email, api_key)

    if not ok or user_row is None:
        return False, "Lien invalide ou expiré."

    user_row["password_hash"] = hash_password(new_password, bcrypt.gensalt())
    user_row["api_key"] = None
    user_row["api_key_created_at"] = None

    return True, "Mot de passe modifié."

# appelé dans Main, en arrivée d'une APL pwreset: Vérifier si c'est bien le dernier lien qui a été cliqué
@anvil.server.callable
def _check_password_reset_link(email, api_key):
    ok, user_row = get_user_if_key_correct(email, api_key)

    if not ok or user_row is None:
        return False, "Lien invalide ou expiré."

    return True, "Lien valide."
#==============================================================================================================================