# Aplicación Principal FastAPI
# ============================
"""
API REST para el Web Scraper Dashboard.
Incluye todos los endpoints para gestionar sitios, productos y scraping.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Imports locales
from .database import get_db, init_db, get_db_session
from .models import Website, Product, PriceHistory, ScrapingLog
from .schemas import (
    WebsiteCreate, WebsiteUpdate, WebsiteResponse,
    ProductResponse, ProductListResponse,
    PriceHistoryResponse, PriceHistoryListResponse,
    ScrapingLogResponse, ScrapeManualRequest, ScrapeManualResponse,
    StatsResponse, MessageResponse
)
from .services.scraper_service import ScraperService
from .scheduler import init_scheduler, shutdown_scheduler, get_scheduler_status

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifecycle manager para startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación."""
    # Startup
    logger.info("🚀 Iniciando Web Scraper Dashboard API")

    # Inicializar base de datos
    init_db()

    # Crear sitios por defecto
    db = get_db_session()
    try:
        service = ScraperService(db)
        service.initialize_default_websites()
    finally:
        db.close()

    # Iniciar scheduler
    init_scheduler()

    yield

    # Shutdown
    logger.info("⏹️ Deteniendo aplicación")
    shutdown_scheduler()


# Crear aplicación FastAPI
app = FastAPI(
    title="Web Scraper Dashboard API",
    description="API para monitoreo de precios de productos de e-commerce",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS (permitir todos los orígenes para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Endpoints de Websites
# ============================================

@app.get("/api/websites", response_model=List[WebsiteResponse], tags=["Websites"])
def list_websites(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Lista todos los sitios web configurados.

    - **active_only**: Si es True, solo retorna sitios activos
    """
    query = db.query(Website)

    if active_only:
        query = query.filter(Website.active == True)

    websites = query.order_by(Website.created_at.desc()).all()

    # Agregar conteo de productos
    result = []
    for website in websites:
        products_count = db.query(func.count(Product.id)).filter(
            Product.website_id == website.id
        ).scalar()

        website_dict = {
            'id': website.id,
            'name': website.name,
            'base_url': website.base_url,
            'scraper_class': website.scraper_class,
            'search_term': website.search_term,
            'active': website.active,
            'created_at': website.created_at,
            'updated_at': website.updated_at,
            'products_count': products_count
        }
        result.append(WebsiteResponse(**website_dict))

    return result


@app.post("/api/websites", response_model=WebsiteResponse, tags=["Websites"])
def create_website(
    website_data: WebsiteCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo sitio web para monitorear.
    """
    # Verificar que no exista
    existing = db.query(Website).filter(Website.name == website_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un sitio con ese nombre")

    # Verificar que el scraper existe
    available_scrapers = ScraperService.get_available_scrapers()
    if website_data.scraper_class not in available_scrapers:
        raise HTTPException(
            status_code=400,
            detail=f"Scraper no válido. Disponibles: {list(available_scrapers.keys())}"
        )

    website = Website(**website_data.model_dump())
    db.add(website)
    db.commit()
    db.refresh(website)

    return WebsiteResponse(
        **website.__dict__,
        products_count=0
    )


@app.put("/api/websites/{website_id}", response_model=WebsiteResponse, tags=["Websites"])
def update_website(
    website_id: int,
    website_data: WebsiteUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza un sitio web existente.
    """
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(status_code=404, detail="Sitio web no encontrado")

    # Actualizar campos proporcionados
    update_data = website_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(website, field, value)

    db.commit()
    db.refresh(website)

    products_count = db.query(func.count(Product.id)).filter(
        Product.website_id == website.id
    ).scalar()

    return WebsiteResponse(**website.__dict__, products_count=products_count)


@app.delete("/api/websites/{website_id}", response_model=MessageResponse, tags=["Websites"])
def delete_website(
    website_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un sitio web y todos sus productos asociados.
    """
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(status_code=404, detail="Sitio web no encontrado")

    db.delete(website)
    db.commit()

    return MessageResponse(message=f"Sitio '{website.name}' eliminado correctamente")


@app.get("/api/scrapers", tags=["Websites"])
def list_available_scrapers():
    """
    Lista los scrapers disponibles para configurar sitios.
    """
    return ScraperService.get_available_scrapers()


# ============================================
# Endpoints de Products
# ============================================

@app.get("/api/products", response_model=ProductListResponse, tags=["Products"])
def list_products(
    website_id: Optional[int] = None,
    search: Optional[str] = None,
    min_discount: Optional[float] = None,
    price_changed: Optional[bool] = None,
    sort_by: str = Query("last_scraped", regex="^(name|current_price|discount|last_scraped)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Lista productos con filtros y paginación.

    - **website_id**: Filtrar por sitio web
    - **search**: Buscar en nombre del producto
    - **min_discount**: Descuento mínimo (0-100)
    - **price_changed**: Solo productos con cambio de precio >10%
    - **sort_by**: Campo para ordenar (name, current_price, discount, last_scraped)
    - **sort_order**: Orden (asc, desc)
    - **page**: Número de página
    - **page_size**: Productos por página
    """
    query = db.query(Product)

    # Aplicar filtros
    if website_id:
        query = query.filter(Product.website_id == website_id)

    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    if min_discount is not None:
        query = query.filter(Product.discount >= min_discount)

    if price_changed is not None:
        query = query.filter(Product.price_changed == price_changed)

    # Contar total
    total = query.count()

    # Aplicar ordenamiento
    sort_column = getattr(Product, sort_by)
    if sort_order == "desc":
        sort_column = desc(sort_column)
    query = query.order_by(sort_column)

    # Aplicar paginación
    offset = (page - 1) * page_size
    products = query.offset(offset).limit(page_size).all()

    # Obtener nombres de websites
    website_names = {
        w.id: w.name for w in db.query(Website).all()
    }

    # Construir respuesta
    items = []
    for product in products:
        product_dict = product.__dict__.copy()
        product_dict['website_name'] = website_names.get(product.website_id)
        items.append(ProductResponse(**product_dict))

    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@app.get("/api/products/{product_id}", response_model=ProductResponse, tags=["Products"])
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene un producto específico por ID.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    website = db.query(Website).filter(Website.id == product.website_id).first()

    return ProductResponse(
        **product.__dict__,
        website_name=website.name if website else None
    )


@app.get("/api/products/{product_id}/history", response_model=PriceHistoryListResponse, tags=["Products"])
def get_product_history(
    product_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Obtiene el histórico de precios de un producto.

    - **days**: Número de días hacia atrás (1-365)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Filtrar por fecha
    since_date = datetime.utcnow() - timedelta(days=days)

    history = db.query(PriceHistory).filter(
        PriceHistory.product_id == product_id,
        PriceHistory.scraped_at >= since_date
    ).order_by(PriceHistory.scraped_at.asc()).all()

    return PriceHistoryListResponse(
        product_id=product_id,
        product_name=product.name,
        items=[PriceHistoryResponse(**h.__dict__) for h in history]
    )


# ============================================
# Endpoints de Scraping
# ============================================

@app.post("/api/scrape/manual", response_model=ScrapeManualResponse, tags=["Scraping"])
def run_manual_scraping(
    request: ScrapeManualRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ejecuta scraping manual para uno o todos los sitios.

    - **website_id**: ID del sitio (None = todos los activos)
    """
    if request.website_id:
        # Scraping de un sitio específico
        website = db.query(Website).filter(Website.id == request.website_id).first()
        if not website:
            raise HTTPException(status_code=404, detail="Sitio web no encontrado")

        if not website.active:
            raise HTTPException(status_code=400, detail="El sitio está desactivado")

        websites = [website]
    else:
        # Scraping de todos los sitios activos
        websites = db.query(Website).filter(Website.active == True).all()

    if not websites:
        raise HTTPException(status_code=400, detail="No hay sitios activos para scrapear")

    # Ejecutar scraping
    service = ScraperService(db)
    logs = []
    total_products = 0

    for website in websites:
        try:
            log = service.run_scraping_for_website(website, max_pages=1)
            logs.append(ScrapingLogResponse(
                **log.__dict__,
                website_name=website.name
            ))
            total_products += log.products_found or 0
        except Exception as e:
            logger.error(f"Error scrapeando {website.name}: {e}")

    return ScrapeManualResponse(
        message=f"Scraping completado para {len(logs)} sitio(s)",
        websites_scraped=len(logs),
        total_products_found=total_products,
        logs=logs
    )


@app.get("/api/scraping-logs", response_model=List[ScrapingLogResponse], tags=["Scraping"])
def list_scraping_logs(
    website_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Lista los últimos logs de scraping.

    - **website_id**: Filtrar por sitio
    - **limit**: Número máximo de logs (1-200)
    """
    query = db.query(ScrapingLog)

    if website_id:
        query = query.filter(ScrapingLog.website_id == website_id)

    logs = query.order_by(desc(ScrapingLog.started_at)).limit(limit).all()

    # Obtener nombres de websites
    website_names = {w.id: w.name for w in db.query(Website).all()}

    return [
        ScrapingLogResponse(
            **log.__dict__,
            website_name=website_names.get(log.website_id)
        )
        for log in logs
    ]


# ============================================
# Endpoints de Estadísticas
# ============================================

@app.get("/api/stats", response_model=StatsResponse, tags=["Statistics"])
def get_stats(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas generales del sistema.
    """
    # Conteos básicos
    total_websites = db.query(func.count(Website.id)).scalar()
    active_websites = db.query(func.count(Website.id)).filter(Website.active == True).scalar()
    total_products = db.query(func.count(Product.id)).scalar()

    # Productos con descuento
    products_with_discount = db.query(func.count(Product.id)).filter(
        Product.discount > 0
    ).scalar()

    products_high_discount = db.query(func.count(Product.id)).filter(
        Product.discount >= 20
    ).scalar()

    products_price_changed = db.query(func.count(Product.id)).filter(
        Product.price_changed == True
    ).scalar()

    # Promedio de descuento
    avg_discount = db.query(func.avg(Product.discount)).filter(
        Product.discount > 0
    ).scalar() or 0

    # Último scraping
    last_log = db.query(ScrapingLog).order_by(
        desc(ScrapingLog.started_at)
    ).first()

    # Scrapings de hoy
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    scrapings_today = db.query(func.count(ScrapingLog.id)).filter(
        ScrapingLog.started_at >= today_start
    ).scalar()

    # Tasa de éxito
    total_scrapings = db.query(func.count(ScrapingLog.id)).scalar()
    successful_scrapings = db.query(func.count(ScrapingLog.id)).filter(
        ScrapingLog.status == 'success'
    ).scalar()

    success_rate = (successful_scrapings / max(total_scrapings, 1)) * 100

    return StatsResponse(
        total_websites=total_websites,
        active_websites=active_websites,
        total_products=total_products,
        products_with_discount=products_with_discount,
        products_high_discount=products_high_discount,
        products_price_changed=products_price_changed,
        average_discount=round(avg_discount, 2),
        last_scraping=last_log.started_at if last_log else None,
        last_scraping_status=last_log.status if last_log else None,
        total_scrapings_today=scrapings_today,
        success_rate=round(success_rate, 2)
    )


@app.get("/api/scheduler/status", tags=["System"])
def get_scheduler_info():
    """
    Obtiene el estado del scheduler.
    """
    return get_scheduler_status()


# ============================================
# Health Check
# ============================================

@app.get("/api/health", tags=["System"])
def health_check():
    """
    Verifica el estado de la API.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# ============================================
# Error Handlers
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Manejador global de excepciones.
    """
    logger.error(f"Error no manejado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "error": str(exc)
        }
    )


# ============================================
# Punto de entrada para desarrollo
# ============================================

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "true").lower() == "true"

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug
    )
