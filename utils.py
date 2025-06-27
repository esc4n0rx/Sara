import os
import tempfile
import logging
from typing import Optional
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

def save_audio_file(audio_data: bytes, extension: str = ".m4a") -> str:
    """
    Salva dados de áudio em um arquivo temporário.
    
    Args:
        audio_data: Dados binários do áudio
        extension: Extensão do arquivo
        
    Returns:
        Caminho para o arquivo temporário criado
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
            temp.write(audio_data)
            temp_path = temp.name
        
        logger.debug(f"Arquivo de áudio salvo: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo de áudio: {e}")
        raise

def format_message_with_clickable_link(text: str, url: Optional[str] = None) -> str:
    """
    Formata uma mensagem com link clicável para Telegram.
    
    Args:
        text: Texto da mensagem
        url: URL para tornar clicável (opcional)
        
    Returns:
        Mensagem formatada com Markdown
    """
    try:
        formatted_text = text
        
        if url:
            # Adiciona link clicável no formato Markdown
            formatted_text += f"\n\n🔗 [Toque aqui para criar no iPhone]({url})"
        
        return formatted_text
        
    except Exception as e:
        logger.error(f"Erro ao formatar mensagem: {e}")
        return text

def escape_markdown(text: str) -> str:
    """
    Escapa caracteres especiais do Markdown para Telegram.
    
    Args:
        text: Texto a ser escapado
        
    Returns:
        Texto com caracteres especiais escapados
    """
    try:
        # Caracteres que precisam ser escapados no Markdown do Telegram
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
        
    except Exception as e:
        logger.error(f"Erro ao escapar markdown: {e}")
        return text

def convert_timezone(dt: datetime, from_tz: str, to_tz: str) -> datetime:
    """
    Converte datetime entre timezones.
    
    Args:
        dt: Datetime a ser convertido
        from_tz: Timezone de origem
        to_tz: Timezone de destino
        
    Returns:
        Datetime convertido
    """
    try:
        if dt.tzinfo is None:
            # Se não tem timezone, assume que é o timezone de origem
            source_tz = pytz.timezone(from_tz)
            dt = source_tz.localize(dt)
        else:
            # Converte para timezone de origem se necessário
            source_tz = pytz.timezone(from_tz)
            if dt.tzinfo != source_tz:
                dt = dt.astimezone(source_tz)
        
        # Converte para timezone de destino
        target_tz = pytz.timezone(to_tz)
        return dt.astimezone(target_tz)
        
    except Exception as e:
        logger.error(f"Erro na conversão de timezone: {e}")
        return dt

def format_datetime_for_user(dt: datetime, timezone: str = "America/Sao_Paulo", 
                           include_date: bool = True, include_time: bool = True) -> str:
    """
    Formata datetime para exibição amigável ao usuário.
    
    Args:
        dt: Datetime a ser formatado
        timezone: Timezone do usuário
        include_date: Se deve incluir a data
        include_time: Se deve incluir o horário
        
    Returns:
        String formatada
    """
    try:
        # Converte para timezone do usuário
        user_tz = pytz.timezone(timezone)
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        local_dt = dt.astimezone(user_tz)
        
        # Formata baseado nas opções
        if include_date and include_time:
            return local_dt.strftime("%d/%m/%Y às %H:%M")
        elif include_date:
            return local_dt.strftime("%d/%m/%Y")
        elif include_time:
            return local_dt.strftime("%H:%M")
        else:
            return local_dt.strftime("%d/%m/%Y %H:%M")
            
    except Exception as e:
        logger.error(f"Erro ao formatar datetime: {e}")
        return str(dt)

def validate_telegram_user_data(user_data: dict) -> bool:
    """
    Valida dados básicos do usuário do Telegram.
    
    Args:
        user_data: Dicionário com dados do usuário
        
    Returns:
        True se os dados são válidos
    """
    try:
        required_fields = ['id']
        
        for field in required_fields:
            if field not in user_data or user_data[field] is None:
                logger.warning(f"Campo obrigatório ausente: {field}")
                return False
        
        # Valida tipo do ID
        if not isinstance(user_data['id'], int):
            logger.warning("ID do usuário deve ser um inteiro")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Erro na validação dos dados do usuário: {e}")
        return False

def clean_temp_files(max_age_hours: int = 24) -> int:
    """
    Limpa arquivos temporários antigos.
    
    Args:
        max_age_hours: Idade máxima em horas para manter arquivos
        
    Returns:
        Número de arquivos removidos
    """
    try:
        temp_dir = tempfile.gettempdir()
        current_time = datetime.now()
        removed_count = 0
        
        for filename in os.listdir(temp_dir):
            if filename.startswith('tmp') and (filename.endswith('.m4a') or filename.endswith('.wav')):
                file_path = os.path.join(temp_dir, filename)
                
                try:
                    # Verifica a idade do arquivo
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    age_hours = (current_time - file_time).total_seconds() / 3600
                    
                    if age_hours > max_age_hours:
                        os.unlink(file_path)
                        removed_count += 1
                        logger.debug(f"Arquivo temporário removido: {filename}")
                        
                except OSError:
                    # Arquivo pode ter sido removido por outro processo
                    continue
        
        if removed_count > 0:
            logger.info(f"{removed_count} arquivos temporários antigos removidos")
        
        return removed_count
        
    except Exception as e:
        logger.error(f"Erro ao limpar arquivos temporários: {e}")
        return 0

def create_status_message(stats: dict) -> str:
    """
    Cria mensagem de status formatada para o usuário.
    
    Args:
        stats: Dicionário com estatísticas
        
    Returns:
        Mensagem formatada
    """
    try:
        total = stats.get('total', 0)
        completed = stats.get('completed', 0)
        pending = stats.get('pending', 0)
        overdue = stats.get('overdue', 0)
        
        message = "📊 **Status dos seus lembretes:**\n\n"
        message += f"📝 Total: {total}\n"
        message += f"✅ Concluídos: {completed}\n"
        message += f"⏰ Pendentes: {pending}\n"
        
        if overdue > 0:
            message += f"🔴 Atrasados: {overdue}\n"
        
        if total > 0:
            completion_rate = (completed / total) * 100
            message += f"\n📈 Taxa de conclusão: {completion_rate:.1f}%"
        
        return message
        
    except Exception as e:
        logger.error(f"Erro ao criar mensagem de status: {e}")
        return "Erro ao obter estatísticas."

def sanitize_filename(filename: str) -> str:
    """
    Sanitiza nome de arquivo removendo caracteres especiais.
    
    Args:
        filename: Nome do arquivo original
        
    Returns:
        Nome do arquivo sanitizado
    """
    try:
        # Remove caracteres especiais
        import re
        sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # Limita o tamanho
        if len(sanitized) > 100:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:100-len(ext)] + ext
        
        return sanitized
        
    except Exception as e:
        logger.error(f"Erro ao sanitizar nome do arquivo: {e}")
        return "arquivo_sanitizado"

def log_user_action(telegram_id: int, action: str, details: str = "") -> None:
    """
    Log de ações do usuário para auditoria.
    
    Args:
        telegram_id: ID do usuário no Telegram
        action: Ação realizada
        details: Detalhes adicionais
    """
    try:
        timestamp = datetime.now().isoformat()
        log_message = f"USER_ACTION: {timestamp} | User: {telegram_id} | Action: {action}"
        
        if details:
            log_message += f" | Details: {details}"
        
        logger.info(log_message)
        
    except Exception as e:
        logger.error(f"Erro ao registrar ação do usuário: {e}")