import json
import os
import logging

logger = logging.getLogger(__name__)

class LocalizationService:
    def __init__(self):
        self.default_lang = "en"
        self.locales = {}
        self.lang_map = {
            "english": "en",
            "hindi": "hi",
            "hinglish": "hinglish",
            "russian": "ru",
            "spanish": "es",
            "french": "fr",
            "chinese": "zh-cn",
            "turkish": "tr"
        }
        self.load_locales()
    
    def load_locales(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        locales_path = os.path.join(base_dir, "locales")
        if not os.path.exists(locales_path):
            logger.warning(f"Locales directory not found: {locales_path}")
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
        # Handle full names like "English" or "Spanish"
        lang = lang.lower() if lang else self.default_lang
        lang_code = self.lang_map.get(lang, lang)
        
        if lang_code not in self.locales:
            lang_code = self.default_lang
        
        text = self.locales.get(lang_code, {}).get(key)
        if text is None:
            # Fallback to English
            text = self.locales.get(self.default_lang, {}).get(key, key)
            
        try:
            return text.format(**kwargs)
        except Exception:
            return text

localization_service = LocalizationService()

