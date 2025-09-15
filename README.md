# Prontuário Médico Digital - Luna Princess Mendes Guimarães

Sistema web exclusivo para organizar e visualizar os exames laboratoriais e o prontuário clínico da cachorrinha "Luna Princess Mendes Guimarães". Desenvolvido em Python com foco em design responsivo e visualmente impressionante, o sistema possui uma interface pública de visualização e uma área administrativa restrita com forte integração de Inteligência Artificial.

## 🎯 Visão Geral

O sistema permite que toda a equipe médica acesse os dados da Luna de forma organizada e segura. A interface pública funciona em modo somente leitura, enquanto a área administrativa permite gerenciamento completo dos dados com processamento inteligente via IA.

## ✨ Funcionalidades da Interface Pública

### 🎨 Design e Cabeçalho
- **Foto da Paciente**: Luna Princess à esquerda com círculo claro no centro
- **Fotos dos Tutores**: Paulo Guimarães e Júlia à direita
- **Título Central**: "Prontuário: Luna" e "Deus opera milagres"
- **Tema Personalizável**: Estilo "prontuário de pediatria"

### 📊 Histórico Completo de Exames
- **Formato**: Grande tabela estilo Excel ocupando a maior parte da tela
- **Estrutura**: Linhas com nomes dos exames, colunas com datas
- **Dados**: Eritrócitos, Hemoglobina, Plaquetas, etc.

### 📈 Ferramenta de Comparativo e Gráficos
- **Seleção de Exames**: Escolher um ou mais tipos (ex: Hemoglobina, Hematócrito)
- **Seleção de Datas**: Datas específicas ou "todos os dias"
- **Geração Automática**: Gráficos interativos dos dados selecionados
- **Exportação**: Copiar gráfico (Ctrl+C) e exportar tabelas

### 📅 História da Doença Atual (HDA)
- **Timeline Interativa**: Linha do tempo horizontal (rosa) na metade superior
- **Navegação**: Setas esquerda/direita para navegar entre datas
- **Detalhes do Dia**: Narrativa médica detalhada e exames relevantes
- **Layout Dividido**: Texto narrativo à esquerda, exames à direita

### 💊 Linha do Tempo de Medicamentos
- **Visualização**: Timeline horizontal com medicamentos em retângulos coloridos
- **Navegação**: Scroll horizontal para navegar no tempo
- **Informações**: Dose, via de administração, datas de início/término
- **Observações**: P.S. com considerações sobre cada medicamento

## ⚙️ Funcionalidades da Área Administrativa (/admin)

### 🔐 Acesso e Segurança
- **Login Protegido**: admin@admin.com / admin123
- **Gestão de Usuários**: Criar novos usuários com email/senha
- **Interface Diferenciada**: Mudança de cor no cabeçalho para modo admin
- **Personalização**: Configuração de tema gráfico

### 📁 Upload e Processamento de Arquivos
- **Interface Intuitiva**: Arrastar e soltar ou botão "Inserir"
- **Múltiplos Formatos**: PDFs, áudios, vídeos, textos, fotos
- **Indicadores de Progresso**: Círculos de pizza azuis com ticks de conclusão
- **Uploads Simultâneos**: Processamento paralelo quando possível
- **Geração de Histórico**: Botão para processar todos os arquivos via IA

### 🤖 Processamento Inteligente com IA
- **Exames PDF**: Extração automática de data, laboratório, médico, nome do exame, valores
- **Criação Dinâmica**: Novos campos para exames não existentes
- **Padronização**: Conversão automática de unidades de medida
- **Prontuário Clínico**: Análise de texto/áudio/vídeo para extrair eventos e datas

### ✏️ Edição e Validação
- **Edição Visual**: Texto original em azul, modificações em vermelho
- **Reprocessamento**: IA corrige ortografia e reorganiza texto
- **Validação**: Confirmação de modificações antes de salvar
- **Log de Modificações**: Registro de quem editou e quando
- **Impressão**: Geração de PDF do prontuário completo

### 💉 Gestão de Medicamentos
- **Entrada por Áudio**: IA interpreta e registra princípio ativo
- **Validação Online**: Verificação de nomes de medicamentos
- **Tabela Organizada**: Princípio ativo, datas, doses, vias, considerações
- **Múltiplos Ciclos**: Diferentes períodos de administração com cores distintas
- **Interação IA**: Perguntas de clarificação e confirmação de inconsistências

## Estrutura do Projeto

O projeto foi organizado em uma estrutura modular para facilitar a manutenção e o desenvolvimento futuro:

```
prontuario-luna/
├── src/                # Código-fonte da aplicação
│   ├── core/           # Arquivos principais (app.py, auth.py, database.py)
│   ├── security/       # Módulos de segurança
│   ├── processing/     # Módulos de processamento de dados
│   ├── utils/          # Funções utilitárias
│   ├── components/     # Componentes Streamlit reutilizáveis
│   └── pages/          # Páginas da aplicação Streamlit
├── assets/             # Arquivos de mídia e estáticos
│   ├── images/         # Imagens e screenshots
│   ├── documents/      # Documentos de texto
│   └── generated/      # Arquivos gerados (ex: relatórios)
├── config/             # Arquivos de configuração
│   ├── .streamlit/     # Configurações do Streamlit
│   ├── pyproject.toml  # Dependências do projeto
│   └── uv.lock         # Lock file de dependências
├── tests/              # Testes automatizados
├── docs/               # Documentação do projeto
└── scripts/            # Scripts utilitários
```

## Tecnologias Utilizadas

- **Backend**: Python
- **Frontend**: Streamlit
- **Banco de Dados**: PostgreSQL
- **IA e Processamento de Dados**: OpenAI API, Pandas, NumPy
- **Visualização de Dados**: Plotly
- **Manipulação de PDF**: PyPDF2, pdfplumber

## Como Executar o Projeto

### Pré-requisitos

- Python 3.9+
- PostgreSQL
- Conta na OpenAI com chave de API

### Instalação

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/drpauloguimaraesjr/prontuario-luna.git
   cd prontuario-luna
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r config/requirements.txt
   ```

4. **Configure as variáveis de ambiente:**
   - Crie um arquivo `.env` na raiz do projeto.
   - Adicione as seguintes variáveis:
     ```
     DATABASE_URL="postgresql://user:password@host:port/database"
     OPENAI_API_KEY="sua_chave_da_openai"
     ENCRYPTION_KEY="sua_chave_de_criptografia"
     APP_ENV="development"  # ou "production"
     ```

5. **Execute a aplicação:**
   ```bash
   streamlit run src/core/app.py
   ```

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e pull requests para melhorar o projeto.

## Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.


