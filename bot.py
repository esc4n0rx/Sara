import os
import logging
import signal
import sys
from typing import Optional
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    MessageHandler, 
    CommandHandler,
    CallbackQueryHandler,
    filters, 
    ContextTypes
)
from config.settings import settings
from database.connection import init_database, db_manager
from services.scheduler_service import SchedulerService
from handlers.command_handlers import CommandHandlers
from handlers.conversation_handlers import ConversationHandlers
from utils import clean_temp_files

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sara_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class SaraBot:
    """Classe principal do bot Sara."""
    
    def __init__(self):
        self.application = None
        self.scheduler_service = None
        self.command_handlers = None
        self.conversation_handlers = None
    
    async def initialize(self) -> None:
        """Inicializa todos os componentes do bot."""
        try:
            logger.info("🚀 Iniciando Sara Bot...")
            
            # Inicializa banco de dados
            logger.info("📊 Inicializando banco de dados...")
            init_database()
            
            # Cria aplicação do Telegram
            self.application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()
            
            # Inicializa serviço de agendamento
            logger.info("⏰ Inicializando serviço de agendamento...")
            self.scheduler_service = SchedulerService(
                self.application.job_queue, 
                self.application.bot
            )
            
            # Inicializa handlers
            self.command_handlers = CommandHandlers(self.scheduler_service)
            self.conversation_handlers = ConversationHandlers(self.scheduler_service)
            
            # Registra handlers
            self._register_handlers()
            
            # Agenda verificação periódica de lembretes
            self.scheduler_service.schedule_periodic_check()
            
            # Reagenda lembretes pendentes
            self.scheduler_service.reschedule_all_pending_reminders()
            
            # Limpa arquivos temporários antigos
            clean_temp_files()
            
            logger.info("✅ Sara Bot inicializada com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização: {e}")
            raise
    
    def _register_handlers(self) -> None:
        """Registra todos os handlers do bot."""
        try:
            # Handlers de comandos
            self.application.add_handler(
                CommandHandler("start", self.command_handlers.start_command)
            )
            self.application.add_handler(
                CommandHandler(["ajuda", "help"], self.command_handlers.help_command)
            )
            self.application.add_handler(
                CommandHandler("lembretes", self.command_handlers.reminders_command)
            )
            self.application.add_handler(
                CommandHandler("status", self.command_handlers.status_command)
            )
            self.application.add_handler(
                CommandHandler("limpar", self.command_handlers.clear_command)
            )
            self.application.add_handler(
                CommandHandler("admin_stats", self.command_handlers.admin_stats_command)
            )
            
            # Handlers de conversa
            self.application.add_handler(
                MessageHandler(filters.VOICE, self.conversation_handlers.handle_voice_message)
            )
            self.application.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    self.conversation_handlers.handle_text_message
                )
            )
            
            # Handler para callback queries (botões inline)
            self.application.add_handler(
                CallbackQueryHandler(self.conversation_handlers.handle_callback_query)
            )
            
            # Handler para mensagens não suportadas
            self.application.add_handler(
                MessageHandler(
                    filters.ALL & ~filters.TEXT & ~filters.VOICE & ~filters.COMMAND,
                    self.conversation_handlers.handle_unknown_message
                )
            )
            
            # Handler de erro global
            self.application.add_error_handler(self._error_handler)
            
            logger.info("📋 Handlers registrados com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao registrar handlers: {e}")
            raise
    
    async def _error_handler(self, update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler global de erros."""
        try:
            error_message = f"Erro no bot: {context.error}"
            logger.error(error_message)
            
            # Se houver update e for possível responder
            if update and update.effective_chat:
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ Houve um erro interno. Nossa equipe foi notificada. Tente novamente em alguns minutos."
                    )
                except Exception as e:
                    logger.error(f"Erro ao enviar mensagem de erro: {e}")
                    
        except Exception as e:
            logger.error(f"Erro no handler de erro: {e}")
    
    async def run(self) -> None:
        """Executa o bot."""
        try:
            await self.initialize()
            
            logger.info("🤖 Sara Bot está rodando! Pressione Ctrl+C para parar.")
            
            # Configura tratamento de sinais para shutdown gracioso
            def signal_handler(signum, frame):
                logger.info("🛑 Sinal de parada recebido. Finalizando...")
                self.shutdown()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Executa o bot
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except KeyboardInterrupt:
            logger.info("🛑 Bot interrompido pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro durante execução: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """Finaliza o bot de forma segura."""
        try:
            logger.info("🧹 Finalizando Sara Bot...")
            
            # Para todos os jobs agendados
            if self.scheduler_service:
                logger.info("⏰ Parando jobs agendados...")
                # Não limpa todos os jobs, apenas para a aplicação
                # Os jobs serão reagendados na próxima inicialização
            
            # Fecha conexões do banco
            if db_manager:
                logger.info("📊 Fechando conexões do banco...")
                db_manager.close()
            
            # Limpa arquivos temporários
            clean_temp_files()
            
            logger.info("✅ Sara Bot finalizada com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro durante shutdown: {e}")

async def main():
    """Função principal."""
    try:
        # Valida configurações
        settings.validate()
        
        # Cria e executa o bot
        bot = SaraBot()
        await bot.run()
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Aplicação interrompida")
    except Exception as e:
        logger.error(f"❌ Erro na execução: {e}")
        sys.exit(1)