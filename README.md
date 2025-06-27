# 🤖 Sara Bot - Assistente Pessoal Inteligente

Sara é um bot Telegram que funciona como sua assistente pessoal, capaz de criar lembretes inteligentes, manter conversas naturais e agendar notificações para seu iPhone.

## ✨ Principais Melhorias Implementadas

### 1. 🔗 Links Clicáveis
- URLs de shortcut agora são formatadas como links clicáveis no Telegram
- Formato Markdown que permite toque direto para abrir no iPhone

### 2. 🧠 Sistema Dinâmico e Inteligente
- **Conversação Natural**: Sara mantém contexto de conversas anteriores
- **Interpretação Inteligente**: Distingue entre lembretes e perguntas gerais
- **Respostas Contextuais**: Responde perguntas sobre qualquer assunto

### 3. ⏰ Sistema de Jobs e Lembretes
- **Agendamento Automático**: Lembretes são enviados na data/hora especificada
- **Verificação Periódica**: Sistema verifica lembretes perdidos a cada 5 minutos
- **Reagendamento**: Lembretes pendentes são automaticamente reagendados na inicialização

### 4. 👥 Sistema Multi-usuário
- **Registro Automático**: Usuários são registrados automaticamente no primeiro uso
- **Isolamento de Dados**: Cada usuário tem seus próprios lembretes e conversas
- **Histórico Individual**: Cada usuário mantém seu histórico de conversa

### 5. 🎯 Prompts Refinados
- **Extração Inteligente**: Melhor identificação de lembretes vs conversas
- **Geração de URLs**: Prompts específicos para criação de shortcuts iOS
- **Contexto de Conversa**: Prompts que mantêm contexto das conversas

## 🚀 Como Executar

### Pré-requisitos
```bash
# Instalar dependências
pip install -r requirements.txt
```

### Configuração
1. Crie um arquivo `.env` na raiz do projeto:
```env
TELEGRAM_TOKEN=seu_token_do_telegram
GROQ_API_KEY=sua_chave_da_groq_api
DATABASE_URL=sqlite:///sara_bot.db
```

2. Inicialize o banco de dados:
```bash
# O banco é criado automaticamente na primeira execução
python bot.py
```

### Execução
```bash
python bot.py
```

## 📋 Comandos Disponíveis

- `/start` - Inicializa o bot e registra o usuário
- `/ajuda` ou `/help` - Mostra informações de ajuda
- `/lembretes` - Lista todos os lembretes do usuário
- `/status` - Mostra estatísticas dos lembretes
- `/limpar` - Limpa o histórico de conversa

## 🎙️ Como Usar

### Criando Lembretes
1. **Por Áudio**: Grave um áudio falando o lembrete
   - "Lembrar de pagar a conta de luz sexta-feira às 9 da manhã"
   
2. **Por Texto**: Digite o lembrete
   - "Criar lembrete para reunião amanhã às 14h"

### Conversação
- Faça qualquer pergunta
- Sara mantém o contexto da conversa
- Responde sobre diversos assuntos

## 🏗️ Arquitetura do Projeto

```
├── bot.py                     # Arquivo principal do bot
├── config/
│   ├── settings.py           # Configurações centralizadas
│   └── prompts.py            # Templates de prompts do LLM
├── database/
│   ├── connection.py         # Gerenciamento de conexões
│   └── models.py             # Modelos SQLAlchemy
├── services/
│   ├── user_service.py       # Serviço de usuários
│   ├── reminder_service.py   # Serviço de lembretes
│   └── scheduler_service.py  # Serviço de agendamento
├── handlers/
│   ├── command_handlers.py   # Handlers de comandos
│   └── conversation_handlers.py # Handlers de conversa
├── whisper_handler.py        # Handler de transcrição
├── llm_handler.py           # Handler melhorado do LLM
├── utils.py                 # Utilitários diversos
└── requirements.txt         # Dependências
```

## 🔧 Principais Componentes

### Services
- **UserService**: Gerencia usuários, registro e histórico de conversas
- **ReminderService**: Cria, agenda e gerencia lembretes
- **SchedulerService**: Sistema de jobs para envio de lembretes

### Handlers
- **CommandHandlers**: Processa comandos do Telegram (/start, /lembretes, etc.)
- **ConversationHandlers**: Processa mensagens de voz e texto

### Database Models
- **User**: Dados do usuário e configurações
- **Reminder**: Lembretes com data, hora e status
- **Conversation**: Histórico de conversas
- **BotSession**: Estados de sessão do bot

## 📱 Integração com iPhone

Sara gera URLs de shortcuts iOS que:
1. São clicáveis diretamente no Telegram
2. Abrem automaticamente o app Shortcuts
3. Executam o shortcut "CriarLembrete" 
4. Passam os dados do lembrete como parâmetros

### Formato da URL
```
shortcuts://run-shortcut?name=CriarLembrete&input=text&text=data+hora+descricao+urgencia
```

## 🛠️ Melhorias Técnicas

### Código Limpo
- **Type Hints**: Todo código usa tipagem estrita
- **Error Handling**: Tratamento robusto de erros
- **Logging**: Sistema completo de logs
- **Modularização**: Código organizado em módulos específicos

### Performance
- **Connection Pooling**: Gerenciamento eficiente de conexões
- **Async/Await**: Processamento assíncrono
- **Cleanup**: Limpeza automática de arquivos temporários

### Segurança
- **Validação**: Validação de todos os inputs
- **Sanitização**: Escape de caracteres especiais
- **Isolamento**: Dados isolados por usuário

## 🚦 Status e Monitoramento

- **Logs Estruturados**: Todas as ações são logadas
- **Métricas**: Estatísticas de uso por usuário
- **Health Checks**: Verificação periódica do sistema
- **Error Tracking**: Rastreamento completo de erros

## 🔮 Próximos Passos

1. **Dashboard Web**: Interface web para monitoramento
2. **Integrações**: Conectar com calendários e outras APIs
3. **IA Avançada**: Melhorar capacidades de conversação
4. **Notificações Push**: Envio direto para dispositivos
5. **Backup/Restore**: Sistema de backup de dados

## 📄 Logs

O bot gera logs em:
- Console (stdout)
- Arquivo `sara_bot.log`

Níveis de log configuráveis por módulo.

---

**Sara Bot** - Sua assistente pessoal inteligente 🤖✨