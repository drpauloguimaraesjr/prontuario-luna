# Configuração no Replit - Prontuário Luna

## 🚀 Passos para Configurar no Replit

### 1. Importar o Repositório
1. Acesse [Replit.com](https://replit.com)
2. Clique em "Create Repl"
3. Selecione "Import from GitHub"
4. Cole a URL: `https://github.com/drpauloguimaraesjr/prontuario-luna.git`
5. Clique em "Import from GitHub"

### 2. Configurar Dependências
1. No terminal do Replit, execute:
```bash
pip install -r config/requirements.txt
```

### 3. Configurar Variáveis de Ambiente
1. Vá em "Secrets" (ícone de cadeado) no painel lateral
2. Adicione as seguintes variáveis:

```
OPENAI_API_KEY = "sua_chave_da_openai_aqui"
DATABASE_URL = "postgresql://user:pass@host:port/db"
ENCRYPTION_KEY = "sua_chave_de_criptografia_32_caracteres"
APP_ENV = "development"
```

### 4. Configurar Arquivo .replit
1. Substitua o conteúdo do arquivo `.replit` por:
```
run = "streamlit run src/core/app_new.py --server.port 8080 --server.address 0.0.0.0"

[nix]
channel = "stable-23.05"

[deployment]
run = ["sh", "-c", "streamlit run src/core/app_new.py --server.port 8080 --server.address 0.0.0.0"]

[[ports]]
localPort = 8080
externalPort = 80

[env]
PYTHONPATH = "/home/runner/prontuario-luna/src"
```

### 5. Executar o Projeto
1. Clique no botão "Run" verde
2. O Streamlit será iniciado na porta 8080
3. Acesse a URL fornecida pelo Replit

## 🔧 Resolução de Problemas Comuns

### Erro de Módulo Não Encontrado
```bash
# Execute no terminal:
pip install --upgrade pip
pip install -r config/requirements.txt
```

### Erro de Porta
- Certifique-se de que o arquivo `.replit` está configurado corretamente
- Use sempre `--server.address 0.0.0.0` para permitir acesso externo

### Erro de Importação de Módulos
```bash
# Adicione o diretório src ao PYTHONPATH:
export PYTHONPATH="/home/runner/prontuario-luna/src:$PYTHONPATH"
```

### Problemas com IA/OpenAI
1. Verifique se a chave da API está correta em Secrets
2. Teste a conexão:
```python
import openai
openai.api_key = "sua_chave"
# Teste básico
```

## 📱 Acessando as Funcionalidades

### Interface Pública
- **URL Principal**: `https://seu-repl.replit.app`
- **Histórico de Exames**: Página inicial
- **Comparativo**: Botão "📈 Comparativo"
- **História da Doença**: Botão "📅 História da Doença"
- **Medicamentos**: Botão "💊 Medicamentos"

### Área Administrativa
- **URL Admin**: `https://seu-repl.replit.app?admin=true`
- **Login**: admin@admin.com / admin123
- **Upload de Arquivos**: Aba "📁 Upload"
- **Processamento IA**: Aba "🤖 Processamento IA"
- **Edição**: Aba "✏️ Edição"
- **Usuários**: Aba "👥 Usuários"

## 🎨 Personalização do Tema

O sistema já vem com tema "pediatria" configurado:
- **Cores principais**: Rosa (#FFB6C1), Rosa claro (#FFC0CB)
- **Cores admin**: Azul claro (#87CEEB), Azul (#ADD8E6)
- **Fontes**: Títulos em marrom (#8B4513), subtítulos em cinza (#696969)

## 📊 Dados de Exemplo

O sistema inclui dados de exemplo para demonstração:
- **Exames**: Hemoglobina, Hematócrito, Eritrócitos, etc.
- **Datas**: Janeiro a Dezembro 2024
- **Medicamentos**: Voriconazol, Canabidiol
- **Eventos**: Timeline com episódios de mioclonias

## 🔄 Atualizações Futuras

Para atualizar o código:
1. Faça as alterações no GitHub
2. No Replit, vá em "Version Control"
3. Clique em "Pull" para sincronizar

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs no console do Replit
2. Confirme se todas as dependências estão instaladas
3. Verifique se as variáveis de ambiente estão configuradas
4. Teste a conectividade com APIs externas

