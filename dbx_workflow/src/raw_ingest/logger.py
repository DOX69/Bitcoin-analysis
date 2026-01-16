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
    BEGIN_KEYWORDS = ('BEGIN', 'STARTED','INITIALIZED','END')
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
        is_warning_or_higher = record.levelno >= logging.WARNING
        is_error = any(word in message.upper() for word in self.ERROR_KEYWORDS)

        if any(word in message.upper() for word in self.BEGIN_KEYWORDS):
            color = self.BLUE
        elif any(word in message.upper() for word in self.SUCCESS_KEYWORDS):
            color = self.GREEN
        elif is_error:
            color = self.RED
        elif is_warning_or_higher:
            color = self.YELLOW
        else:
            color = self.RESET
        base_format = f"{color}%(asctime)s - %(levelname)s "
        # Format avec chemin court + couleurs
        if is_error or is_warning_or_higher:
            log_format = (
            f"{base_format}- {short_path}:%(lineno)d - %(message)s{self.RESET}"    
            )
        else: 
            log_format = (
            f"{base_format}- %(name)s - %(message)s{self.RESET}"  
            )
        formatter = logging.Formatter(log_format)
        return formatter.format(record)

# # # --- TESTS ---
# logging.basicConfig(
#     level=os.getenv("LOG_LEVEL", "INFO"),
#     format='%(asctime)s - %(pathname)s:%(lineno)d - %(levelname)s - %(message)s',
#     handlers=[logging.StreamHandler()]
# )

# logger = logging.getLogger(__name__)

# for handler in logger.handlers:
#     handler.setFormatter(CustomFormatter())

# for handler in logging.root.handlers:
#     handler.setFormatter(CustomFormatter())
# if __name__ == "__main__":
#     logger.info("Application BEGIN - Démarrage du service")
#     logger.info("Connexion OK établie avec la base de données")
#     logger.warning("Attention: ressources limitées")
#     logger.error("Erreur FAILED lors du traitement")
#     logger.info("Le processus continue")