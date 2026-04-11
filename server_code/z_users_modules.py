from anvil import *
import anvil.files
from anvil.files import data_files
import anvil.email

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

# Forcer login de l'utilisateur qui se connecte    
@anvil.server.callable
def force_log(user_row):
    user=anvil.users.force_login(user_row,remember=True)
    user["last_login"]=Time.french_zone_time()  # Update the login time
    return user

""" demande de chgt de Password """    
@anvil.server.callable
def _send_password_reset(email):
    """Send a password reset email to the specified user"""
    # Récupération des variables globales utilisées ici
    dict_var_glob = Variables_globales.get_variable_names()   # var_globale du mail d'AMS, stockées ds table 
    ams_mail = dict_var_glob["ams_mail"]   # var globale Mail AMS
    code_app1 = dict_var_glob["code_app1"]      # var_globale de l'app
    en_tete_address = code_app1+"/_/theme/"+ dict_var_glob["app_en_tete"]  #Logo_F_S_small.png
    #nom_app_pour_mail = dict_var_glob["nom_app_pour_mail"]

    user = app_tables.users.get(email=email)
    t=recup_time() # t will be text form (module at the end of this server code module)
    if user is not None:
        anvil.email.send(to=user['email'], subject="Réinitialisez votre mot de passe",
                         html=f"""
<p><img src = {en_tete_address} width="772" height="263"> </p> 
<b>Mme/Mr {user["nom"]},</b><br>
<br>
Avez-vous bien demandé une modification du mot de passe de votre compte ? Si ce n'est pas vous, supprimez cet email ! <br>
<br>
Si vous désirez poursuivre et ré-initialiser votre mot de passe, <b>clickez le lien ci-dessous:</b>
<br>

{code_app1}/#?a=pwreset&email={url_encode(user['email'])}&api={url_encode(user['api_key'])}&t={t} <br>
<br><br>
<b><i>         L'équipe d'AMSport,</b></i><br>
mail: {ams_mail} <br>
""")

        return True



"""Envoi du mail de confirmation: le mail du new user doit être confirmé"""
@anvil.server.callable
def _send_email_confirm_link(email):
    # Récupération des variables globales utilisées ici
    dict_var_glob = Variables_globales.get_variable_names()   # var_globale du mail d'AMS, stockées ds table 
    ams_mail = dict_var_glob["ams_mail"]   # var globale Mail AMS
    code_app1 = dict_var_glob["code_app1"]      # var_globale de l'apli AMS DATA
    en_tete_address = code_app1+"/_/theme/"+ dict_var_glob["app_en_tete"]
    nom_app_pour_mail = dict_var_glob["nom_app_pour_mail"]

    user = app_tables.users.get(email=email)
    t=recup_time() # t will be text form (module at the end of this server code module)
    if user is not None and not user['confirmed_email']:  # User table, Column confirmed_email not checked/True
        anvil.email.send(to=user['email'],
                         subject="Confirmation de votre adresse email",
                         from_address = "jmarc@jmm-formation-et-services.fr",
                         from_name = "AMSport",
                         html=f"""
<p><img src = {en_tete_address} width="772" height="263"> </p> 
<b>Mme/Mr {user["nom"]},</b><br>
<br>
Merci de votre enregistrement sur {nom_app_pour_mail} !<br>
Afin de confirmer votre adresse mail, <b>clickez le lien ci-dessous:</b><br>
<br>
{code_app1}/#?a=confirm&email={url_encode(user['email'])}&hpw={url_encode(user['password_hash'])}&t={t} <br>
<br><br>
<b><i>         L'équipe d'AMSport,</b></i><br>
mail: {ams_mail} <br>
""")
    return True

""" Création de la clef API si non déjà créée"""
def mk_api_key():
    user_api_key = str(uuid.uuid4())   # Création de l'identifiant unique et transformation en chaîne
    #print(f"UUID  généré: {user_api_key}")
    return user_api_key


"""
# Add the user in a transaction, to make sure there is only ever one user in this database
# with this email address. The transaction might retry or abort, so wait until after it's
# done before sending the email.
"""
@anvil.server.callable
@anvil.tables.in_transaction
def do_signup(email, name, password, num_stage, pour_stage="0"):
    print(f"Module 'z_user_modules / do_sign_up': création du user:{email}, {name}, stage {num_stage} pour le stage {pour_stage}")
    pwhash = hash_password(password, bcrypt.gensalt())
    user = app_tables.users.get(email=email)
    if user is None:   # user not created yet
        api = mk_api_key()
        date_heure = Time.french_zone_time()
        role_user ="S"  # stagiaire par défaut
        if num_stage is not None or num_stage != "":
            # lecture du stage sur son num(numéric)
            try:
                stage_row=app_tables.stages.get(numero=int(num_stage))
                role_user = stage_row["type_stage"]
                print(f"Module 'z_user_modules / do_sign_up': Stage {num_stage} bien lu ***")
                print(f"Module 'z_user_modules / do_sign_up': rôle du user: {role_user}")
            except Exception as e:
                print(f"Module 'z_user_modules / do_sign_up': création du user: *** erreur en inscription au stage ({num_stage}) à attribuer pour ce nouvel user *** , role='S' par défaut")
                print(e)
                print("------------------------------------")
                role_user = "S" # par défaut
        try:        
            user = app_tables.users.add_row(email=email.lower(),
                                            role=role_user,
                                            enabled=True,
                                            nom=name,
                                            password_hash=pwhash,
                                            api_key=api,
                                            signed_up=date_heure,
                                           )
            print("création user", user['email'])
            err = None # pas d'erreur
        except Exception as e:
            return e
    else:  # erreur 
        print(f"Module 'z_user_modules / do_sign_up', en création du user, son adresse mail {user['email']} déjà existante ! ") 
        err = "Cette adresse mail est déjà connue... Essayez de vous connecter."
    return err



# for Pw reset or new user email confirmation  
# is the Api key in URL matches the table API     
def get_user_if_key_correct(email, api_key):
  user_row = app_tables.users.get(email=email)
  if user_row is not None and user_row['api_key'] is not None:
    # Use bcrypt to hash the api key and compare the hashed version.
    # The naive way (api_key == user['api_key']) would expose a timing vulnerability.
    salt = bcrypt.gensalt()
    if hash_password(api_key, salt) == hash_password(user_row['api_key'], salt):
      return True, user_row
  else:
      print("Le mail n'existe pas dans la table users")
      return False, None




# is the Api key in URL matches the table API
@anvil.server.callable
def _is_password_key_correct(email, api_key):
  test_2api_identical = False  
  test_2api_identical = get_user_if_key_correct(email, api_key)
  return test_2api_identical  #True if 2 apis identicals




""" ************************************************************************** """
"""     PASS WORD RESET                                                        """    
""" ************************************************************************** """
@anvil.server.callable
def _perform_password_reset(email, api_key, new_password):
  """Perform a password reset if the key matches; return True if it did."""
  bool, user_row = get_user_if_key_correct(email, api_key)
  if bool:  #user exists, I log him
    user_row['password_hash'] = hash_password(new_password, bcrypt.gensalt())
    return True
 

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

