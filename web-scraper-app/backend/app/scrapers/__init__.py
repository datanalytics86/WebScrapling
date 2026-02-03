# Módulo de Scrapers
# ==================
"""
Scrapers específicos para cada sitio web.
Cada scraper hereda de BaseScraper e implementa la lógica de extracción.
"""

from .base_scraper import BaseScraper
from .mercadolibre_scraper import MercadoLibreScraper
from .falabella_scraper import FalabellaScraper
from .bci_scraper import BciBenefitsScraper

__all__ = ['BaseScraper', 'MercadoLibreScraper', 'FalabellaScraper', 'BciBenefitsScraper']
