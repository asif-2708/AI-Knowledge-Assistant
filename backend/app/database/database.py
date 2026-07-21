from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
import psycopg2

from ..core.config import settings


def create_database_if_missing(url: str, quiet: bool = False):
    parsed_url = make_url(str(url))
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
    except Exception:
        # If running outside Docker container and 'db' host fails, try 'localhost'
        parsed_url = make_url(str(url))
        if parsed_url.host == "db":
            try:
                local_url = str(url).replace("@db:", "@localhost:").replace("@db/", "@localhost/")
                create_database_if_missing(local_url, quiet=False)
                engine = create_engine(local_url, pool_pre_ping=True)
                with engine.connect():
                    pass
                print(f"Connected to PostgreSQL at localhost:5432 ({parsed_url.database})")
                return engine
            except Exception:
                pass

        print("INFO: Postgres database not reachable, falling back to local SQLite at ./ai_knowledge.db")

    return create_engine(
        "sqlite:///./ai_knowledge.db",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )


engine = create_engine_with_fallback(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
