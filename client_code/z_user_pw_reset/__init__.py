from ._anvil_designer import z_user_pw_resetTemplate
from anvil import *
import m3.components as m3
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
#import anvil.js  # pour fermer la fenêtre qd on a demandé à l'utilisateur d'aller ds ses mails pour valider le mail de confirmation
#from anvil.js.window import localStorage
from anvil.js import window
from .. import Mail_valideur  # pour button_export_xls_click
from .. import Retour_par_test_ecran

class z_user_pw_reset(z_user_pw_resetTemplate):
    def __init__(self, email, api_key, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        
        #pour permettre un affichage du bg couleur non gérer par google, voir theme.css 
        self.password_box.role = "login-field"
        self.password_repeat_box.role = "login-field"
        
        self.password_box.text = ""
        self.password_repeat_box.text = ""
        self.email = email
        self.api_key = api_key

    def focus_password(self, **kws):
        """Focus on the password box."""
        self.password_box.focus()

    def button_validation_click(self, **event_args):
        """This method is called when the button is clicked"""
        if self.password_box.text == "":
            alert("Entrez votre Mot de Passe !")
            return
        if self.password_repeat_box.text == "":
            alert("Entrez votre Mot de Passe une 2eme fois !")
            return         
        # si 2 pass words identiques
        if self.password_box.text == self.password_repeat_box.text:
            r=anvil.server.call("_perform_password_reset",self.email, self.api_key, self.password_box.text)
            if r:
                alert("Connectez avec le nouveau Mot de Passe !")
                Retour_par_test_ecran.largeur_ecran()
        else:
            alert("Les Mots de Passe sont différents !")
            return

    def button_retour_click(self, **event_args):
        """This method is called when the button is clicked"""
        open_form('Main')

    def password_repeat_box_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        self.button_validation.visible = True

    def password_repeat_box_change(self, **event_args):
        """This method is called when the text in this component is edited."""
        self.button_validation.visible = True
