import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from services.user_service import UserService
from services.reminder_service import ReminderService
from services.scheduler_service import SchedulerService
from whisper_handler import WhisperHandler
from llm_handler import LLMHandler
from database.connection import db_manager
from utils import save_audio_file, format_message_with_clickable_link, log_user_action

logger = logging.getLogger(__name__)

class ConversationHandlers:
    """Handlers para conversação (texto e áudio)."""
    
    def __init__(self, scheduler_service: SchedulerService):
        self.scheduler_service = scheduler_service
        self.whisper_handler = WhisperHandler()
        self.llm_handler = LLMHandler()
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para mensagens de voz."""
        try:
            telegram_user = update.effective_user
            
            # Baixa o arquivo de áudio
            file = await context.bot.get_file(update.message.voice.file_id)
            audio_data = await file.download_as_bytearray()
            audio_path = save_audio_file(audio_data, ".m4a")
            
            log_user_action(telegram_user.id, "voice_message", f"file_size: {len(audio_data)}")
            
            # Informa que está processando
            await update.message.reply_text("🎙️ Transcrevendo seu áudio...")
            
            # Transcreve o áudio
            transcription = self.whisper_handler.transcribe_audio(audio_path)
            
            if not transcription:
                await update.message.reply_text(
                    "❌ Não consegui transcrever o áudio. Tente novamente ou envie uma mensagem de texto."
                )
                return
            
            # Mostra a transcrição
            await update.message.reply_text(f"📝 **Transcrição:** {transcription}")
            
            # Salva a mensagem de voz no histórico
            with db_manager.get_sync_session() as db:
                user_service = UserService(db)
                user_service.get_or_create_user(telegram_user)
                user_service.add_conversation_message(
                    telegram_user.id, 
                    "user", 
                    transcription,
                    is_voice=True,
                    transcription=transcription
                )
            
            # Processa a transcrição como uma mensagem de texto
            await self._process_text_message(update, context, transcription, is_from_voice=True)
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de voz: {e}")
            await update.message.reply_text(
                "❌ Houve um erro ao processar seu áudio. Tente novamente."
            )
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para mensagens de texto."""
        try:
            telegram_user = update.effective_user
            text = update.message.text
            
            log_user_action(telegram_user.id, "text_message", f"length: {len(text)}")
            
            # Salva a mensagem no histórico
            with db_manager.get_sync_session() as db:
                user_service = UserService(db)
                user_service.get_or_create_user(telegram_user)
                user_service.add_conversation_message(telegram_user.id, "user", text)
            
            # Processa a mensagem
            await self._process_text_message(update, context, text)
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de texto: {e}")
            await update.message.reply_text(
                "❌ Houve um erro ao processar sua mensagem. Tente novamente."
            )
    
    async def _process_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  text: str, is_from_voice: bool = False) -> None:
        """Processa uma mensagem de texto (pode vir de transcrição de voz)."""
        try:
            telegram_user = update.effective_user
            
            # Busca histórico de conversa
            with db_manager.get_sync_session() as db:
                user_service = UserService(db)
                user = user_service.get_user_by_telegram_id(telegram_user.id)
                conversation_history = user_service.get_conversation_history(telegram_user.id, limit=10)
            
            if not is_from_voice:
                await update.message.reply_text("🤔 Analisando sua mensagem...")
            
            # Converte histórico para formato do LLM
            history_for_llm = []
            for conv in conversation_history:
                history_for_llm.append({
                    "message_type": conv.message_type,
                    "content": conv.content,
                    "is_voice": conv.is_voice,
                    "transcription": conv.transcription
                })
            
            # Interpreta a mensagem com o LLM
            interpretation = self.llm_handler.interpret_message(text, history_for_llm)
            
            if interpretation.get("is_reminder"):
                await self._handle_reminder_creation(
                    update, context, interpretation, telegram_user, user
                )
            else:
                await self._handle_general_conversation(
                    update, context, interpretation, telegram_user
                )
                
        except Exception as e:
            logger.error(f"Erro ao processar texto: {e}")
            await update.message.reply_text(
                "❌ Houve um erro ao analisar sua mensagem. Tente novamente."
            )
    
    async def _handle_reminder_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                      interpretation: dict, telegram_user, user) -> None:
        """Processa a criação de um lembrete."""
        try:
            description = interpretation.get("description", "")
            date = interpretation.get("date", "hoje")
            time = interpretation.get("time", "09:00")
            urgency = interpretation.get("urgency", "média")
            
            await update.message.reply_text("📅 Criando seu lembrete...")
            
            # Gera URL do shortcut
            shortcut_url = self.llm_handler.generate_shortcut_url(description, date, time, urgency)
            
            # Processa data/hora
            with db_manager.get_sync_session() as db:
                reminder_service = ReminderService(db)
                
                reminder_data = {
                    "description": description,
                    "date": date,
                    "time": time,
                    "urgency": urgency
                }
                
                reminder_datetime = reminder_service.parse_reminder_data(
                    reminder_data, user.timezone
                )
                
                if not reminder_datetime:
                    await update.message.reply_text(
                        "❌ Não consegui entender a data/hora. Pode tentar novamente sendo mais específico?"
                    )
                    return
                
                # Cria o lembrete no banco
                reminder = reminder_service.create_reminder(
                    telegram_user.id,
                    description,
                    reminder_datetime,
                    urgency,
                    shortcut_url
                )
                
                if not reminder:
                    await update.message.reply_text(
                        "❌ Erro ao criar lembrete. Tente novamente."
                    )
                    return
                
                # Agenda o lembrete
                if self.scheduler_service.schedule_reminder(reminder):
                    log_user_action(telegram_user.id, "reminder_created", f"id: {reminder.id}")
                    
                    # Mensagem de sucesso com link clicável
                    success_message = (
                        f"✅ **Lembrete criado com sucesso!**\n\n"
                        f"📋 **Descrição:** {description}\n"
                        f"📅 **Data/Hora:** {reminder_datetime.strftime('%d/%m/%Y às %H:%M')}\n"
                        f"🎯 **Urgência:** {urgency}\n\n"
                        f"⏰ Vou te lembrar na data e hora marcadas!"
                    )
                    
                    formatted_message = format_message_with_clickable_link(success_message, shortcut_url)
                    
                    await update.message.reply_text(
                        formatted_message,
                        parse_mode='Markdown'
                    )
                    
                    # Salva resposta do assistente no histórico
                    user_service = reminder_service.user_service
                    user_service.add_conversation_message(
                        telegram_user.id, 
                        "assistant", 
                        f"Lembrete criado: {description} para {date} às {time}"
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ Lembrete criado, mas houve problema ao agendar. Verifique em /lembretes"
                    )
                    
        except Exception as e:
            logger.error(f"Erro ao criar lembrete: {e}")
            await update.message.reply_text(
                "❌ Erro ao criar lembrete. Tente novamente."
            )
    
    async def _handle_general_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                         interpretation: dict, telegram_user) -> None:
        """Processa uma conversa geral (não é lembrete)."""
        try:
            response = interpretation.get("response", "Como posso ajudar?")
            
            log_user_action(telegram_user.id, "general_conversation", f"response_length: {len(response)}")
            
            # Envia a resposta
            await update.message.reply_text(response)
            
            # Salva resposta do assistente no histórico
            with db_manager.get_sync_session() as db:
                user_service = UserService(db)
                user_service.add_conversation_message(
                    telegram_user.id, 
                    "assistant", 
                    response
                )
                
        except Exception as e:
            logger.error(f"Erro na conversa geral: {e}")
            await update.message.reply_text(
                "❌ Erro ao responder. Tente novamente."
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para callback queries (botões inline)."""
        try:
            query = update.callback_query
            telegram_user = query.from_user
            data = query.data
            
            log_user_action(telegram_user.id, "callback_query", f"data: {data}")
            
            # Responde ao callback para remover o loading
            await query.answer()
            
            if data.startswith("complete_reminder_"):
                reminder_id = int(data.split("_")[2])
                await self._handle_complete_reminder(query, reminder_id, telegram_user.id)
            
            elif data.startswith("delete_reminder_"):
                reminder_id = int(data.split("_")[2])
                await self._handle_delete_reminder(query, reminder_id, telegram_user.id)
            
            else:
                await query.edit_message_text("❌ Ação não reconhecida.")
                
        except Exception as e:
            logger.error(f"Erro no callback query: {e}")
            try:
                await update.callback_query.answer("Erro ao processar ação.")
            except:
                pass
    
    async def _handle_complete_reminder(self, query, reminder_id: int, telegram_id: int) -> None:
        """Marca um lembrete como completado."""
        try:
            with db_manager.get_sync_session() as db:
                reminder_service = ReminderService(db)
                success = reminder_service.mark_reminder_as_completed(reminder_id)
            
            if success:
                log_user_action(telegram_id, "reminder_completed", f"id: {reminder_id}")
                await query.edit_message_text(
                    "✅ Lembrete marcado como concluído!\n\n"
                    "Parabéns por completar sua tarefa! 🎉"
                )
            else:
                await query.edit_message_text(
                    "❌ Erro ao marcar lembrete como concluído."
                )
                
        except Exception as e:
            logger.error(f"Erro ao completar lembrete {reminder_id}: {e}")
            await query.edit_message_text("❌ Erro interno.")
    
    async def _handle_delete_reminder(self, query, reminder_id: int, telegram_id: int) -> None:
        """Remove um lembrete."""
        try:
            with db_manager.get_sync_session() as db:
                reminder_service = ReminderService(db)
                success = reminder_service.delete_reminder(reminder_id, telegram_id)
            
            if success:
                log_user_action(telegram_id, "reminder_deleted", f"id: {reminder_id}")
                await query.edit_message_text(
                    "🗑️ Lembrete removido com sucesso!"
                )
            else:
                await query.edit_message_text(
                    "❌ Erro ao remover lembrete ou lembrete não encontrado."
                )
                
        except Exception as e:
            logger.error(f"Erro ao deletar lembrete {reminder_id}: {e}")
            await query.edit_message_text("❌ Erro interno.")
    
    async def handle_unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para tipos de mensagem não suportados."""
        try:
            telegram_user = update.effective_user
            
            log_user_action(telegram_user.id, "unknown_message_type")
            
            await update.message.reply_text(
                "🤔 Desculpe, ainda não sei lidar com esse tipo de mensagem.\n\n"
                "Você pode:\n"
                "🎙️ Enviar mensagens de voz\n"
                "💬 Enviar mensagens de texto\n"
                "⌨️ Usar os comandos disponíveis\n\n"
                "Digite /ajuda para mais informações!"
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem desconhecida: {e}")
            try:
                await update.message.reply_text(
                    "❌ Erro ao processar mensagem."
                )
            except:
                pass