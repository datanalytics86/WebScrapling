# Configuración de Base de Datos SQLite
# ======================================
"""
Configuración de SQLAlchemy para SQLite.
Incluye funciones para crear y gestionar la conexión a la base de datos.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# URL de la base de datos (SQLite por defecto)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./scraper.db")

# Crear engine de SQLAlchemy
# check_same_thread=False es necesario para SQLite con FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # Cambiar a True para ver queries SQL en consola
)

# Habilitar foreign keys en SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Habilita las restricciones de foreign keys en SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Crear sesión local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos
Base = declarative_base()


def get_db():
    """
    Generador de sesiones de base de datos.
    Uso: se inyecta como dependencia en los endpoints de FastAPI.

    Yields:
        Session: Sesión de base de datos
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    Debe llamarse al iniciar la aplicación.
    """
    from . import models  # Import aquí para evitar imports circulares
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada correctamente")


def get_db_session():
    """
    Retorna una nueva sesión de base de datos.
    Uso: cuando no se puede usar el generador (ej: en el scheduler)

    Returns:
        Session: Nueva sesión de base de datos
    """
    return SessionLocal()
