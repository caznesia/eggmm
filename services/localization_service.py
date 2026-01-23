import json
import os
import logging

logger = logging.getLogger(__name__)

class LocalizationService:
    def __init__(self):
        self.default_lang = "en"
        self.locales = {}
        self.load_locales()
    
    def load_locales(self):
        locales_path = "locales"
        if not os.path.exists(locales_path):
            logger.warning("Locales directory not found.")
            return

        for filename in os.listdir(locales_path):
            if filename.endswith(".json"):
                lang = filename[:-5]
                try:
                    with open(os.path.join(locales_path, filename), 'r', encoding='utf-8') as f:
                        self.locales[lang] = json.load(f)
                    logger.info(f"Loaded locale: {lang}")
                except Exception as e:
                    logger.error(f"Failed to load locale {lang}: {e}")

    def get(self, key, lang="en", **kwargs):
        lang = lang.lower() if lang else self.default_lang
        if lang not in self.locales:
            lang = self.default_lang
        
        text = self.locales.get(lang, {}).get(key)
        if text is None:
            
            text = self.locales.get(self.default_lang, {}).get(key, key)
            
        try:
            return text.format(**kwargs)
        except Exception:
            return text

localization_service = LocalizationService()

