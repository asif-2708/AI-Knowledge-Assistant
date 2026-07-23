from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
import psycopg2

from ..core.config import settings


def create_database_if_missing(url, quiet: bool = False):
    parsed_url = make_url(str(url)) if isinstance(url, str) else url
    db_name = parsed_url.database
    if not db_name or db_name == "postgres":
        return

    admin_url = parsed_url.set(database="postgres")
    try:
        conn = psycopg2.connect(
            dbname=admin_url.database,
            user=admin_url.username,
            password=admin_url.password,
            host=admin_url.host or "localhost",
            port=admin_url.port or 5432,
        )
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cursor.fetchone() is None:
                print(f"Creating missing PostgreSQL database: {db_name}")
                cursor.execute(f"CREATE DATABASE \"{db_name}\"")
        conn.close()
    except Exception as exc:
        if not quiet:
            print("WARNING: Could not create or access configured database:", exc)
        raise


def ensure_pgvector_extension(engine):
    return


def create_engine_with_fallback(url: str):
    try:
        create_database_if_missing(url, quiet=True)
        engine = create_engine(str(url), pool_pre_ping=True)
        with engine.connect():
            pass
        return engine
    except Exception as e:
        # If running outside Docker container and 'db'/'ai_knowledge_db' host fails, try 'localhost:5433'
        parsed_url = make_url(str(url))
        if parsed_url.host in ("db", "ai_knowledge_db"):
            try:
                local_url = parsed_url.set(host="localhost", port=5433)
                create_database_if_missing(local_url, quiet=True)
                engine = create_engine(local_url, pool_pre_ping=True)
                with engine.connect():
                    pass
                print(f"Connected to Docker PostgreSQL at localhost:5433 ({parsed_url.database})")
                return engine
            except Exception as local_e:
                print(f"ERROR: Could not connect to PostgreSQL on localhost:5433. Is Docker running? Error: {local_e}")
                raise local_e
        
        print(f"ERROR: Could not connect to PostgreSQL at {url}. Error: {e}")
        raise e


engine = create_engine_with_fallback(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
