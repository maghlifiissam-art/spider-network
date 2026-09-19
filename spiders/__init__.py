"""Spider Network: specialized background agents (spiders)."""

from .base import BaseSpider, SpiderResult
from .affiliate import AffiliateSpider
from .media import MediaSpider
from .digital_products import DigitalProductsSpider
from .engineering import EngineeringSpider
from .electronics import ElectronicsSpider

ALL_SPIDERS = {
    "affiliate": AffiliateSpider,
    "media": MediaSpider,
    "digital_products": DigitalProductsSpider,
    "engineering": EngineeringSpider,
    "electronics": ElectronicsSpider,
}

__all__ = [
    "BaseSpider",
    "SpiderResult",
    "ALL_SPIDERS",
    "AffiliateSpider",
    "MediaSpider",
    "DigitalProductsSpider",
    "EngineeringSpider",
    "ElectronicsSpider",
]
