# Schemas Pydantic
# ================
"""
Schemas de validación y serialización para la API.
Definen la estructura de datos de entrada y salida.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# Schemas de Website
# ============================================

class WebsiteBase(BaseModel):
    """Schema base para Website"""
    name: str = Field(..., min_length=1, max_length=100, description="Nombre del sitio")
    base_url: str = Field(..., min_length=1, max_length=500, description="URL base del sitio")
    scraper_class: str = Field(..., description="Clase del scraper a usar")
    search_term: str = Field(default="notebook", description="Término de búsqueda")
    active: bool = Field(default=True, description="Si el sitio está activo")


class WebsiteCreate(WebsiteBase):
    """Schema para crear un Website"""
    pass


class WebsiteUpdate(BaseModel):
    """Schema para actualizar un Website"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    search_term: Optional[str] = None
    active: Optional[bool] = None


class WebsiteResponse(WebsiteBase):
    """Schema de respuesta para Website"""
    id: int
    created_at: datetime
    updated_at: datetime
    products_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Schemas de Product
# ============================================

class ProductBase(BaseModel):
    """Schema base para Product"""
    name: str = Field(..., max_length=500)
    url: str = Field(..., max_length=1000)
    current_price: float = Field(..., gt=0)
    original_price: Optional[float] = None
    discount: float = Field(default=0, ge=0, le=100)
    image_url: Optional[str] = None


class ProductResponse(ProductBase):
    """Schema de respuesta para Product"""
    id: int
    website_id: int
    external_id: Optional[str] = None
    currency: str = "CLP"
    in_stock: bool = True
    price_changed: bool = False
    price_change_percent: float = 0
    last_scraped: datetime
    created_at: datetime
    website_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    """Schema para listado paginado de productos"""
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================
# Schemas de PriceHistory
# ============================================

class PriceHistoryResponse(BaseModel):
    """Schema de respuesta para PriceHistory"""
    id: int
    product_id: int
    price: float
    original_price: Optional[float] = None
    discount: float = 0
    scraped_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriceHistoryListResponse(BaseModel):
    """Schema para listado de histórico de precios"""
    product_id: int
    product_name: str
    items: List[PriceHistoryResponse]


# ============================================
# Schemas de ScrapingLog
# ============================================

class ScrapingLogResponse(BaseModel):
    """Schema de respuesta para ScrapingLog"""
    id: int
    website_id: int
    website_name: Optional[str] = None
    status: str
    products_found: int
    products_updated: int
    products_new: int
    errors: Optional[str] = None
    duration: Optional[float] = None
    started_at: datetime
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Schemas de Scraping Manual
# ============================================

class ScrapeManualRequest(BaseModel):
    """Schema para solicitar scraping manual"""
    website_id: Optional[int] = Field(None, description="ID del sitio (None = todos)")


class ScrapeManualResponse(BaseModel):
    """Schema de respuesta para scraping manual"""
    message: str
    websites_scraped: int
    total_products_found: int
    logs: List[ScrapingLogResponse]


# ============================================
# Schemas de Estadísticas
# ============================================

class StatsResponse(BaseModel):
    """Schema para estadísticas generales"""
    total_websites: int
    active_websites: int
    total_products: int
    products_with_discount: int
    products_high_discount: int  # Descuento > 20%
    products_price_changed: int
    average_discount: float
    last_scraping: Optional[datetime] = None
    last_scraping_status: Optional[str] = None
    total_scrapings_today: int
    success_rate: float  # Porcentaje de scrapings exitosos


# ============================================
# Schemas de respuesta genérica
# ============================================

class MessageResponse(BaseModel):
    """Schema para mensajes simples"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Schema para errores"""
    detail: str
    error_code: Optional[str] = None
