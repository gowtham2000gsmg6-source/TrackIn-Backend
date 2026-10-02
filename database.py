import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Fetch database URL from environment variables, default to a local SQLite database for development ease
database_url = make_url(os.getenv("DATABASE_URL", "sqlite:///./mcet_visitor_tracking.db"))

# Use the PostgreSQL driver already installed in requirements.txt, including
# when a provider supplies a URL explicitly selecting psycopg 3.
if database_url.drivername in {
    "postgres",
    "postgresql",
    "postgres+psycopg",
    "postgresql+psycopg",
}:
    database_url = database_url.set(drivername="postgresql+psycopg2")

# Setup database connection arguments
connect_args = {}
engine_kwargs = {}
if database_url.drivername.startswith("sqlite"):
    # NOTE: SQLite is fine for local dev, but Vercel's Python functions run on
    # ephemeral, read-mostly serverless containers with no persistent disk -
    # any writes (new visitors, check-ins) would vanish between requests and
    # concurrent invocations wouldn't share a file at all. Set a real
    # DATABASE_URL (e.g. a free Neon/Supabase Postgres instance) in
    # production; this branch only exists for `uvicorn main:app` locally.
    connect_args = {"check_same_thread": False}
else:
    # Serverless functions spin up many short-lived instances, so keep the
    # pool small and recycle connections that providers may silently close.
    engine_kwargs = {"pool_pre_ping": True, "pool_size": 3, "max_overflow": 2}

engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get db session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
