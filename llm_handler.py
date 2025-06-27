import os
import json
import logging
import urllib.parse
from typing import Dict, Any, Optional, List
from groq import Groq
from config.settings import settings
from config.prompts import PromptTemplates

logger = logging.getLogger(__name__)

class LLMHandler:
    """Handler melhorado para interação com LLM usando prompts refinados."""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
    
    def interpret_message(self, text: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Interpreta uma mensagem do usuário e determina se é um lembrete ou conversa geral.
        
        Returns:
            Dict com estrutura:
            {
                "is_reminder": bool,
                "response": str (se não for lembrete),
                "description": str (se for lembrete),
                "date": str,
                "time": str,
                "urgency": str
            }
        """
        try:
            # Se há histórico de conversa, usa contexto
            if conversation_history:
                formatted_history = self._format_conversation_history(conversation_history)
                prompt = PromptTemplates.format_conversation_context(formatted_history, text)
                system_prompt = PromptTemplates.SYSTEM_ASSISTANT
            else:
                # Sem histórico, usa prompt de extração de lembrete
                prompt = PromptTemplates.format_reminder_extraction(text)
                system_prompt = "Você é um assistente que analisa mensagens para identificar lembretes."
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            completion = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.3,
                max_completion_tokens=512,
                top_p=0.9,
                stream=False
            )
            
            response_text = completion.choices[0].message.content.strip()
            
            # Tenta fazer parse do JSON
            try:
                result = json.loads(response_text)
                return self._validate_response(result)
            except json.JSONDecodeError:
                # Se não conseguir fazer parse, trata como resposta geral
                logger.warning(f"Resposta do LLM não é JSON válido: {response_text}")
                return {
                    "is_reminder": False,
                    "response": response_text
                }
                
        except Exception as e:
            logger.error(f"Erro ao interpretar mensagem: {e}")
            return {
                "is_reminder": False,
                "response": "Desculpe, tive um problema para processar sua mensagem. Pode tentar novamente?"
            }
    
    def generate_shortcut_url(self, description: str, date: str, time: str, urgency: str) -> str:
        """Gera URL do shortcut iOS para criar lembrete."""
        try:
            prompt = PromptTemplates.format_shortcut_generator(description, date, time, urgency)
            
            messages = [
                {
                    "role": "system", 
                    "content": "Você gera URLs de atalhos iOS. Responda apenas com a URL, sem explicações."
                },
                {"role": "user", "content": prompt}
            ]
            
            completion = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.1,
                max_completion_tokens=256,
                top_p=0.9,
                stream=False
            )
            
            url = completion.choices[0].message.content.strip()
            
            # Fallback manual se o LLM não gerar corretamente
            if not url.startswith("shortcuts://"):
                url = self._generate_shortcut_url_fallback(description, date, time, urgency)
            
            return url
            
        except Exception as e:
            logger.error(f"Erro ao gerar URL do shortcut: {e}")
            return self._generate_shortcut_url_fallback(description, date, time, urgency)
    
    def _generate_shortcut_url_fallback(self, description: str, date: str, time: str, urgency: str) -> str:
        """Gera URL do shortcut como fallback se o LLM falhar."""
        try:
            # Combina os parâmetros
            params = f"{date}+{time}+{description}+{urgency}"
            
            # Codifica para URL
            encoded_params = urllib.parse.quote_plus(params)
            
            # Monta a URL
            url = f"shortcuts://run-shortcut?name={settings.SHORTCUT_BASE_NAME}&input=text&text={encoded_params}"
            
            return url
            
        except Exception as e:
            logger.error(f"Erro no fallback da URL do shortcut: {e}")
            return f"shortcuts://run-shortcut?name={settings.SHORTCUT_BASE_NAME}"
    
    def generate_conversational_response(self, text: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Gera uma resposta conversacional natural."""
        try:
            system_prompt = PromptTemplates.SYSTEM_ASSISTANT
            
            if conversation_history:
                formatted_history = self._format_conversation_history(conversation_history)
                user_prompt = PromptTemplates.format_conversation_context(formatted_history, text)
            else:
                user_prompt = text
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            completion = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.7,
                max_completion_tokens=512,
                top_p=0.9,
                stream=False
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta conversacional: {e}")
            return "Desculpe, tive um problema para responder. Como posso ajudar?"
    
    def _format_conversation_history(self, conversations: List[Dict]) -> str:
        """Formata o histórico de conversa para o prompt."""
        try:
            formatted_lines = []
            
            for conv in reversed(conversations[-10:]):  # Últimas 10 mensagens
                role = "Usuário" if conv.get("message_type") == "user" else "Sara"
                content = conv.get("content", "")
                
                # Se for mensagem de voz, usa a transcrição
                if conv.get("is_voice") and conv.get("transcription"):
                    content = f"[Áudio] {conv.get('transcription')}"
                
                formatted_lines.append(f"{role}: {content}")
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            logger.error(f"Erro ao formatar histórico de conversa: {e}")
            return ""
    
    def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Valida e normaliza a resposta do LLM."""
        try:
            # Garante que is_reminder existe
            if "is_reminder" not in response:
                response["is_reminder"] = False
            
            # Se for lembrete, valida campos obrigatórios
            if response.get("is_reminder"):
                if "description" not in response:
                    response["description"] = "Lembrete sem descrição"
                if "date" not in response:
                    response["date"] = "hoje"
                if "time" not in response:
                    response["time"] = "09:00"
                if "urgency" not in response:
                    response["urgency"] = "média"
            
            # Se não for lembrete, garante que tem response
            if not response.get("is_reminder") and "response" not in response:
                response["response"] = "Como posso ajudar você?"
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao validar resposta: {e}")
            return {
                "is_reminder": False,
                "response": "Houve um erro ao processar sua mensagem."
            }

# Função de compatibilidade com o código antigo
def interpret_command(text: str) -> str:
    """Função de compatibilidade - gera apenas a URL do shortcut."""
    handler = LLMHandler()
    result = handler.interpret_message(text)
    
    if result.get("is_reminder"):
        return handler.generate_shortcut_url(
            result.get("description", ""),
            result.get("date", "hoje"),
            result.get("time", "09:00"),
            result.get("urgency", "média")
        )
    else:
        # Se não for lembrete, retorna uma URL padrão
        return f"shortcuts://run-shortcut?name={settings.SHORTCUT_BASE_NAME}"