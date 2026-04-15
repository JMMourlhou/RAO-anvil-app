from ._anvil_designer import MainTemplate
from anvil import *
import anvil.server
import m3.components as m3
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
# modules de gestion des users: login, reset pw, new user
from ..z_user_login import z_user_login
from ..z_user_pw_reset import z_user_pw_reset
from ..z_user_new_account import z_user_new_account
from anvil.js import window

class Main(MainTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Any code you write here will run before the form opens.
        self.bt_user_mail.text = "Vous n'êtes pas connecté."
        # Y a t il une URL active ?
        h = anvil.get_url_hash()
        if isinstance(h, dict):
            # lien de confirmation d'un nouvel user ?
            if h.get("a") == "confirm":
                # pas de controle de délai dépassé ici, mais ce fait ds module 'confirm_email_address' suivant
                ok, msg = anvil.server.call(
                    "confirm_email_address",
                    h.get("email"),
                    h.get("api_key"),
                )
                alert(msg, title="Confirmation")
                
            # lien de reset d'un Mot de Passe ?
            if h.get("a") == "pwreset":
                # pas de controle de délai dépassé ici, mais ce fait ds module 'confirm_email_address' suivant
                
                # controle si c'est le dernier lien, avec la bon API key
                ok, msg = anvil.server.call(
                    "_check_password_reset_link",
                    h.get("email"),
                    h.get("api_key"),
                )
                if ok: # c'est bien le dernier lien cliqué dans le mail
                    self.flow_panel_connect.visible = False
                    self.bt_user_mail.text = "Ré-initialisation du Mot de Passe"
                    self.content_panel.clear()
                    self.content_panel.add_component(z_user_pw_reset(
                                                                        h.get("email"),
                                                                        h.get("api_key")
                                                                    ),
                                                        full_width_row=False
                                                     )
                else: # pas le dernier lien cliqué
                    anvil.set_url_hash("")
                    alert(msg, title="Réinitialisation du mot de passe")
                    open_form("Main")
            anvil.set_url_hash("")      
            
    def button_se_connecter_click(self, **event_args):
        """This method is called when the button is clicked"""
        self.bt_user_mail.text = "Connection"
        self.flow_panel_connect.visible = False
        #from sign_in_for_AMS_Data.LoginDialog_V2 import LoginDialog_V2
        self.content_panel.clear()
        self.content_panel.add_component(z_user_login(), full_width_row=False)

    def bt_user_mail_click(self, **event_args):
        """This method is called when the button is clicked"""
        pass

    def bt_sign_in_click(self, h={}, **event_args):
        """This method is called when the button is clicked"""
        self.bt_user_mail.text = "Création de votre compte"
        self.flow_panel_connect.visible = False
        self.content_panel.clear()        
        self.content_panel.add_component(z_user_new_account(h), full_width_row=True)

    def bt_close_click(self, **event_args):
        """This method is called when the button is clicked"""
        self.content_panel.clear()
        anvil.users.logout()  # logging out the user
        self.user = None
        window.close()

    """ ***********************************************************************************************"""
    """ ****************************** Gestions  BOUTONS CONNECTION et leurs clicks ******************************"""
    """ ***********************************************************************************************"""
    def display_bt_mail(self, **event_args):
        if self.user:
            self.bt_user_mail.text = self.user["email"]
            self.flow_panel_connect.visible = True
            self.bt_se_connecter.visible = False
            self.bt_se_deconnecter.visible = True
        else:
            # Pas de USER
            self.bt_user_mail.text = "Non connecté"
            self.bt_user_mail.enabled = False
            self.bt_se_connecter.visible = True
            self.bt_sign_in.visible = True

            self.bt_se_deconnecter.visible = False
            #self.column_panel_admin.visible = False
            #self.column_panel_others.visible = False

    """ ***********************************************************************************************"""
    """ ****************************** Gestions  AUTRES BOUTONS et leurs clicks ******************************"""
    """ ***********************************************************************************************"""
    def display_admin_or_other_buttons(self, **event_args):
        if self.user:
            if self.user["enabled"] is False:
                alert("Not 'enabled' in table users")
                self.bt_sign_in.visible = False
                return

            self.bt_sign_in.visible = False
            self.bt_user_mail.enabled = True
            self.label_role.text = self.user['role']   # affichage du role