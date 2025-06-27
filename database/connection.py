import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config.settings import settings
from database.models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador de conexões com o banco de dados."""
    
    def __init__(self):
        """Inicializa o gerenciador de banco de dados."""
        self.engine = None
        self.SessionLocal = None
        self._setup_database()
    
    def _setup_database(self) -> None:
        """Configura a conexão com o banco de dados."""
        try:
            # Configurações específicas para SQLite
            if settings.DATABASE_URL.startswith("sqlite"):
                self.engine = create_engine(
                    settings.DATABASE_URL,
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 20
                    },
                    echo=False  # Mude para True para debug SQL
                )
            else:
                self.engine = create_engine(
                    settings.DATABASE_URL,
                    pool_pre_ping=True,
                    echo=False
                )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Conexão com banco de dados configurada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao configurar banco de dados: {e}")
            raise
    
    def create_tables(self) -> None:
        """Cria todas as tabelas no banco de dados."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Tabelas criadas com sucesso")
        except Exception as e:
            logger.error(f"Erro ao criar tabelas: {e}")
            raise
    
    def get_session(self) -> Generator[Session, None, None]:
        """Retorna uma sessão do banco de dados."""
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            logger.error(f"Erro na sessão do banco: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_sync_session(self) -> Session:
        """Retorna uma sessão síncrona (para uso fora de context managers)."""
        return self.SessionLocal()
    
    def close(self) -> None:
        """Fecha todas as conexões do pool."""
        if self.engine:
            self.engine.dispose()
            logger.info("Conexões do banco de dados fechadas")

# Instância global do gerenciador de banco
db_manager = DatabaseManager()

def get_db() -> Generator[Session, None, None]:
    """Dependency para obter uma sessão do banco de dados."""
    yield from db_manager.get_session()

def init_database() -> None:
    """Inicializa o banco de dados criando as tabelas."""
    db_manager.create_tables()