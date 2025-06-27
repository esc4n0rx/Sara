import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from services.user_service import UserService
from services.reminder_service import ReminderService
from services.scheduler_service import SchedulerService
from database.connection import db_manager
from utils import create_status_message, log_user_action
from config.settings import settings

logger = logging.getLogger(__name__)

class CommandHandlers:
    """Handlers para comandos do bot."""
    
    def __init__(self, scheduler_service: SchedulerService):
        self.scheduler_service = scheduler_service
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para o comando /start."""
        try:
            telegram_user = update.effective_user
            chat_id = update.effective_chat.id
            
            # Registra ou atualiza usuário no banco
            with db_manager.get_sync_session() as db:
                user_service = UserService(db)
                user = user_service.get_or_create_user(telegram_user)
            
            log_user_action(telegram_user.id, "start_command")
            
            welcome_message = (
                f"👋 Olá, {telegram_user.first_name}!\n\n"
                f"Eu sou a **Sara**, sua assistente pessoal! 🤖\n\n"
                f"**O que posso fazer por você:**\n"
                f"🎙️ Envie áudios para criar lembretes\n"
                f"💬 Faça perguntas ou converse comigo\n"
                f"📅 Crio lembretes inteligentes para seu iPhone\n"
                f"⏰ Te lembro na data e hora que você escolher\n\n"
                f"**Comandos disponíveis:**\n"
                f"/lembretes - Ver seus lembretes\n"
                f"/status - Estatísticas dos lembretes\n"
                f"/ajuda - Mais informações\n"
                f"/limpar - Limpar histórico de conversa\n\n"
                f"Comece enviando um áudio ou digitando algo! 😊"
            )
            
            await update.message.reply_text(
                welcome_message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro no comando start: {e}")
            await update.message.reply_text(
                "Houve um erro ao inicializar. Tente novamente."
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para o comando /ajuda."""
        try:
            telegram_user = update.effective_user
            log_user_action(telegram_user.id, "help_command")
            
            help_message = (
                "🤖 **Como usar a Sara:**\n\n"
                "**📱 Criando lembretes por áudio:**\n"
                "• Grave um áudio falando o que quer lembrar\n"
                "• Inclua data, hora e descrição\n"
                "• Ex: \"Lembrar de pagar a conta de luz sexta-feira às 9h\"\n\n"
                "**💬 Conversando:**\n"
                "• Faça perguntas sobre qualquer assunto\n"
                "• Mantenho o contexto da nossa conversa\n"
                "• Posso ajudar com informações gerais\n\n"
                "**📅 Sobre os lembretes:**\n"
                "• Crio um link clicável para seu iPhone\n"
                "• O lembrete é adicionado automaticamente\n"
                "• Te aviso na data/hora que você escolher\n\n"
                "**⚙️ Comandos úteis:**\n"
                "/lembretes - Lista seus lembretes\n"
                "/status - Mostra estatísticas\n"
                "/limpar - Remove histórico de conversa\n\n"
                "**💡 Dicas:**\n"
                "• Seja específico com datas e horários\n"
                "• Use \"hoje\", \"amanhã\" ou datas completas\n"
                "• Indique a urgência (baixa, média, alta)\n\n"
                "Precisa de mais ajuda? Só perguntar! 😊"
            )
            
            await update.message.reply_text(
                help_message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro no comando help: {e}")
            await update.message.reply_text(
                "Erro ao exibir ajuda. Tente novamente."
            )
    
    async def reminders_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para o comando /lembretes."""
        try:
            telegram_user = update.effective_user
            log_user_action(telegram_user.id, "reminders_command")
            
            with db_manager.get_sync_session() as db:
                reminder_service = ReminderService(db)
                user_service = UserService(db)
                
                # Busca usuário para obter timezone
                user = user_service.get_user_by_telegram_id(telegram_user.id)
                if not user:
                    await update.message.reply_text(
                        "Você precisa usar /start primeiro para se registrar."
                    )
                    return
                
                # Busca lembretes do usuário
                reminders = reminder_service.get_user_reminders(telegram_user.id)
                
                if not reminders:
                    message = (
                        "📝 Você ainda não tem lembretes.\n\n"
                        "Envie um áudio para criar seu primeiro lembrete!"
                    )
                else:
                    message = reminder_service.format_reminder_list(reminders, user.timezone)
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro no comando reminders: {e}")
            await update.message.reply_text(
                "Erro ao buscar lembretes. Tente novamente."
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para o comando /status."""
        try:
            telegram_user = update.effective_user
            log_user_action(telegram_user.id, "status_command")
            
            with db_manager.get_sync_session() as db:
                reminder_service = ReminderService(db)
                stats = reminder_service.get_reminder_statistics(telegram_user.id)
            
            if not stats:
                message = (
                    "📊 Ainda não há estatísticas para mostrar.\n\n"
                    "Crie alguns lembretes primeiro!"
                )
            else:
                message = create_status_message(stats)
                
                # Adiciona informações do sistema
                job_count = self.scheduler_service.get_scheduled_jobs_count()
                message += f"\n\n🔧 Jobs agendados: {job_count}"
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro no comando status: {e}")
            await update.message.reply_text(
                "Erro ao obter estatísticas. Tente novamente."
            )
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para o comando /limpar."""
        try:
            telegram_user = update.effective_user
            log_user_action(telegram_user.id, "clear_command")
            
            with db_manager.get_sync_session() as db:
                user_service = UserService(db)
                success = user_service.clear_conversation_history(telegram_user.id)
            
            if success:
                message = (
                    "🧹 Histórico de conversa limpo com sucesso!\n\n"
                    "Nossa próxima conversa será como se fosse a primeira vez."
                )
            else:
                message = "Erro ao limpar histórico. Tente novamente."
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Erro no comando clear: {e}")
            await update.message.reply_text(
                "Erro ao limpar histórico. Tente novamente."
            )
    
    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para comando de estatísticas administrativas (se necessário)."""
        try:
            telegram_user = update.effective_user
            
            # Verifica se é um administrador (implemente sua lógica aqui)
            admin_ids = []  # Lista de IDs de administradores
            if telegram_user.id not in admin_ids:
                await update.message.reply_text("Comando não autorizado.")
                return
            
            log_user_action(telegram_user.id, "admin_stats_command")
            
            with db_manager.get_sync_session() as db:
                # Estatísticas gerais do sistema
                from database.models import User, Reminder
                
                total_users = db.query(User).count()
                active_users = db.query(User).filter(User.is_active == True).count()
                total_reminders = db.query(Reminder).count()
                pending_reminders = db.query(Reminder).filter(
                    Reminder.is_completed == False,
                    Reminder.is_sent == False
                ).count()
            
            job_count = self.scheduler_service.get_scheduled_jobs_count()
            
            admin_message = (
                "🔧 **Estatísticas do Sistema:**\n\n"
                f"👥 Usuários totais: {total_users}\n"
                f"✅ Usuários ativos: {active_users}\n"
                f"📝 Lembretes totais: {total_reminders}\n"
                f"⏰ Lembretes pendentes: {pending_reminders}\n"
                f"🔄 Jobs agendados: {job_count}\n"
            )
            
            await update.message.reply_text(
                admin_message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro no comando admin_stats: {e}")
            await update.message.reply_text(
                "Erro ao obter estatísticas administrativas."
            )