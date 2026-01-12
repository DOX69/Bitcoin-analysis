import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class CustomFormatter(logging.Formatter):
    """Formateur affichant parent_folder/filename à la place du chemin complet"""

    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BEGIN_KEYWORDS = ('BEGIN', 'STARTED','INITIALIZED')
    SUCCESS_KEYWORDS = ('OK', 'SUCCEEDED', 'COMPLETED')
    ERROR_KEYWORDS = ('ERROR', 'FAILED', 'EXCEPTION', 'CRITICAL')
    
    def format(self, record):
        # Extraire seulement dossier parent + nom du fichier
        file_path = Path(record.pathname)
        parent_folder = file_path.parent.name
        filename = file_path.name
        short_path = f"{parent_folder}/{filename}"
        
        # Logique de couleur
        message = record.getMessage()
        if any(word in message.upper() for word in self.BEGIN_KEYWORDS):
            color = self.BLUE
        elif any(word in message.upper() for word in self.SUCCESS_KEYWORDS):
            color = self.GREEN
        elif any(word in message.upper() for word in self.ERROR_KEYWORDS):
            color = self.RED
        elif record.levelno >= logging.WARNING:
            color = self.YELLOW
        else:
            color = self.RESET
        
        # Format avec chemin court + couleurs
        log_format = (
            f"{color}%(asctime)s - %(name)s - {short_path}:%(lineno)d "
            f"- %(levelname)s - %(message)s{self.RESET}"
        )
        formatter = logging.Formatter(log_format)
        return formatter.format(record)

# # --- TESTS ---
# if __name__ == "__main__":
#     logger.info("Application BEGIN - Démarrage du service")
#     logger.info("Connexion OK établie avec la base de données")
#     logger.warning("Attention: ressources limitées")
#     logger.error("Erreur FAILED lors du traitement")
#     logger.info("Le processus continue")