import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _build_url() -> str:
    """
    JawsDB Maria provides JAWSDB_MARIA_URL as:
      mysql://user:pass@host:port/dbname
    SQLAlchemy async needs the aiomysql driver:
      mysql+aiomysql://user:pass@host:port/dbname
    """
    url = settings.db_url
    if url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+aiomysql://", 1)
    return url


engine = create_async_engine(
    _build_url(),
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables on startup, retrying until DB is ready."""
    for attempt in range(30):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "ALTER TABLE pull_requests ADD COLUMN IF NOT EXISTS "
                        "review_status ENUM('changes_requested','approved','commented') NULL"
                    )
                )
                await conn.execute(
                    __import__("sqlalchemy").text(
                        "ALTER TABLE pull_requests ADD COLUMN IF NOT EXISTS "
                        "reviewers JSON NULL"
                    )
                )
            return
        except Exception as e:
            logger.warning(f"DB not ready ({attempt + 1}/30): {e}")
            await asyncio.sleep(2)
    raise RuntimeError("Could not connect to database after 30 attempts")
