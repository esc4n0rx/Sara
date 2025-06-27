from typing import Dict, Any

class PromptTemplates:
    """Templates de prompts refinados para o sistema."""
    
    SYSTEM_ASSISTANT = """
    Você é Sara, um assistente pessoal inteligente e proativo que ajuda usuários a organizar sua vida.
    
    SUAS CAPACIDADES:
    - Criar lembretes e tarefas
    - Responder perguntas gerais
    - Manter conversas naturais
    - Agendar notificações futuras
    
    PERSONALIDADE:
    - Amigável e prestativa
    - Usa emojis de forma moderada
    - Fala de forma natural em português brasileiro
    - É proativa em sugerir melhorias na organização
    
    IMPORTANTE:
    - Se o usuário pedir para criar um lembrete, extraia TODOS os detalhes (data, hora, descrição)
    - Se faltar informações, pergunte educadamente
    - Para perguntas gerais, responda de forma útil e completa
    - Mantenha o contexto da conversa
    """
    
    REMINDER_EXTRACTION = """
    Analise a seguinte mensagem e determine se é uma solicitação de lembrete.
    
    Se FOR um lembrete, extraia as informações no formato JSON:
    {{
        "is_reminder": true,
        "description": "descrição do lembrete",
        "date": "YYYY-MM-DD ou 'hoje' ou 'amanhã'",
        "time": "HH:MM" ou null,
        "urgency": "baixa|média|alta"
    }}
    
    Se NÃO FOR um lembrete, responda:
    {{
        "is_reminder": false,
        "response": "sua resposta natural para a pergunta/conversa"
    }}
    
    EXEMPLOS DE LEMBRETES:
    - "lembrar de pagar a conta de luz sexta-feira às 9h"
    - "me avise para ligar para o médico amanhã"
    - "criar um lembrete para a reunião às 14h"
    
    EXEMPLOS QUE NÃO SÃO LEMBRETES:
    - "como está o tempo hoje?"
    - "me explique sobre inteligência artificial"
    - "qual é a capital do Brasil?"
    
    Mensagem do usuário: "{user_message}"
    """
    
    SHORTCUT_URL_GENERATOR = """
    Gere uma URL de atalho iOS para criar um lembrete com as seguintes informações:
    
    Dados do lembrete:
    - Descrição: {description}
    - Data: {date}
    - Hora: {time}
    - Urgência: {urgency}
    
    Formato da URL:
    shortcuts://run-shortcut?name=CriarLembrete&input=text&text={encoded_params}
    
    Os parâmetros devem ser codificados em URL e separados por + no seguinte formato:
    data+hora+descrição+urgência
    
    Exemplo: sexta-feira+09:00+pagar+conta+de+luz+média
    
    Responda APENAS com a URL, sem explicações.
    """
    
    CONVERSATION_CONTEXT = """
    Contexto da conversa anterior:
    {conversation_history}
    
    Mensagem atual do usuário: {current_message}
    
    Responda de forma natural, considerando o contexto da conversa.
    Seja útil, amigável e mantenha a consistência com as mensagens anteriores.
    """

    @staticmethod
    def format_reminder_extraction(user_message: str) -> str:
        """Formata o prompt de extração de lembrete."""
        return PromptTemplates.REMINDER_EXTRACTION.format(user_message=user_message)
    
    @staticmethod
    def format_shortcut_generator(description: str, date: str, time: str, urgency: str) -> str:
        """Formata o prompt para gerar URL do shortcut."""
        return PromptTemplates.SHORTCUT_URL_GENERATOR.format(
            description=description,
            date=date,
            time=time,
            urgency=urgency
        )
    
    @staticmethod
    def format_conversation_context(conversation_history: str, current_message: str) -> str:
        """Formata o prompt com contexto de conversa."""
        return PromptTemplates.CONVERSATION_CONTEXT.format(
            conversation_history=conversation_history,
            current_message=current_message
        )