from ._anvil_designer import Form1Template
from anvil import *
import anvil.users
import anvil.server
import m3.components as m3
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .. import Mail_valideur  # pour button_export_xls_click



class Form1(Form1Template):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Any code you write here will run before the form opens.

    def focus_name(self, **kws):
        """Focus on the password box."""
        self.email_box.focus()       

    def button_retour_click(self, **event_args):
        """This method is called when the button is clicked"""
        open_form('Main')

    def button_validation_click(self, **event_args):
        """This method is called when the button is clicked"""
        # --------------------------------Tests sur mail
        # mail vide ?
        if self.email_box.text == "":
            alert("Entrez votre mail !")
            #AlertHTML.info("Oublie :", "Entrez votre mail !")
            return
        # mail en minuscule    et strip
        mel = self.email_box.text
        mel = mel.lower()
        mel = mel.strip()
        self.email_box.text = mel

        # Mail format validation
        result = Mail_valideur.is_valid_email(mel)    # dans module Mail_valideur, fonction appelée 'is_valid_email'
        if result is False:
            alert("Mail erroné !")
            #AlertHTML.error("Adresse Mail :", "Mail erroné !")
            self.email_box.focus()
            return

        # Tests sur mot de passe   
        if self.password_box.text == "":
            #AlertHTML.info("Oublie :", "Entrez votre Mot de Passe !")
            alert("Entrez votre Mot de Passe !")
            self.password_box.focus()
            return   
        # ------------------------------------------------------------   VALIDATION 
        try:
            user=anvil.users.login_with_email(self.email_box.text, self.password_box.text, remember=True)
            user=anvil.server.call("force_log",user)
            #open_form('Main',99)    #x=3 si login normal
            open_form('Main') 
            #return_to_mother_app.calling_mother_app(99)    #je retourne et efface l'url
        except anvil.users.EmailNotConfirmed:
            alert("Votre mail n'est pas encore confirmé! Nous vous envoyons un nouveau lien par mail !")
            #AlertHTML.info("Erreur :","Votre mail n'est pas encore confirmé! Nous vous envoyons un nouveau lien par mail !")
            if anvil.server.call('_send_email_confirm_link', self.email_box.text):
                #AlertHTML.info("Confirmation de votre mail :", f"Un nouvel email de confirmation vous a été envoyé à {self.email_box.text}.")
                alert(f"Un nouvel email de confirmation vous a été envoyé à {self.email_box.text}.")
                #open_form('Main',99)   #je retourne et efface l'url
                open_form('Main')   #je retourne et efface l'url
        except anvil.users.AuthenticationFailed as e:
            #alert(f"Erreur:\n\n{e}")
            #AlertHTML.error("Erreur :", "Email ou Mot de Passe erroné !")
            alert("Email ou Mot de Passe erroné !")
            return

    def reset_pw_link_click(self, **event_args):
        """This method is called when the link is clicked"""
        # --------------------------------Tests sur mail
        # mail vide ?
        if self.email_box.text == "":
            #AlertHTML.info("Oublie :", "Entrez votre mail !")
            alert("Entrez votre mail !")
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
            #AlertHTML.error("Adresse Mail :", "Mail erroné !")
            alert("Mail erroné !")
            self.email_box.focus()
            return

        if anvil.server.call('_send_password_reset', self.email_box.text):
            #AlertHTML.info("Réinitialisation du Mot de Passe :", f"Un mail de réinitilisation vous a été envoyé à {self.email_box.text}.")
            alert(f"Un mail de réinitilisation vous a été envoyé à {self.email_box.text}.")
            #open_form('Main',99)     #je retourne et efface l'url
            open_form('Main')     #je retourne et efface l'url

    def email_box_pressed_enter(self, **event_args):
        """This method is called when the user presses Enter in this text box"""
        self.button_validation_click()

    def password_box_pressed_enter(self, **event_args):
        """This method is called when the user presses Enter in this text box"""
        self.button_validation_click()

    def password_box_change(self, **event_args):
        """This method is called when the text in this component is edited."""
        self.button_validation.visible = True

