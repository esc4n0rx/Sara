import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from dateutil.parser import parse as parse_date
import pytz
from database.models import User, Reminder
from services.user_service import UserService
from config.settings import settings

logger = logging.getLogger(__name__)

class ReminderService:
    """Serviço para gerenciamento de lembretes."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.user_service = UserService(db_session)
    
    def create_reminder(self, telegram_id: int, description: str, 
                       reminder_date: datetime, urgency: str = "média", 
                       shortcut_url: Optional[str] = None) -> Optional[Reminder]:
        """Cria um novo lembrete."""
        try:
            user = self.user_service.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.error(f"Usuário {telegram_id} não encontrado para criar lembrete")
                return None
            
            # Gera um ID único para o job
            job_id = f"reminder_{uuid.uuid4().hex[:8]}_{user.id}"
            
            reminder = Reminder(
                user_id=user.id,
                description=description,
                reminder_date=reminder_date,
                urgency=urgency,
                job_id=job_id,
                shortcut_url=shortcut_url
            )
            
            self.db.add(reminder)
            self.db.commit()
            self.db.refresh(reminder)
            
            logger.info(f"Lembrete criado: {reminder.id} para usuário {telegram_id}")
            return reminder
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar lembrete: {e}")
            return None
    
    def get_user_reminders(self, telegram_id: int, 
                          include_completed: bool = False) -> List[Reminder]:
        """Obtém todos os lembretes de um usuário."""
        try:
            user = self.user_service.get_user_by_telegram_id(telegram_id)
            if not user:
                return []
            
            query = self.db.query(Reminder).filter(Reminder.user_id == user.id)
            
            if not include_completed:
                query = query.filter(Reminder.is_completed == False)
            
            return query.order_by(Reminder.reminder_date.asc()).all()
            
        except Exception as e:
            logger.error(f"Erro ao buscar lembretes do usuário {telegram_id}: {e}")
            return []
    
    def get_pending_reminders(self, limit_date: Optional[datetime] = None) -> List[Reminder]:
        """Obtém lembretes pendentes que precisam ser enviados."""
        try:
            query = self.db.query(Reminder).filter(
                Reminder.is_sent == False,
                Reminder.is_completed == False
            )
            
            if limit_date:
                query = query.filter(Reminder.reminder_date <= limit_date)
            else:
                # Por padrão, busca lembretes até agora
                query = query.filter(Reminder.reminder_date <= datetime.now(pytz.UTC))
            
            return query.order_by(Reminder.reminder_date.asc()).all()
            
        except Exception as e:
            logger.error(f"Erro ao buscar lembretes pendentes: {e}")
            return []
    
    def mark_reminder_as_sent(self, reminder_id: int) -> bool:
        """Marca um lembrete como enviado."""
        try:
            reminder = self.db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if reminder:
                reminder.is_sent = True
                self.db.commit()
                logger.info(f"Lembrete {reminder_id} marcado como enviado")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao marcar lembrete {reminder_id} como enviado: {e}")
            return False
    
    def mark_reminder_as_completed(self, reminder_id: int) -> bool:
        """Marca um lembrete como completado."""
        try:
            reminder = self.db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if reminder:
                reminder.is_completed = True
                self.db.commit()
                logger.info(f"Lembrete {reminder_id} marcado como completado")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao marcar lembrete {reminder_id} como completado: {e}")
            return False
    
    def delete_reminder(self, reminder_id: int, telegram_id: int) -> bool:
        """Remove um lembrete (apenas se pertencer ao usuário)."""
        try:
            user = self.user_service.get_user_by_telegram_id(telegram_id)
            if not user:
                return False
            
            reminder = self.db.query(Reminder).filter(
                Reminder.id == reminder_id,
                Reminder.user_id == user.id
            ).first()
            
            if reminder:
                self.db.delete(reminder)
                self.db.commit()
                logger.info(f"Lembrete {reminder_id} removido para usuário {telegram_id}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao remover lembrete {reminder_id}: {e}")
            return False
    
    def parse_reminder_data(self, reminder_data: Dict[str, Any], 
                           user_timezone: str = settings.DEFAULT_TIMEZONE) -> Optional[datetime]:
        """Converte dados de lembrete em datetime com timezone."""
        try:
            date_str = reminder_data.get("date", "")
            time_str = reminder_data.get("time", "")
            
            # Timezone do usuário
            tz = pytz.timezone(user_timezone)
            now = datetime.now(tz)
            
            # Processa data relativa
            if date_str.lower() in ["hoje", "today"]:
                target_date = now.date()
            elif date_str.lower() in ["amanhã", "amanha", "tomorrow"]:
                target_date = (now + timedelta(days=1)).date()
            else:
                # Tenta fazer parse da data
                try:
                    parsed_date = parse_date(date_str, default=now)
                    target_date = parsed_date.date()
                except:
                    # Se falhar, assume hoje
                    target_date = now.date()
            
            # Processa horário
            if time_str:
                try:
                    time_parts = time_str.split(":")
                    if len(time_parts) >= 2:
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                    else:
                        hour = int(time_str)
                        minute = 0
                except:
                    hour, minute = 9, 0  # Horário padrão
            else:
                hour, minute = 9, 0  # Horário padrão se não especificado
            
            # Combina data e hora com timezone
            target_datetime = tz.localize(
                datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))
            )
            
            # Converte para UTC para armazenamento
            return target_datetime.astimezone(pytz.UTC)
            
        except Exception as e:
            logger.error(f"Erro ao processar dados do lembrete: {e}")
            return None
    
    def format_reminder_list(self, reminders: List[Reminder], 
                           user_timezone: str = settings.DEFAULT_TIMEZONE) -> str:
        """Formata uma lista de lembretes para exibição."""
        if not reminders:
            return "📝 Você não tem lembretes pendentes."
        
        tz = pytz.timezone(user_timezone)
        formatted_reminders = []
        
        for reminder in reminders:
            # Converte data para timezone do usuário
            local_date = reminder.reminder_date.astimezone(tz)
            date_str = local_date.strftime("%d/%m/%Y às %H:%M")
            
            # Emoji baseado na urgência
            urgency_emoji = {
                "baixa": "🟢",
                "média": "🟡", 
                "alta": "🔴"
            }.get(reminder.urgency, "🟡")
            
            # Status
            status = "✅" if reminder.is_completed else "⏰"
            
            formatted_reminders.append(
                f"{status} {urgency_emoji} {date_str}\n"
                f"   📋 {reminder.description}"
            )
        
        return "📝 **Seus lembretes:**\n\n" + "\n\n".join(formatted_reminders)
    
    def get_reminder_statistics(self, telegram_id: int) -> Dict[str, int]:
        """Obtém estatísticas dos lembretes do usuário."""
        try:
            user = self.user_service.get_user_by_telegram_id(telegram_id)
            if not user:
                return {}
            
            total = self.db.query(Reminder).filter(Reminder.user_id == user.id).count()
            completed = self.db.query(Reminder).filter(
                Reminder.user_id == user.id,
                Reminder.is_completed == True
            ).count()
            pending = self.db.query(Reminder).filter(
                Reminder.user_id == user.id,
                Reminder.is_completed == False,
                Reminder.reminder_date > datetime.now(pytz.UTC)
            ).count()
            overdue = self.db.query(Reminder).filter(
                Reminder.user_id == user.id,
                Reminder.is_completed == False,
                Reminder.reminder_date <= datetime.now(pytz.UTC)
            ).count()
            
            return {
                "total": total,
                "completed": completed,
                "pending": pending,
                "overdue": overdue
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de lembretes: {e}")
            return {}