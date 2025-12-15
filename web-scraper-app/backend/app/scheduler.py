# Configuración de APScheduler
# ============================
"""
Configuración del scheduler para ejecutar scrapers periódicamente.
Usa APScheduler con almacenamiento en memoria.
"""

import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from .database import get_db_session
from .services.scraper_service import ScraperService

# Configurar logging
logger = logging.getLogger(__name__)

# Configuración del scheduler
SCHEDULER_ENABLED = os.getenv('SCHEDULER_ENABLED', 'true').lower() == 'true'
SCRAPING_INTERVAL_HOURS = int(os.getenv('SCRAPING_INTERVAL_HOURS', 6))

# Instancia global del scheduler
scheduler = BackgroundScheduler(
    job_defaults={
        'coalesce': True,  # Combinar ejecuciones perdidas
        'max_instances': 1  # Solo una instancia a la vez
    }
)


def scraping_job():
    """
    Job de scraping que se ejecuta periódicamente.
    Scrapea todos los sitios activos.
    """
    logger.info("🕐 Iniciando job de scraping programado")

    try:
        # Crear sesión de BD
        db = get_db_session()

        try:
            # Crear servicio y ejecutar
            service = ScraperService(db)
            logs = service.run_all_active_websites(max_pages=1)

            # Resumen
            total_products = sum(log.products_found or 0 for log in logs)
            success_count = sum(1 for log in logs if log.status == 'success')

            logger.info(
                f"✅ Job completado: {len(logs)} sitios procesados, "
                f"{success_count} exitosos, {total_products} productos encontrados"
            )

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error en job de scraping: {e}")


def job_listener(event):
    """
    Listener para eventos del scheduler.
    Registra cuando los jobs se ejecutan o fallan.
    """
    if event.exception:
        logger.error(f"❌ Job falló: {event.job_id}")
    else:
        logger.info(f"✅ Job completado: {event.job_id}")


def init_scheduler():
    """
    Inicializa y arranca el scheduler.
    """
    if not SCHEDULER_ENABLED:
        logger.info("⏸️ Scheduler deshabilitado por configuración")
        return

    # Agregar listener de eventos
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # Agregar job de scraping
    scheduler.add_job(
        scraping_job,
        trigger=IntervalTrigger(hours=SCRAPING_INTERVAL_HOURS),
        id='scraping_job',
        name='Scraping Periódico',
        replace_existing=True
    )

    # Iniciar scheduler
    scheduler.start()

    logger.info(
        f"🚀 Scheduler iniciado. Scraping programado cada {SCRAPING_INTERVAL_HOURS} horas"
    )

    # Mostrar próxima ejecución
    jobs = scheduler.get_jobs()
    for job in jobs:
        logger.info(f"   Próxima ejecución de '{job.name}': {job.next_run_time}")


def shutdown_scheduler():
    """
    Detiene el scheduler de forma segura.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("⏹️ Scheduler detenido")


def get_scheduler_status() -> dict:
    """
    Obtiene el estado actual del scheduler.

    Returns:
        Diccionario con información del estado
    """
    jobs_info = []

    if scheduler.running:
        for job in scheduler.get_jobs():
            jobs_info.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'pending': job.pending
            })

    return {
        'running': scheduler.running,
        'enabled': SCHEDULER_ENABLED,
        'interval_hours': SCRAPING_INTERVAL_HOURS,
        'jobs': jobs_info
    }


def trigger_immediate_scraping():
    """
    Dispara una ejecución inmediata del scraping.
    """
    logger.info("🔄 Disparando scraping manual")

    # Ejecutar en un thread separado para no bloquear
    from threading import Thread
    thread = Thread(target=scraping_job)
    thread.start()

    return True
