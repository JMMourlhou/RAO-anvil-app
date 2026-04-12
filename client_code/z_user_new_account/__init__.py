from ._anvil_designer import z_user_new_accountTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.js   # pour fermer la fenêtre qd on a demandé à l'utilisateur d'aller ds ses mails pour valider le mail de confirmation
from anvil.js.window import localStorage
from anvil.js import window
from .. import Mail_valideur  # pour button_export_xls_click


class z_user_new_account(z_user_new_accountTemplate):
    def __init__(self, h={}, num_stage=0, pour_stage=0, x=0, **properties):
        # ERREUR SI JE NE METS PAS X=0, nb de param erronés.... car situé à la fin de la liste
        # Set Form properties and Data Bindings.
        # Any code you write here will run when the form opens.

        #alert(f"num_stage: {num_stage}")
        #alert(f"h: {h}")
        #alert(f"pour_stage: {pour_stage}")
        #alert(f"x: {x}")

        self.init_components(**properties)
        self.name_box.text = ""
        self.email_box.text = ""
        self.password_box.text = ""
        self.password_repeat_box.text = ""
        self.num_stage = num_stage
        self.pour_stage = pour_stage

    def button_validation_click(self, **event_args):
        """This method is called when the button is clicked"""
        # nom vide ?
        if self.name_box.text == "":
            alert("Entrez votre nom svp !")
            return
        # lg du nom >= 2 ? mais pas bloquant
        if len(self.name_box.text) <= 2 :
            r=alert("Votre Nom est-il correct ?",buttons=[("non",False),("oui",True)])
            if not r :   #Non, nom pas correct
                return
        #1ere lettre en majuscules
        nm = self.name_box.text
        nm = nm.capitalize()
        self.name_box.text = nm

        # mail vide ?
        if self.email_box.text == "":
            alert("Entrez votre mail svp !")
            self.email_box.focus()
            return
        # mail en minuscule    et strip
        mel = self.email_box.text
        mel = mel.lower()
        mel = mel.strip()
        self.email_box.text = mel

        # Mail format validation
        result = Mail_valideur.is_valid_email(mel)    # dans module Mail_valideur, fonction appelée 'is_valid_email'
        if result is False:
            alert("Le mail n'a pas le bon format !")
            self.email_box.focus()
            return

        if self.password_box.text != self.password_repeat_box.text:
            alert("Les mots de passe sont différents !")
            return
        # ------------------------------------------------------------   VALIDATION 
        err = anvil.server.call('do_signup', self.email_box.text, self.name_box.text, self.password_box.text, self.num_stage, self.pour_stage)
        if err is not None:    #erreur, on revient ds mother app
            alert(err)
            #open_form("Main",99)
            open_form("Main")
            
        else:           #Pas d'erreur, on envoi le mail de confirmation
            if anvil.server.call('_send_email_confirm_link', self.email_box.text):
                alert(f"Un email de confirmation a été envoyé à l'adresse {self.email_box.text}.<br> Ouvrez-le et cliquez sur le lien.")
                # Déconnecter l'utilisateur 
                anvil.users.logout()
                window.close()
            else:
                alert(f"'{self.email_box.text}', cette adresse est déjà confirmée. Connectez-vous !")
                """
                A FAIRE envoi en connection
                """
            #return_to_mother_app.calling_mother_app()
            """  ============================================================================================ """   

    def button_retour_click(self, **event_args):
        """This method is called when the button is clicked"""
        #open_form('Main', 99)
        open_form('Main')

    def password_repeat_box_pressed_enter(self, **event_args):
        """This method is called when the user presses Enter in this text box"""
        self.button_validation_click()

    def form_show(self, **event_args):
        """This method is called when the form is shown on the page"""
        self.name_box.focus() 

    def password_box_pressed_enter(self, **event_args):
        """This method is called when the user presses enter in this component."""
        pass

