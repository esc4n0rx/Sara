import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from telegram import User as TelegramUser
from database.models import User, Conversation
from database.connection import get_db

logger = logging.getLogger(__name__)

class UserService:
    """Serviço para gerenciamento de usuários."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_or_create_user(self, telegram_user: TelegramUser) -> User:
        """Obtém ou cria um usuário baseado nos dados do Telegram."""
        try:
            # Tenta encontrar usuário existente
            user = self.db.query(User).filter(
                User.telegram_id == telegram_user.id
            ).first()
            
            if user:
                # Atualiza informações se necessário
                updated = False
                if user.username != telegram_user.username:
                    user.username = telegram_user.username
                    updated = True
                if user.first_name != telegram_user.first_name:
                    user.first_name = telegram_user.first_name
                    updated = True
                if user.last_name != telegram_user.last_name:
                    user.last_name = telegram_user.last_name
                    updated = True
                
                if updated:
                    self.db.commit()
                    logger.info(f"Usuário {user.telegram_id} atualizado")
                
                return user
            
            # Cria novo usuário
            new_user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name
            )
            
            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)
            
            logger.info(f"Novo usuário criado: {new_user.telegram_id}")
            return new_user
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Erro de integridade ao criar usuário: {e}")
            # Tenta buscar novamente (pode ter sido criado em outra thread)
            return self.db.query(User).filter(
                User.telegram_id == telegram_user.id
            ).first()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar/obter usuário: {e}")
            raise
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Obtém um usuário pelo ID do Telegram."""
        try:
            return self.db.query(User).filter(
                User.telegram_id == telegram_id
            ).first()
        except Exception as e:
            logger.error(f"Erro ao buscar usuário {telegram_id}: {e}")
            return None
    
    def update_user_timezone(self, telegram_id: int, timezone: str) -> bool:
        """Atualiza o timezone do usuário."""
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            if user:
                user.timezone = timezone
                self.db.commit()
                logger.info(f"Timezone do usuário {telegram_id} atualizado para {timezone}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar timezone do usuário {telegram_id}: {e}")
            return False
    
    def deactivate_user(self, telegram_id: int) -> bool:
        """Desativa um usuário."""
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            if user:
                user.is_active = False
                self.db.commit()
                logger.info(f"Usuário {telegram_id} desativado")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao desativar usuário {telegram_id}: {e}")
            return False
    
    def add_conversation_message(self, telegram_id: int, message_type: str, 
                               content: str, is_voice: bool = False, 
                               transcription: Optional[str] = None) -> bool:
        """Adiciona uma mensagem ao histórico de conversa."""
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.error(f"Usuário {telegram_id} não encontrado para adicionar conversa")
                return False
            
            conversation = Conversation(
                user_id=user.id,
                message_type=message_type,
                content=content,
                is_voice=is_voice,
                transcription=transcription
            )
            
            self.db.add(conversation)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao adicionar mensagem à conversa: {e}")
            return False
    
    def get_conversation_history(self, telegram_id: int, limit: int = 10) -> List[Conversation]:
        """Obtém o histórico de conversa de um usuário."""
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                return []
            
            return self.db.query(Conversation).filter(
                Conversation.user_id == user.id
            ).order_by(
                Conversation.created_at.desc()
            ).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico de conversa: {e}")
            return []
    
    def clear_conversation_history(self, telegram_id: int) -> bool:
        """Limpa o histórico de conversa de um usuário."""
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                return False
            
            self.db.query(Conversation).filter(
                Conversation.user_id == user.id
            ).delete()
            
            self.db.commit()
            logger.info(f"Histórico de conversa do usuário {telegram_id} limpo")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao limpar histórico de conversa: {e}")
            return False