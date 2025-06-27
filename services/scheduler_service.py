import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from telegram.ext import JobQueue, CallbackContext
from telegram import Bot
from sqlalchemy.orm import Session
from services.reminder_service import ReminderService
from database.connection import db_manager
from database.models import Reminder
import pytz

logger = logging.getLogger(__name__)

class SchedulerService:
    """Serviço para gerenciamento de jobs agendados."""
    
    def __init__(self, job_queue: JobQueue, bot: Bot):
        self.job_queue = job_queue
        self.bot = bot
    
    def schedule_reminder(self, reminder: Reminder) -> bool:
        """Agenda um lembrete para ser enviado na data/hora especificada."""
        try:
            # Calcula quando enviar o lembrete
            now = datetime.now(pytz.UTC)
            reminder_time = reminder.reminder_date
            
            if reminder_time <= now:
                # Se o lembrete é para agora ou já passou, agenda para daqui a 1 minuto
                when = 60
            else:
                # Calcula a diferença em segundos
                delta = reminder_time - now
                when = delta.total_seconds()
            
            # Cria o job
            job = self.job_queue.run_once(
                callback=self._send_reminder_callback,
                when=when,
                data={
                    'reminder_id': reminder.id,
                    'user_telegram_id': reminder.user.telegram_id,
                    'description': reminder.description,
                    'shortcut_url': reminder.shortcut_url
                },
                name=reminder.job_id
            )
            
            logger.info(f"Lembrete {reminder.id} agendado para {reminder_time} (em {when}s)")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao agendar lembrete {reminder.id}: {e}")
            return False
    
    def cancel_reminder(self, job_id: str) -> bool:
        """Cancela um lembrete agendado."""
        try:
            current_jobs = self.job_queue.get_jobs_by_name(job_id)
            for job in current_jobs:
                job.schedule_removal()
            
            logger.info(f"Job {job_id} cancelado")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao cancelar job {job_id}: {e}")
            return False
    
    def _send_reminder_callback(self, context: CallbackContext) -> None:
        """Callback executado quando um lembrete deve ser enviado."""
        try:
            data = context.job.data
            reminder_id = data['reminder_id']
            user_telegram_id = data['user_telegram_id']
            description = data['description']
            shortcut_url = data['shortcut_url']
            
            # Atualiza o status do lembrete no banco
            with db_manager.get_sync_session() as db:
                reminder_service = ReminderService(db)
                reminder_service.mark_reminder_as_sent(reminder_id)
            
            # Monta a mensagem
            message = f"⏰ **Lembrete!**\n\n📋 {description}"
            
            if shortcut_url:
                message += f"\n\n🔗 [Toque aqui para criar no iPhone]({shortcut_url})"
            
            # Envia a mensagem
            context.bot.send_message(
                chat_id=user_telegram_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Lembrete {reminder_id} enviado para usuário {user_telegram_id}")
            
        except Exception as e:
            logger.error(f"Erro ao enviar lembrete: {e}")
    
    def schedule_periodic_check(self) -> None:
        """Agenda verificação periódica de lembretes pendentes."""
        try:
            # Verifica lembretes pendentes a cada 5 minutos
            self.job_queue.run_repeating(
                callback=self._check_pending_reminders_callback,
                interval=300,  # 5 minutos
                first=60,  # Primeira execução em 1 minuto
                name="periodic_reminder_check"
            )
            
            logger.info("Verificação periódica de lembretes agendada")
            
        except Exception as e:
            logger.error(f"Erro ao agendar verificação periódica: {e}")
    
    def _check_pending_reminders_callback(self, context: CallbackContext) -> None:
        """Callback para verificar lembretes pendentes que podem ter sido perdidos."""
        try:
            with db_manager.get_sync_session() as db:
                reminder_service = ReminderService(db)
                
                # Busca lembretes que deveriam ter sido enviados mas não foram
                now = datetime.now(pytz.UTC)
                pending_reminders = reminder_service.get_pending_reminders(limit_date=now)
                
                for reminder in pending_reminders:
                    # Verifica se o job ainda existe
                    existing_jobs = self.job_queue.get_jobs_by_name(reminder.job_id)
                    
                    if not existing_jobs:
                        # Job não existe, envia o lembrete agora
                        self._send_reminder_callback_direct(reminder)
                        logger.info(f"Lembrete perdido {reminder.id} enviado via verificação periódica")
                
        except Exception as e:
            logger.error(f"Erro na verificação periódica de lembretes: {e}")
    
    def _send_reminder_callback_direct(self, reminder: Reminder) -> None:
        """Envia um lembrete diretamente (sem context de job)."""
        try:
            # Atualiza o status do lembrete no banco
            with db_manager.get_sync_session() as db:
                reminder_service = ReminderService(db)
                reminder_service.mark_reminder_as_sent(reminder.id)
            
            # Monta a mensagem
            message = f"⏰ **Lembrete!**\n\n📋 {reminder.description}"
            
            if reminder.shortcut_url:
                message += f"\n\n🔗 [Toque aqui para criar no iPhone]({reminder.shortcut_url})"
            
            # Envia a mensagem
            self.bot.send_message(
                chat_id=reminder.user.telegram_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro ao enviar lembrete direto {reminder.id}: {e}")
    
    def reschedule_all_pending_reminders(self) -> None:
        """Reagenda todos os lembretes pendentes (útil na inicialização)."""
        try:
            with db_manager.get_sync_session() as db:
                reminder_service = ReminderService(db)
                
                # Busca todos os lembretes futuros não enviados
                future_date = datetime.now(pytz.UTC) + timedelta(days=365)  # 1 ano no futuro
                pending_reminders = db.query(Reminder).filter(
                    Reminder.is_sent == False,
                    Reminder.is_completed == False,
                    Reminder.reminder_date > datetime.now(pytz.UTC),
                    Reminder.reminder_date <= future_date
                ).all()
                
                scheduled_count = 0
                for reminder in pending_reminders:
                    if self.schedule_reminder(reminder):
                        scheduled_count += 1
                
                logger.info(f"{scheduled_count} lembretes pendentes reagendados")
                
        except Exception as e:
            logger.error(f"Erro ao reagendar lembretes pendentes: {e}")
    
    def get_scheduled_jobs_count(self) -> int:
        """Retorna o número de jobs atualmente agendados."""
        try:
            return len(self.job_queue.jobs())
        except Exception as e:
            logger.error(f"Erro ao contar jobs agendados: {e}")
            return 0
    
    def clear_all_jobs(self) -> None:
        """Remove todos os jobs agendados (usar com cuidado)."""
        try:
            for job in self.job_queue.jobs():
                job.schedule_removal()
            logger.info("Todos os jobs foram removidos")
        except Exception as e:
            logger.error(f"Erro ao limpar jobs: {e}")