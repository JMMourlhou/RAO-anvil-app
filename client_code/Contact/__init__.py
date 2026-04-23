from ._anvil_designer import ContactTemplate
from anvil import *
import anvil.server
import m3.components as m3
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .. import Mail_valideur  

class Contact(ContactTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        self.text_area_message.height = 100

        
    def button_retour_click(self, **event_args):
        """This method is called when the button is clicked"""
        open_form("Main_large_screen")

    def button_envoi_mail_click(self, **event_args):
        """This method is called when the button is clicked"""
        drop = self.dropdown_sujets.selected_value
        nom = (self.text_box_nom.text or "").capitalize().strip()
        activite = (self.text_box_activite.text or "").capitalize().strip()
        tel = (self.text_box_tel.text or "").strip()
        mail = (self.text_box_mail.text or "").strip()
        message = (self.text_area_message.text or "").strip()
        
        if nom != "" and activite !="" and tel and mail and drop:
            pass
        else:
            alert("Remplissez ce formulaire entierrement avant de l'envoyer !")
            if nom == "": self.text_box_nom.focus()
            if activite == "": self.text_box_activite.focus()
            if not tel: self.text_box_activite.focus()
            if not tel: self.text_box_tel.focus()
            if not mail: self.text_box_mail.focus()
            if not message: self.message_area.focus()
            if drop is None:
                alert("Sélectionnez l'objet !")
                self.dropdown_sujets.icon_color =  "theme:Red" 
                self.timer_1.interval = 0.5
                
        # Mail format validation
        result = Mail_valideur.is_valid_email(mail)    # dans module Mail_valideur, fonction appelée 'is_valid_email'
        if result is False:
            alert("L'adrese Mail a un format erroné !")
            self.text_box_mail.focus()
            return

        # Tel au bon format
        #alert(len(tel))
        #alert(tel.isdigit())
        if len(tel) != 10 or not tel.isdigit():
            alert("Le numéro de téléphone doit contenir exactement 10 chiffres, sans espace ni autre caractère.")
            self.text_box_tel.focus()
            return


    def dropdown_sujets_change(self, **event_args):
        """This method is called when an item is selected"""
        self.dropdown_sujets.icon_color = "theme:Primary"     # au cas où l'icone était rouge car pas de saisie de l'objet
        self.timer_1.interval = 0
    
    def text_area_message_change(self, **event_args):
        """This method is called when the text in this component is edited."""
        self.button_envoi_mail.visible = True


    def timer_1_tick(self, **event_args):
        """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
        if self.dropdown_sujets.icon_color == "theme:Primary":
            self.dropdown_sujets.icon_color =  "theme:Red"
        else:
             self.dropdown_sujets.icon_color = "theme:Primary"