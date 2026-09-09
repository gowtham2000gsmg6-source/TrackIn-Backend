import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Fetch database URL from environment variables, default to a local SQLite database for development ease
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mcet_visitor_tracking.db")

# Some providers (Neon, Supabase, Render, Railway) hand out "postgres://" URLs,
# but SQLAlchemy 2.x requires the "postgresql://" scheme.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Setup database connection arguments
connect_args = {}
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
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

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get db session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
