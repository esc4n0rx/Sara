import os
from groq import Groq

def interpret_command(text: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    system_prompt = (
        "Você é Sara, um assistente pessoal que ajuda o usuário a organizar tarefas e lembretes. "
        "Receba comandos em português e extraia a ação, data, horário e descrição. "
        "Responda apenas com uma URL de atalho iOS no formato 'shortcuts://run-shortcut?name=...'"
        "Use o nome do atalho definido como variável e envie parâmetros no texto."
        "Exemplo: 'shortcuts://run-shortcut?name=CriarLembrete&input=text&text=sexta-feira+09:00+pagar+a+conta+de+luz'"
    )

    messages = [
        { "role": "system", "content": system_prompt },
        { "role": "user", "content": text }
    ]

    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages,
        temperature=0.7,
        max_completion_tokens=256,
        top_p=1,
        stream=False
    )

    return completion.choices[0].message.content.strip()
