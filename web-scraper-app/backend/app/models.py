# Modelos SQLAlchemy
# ==================
"""
Modelos de base de datos para el Web Scraper Dashboard.
Define las tablas: Website, Product, PriceHistory, ScrapingLog
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from .database import Base


class Website(Base):
    """
    Modelo para sitios web monitoreados.
    Representa cada sitio de e-commerce del que se extraen datos.
    """
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    base_url = Column(String(500), nullable=False)
    scraper_class = Column(String(100), nullable=False)  # Nombre de la clase scraper
    search_term = Column(String(200), default="notebook")  # Término de búsqueda
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    products = relationship("Product", back_populates="website", cascade="all, delete-orphan")
    scraping_logs = relationship("ScrapingLog", back_populates="website", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Website(id={self.id}, name='{self.name}')>"


class Product(Base):
    """
    Modelo para productos monitoreados.
    Almacena información actualizada del producto y su precio actual.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(String(100))  # ID del producto en el sitio original
    name = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    image_url = Column(String(1000))
    current_price = Column(Float, nullable=False)
    original_price = Column(Float)  # Precio sin descuento
    discount = Column(Float, default=0)  # Porcentaje de descuento
    currency = Column(String(10), default="CLP")
    in_stock = Column(Boolean, default=True)
    price_changed = Column(Boolean, default=False)  # Indica cambio >10%
    price_change_percent = Column(Float, default=0)  # Porcentaje de cambio
    last_scraped = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    website = relationship("Website", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")

    # Índices para búsquedas frecuentes
    __table_args__ = (
        Index('idx_product_website', 'website_id'),
        Index('idx_product_name', 'name'),
        Index('idx_product_price', 'current_price'),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name[:30]}...', price={self.current_price})>"


class PriceHistory(Base):
    """
    Modelo para histórico de precios.
    Almacena cada precio registrado para un producto.
    """
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    price = Column(Float, nullable=False)
    original_price = Column(Float)
    discount = Column(Float, default=0)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    product = relationship("Product", back_populates="price_history")

    # Índice para consultas por producto y fecha
    __table_args__ = (
        Index('idx_history_product_date', 'product_id', 'scraped_at'),
    )

    def __repr__(self):
        return f"<PriceHistory(product_id={self.product_id}, price={self.price}, date={self.scraped_at})>"


class ScrapingLog(Base):
    """
    Modelo para logs de scraping.
    Registra cada ejecución del scraper con sus resultados.
    """
    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False)  # success, error, partial
    products_found = Column(Integer, default=0)
    products_updated = Column(Integer, default=0)
    products_new = Column(Integer, default=0)
    errors = Column(Text)  # JSON con lista de errores
    duration = Column(Float)  # Duración en segundos
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)

    # Relaciones
    website = relationship("Website", back_populates="scraping_logs")

    # Índice para consultas por fecha
    __table_args__ = (
        Index('idx_log_date', 'started_at'),
    )

    def __repr__(self):
        return f"<ScrapingLog(id={self.id}, website_id={self.website_id}, status='{self.status}')>"
