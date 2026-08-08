# WebScrapling (legacy prototype)

> **Estado:** prototipo de febrero 2026, **sin mantenimiento activo** en esta rama.
>
> **Solución actual recomendada (Tier-1):**  
> **[AdaptiveScraper](https://github.com/datanalytics86/AdaptiveScraper)** — extractor adaptable URL → CSV/Excel  
> (httpx + Playwright, tablas/cards/vehículos, validado con checkeados.cl).

## Qué hay aquí

Carpeta `web-scraper-app/`: dashboard de precios (MercadoLibre + Falabella) + scripts standalone históricos (inmobiliario, beneficios bancarios).

## Limitaciones conocidas (prototipo Claude)

- CORS abierto, sin autenticación
- Scraping síncrono
- SQLite, sin Docker/CI/tests sólidos
- Scripts Excel sueltos no integrados

## Dónde continuar

| Necesidad | Repo |
|-----------|------|
| Extraer datos de cualquier URL a CSV/Excel | https://github.com/datanalytics86/AdaptiveScraper |
| Este dashboard de precios (histórico) | carpeta `web-scraper-app/` en este repo |

---

*Actualizado: 2026-08-08 — enlace a AdaptiveScraper.*
