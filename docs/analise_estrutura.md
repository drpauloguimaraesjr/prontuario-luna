# Análise da Estrutura Atual - Prontuário Luna

## Visão Geral do Projeto
- **Nome**: Sistema de Prontuário Médico Digital para Luna Princess
- **Tipo**: Aplicação web Streamlit para gestão de prontuário veterinário
- **Tecnologias**: Python, Streamlit, PostgreSQL, OpenAI API
- **Finalidade**: Gerenciar exames laboratoriais, histórico médico e dados de uma cachorra

## Estrutura Atual de Arquivos

### Arquivos na Raiz (Problemas Identificados)
```
prontuario-luna/
├── app.py (15K) - Arquivo principal da aplicação
├── ai_processing.py (15K) - Processamento com IA
├── auth.py (63K) - Sistema de autenticação
├── database.py (71K) - Gerenciamento de banco de dados
├── encryption_utils.py (10K) - Utilitários de criptografia
├── pdf_generator.py (16K) - Geração de PDFs
├── security_migration.py (19K) - Migração de segurança
├── security_setup.py (12K) - Configuração de segurança
├── shareable_links.py (22K) - Links compartilháveis
├── test_security_integration.py (24K) - Testes de segurança
├── utils.py (11K) - Utilitários gerais
├── pyproject.toml (526B) - Configuração do projeto
├── uv.lock (246K) - Lock file de dependências
├── .replit (1.1K) - Configuração Replit
└── replit.md (4.5K) - Documentação do Replit
```

### Pastas Organizadas (Pontos Positivos)
```
├── .streamlit/
│   └── config.toml - Configuração do Streamlit
├── components/
│   ├── comparisons.py (30K) - Componente de comparações
│   ├── lab_results.py (11K) - Componente de resultados laboratoriais
│   └── timeline.py (13K) - Componente de timeline
├── pages/
│   ├── admin.py (76K) - Página administrativa
│   └── admin_dashboard_helpers.py (16K) - Helpers do dashboard
└── attached_assets/
    ├── generated_images/
    │   └── Lab_report_sample_PDF_7e9a30a2.png (386K)
    ├── Captura de Tela 2025-09-14 às 13.00.19_1757865624814.png (298K)
    ├── Pasted--Speaker-1-00-00-01-Eu-preciso-fazer-um-sistema-que-organize-todos-os-exames-laboratoriais-da-minha--1757749953055_1757749953055.txt (40K)
    └── Pasted-Vis-o-Geral-do-Sistema-Prontu-rio-M-dico-Digital-para-Luna-Princess-Mendes-Guimar-es-Olha-doutor--1757749901232_1757749901233.txt (12K)
```

## Problemas Identificados

### 1. Organização de Arquivos
- **Muitos arquivos na raiz**: 12 arquivos Python principais na raiz do projeto
- **Falta de estrutura modular**: Arquivos relacionados não estão agrupados
- **Mistura de responsabilidades**: Arquivos de diferentes propósitos no mesmo nível

### 2. Nomenclatura Inconsistente
- **Arquivos de assets**: Nomes muito longos e com caracteres especiais
- **Falta de padrão**: Alguns arquivos usam snake_case, outros não seguem padrão
- **Nomes descritivos demais**: Alguns nomes de arquivo são excessivamente longos

### 3. Documentação
- **Ausência de README.md**: Não há documentação principal do projeto
- **Documentação dispersa**: Informações estão apenas no replit.md
- **Falta de instruções**: Sem guia de instalação ou uso

### 4. Estrutura de Pastas
- **Falta de organização por funcionalidade**: Arquivos relacionados espalhados
- **Ausência de pastas importantes**: Sem pastas para docs, tests, config, etc.
- **Assets mal organizados**: Arquivos de mídia com nomes problemáticos

### 5. Configuração e Dependências
- **Configurações espalhadas**: Arquivos de config em diferentes locais
- **Falta de requirements.txt**: Apenas pyproject.toml e uv.lock
- **Configurações de ambiente**: Sem arquivo .env.example

## Pontos Positivos Identificados

### 1. Separação de Componentes
- Pasta `components/` bem estruturada com componentes Streamlit
- Separação clara entre componentes de UI

### 2. Páginas Organizadas
- Pasta `pages/` para páginas administrativas
- Separação entre lógica principal e helpers

### 3. Configuração Streamlit
- Pasta `.streamlit/` com configurações adequadas

### 4. Modularidade Parcial
- Alguns módulos bem definidos (auth, database, utils)
- Separação de responsabilidades em alguns arquivos

## Recomendações de Reorganização

### 1. Estrutura de Pastas Proposta
```
prontuario-luna/
├── src/
│   ├── core/
│   ├── components/
│   ├── pages/
│   ├── utils/
│   └── config/
├── assets/
├── docs/
├── tests/
├── scripts/
└── config/
```

### 2. Agrupamento por Funcionalidade
- **Core**: Arquivos principais (app, database, auth)
- **Security**: Arquivos de segurança agrupados
- **Processing**: Arquivos de processamento (AI, PDF)
- **Utils**: Utilitários e helpers

### 3. Melhorias de Nomenclatura
- Padronizar nomes de arquivos
- Renomear assets com nomes mais limpos
- Usar convenções consistentes

### 4. Documentação
- Criar README.md completo
- Adicionar documentação técnica
- Incluir guias de instalação e uso

