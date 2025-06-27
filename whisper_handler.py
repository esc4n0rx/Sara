import os
import logging
from typing import Optional
from groq import Groq
from config.settings import settings

logger = logging.getLogger(__name__)

class WhisperHandler:
    """Handler melhorado para transcrição de áudio usando Whisper."""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
    
    def transcribe_audio(self, audio_path: str, language: str = "pt") -> Optional[str]:
        """
        Transcreve áudio para texto usando Whisper.
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            language: Código do idioma (pt para português)
            
        Returns:
            Texto transcrito ou None em caso de erro
        """
        try:
            if not os.path.exists(audio_path):
                logger.error(f"Arquivo de áudio não encontrado: {audio_path}")
                return None
            
            # Verifica o tamanho do arquivo (limite da API)
            file_size = os.path.getsize(audio_path)
            if file_size > 25 * 1024 * 1024:  # 25MB
                logger.error(f"Arquivo muito grande: {file_size} bytes")
                return None
            
            with open(audio_path, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=(audio_path, file.read()),
                    model=settings.WHISPER_MODEL,
                    response_format="verbose_json",
                    language=language,
                    temperature=0.0  # Mais determinístico
                )
            
            # Extrai apenas o texto
            text = transcription.text.strip()
            
            if not text:
                logger.warning("Transcrição resultou em texto vazio")
                return None
            
            logger.info(f"Áudio transcrito com sucesso: {len(text)} caracteres")
            return text
            
        except Exception as e:
            logger.error(f"Erro na transcrição do áudio: {e}")
            return None
        finally:
            # Limpa o arquivo temporário
            try:
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
                    logger.debug(f"Arquivo temporário removido: {audio_path}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
    
    def validate_audio_format(self, audio_path: str) -> bool:
        """
        Valida se o formato do áudio é suportado.
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            
        Returns:
            True se o formato for suportado
        """
        try:
            # Formatos suportados pelo Whisper via Groq
            supported_formats = ['.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm']
            
            file_extension = os.path.splitext(audio_path)[1].lower()
            
            if file_extension in supported_formats:
                return True
            else:
                logger.warning(f"Formato de áudio não suportado: {file_extension}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao validar formato do áudio: {e}")
            return False
    
    def get_audio_duration_estimate(self, audio_path: str) -> Optional[float]:
        """
        Estima a duração do áudio baseado no tamanho do arquivo.
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            
        Returns:
            Duração estimada em segundos ou None
        """
        try:
            if not os.path.exists(audio_path):
                return None
            
            file_size = os.path.getsize(audio_path)
            
            # Estimativa grosseira: ~1MB por minuto para arquivos comprimidos
            estimated_duration = (file_size / (1024 * 1024)) * 60
            
            return estimated_duration
            
        except Exception as e:
            logger.error(f"Erro ao estimar duração do áudio: {e}")
            return None

# Função de compatibilidade com o código antigo
def transcribe_audio(audio_path: str) -> str:
    """Função de compatibilidade com a interface anterior."""
    handler = WhisperHandler()
    result = handler.transcribe_audio(audio_path)
    return result if result else "Não foi possível transcrever o áudio."