# 🕷️ Web Scraper Dashboard

Dashboard de monitoreo de precios para e-commerce chileno. Permite hacer scraping de productos de MercadoLibre y Falabella, guardar histórico de precios y visualizar tendencias.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Características

- **Scraping automático** cada 6 horas (configurable)
- **Scrapers** para MercadoLibre Chile y Falabella Chile
- **Dashboard interactivo** con estadísticas en tiempo real
- **Histórico de precios** con gráficos
- **Detección de cambios** de precio mayores al 10%
- **API REST** completa con documentación automática
- **Rotación de User-Agent** para evitar bloqueos
- **Reintentos automáticos** con backoff exponencial

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Backend | FastAPI + Python 3.9+ |
| Base de datos | SQLite + SQLAlchemy |
| Scraping | BeautifulSoup4 + Requests |
| Scheduler | APScheduler |
| Frontend | HTML/CSS/JS + Chart.js |

## 📁 Estructura del Proyecto

```
web-scraper-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # Aplicación FastAPI
│   │   ├── database.py          # Configuración SQLite
│   │   ├── models.py            # Modelos SQLAlchemy
│   │   ├── schemas.py           # Schemas Pydantic
│   │   ├── scheduler.py         # Configuración APScheduler
│   │   ├── scrapers/
│   │   │   ├── __init__.py
│   │   │   ├── base_scraper.py         # Clase base abstracta
│   │   │   ├── mercadolibre_scraper.py # Scraper MercadoLibre
│   │   │   └── falabella_scraper.py    # Scraper Falabella
│   │   └── services/
│   │       ├── __init__.py
│   │       └── scraper_service.py      # Lógica de negocio
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html               # Dashboard principal
│   ├── styles.css               # Estilos CSS
│   ├── app.js                   # JavaScript
│   └── assets/
└── README.md
```

## 📦 Requisitos del Sistema

- **Python** 3.9 o superior
- **pip** (gestor de paquetes de Python)
- **Conexión a internet** (para scraping)
- **Navegador moderno** (Chrome, Firefox, Edge)

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd web-scraper-app
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar si es necesario (opcional)
nano .env
```

### 5. Iniciar el backend

```bash
# Desde el directorio backend/
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Iniciar el frontend

En una nueva terminal:

```bash
# Desde el directorio frontend/
python -m http.server 3000
```

### 7. Acceder al dashboard

- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc

## ⚙️ Configuración

El archivo `.env` permite configurar:

```env
# Base de datos
DATABASE_URL=sqlite:///./scraper.db

# Servidor
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Scheduler
SCHEDULER_ENABLED=true
SCRAPING_INTERVAL_HOURS=6

# Scraping
REQUEST_DELAY_MIN=2
REQUEST_DELAY_MAX=5
MAX_RETRIES=3

# Alertas
PRICE_CHANGE_THRESHOLD=10
```

## 📡 API Endpoints

### Websites
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/websites` | Listar sitios |
| POST | `/api/websites` | Crear sitio |
| PUT | `/api/websites/{id}` | Actualizar sitio |
| DELETE | `/api/websites/{id}` | Eliminar sitio |

### Products
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/products` | Listar productos (con filtros) |
| GET | `/api/products/{id}` | Obtener producto |
| GET | `/api/products/{id}/history` | Histórico de precios |

### Scraping
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/scrape/manual` | Ejecutar scraping manual |
| GET | `/api/scraping-logs` | Últimos logs |

### Estadísticas
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/stats` | Estadísticas generales |
| GET | `/api/scheduler/status` | Estado del scheduler |
| GET | `/api/health` | Health check |

## 🔧 Agregar Nuevos Scrapers

### 1. Crear archivo del scraper

```python
# backend/app/scrapers/nuevo_scraper.py

from typing import List
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, ScrapedProduct


class NuevoScraper(BaseScraper):
    """Scraper para NuevoSitio.com"""

    @property
    def name(self) -> str:
        return "Nuevo Sitio"

    @property
    def base_url(self) -> str:
        return "https://www.nuevositio.com"

    def build_search_url(self, search_term: str, page: int = 1) -> str:
        return f"{self.base_url}/search?q={search_term}&page={page}"

    def parse_products(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        products = []

        # Implementar lógica de extracción
        for card in soup.select('.product-card'):
            name = card.select_one('.title').get_text(strip=True)
            price = self.clean_price(card.select_one('.price').get_text())
            url = card.select_one('a')['href']

            products.append(ScrapedProduct(
                external_id=None,
                name=name,
                url=url,
                current_price=price,
                original_price=None,
                discount=0,
                image_url=None,
                currency="CLP"
            ))

        return products
```

### 2. Registrar el scraper

```python
# backend/app/scrapers/__init__.py

from .nuevo_scraper import NuevoScraper

__all__ = ['BaseScraper', 'MercadoLibreScraper', 'FalabellaScraper', 'NuevoScraper']
```

### 3. Agregar al servicio

```python
# backend/app/services/scraper_service.py

from ..scrapers.nuevo_scraper import NuevoScraper

class ScraperService:
    SCRAPER_CLASSES = {
        'MercadoLibreScraper': MercadoLibreScraper,
        'FalabellaScraper': FalabellaScraper,
        'NuevoScraper': NuevoScraper,  # Agregar aquí
    }
```

### 4. Crear sitio en la base de datos

Desde la API o el dashboard, crear un nuevo sitio con:
- `name`: "Nuevo Sitio"
- `base_url`: "https://www.nuevositio.com"
- `scraper_class`: "NuevoScraper"
- `search_term`: "notebook"

## 🧪 Testing Manual

### Probar la API

```bash
# Health check
curl http://localhost:8000/api/health

# Listar productos
curl http://localhost:8000/api/products

# Ejecutar scraping
curl -X POST http://localhost:8000/api/scrape/manual \
  -H "Content-Type: application/json" \
  -d '{"website_id": null}'

# Ver estadísticas
curl http://localhost:8000/api/stats
```

## 🐛 Solución de Problemas

### Error de CORS
Asegúrate de que el frontend accede a la API desde `localhost:8000` y no desde otro puerto.

### Scraping bloqueado
Los sitios pueden bloquear requests frecuentes. Prueba:
1. Aumentar `REQUEST_DELAY_MIN` y `REQUEST_DELAY_MAX`
2. Verificar que el User-Agent sea válido
3. Reducir la frecuencia del scheduler

### Base de datos no se crea
```bash
# Eliminar y recrear
rm backend/scraper.db
# Reiniciar el backend
```

### Dependencias faltantes
```bash
pip install -r requirements.txt --upgrade
```

## 📈 Uso de Recursos

- **Base de datos**: ~1MB por cada 1000 productos
- **Memoria**: ~100MB en ejecución
- **CPU**: Mínimo durante el dashboard, mayor durante scraping

## 📜 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## ⚠️ Disclaimer

Este proyecto es solo para fines educativos y de uso personal. Asegúrate de cumplir con los términos de servicio de los sitios web que scrapeas. El scraping excesivo puede resultar en bloqueos de IP.

---

Desarrollado con ❤️ para el monitoreo de precios en Chile.
