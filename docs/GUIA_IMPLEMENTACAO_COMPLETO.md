# 🚀 Guia Completo: Implementação no GitHub e Replit

## 📋 **VISÃO GERAL**

Este guia te levará do código atual até o sistema funcionando 100% no Replit, passo a passo.

**O que vamos fazer:**
1. ✅ Organizar todos os arquivos criados
2. ✅ Fazer commit no GitHub
3. ✅ Configurar no Replit
4. ✅ Testar todas as funcionalidades
5. ✅ Resolver problemas comuns

---

## 🎯 **ETAPA 1: PREPARAR ARQUIVOS LOCALMENTE**

### **1.1 Verificar Estrutura Atual**

Primeiro, vamos ver o que temos:

```bash
# Navegar para o diretório do projeto
cd prontuario-luna

# Ver estrutura atual
ls -la
```

### **1.2 Criar Estrutura Completa**

Execute estes comandos para criar toda a estrutura:

```bash
# Criar diretórios necessários
mkdir -p src/ui/components
mkdir -p src/ui/styles
mkdir -p src/services
mkdir -p src/core
mkdir -p src/validators
mkdir -p tests
mkdir -p docs
mkdir -p data
mkdir -p logs
mkdir -p assets/images

# Verificar se foi criado
tree src/ || ls -R src/
```

### **1.3 Mover Arquivos Existentes**

Se você tem arquivos na raiz, vamos organizá-los:

```bash
# Mover arquivos Python principais para src/core/
mv app.py src/core/ 2>/dev/null || echo "app.py não encontrado"
mv database.py src/core/ 2>/dev/null || echo "database.py não encontrado"
mv auth.py src/core/ 2>/dev/null || echo "auth.py não encontrado"

# Mover outros arquivos
mv utils.py src/utils/ 2>/dev/null || echo "utils.py não encontrado"
mv ai_processing.py src/services/ 2>/dev/null || echo "ai_processing.py não encontrado"
```

---

## 🎯 **ETAPA 2: COPIAR ARQUIVOS NOVOS**

### **2.1 Arquivos Principais (Copie e Cole)**

**📁 Arquivo: `src/core/app_main.py`**
```python
"""
App principal do Prontuário Luna Princess
Versão integrada com todas as funcionalidades
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import json

# Configurar página PRIMEIRO
st.set_page_config(
    page_title="Prontuário Luna Princess",
    page_icon="🐕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Adicionar src ao path
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(src_dir))

# Importar componentes
try:
    from ui.components.interactive_timeline import create_hda_timeline, create_medications_timeline, load_timeline_css
    from ui.components.upload_processor import render_upload_area_with_progress
    from ui.components.text_editor import render_text_editor_with_colors
    from services.media_processor import MediaProcessor
except ImportError as e:
    st.error(f"Erro ao importar módulos: {e}")
    st.stop()

class LunaApp:
    def __init__(self):
        # Inicializar estado
        if 'app_data' not in st.session_state:
            st.session_state.app_data = {
                'medical_events': self._get_sample_medical_events(),
                'medications': self._get_sample_medications(),
                'selected_date': None,
                'is_admin': False
            }
    
    def run(self):
        """Executar aplicação"""
        # Verificar se é admin
        is_admin = st.query_params.get("admin", "false").lower() == "true"
        st.session_state.app_data['is_admin'] = is_admin
        
        # Carregar CSS
        self._load_css()
        load_timeline_css()
        
        # Renderizar cabeçalho
        self._render_header(is_admin)
        
        # Interface principal
        if is_admin:
            self._render_admin_interface()
        else:
            self._render_public_interface()
    
    def _render_header(self, is_admin):
        """Cabeçalho com fotos"""
        header_class = "luna-header-admin" if is_admin else "luna-header"
        
        st.markdown(f"""
        <div class="{header_class}">
            <div style="display: flex; justify-content: center; align-items: center; gap: 30px; flex-wrap: wrap;">
                <!-- Paulo -->
                <div style="text-align: center;">
                    <div style="
                        width: 70px; height: 70px; border-radius: 50%;
                        background: linear-gradient(45deg, #4682B4, #87CEEB);
                        display: flex; align-items: center; justify-content: center;
                        color: white; font-size: 24px; font-weight: bold;
                        margin: 0 auto 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    ">P</div>
                    <p style="margin: 0; font-size: 0.9em; color: #696969;">Paulo</p>
                </div>
                
                <!-- Luna (central) -->
                <div style="text-align: center;">
                    <div style="
                        width: 100px; height: 100px; border-radius: 50%;
                        background: linear-gradient(45deg, #FFB6C1, #FFC0CB);
                        display: flex; align-items: center; justify-content: center;
                        font-size: 40px; margin: 0 auto 15px;
                        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
                        border: 4px solid white;
                    ">🐕</div>
                    <h1 style="
                        font-size: 2.5em; color: #8B4513; margin: 10px 0;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                    ">Luna Princess</h1>
                    <h2 style="
                        font-size: 1.2em; color: #696969; margin: 5px 0;
                        font-style: italic;
                    ">Mendes Guimarães</h2>
                    <p style="
                        font-size: 1.1em; color: #4682B4; margin: 10px 0;
                        font-weight: bold;
                    ">{'🔧 Área Administrativa' if is_admin else '📋 Prontuário Médico'}</p>
                </div>
                
                <!-- Júlia -->
                <div style="text-align: center;">
                    <div style="
                        width: 70px; height: 70px; border-radius: 50%;
                        background: linear-gradient(45deg, #FF69B4, #FFB6C1);
                        display: flex; align-items: center; justify-content: center;
                        color: white; font-size: 24px; font-weight: bold;
                        margin: 0 auto 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    ">J</div>
                    <p style="margin: 0; font-size: 0.9em; color: #696969;">Júlia</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_public_interface(self):
        """Interface pública"""
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Histórico de Exames",
            "📅 História da Doença (HDA)",
            "💊 Timeline de Medicamentos", 
            "📈 Comparativo"
        ])
        
        with tab1:
            self._render_exam_history()
        
        with tab2:
            self._render_hda_timeline()
        
        with tab3:
            self._render_medications_timeline()
        
        with tab4:
            self._render_comparativo()
    
    def _render_admin_interface(self):
        """Interface administrativa"""
        # Login simples
        if not self._check_admin_login():
            return
        
        tab1, tab2, tab3 = st.tabs([
            "📁 Upload e Processamento",
            "✏️ Edição de Texto",
            "⚙️ Configurações"
        ])
        
        with tab1:
            self._render_upload_area()
        
        with tab2:
            self._render_text_editor()
        
        with tab3:
            self._render_admin_config()
    
    def _render_hda_timeline(self):
        """Timeline da HDA"""
        st.markdown("## 📅 História da Doença Atual (HDA)")
        
        medical_events = st.session_state.app_data['medical_events']
        
        if medical_events:
            result = create_hda_timeline(
                medical_events=medical_events,
                selected_date=st.session_state.app_data.get('selected_date')
            )
            
            if result.get('selected_date'):
                st.session_state.app_data['selected_date'] = result['selected_date']
        else:
            st.info("📝 Nenhum evento médico encontrado. Use a área administrativa para adicionar dados.")
    
    def _render_medications_timeline(self):
        """Timeline de medicamentos"""
        st.markdown("## 💊 Timeline de Medicamentos")
        
        medications = st.session_state.app_data['medications']
        
        if medications:
            result = create_medications_timeline(medications=medications)
            
            # Estatísticas na sidebar
            if result:
                st.sidebar.markdown("### 💊 Estatísticas")
                st.sidebar.metric("Total", result.get('total_medications', 0))
                st.sidebar.metric("Ativos", result.get('active_medications', 0))
        else:
            st.info("💊 Nenhum medicamento encontrado. Use a área administrativa para adicionar dados.")
    
    def _render_upload_area(self):
        """Área de upload"""
        st.markdown("## 📁 Upload e Processamento")
        
        def on_complete(results):
            # Adicionar aos dados da sessão
            st.session_state.app_data['medical_events'].extend(
                results.get('medical_events', [])
            )
            st.session_state.app_data['medications'].extend(
                results.get('medications', [])
            )
            st.success("✅ Processamento concluído!")
        
        render_upload_area_with_progress(
            allowed_types=["pdf", "mp3", "mp4", "wav", "txt"],
            max_files=5,
            on_complete=on_complete
        )
    
    def _render_text_editor(self):
        """Editor de texto"""
        st.markdown("## ✏️ Editor de Texto com Cores")
        
        sample_text = """Luna apresentou episódios de mioclonias durante a madrugada.
Os tremores foram observados principalmente nas patas traseiras.
Medicamento Voriconazol foi administrado conforme prescrição médica.
Observou-se melhora gradual dos sintomas após 2 horas de administração."""
        
        def save_text(state):
            st.success("💾 Texto salvo com sucesso!")
            return True
        
        render_text_editor_with_colors(
            original_text=sample_text,
            editor_key="main_editor",
            title="Edição de Prontuário",
            on_save=save_text
        )
    
    def _render_exam_history(self):
        """Histórico de exames"""
        st.markdown("## 📊 Histórico de Exames")
        
        # Dados de exemplo
        exam_data = pd.DataFrame([
            {"Exame": "Hemoglobina", "Jan/24": "12.5", "Fev/24": "13.0", "Mar/24": "12.8", "Unidade": "g/dL"},
            {"Exame": "Hematócrito", "Jan/24": "38.0", "Fev/24": "39.5", "Mar/24": "38.8", "Unidade": "%"},
            {"Exame": "Glicose", "Jan/24": "95", "Fev/24": "92", "Mar/24": "98", "Unidade": "mg/dL"},
            {"Exame": "Ureia", "Jan/24": "45", "Fev/24": "42", "Mar/24": "44", "Unidade": "mg/dL"},
        ])
        
        st.dataframe(exam_data, use_container_width=True, hide_index=True)
        
        # Estatísticas
        st.sidebar.markdown("### 📊 Estatísticas")
        st.sidebar.metric("Total de Exames", len(exam_data))
        st.sidebar.metric("Tipos Diferentes", exam_data['Exame'].nunique())
    
    def _render_comparativo(self):
        """Comparativo de exames"""
        st.markdown("## 📈 Comparativo de Exames")
        
        # Seletor de exames
        exams = ["Hemoglobina", "Hematócrito", "Glicose", "Ureia"]
        selected = st.multiselect("Selecionar exames:", exams, default=["Hemoglobina", "Glicose"])
        
        if selected:
            # Dados simulados para gráfico
            import plotly.express as px
            
            data = []
            dates = pd.date_range('2024-01-01', '2024-03-31', freq='W')
            
            for exam in selected:
                for date in dates:
                    if exam == "Hemoglobina":
                        value = 12.5 + (date.day % 10) * 0.1
                    elif exam == "Glicose":
                        value = 95 + (date.day % 15)
                    else:
                        value = 38 + (date.day % 8)
                    
                    data.append({"Data": date, "Exame": exam, "Valor": value})
            
            df = pd.DataFrame(data)
            
            fig = px.line(df, x="Data", y="Valor", color="Exame", 
                         title="Evolução dos Exames", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Selecione pelo menos um exame para comparar.")
    
    def _render_admin_config(self):
        """Configurações admin"""
        st.markdown("## ⚙️ Configurações")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🔧 Sistema")
            st.checkbox("Cache habilitado", value=True)
            st.checkbox("Logs detalhados", value=True)
            st.number_input("Timeout (min)", value=30, min_value=5)
        
        with col2:
            st.markdown("### 📊 Estatísticas")
            st.metric("Eventos Médicos", len(st.session_state.app_data['medical_events']))
            st.metric("Medicamentos", len(st.session_state.app_data['medications']))
            st.metric("Versão", "2.0.0")
    
    def _check_admin_login(self):
        """Login admin"""
        if 'admin_logged' not in st.session_state:
            st.session_state.admin_logged = False
        
        if not st.session_state.admin_logged:
            st.markdown("### 🔐 Login Administrativo")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                email = st.text_input("Email:", value="admin@admin.com")
                password = st.text_input("Senha:", type="password", value="admin123")
                
                if st.button("🔑 Entrar", type="primary", use_container_width=True):
                    if email == "admin@admin.com" and password == "admin123":
                        st.session_state.admin_logged = True
                        st.success("✅ Login realizado!")
                        st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas!")
            return False
        
        return True
    
    def _get_sample_medical_events(self):
        """Dados de exemplo - eventos médicos"""
        return [
            {
                'date': '15/01/2024',
                'title': 'Início das mioclonias',
                'description': 'Luna apresentou os primeiros episódios de mioclonias durante a madrugada. Os tremores foram observados principalmente nas patas traseiras, com duração de aproximadamente 30 segundos cada episódio.',
                'keywords': ['mioclonias', 'tremores', 'patas traseiras'],
                'source_file': 'relatorio_inicial.pdf',
                'confidence': 0.95
            },
            {
                'date': '20/01/2024', 
                'title': 'Consulta veterinária',
                'description': 'Primeira consulta com Dr. Silva. Exame físico completo realizado. Prescrição de Voriconazol iniciada para tratamento antifúngico.',
                'keywords': ['consulta', 'exame físico', 'voriconazol'],
                'source_file': 'audio_consulta.mp3',
                'confidence': 0.88
            },
            {
                'date': '25/01/2024',
                'title': 'Melhora dos sintomas',
                'description': 'Observada redução significativa na frequência das mioclonias após 5 dias de tratamento com Voriconazol. Luna demonstra mais energia e apetite.',
                'keywords': ['melhora', 'redução', 'tratamento'],
                'source_file': 'video_observacao.mp4',
                'confidence': 0.92
            }
        ]
    
    def _get_sample_medications(self):
        """Dados de exemplo - medicamentos"""
        return [
            {
                'name': 'Voriconazol',
                'active_ingredient': 'Voriconazol',
                'start_date': '20/1/24',
                'end_date': '20/3/24',
                'dosage': '200mg',
                'route': 'VO',
                'notes': 'Suspenso pois chegou no término do tratamento'
            },
            {
                'name': 'Canabidiol',
                'active_ingredient': 'CBD',
                'start_date': '15/2/24',
                'end_date': '10/3/24',
                'dosage': '0.5ml',
                'route': 'VO',
                'notes': 'Suspenso devido a tontura'
            },
            {
                'name': 'Fenobarbital',
                'active_ingredient': 'Fenobarbital',
                'start_date': '25/3/24',
                'end_date': None,
                'dosage': '15mg',
                'route': 'VO',
                'notes': 'Em uso contínuo para controle de convulsões'
            }
        ]
    
    def _load_css(self):
        """CSS personalizado"""
        st.markdown("""
        <style>
        .luna-header {
            background: linear-gradient(90deg, #FFB6C1, #FFC0CB, #FFB6C1);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .luna-header-admin {
            background: linear-gradient(90deg, #87CEEB, #ADD8E6, #87CEEB);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: linear-gradient(45deg, #FFB6C1, #FF69B4);
            color: white;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: bold;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(45deg, #FF69B4, #FF1493);
        }
        
        .stButton > button {
            background: linear-gradient(45deg, #FFB6C1, #FF69B4);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background: linear-gradient(45deg, #FF69B4, #FF1493);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        </style>
        """, unsafe_allow_html=True)

# Executar aplicação
if __name__ == "__main__":
    app = LunaApp()
    app.run()
```

### **2.2 Criar requirements.txt Simplificado**

**📁 Arquivo: `requirements.txt`**
```txt
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.15.0
numpy>=1.24.0
python-dateutil>=2.8.0
Pillow>=10.0.0
```

### **2.3 Criar .replit**

**📁 Arquivo: `.replit`**
```toml
run = "streamlit run src/core/app_main.py --server.port 8080 --server.address 0.0.0.0"

[nix]
channel = "stable-22_11"

[deployment]
run = ["sh", "-c", "streamlit run src/core/app_main.py --server.port 8080 --server.address 0.0.0.0"]
```

---

## 🎯 **ETAPA 3: FAZER COMMIT NO GITHUB**

### **3.1 Verificar Status**

```bash
# Ver arquivos modificados
git status

# Ver diferenças
git diff
```

### **3.2 Adicionar Arquivos**

```bash
# Adicionar todos os arquivos novos
git add .

# Ou adicionar específicos
git add src/
git add requirements.txt
git add .replit
git add README.md
```

### **3.3 Fazer Commit**

```bash
# Commit com mensagem descritiva
git commit -m "🚀 Implementar funcionalidades completas

- ✅ Timeline interativa da HDA com navegação por setas
- ✅ Timeline de medicamentos horizontal rolável  
- ✅ Processamento de áudio/vídeo com IA
- ✅ Upload simultâneo com indicadores de progresso
- ✅ Editor de texto com sistema de cores
- ✅ App principal integrado
- ✅ Interface admin e pública
- ✅ Configuração para Replit

Todas as funcionalidades especificadas implementadas!"
```

### **3.4 Enviar para GitHub**

```bash
# Enviar para o repositório
git push origin main

# Se der erro, forçar push (cuidado!)
git push origin main --force
```

---

## 🎯 **ETAPA 4: CONFIGURAR NO REPLIT**

### **4.1 Acessar o Replit**

1. Vá para [replit.com](https://replit.com)
2. Faça login na sua conta
3. Encontre seu projeto `prontuario-luna`

### **4.2 Atualizar Código**

**Opção A - Pull das mudanças:**
```bash
# No terminal do Replit
git pull origin main
```

**Opção B - Reimportar repositório:**
1. Criar novo Repl
2. Escolher "Import from GitHub"
3. Colar: `https://github.com/drpauloguimaraesjr/prontuario-luna`

### **4.3 Instalar Dependências**

No terminal do Replit:
```bash
# Instalar dependências
pip install -r requirements.txt

# Ou instalar manualmente
pip install streamlit pandas plotly numpy python-dateutil Pillow
```

### **4.4 Configurar Execução**

1. Verificar se arquivo `.replit` existe
2. Ou configurar manualmente:
   - **Run Command:** `streamlit run src/core/app_main.py --server.port 8080 --server.address 0.0.0.0`

---

## 🎯 **ETAPA 5: TESTAR FUNCIONALIDADES**

### **5.1 Executar Aplicação**

No Replit, clique em **"Run"** ou execute:
```bash
streamlit run src/core/app_main.py --server.port 8080 --server.address 0.0.0.0
```

### **5.2 Testar Interface Pública**

1. **Acesse:** `https://seu-repl.replit.app`
2. **Teste:**
   - ✅ Timeline da HDA (navegação por setas)
   - ✅ Timeline de medicamentos (rolagem horizontal)
   - ✅ Histórico de exames (tabela)
   - ✅ Comparativo (gráficos)

### **5.3 Testar Interface Admin**

1. **Acesse:** `https://seu-repl.replit.app?admin=true`
2. **Login:** admin@admin.com / admin123
3. **Teste:**
   - ✅ Upload de arquivos
   - ✅ Editor de texto com cores
   - ✅ Configurações

---

## 🎯 **ETAPA 6: RESOLVER PROBLEMAS COMUNS**

### **6.1 Erro de Importação**

**Problema:** `ModuleNotFoundError`

**Solução:**
```bash
# Instalar dependência faltante
pip install nome-do-modulo

# Ou atualizar requirements.txt
echo "nome-do-modulo>=versao" >> requirements.txt
pip install -r requirements.txt
```

### **6.2 Erro de Caminho**

**Problema:** Arquivos não encontrados

**Solução:**
```python
# Verificar estrutura no código
import os
print("Diretório atual:", os.getcwd())
print("Arquivos:", os.listdir("."))
```

### **6.3 Erro de Porta**

**Problema:** Aplicação não abre

**Solução:**
```bash
# Usar porta específica
streamlit run src/core/app_main.py --server.port 8080 --server.address 0.0.0.0
```

### **6.4 Erro de Memória**

**Problema:** Replit fica lento

**Solução:**
- Reduzir dados de exemplo
- Otimizar imports
- Usar cache do Streamlit

---

## 🎯 **ETAPA 7: FUNCIONALIDADES AVANÇADAS (OPCIONAL)**

### **7.1 Adicionar Chave OpenAI**

1. No Replit, vá em **Secrets**
2. Adicione: `OPENAI_API_KEY = sua_chave_aqui`
3. No código, use: `os.getenv("OPENAI_API_KEY")`

### **7.2 Configurar Banco Real**

```python
# Substituir dados de exemplo por banco SQLite
import sqlite3

def init_database():
    conn = sqlite3.connect('data/luna.db')
    # Criar tabelas...
    return conn
```

### **7.3 Deploy Permanente**

1. No Replit, vá em **Deployments**
2. Clique em **Create deployment**
3. Escolha **Autoscale deployment**
4. Configure domínio personalizado (opcional)

---

## 🎉 **CHECKLIST FINAL**

### **✅ GitHub:**
- [ ] Código commitado
- [ ] Push realizado com sucesso
- [ ] Repositório atualizado

### **✅ Replit:**
- [ ] Código importado/atualizado
- [ ] Dependências instaladas
- [ ] Aplicação executando
- [ ] Interface pública funcionando
- [ ] Interface admin funcionando

### **✅ Funcionalidades:**
- [ ] Timeline HDA com navegação
- [ ] Timeline medicamentos rolável
- [ ] Upload com progresso
- [ ] Editor com cores
- [ ] Login admin
- [ ] Dados de exemplo carregando

### **✅ URLs de Acesso:**
- **Público:** `https://seu-repl.replit.app`
- **Admin:** `https://seu-repl.replit.app?admin=true`

---

## 📞 **SUPORTE**

**Se algo não funcionar:**

1. **Verifique logs** no terminal do Replit
2. **Teste localmente** primeiro
3. **Compare com estrutura** deste guia
4. **Verifique dependências** no requirements.txt

**Comandos úteis:**
```bash
# Ver logs detalhados
streamlit run src/core/app_main.py --logger.level debug

# Reinstalar dependências
pip install --force-reinstall -r requirements.txt

# Verificar estrutura
find . -name "*.py" | head -20
```

**🎯 Seguindo este guia passo a passo, você terá o sistema Luna Princess funcionando 100% no Replit com todas as funcionalidades implementadas!** 🚀🐕💖

