import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import base64
import io
import os
import sys
from pathlib import Path

# Importar módulos personalizados
from database import DatabaseManager
from auth import AuthManager
from components.lab_results import LabResultsComponent
from components.timeline import TimelineComponent
from components.comparisons import ComparisonComponent
from utils import format_date, convert_units
from encryption_utils import get_encryption_manager

# Configuração da página
st.set_page_config(
    page_title="Prontuário Luna",
    page_icon="🐕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# VALIDAÇÃO CRÍTICA DE SEGURANÇA NA INICIALIZAÇÃO
def validate_security_requirements():
    """Validar requisitos críticos de segurança antes de inicializar a aplicação"""
    import os
    import sys
    
    # Verificar ambiente de produção
    app_env = os.getenv('APP_ENV', '').lower()
    is_production = app_env == 'production'
    
    if is_production:
        # PRODUÇÃO: Validação rigorosa obrigatória
        
        # 1. Verificar se ENCRYPTION_KEY está configurada
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key or not encryption_key.strip():
            st.error("🚨 **FALHA CRÍTICA DE SEGURANÇA EM PRODUÇÃO**")
            st.error("ENCRYPTION_KEY é obrigatória em ambiente de produção.")
            st.error("Configure a chave de criptografia antes de inicializar o sistema.")
            sys.stderr.write("PRODUCTION ERROR: Missing ENCRYPTION_KEY\n")
            st.stop()
        
        # 2. Verificar se a chave tem formato/tamanho válido
        if len(encryption_key) < 32:
            st.error("🚨 **FALHA CRÍTICA DE SEGURANÇA EM PRODUÇÃO**")
            st.error("ENCRYPTION_KEY deve ter pelo menos 32 caracteres em produção.")
            sys.stderr.write("PRODUCTION ERROR: Invalid ENCRYPTION_KEY length\n")
            st.stop()
        
        # 3. Verificar outras variáveis críticas de produção
        required_prod_vars = ['PGHOST', 'PGDATABASE', 'PGUSER', 'PGPASSWORD']
        for var in required_prod_vars:
            if not os.getenv(var):
                st.error(f"🚨 **FALHA CRÍTICA DE SEGURANÇA EM PRODUÇÃO**")
                st.error(f"Variável de ambiente obrigatória ausente: {var}")
                sys.stderr.write(f"PRODUCTION ERROR: Missing {var}\n")
                st.stop()
        
        # Log de inicialização segura (sem expor valores)
        sys.stderr.write("[SECURITY] Production security validation passed\n")
    
    # Verificar criptografia obrigatória
    encryption_manager = get_encryption_manager()
    
    if not encryption_manager.is_encryption_available():
        st.error("🚨 **FALHA CRÍTICA DE SEGURANÇA**")
        st.error("Sistema de criptografia não está disponível.")
        st.error("A aplicação não pode operar sem criptografia adequada.")
        if is_production:
            st.error("ERRO CRÍTICO EM PRODUÇÃO: Falha na inicialização da criptografia.")
            sys.stderr.write("PRODUCTION ERROR: Encryption initialization failed\n")
        else:
            st.error("Configure ENCRYPTION_KEY no ambiente de produção.")
        st.stop()
    
    # Teste de funcionalidade da criptografia
    if not encryption_manager.test_encryption():
        st.error("🚨 **FALHA CRÍTICA DE SEGURANÇA**")
        st.error("Teste de criptografia falhou.")
        st.error("Sistema de criptografia não está funcionando corretamente.")
        if is_production:
            sys.stderr.write("PRODUCTION ERROR: Encryption test failed\n")
        st.stop()
    
    # PRODUÇÃO: Verificações adicionais de segurança
    if is_production:
        # Verificar se não há chaves temporárias sendo usadas
        try:
            # Tentar criar um novo manager para verificar se há geração automática
            from encryption_utils import EncryptionManager
            test_manager = EncryptionManager()
            if not test_manager.is_encryption_available():
                st.error("🚨 **FALHA DE SEGURANÇA EM PRODUÇÃO**")
                st.error("Detecção de chave temporária ou geração automática em produção.")
                sys.stderr.write("PRODUCTION ERROR: Temporary key detected\n")
                st.stop()
        except Exception as e:
            sys.stderr.write(f"[SECURITY] Encryption manager validation: {str(e)}\n")

# Executar validação de segurança ANTES de qualquer inicialização
validate_security_requirements()

# Log de inicialização segura
import sys
app_env = os.getenv('APP_ENV', 'development').lower()
sys.stderr.write(f"[SECURITY] Application starting in {app_env} mode\n")

# Inicializar banco de dados e autenticação
@st.cache_resource
def init_database():
    return DatabaseManager()

@st.cache_resource
def init_auth():
    return AuthManager()

db = init_database()
auth = init_auth()

# MIDDLEWARE DE SEGURANÇA - Enforçar mudança obrigatória de senha
def apply_security_middleware():
    """Aplicar middleware de segurança que bloqueia funcionalidades quando necessário"""
    
    # Se usuário está autenticado, verificar se precisa mudar senha
    if auth.is_authenticated():
        # Enforcement crítico - bloqueia TODA funcionalidade se senha precisa ser alterada
        if auth.enforce_password_change():
            # Se enforce_password_change() retorna True, significa que está bloqueando
            # Interromper execução aqui - usuário só pode alterar senha
            st.stop()
    
    return True

# Aplicar middleware de segurança ANTES de qualquer funcionalidade
apply_security_middleware()

# Verificar se é um link compartilhado
query_params = st.query_params
share_id = query_params.get('share')

if share_id:
    # Renderizar conteúdo compartilhado
    from shareable_links import render_shared_content
    render_shared_content(share_id, db)
    st.stop()  # Para execução após renderizar conteúdo compartilhado

# CSS personalizado para estilização
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        border-bottom: 2px solid #FF69B4;
        margin-bottom: 2rem;
    }
    
    .patient-info {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 2rem;
        margin: 1rem 0;
    }
    
    .patient-photo {
        border-radius: 50%;
        border: 4px solid #FF69B4;
        width: 120px;
        height: 120px;
        object-fit: cover;
    }
    
    .tutor-photo {
        border-radius: 50%;
        border: 2px solid #ccc;
        width: 60px;
        height: 60px;
        object-fit: cover;
    }
    
    .timeline-container {
        background: linear-gradient(90deg, #FF69B4 0%, #FFB6C1 100%);
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .medication-timeline {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .export-button {
        background: #FF69B4;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        cursor: pointer;
    }
    
    .nav-tabs {
        display: flex;
        gap: 1rem;
        margin-bottom: 2rem;
        justify-content: center;
    }
    
    .nav-tab {
        padding: 0.5rem 1rem;
        border: 2px solid #FF69B4;
        border-radius: 20px;
        background: white;
        color: #FF69B4;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .nav-tab.active {
        background: #FF69B4;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def render_header():
    """Renderizar o cabeçalho principal com informações do paciente"""
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 3, 2])
    
    with col2:
        st.markdown("# 🐕 Prontuário Luna")
        st.markdown("*Deus opera milagres*")
        
        # Seção de informações do paciente
        patient_info = db.get_patient_info()
        if patient_info:
            st.markdown(f"**Paciente:** {patient_info.get('name', 'Luna Princess Mendes Guimarães')}")
            
            # Exibir fotos se disponíveis
            photos = db.get_patient_photos()
            if photos:
                col_photo1, col_photo2, col_photo3 = st.columns([1, 2, 1])
                with col_photo2:
                    if photos.get('luna'):
                        st.image(photos['luna'], width=120, caption="Luna")
                
                col_tutor1, col_tutor2 = st.columns(2)
                with col_tutor1:
                    if photos.get('tutor1'):
                        st.image(photos['tutor1'], width=60, caption="Paulo")
                with col_tutor2:
                    if photos.get('tutor2'):
                        st.image(photos['tutor2'], width=60, caption="Júlia")
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    """Lógica principal da aplicação"""
    
    # Verificar se está acessando rota administrativa
    query_params = st.query_params
    if query_params.get('page') == 'admin':
        # Importar e executar página administrativa
        from pages.admin import run_admin_page
        run_admin_page(db, auth)
        return
    
    # Inicializar estado da sessão
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 'complete_history'
    
    # Renderizar cabeçalho
    render_header()
    
    # Abas de navegação
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Histórico Completo", key="tab_complete"):
            st.session_state.current_tab = 'complete_history'
    
    with col2:
        if st.button("📈 Comparativo", key="tab_comparison"):
            st.session_state.current_tab = 'comparison'
    
    with col3:
        if st.button("📅 História da Doença Atual", key="tab_timeline"):
            st.session_state.current_tab = 'timeline'
    
    with col4:
        if st.button("💊 Histórico de Medicamentos", key="tab_medications"):
            st.session_state.current_tab = 'medications'
    
    # Renderizar conteúdo baseado na aba selecionada
    if st.session_state.current_tab == 'complete_history':
        render_complete_history()
    elif st.session_state.current_tab == 'comparison':
        render_comparison_tab()
    elif st.session_state.current_tab == 'timeline':
        render_timeline_tab()
    elif st.session_state.current_tab == 'medications':
        render_medications_tab()
    
    # Link de acesso administrativo (discreto)
    st.markdown("---")
    if st.button("🔐 Acesso Administrativo", help="Clique para acessar a área administrativa"):
        st.query_params.page = 'admin'
        st.rerun()

def render_complete_history():
    """Renderizar a tabela completa do histórico de resultados laboratoriais"""
    st.header("📊 Histórico Completo de Exames")
    
    lab_component = LabResultsComponent(db)
    lab_component.render()
    
    # Opções de exportação
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Exportar Tabela (CSV)"):
            csv_data = lab_component.export_to_csv()
            if csv_data:
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"exames_luna_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    with col2:
        if st.button("📄 Exportar Prontuário (PDF)"):
            try:
                from pdf_generator import MedicalRecordPDFGenerator
                
                with st.spinner("Gerando prontuário em PDF..."):
                    pdf_generator = MedicalRecordPDFGenerator(db)
                    pdf_bytes = pdf_generator.generate_complete_medical_record()
                    
                    # Nome do arquivo com data
                    filename = f"prontuario_luna_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    
                    st.download_button(
                        label="📥 Baixar Prontuário Completo",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.success("✅ Prontuário PDF gerado com sucesso!")
                    
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")
                st.info("Verifique se todos os dados necessários estão disponíveis.")

def render_comparison_tab():
    """Renderizar a interface de comparação e gráficos"""
    st.header("📈 Comparativo de Exames")
    
    comparison_component = ComparisonComponent(db)
    comparison_component.render()

def render_timeline_tab():
    """Renderizar a linha do tempo do histórico médico"""
    st.header("📅 História da Doença Atual")
    
    timeline_component = TimelineComponent(db)
    timeline_component.render()

def render_medications_tab():
    """Renderizar a linha do tempo do histórico de medicamentos"""
    st.header("💊 Histórico de Medicamentos")
    
    medications = db.get_medication_history()
    
    if not medications:
        st.info("Nenhum medicamento registrado ainda.")
        return
    
    # Criar visualização da linha do tempo de medicamentos
    fig = go.Figure()
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
    
    for i, med in enumerate(medications):
        color = colors[i % len(colors)]
        
        fig.add_trace(go.Scatter(
            x=[med['start_date'], med['end_date']] if med['end_date'] else [med['start_date'], datetime.now()],
            y=[med['name'], med['name']],
            mode='lines+markers',
            line=dict(color=color, width=10),
            marker=dict(size=8, color=color),
            name=med['name'],
            hovertemplate=f"<b>{med['name']}</b><br>" +
                         f"Dose: {med['dose']}<br>" +
                         f"Via: {med['route']}<br>" +
                         f"Início: {med['start_date']}<br>" +
                         f"Fim: {med['end_date'] if med['end_date'] else 'Em uso'}<br>" +
                         f"Observações: {med.get('notes', 'N/A')}<extra></extra>"
        ))
    
    fig.update_layout(
        title="Linha do Tempo dos Medicamentos",
        xaxis_title="Data",
        yaxis_title="Medicamento",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela de detalhes dos medicamentos
    if medications:
        st.subheader("Detalhes dos Medicamentos")
        
        med_df = pd.DataFrame(medications)
        st.dataframe(med_df, use_container_width=True)

if __name__ == "__main__":
    main()
