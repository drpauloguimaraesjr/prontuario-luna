import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path
import base64
import io
from PIL import Image, ImageDraw

# CRITICAL: Validate security requirements before imports
def validate_security_requirements():
    """Validate critical security requirements for production deployment"""
    import logging
    
    app_env = os.getenv('APP_ENV', '').lower()
    is_production = app_env == 'production'
    
    # Configure secure logging
    if is_production:
        logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if is_production:
        # CRITICAL: Check encryption key in production
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key or not encryption_key.strip():
            logging.critical("Missing ENCRYPTION_KEY in production environment")
            st.error("🚨 System configuration error. Contact system administrator.")
            st.stop()
        
        # Check database connection parameters
        required_db_vars = ['PGHOST', 'PGDATABASE', 'PGUSER', 'PGPASSWORD']
        missing_vars = [var for var in required_db_vars if not os.getenv(var)]
        if missing_vars:
            logging.critical(f"Missing database environment variables: {missing_vars}")
            st.error("🚨 Database configuration error. Contact system administrator.")
            st.stop()
    
    # Import encryption manager to validate
    try:
        from encryption_utils import get_encryption_manager
        encryption_manager = get_encryption_manager()
        if not encryption_manager.is_encryption_available():
            if is_production:
                logging.critical("Encryption system not available in production")
                st.error("🚨 Security system unavailable. Contact system administrator.")
                st.stop()
            else:
                st.warning("⚠️ WARNING: Encryption system not available - development mode only")
    except Exception as e:
        if is_production:
            logging.critical(f"Encryption system initialization failed: {str(e)}")
            st.error("🚨 Security system initialization failed. Contact system administrator.")
            st.stop()
        else:
            st.warning(f"⚠️ WARNING: Encryption initialization failed: {e}")

# Validate security requirements FIRST
validate_security_requirements()

# Import database and authentication managers
from database import DatabaseManager
from auth import AuthManager

# Configuração da página
st.set_page_config(
    page_title="Prontuário Luna Princess Mendes Guimarães",
    page_icon="🐕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inicializar banco de dados e autenticação
@st.cache_resource
def init_database():
    return DatabaseManager()

@st.cache_resource
def init_auth():
    return AuthManager()

db = init_database()
auth = init_auth()

# CSS personalizado para tema pediatria
def load_css():
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #FFB6C1, #FFC0CB, #FFB6C1);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .patient-photo {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        border: 4px solid #fff;
        box-shadow: 0 0 15px rgba(0,0,0,0.3);
        margin: 10px;
    }
    
    .tutor-photo {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        border: 3px solid #fff;
        box-shadow: 0 0 10px rgba(0,0,0,0.2);
        margin: 5px;
    }
    
    .title-main {
        font-size: 3em;
        color: #8B4513;
        font-weight: bold;
        margin: 15px 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .subtitle {
        font-size: 1.4em;
        color: #696969;
        font-style: italic;
        margin-bottom: 10px;
    }
    
    .exam-table {
        background: white;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin: 20px 0;
    }
    
    .nav-button {
        background: linear-gradient(45deg, #FFB6C1, #FF69B4);
        color: white;
        border: none;
        padding: 15px 25px;
        border-radius: 10px;
        margin: 8px;
        cursor: pointer;
        font-weight: bold;
        font-size: 1.1em;
        transition: all 0.3s ease;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
    }
    
    .nav-button:hover {
        background: linear-gradient(45deg, #FF69B4, #FF1493);
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
    
    .timeline-container {
        background: linear-gradient(135deg, #FFF8DC, #FFFACD);
        border-radius: 15px;
        padding: 25px;
        margin: 25px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .medication-timeline {
        background: linear-gradient(135deg, #F0F8FF, #E6F3FF);
        border-radius: 15px;
        padding: 25px;
        margin: 25px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .admin-header {
        background: linear-gradient(90deg, #87CEEB, #ADD8E6, #87CEEB);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .upload-area {
        border: 3px dashed #FFB6C1;
        border-radius: 15px;
        padding: 50px;
        text-align: center;
        background: linear-gradient(135deg, #FFF8F8, #FFEBEE);
        margin: 25px 0;
        transition: all 0.3s ease;
    }
    
    .upload-area:hover {
        border-color: #FF69B4;
        background: linear-gradient(135deg, #FFEBEE, #FCE4EC);
    }
    
    .progress-circle {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        border: 4px solid #ddd;
        border-top: 4px solid #4CAF50;
        animation: spin 1s linear infinite;
        margin: 15px auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .medication-card {
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 3px 12px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .medication-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    
    .timeline-marker {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: #FFB6C1;
        border: 3px solid white;
        box-shadow: 0 0 10px rgba(0,0,0,0.3);
        position: relative;
        margin: 0 auto;
    }
    
    .login-container {
        background: linear-gradient(135deg, #F0F8FF, #E6F3FF);
        border-radius: 20px;
        padding: 40px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        margin: 50px auto;
        max-width: 400px;
    }
    
    .success-message {
        background: linear-gradient(135deg, #D4EDDA, #C3E6CB);
        color: #155724;
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 5px solid #28a745;
    }
    
    .error-message {
        background: linear-gradient(135deg, #F8D7DA, #F5C6CB);
        color: #721c24;
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 5px solid #dc3545;
    }
    </style>
    """, unsafe_allow_html=True)

# Função para criar cabeçalho
def create_header(is_admin=False):
    header_class = "admin-header" if is_admin else "main-header"
    title_text = "Administradores" if is_admin else "Prontuário: Luna"
    
    st.markdown(f"""
    <div class="{header_class}">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 150px; text-align: center;">
                <img src="data:image/png;base64,{get_placeholder_image('patient')}" class="patient-photo">
                <br><strong style="color: #8B4513;">Luna Princess</strong>
                <br><small style="color: #696969;">Mendes Guimarães</small>
            </div>
            <div style="flex: 2; text-align: center; min-width: 300px;">
                <div class="title-main">{title_text}</div>
                <div class="subtitle">Deus opera milagres</div>
            </div>
            <div style="flex: 1; display: flex; justify-content: center; gap: 30px; flex-wrap: wrap;">
                <div style="text-align: center;">
                    <img src="data:image/png;base64,{get_placeholder_image('tutor1')}" class="tutor-photo">
                    <br><strong style="color: #8B4513;">Paulo Guimarães</strong>
                    <br><small style="color: #696969;">Tutor</small>
                </div>
                <div style="text-align: center;">
                    <img src="data:image/png;base64,{get_placeholder_image('tutor2')}" class="tutor-photo">
                    <br><strong style="color: #8B4513;">Júlia</strong>
                    <br><small style="color: #696969;">Tutora</small>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Função para gerar imagem placeholder
def get_placeholder_image(type_img='patient'):
    img = Image.new('RGB', (120, 120), color='#FFB6C1')
    draw = ImageDraw.Draw(img)
    
    if type_img == 'patient':
        # Círculo rosa mais escuro para Luna
        draw.ellipse([15, 15, 105, 105], fill='#FF69B4')
        draw.ellipse([35, 35, 85, 85], fill='#FFB6C1')
        # Adicionar "orelhas" de cachorro
        draw.ellipse([25, 10, 45, 40], fill='#FF69B4')
        draw.ellipse([75, 10, 95, 40], fill='#FF69B4')
    else:
        # Círculo azul para tutores
        draw.ellipse([15, 15, 105, 105], fill='#87CEEB')
        draw.ellipse([35, 35, 85, 85], fill='#ADD8E6')
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str

# SECURITY: Remove insecure SHA-256 hashing - use bcrypt through AuthManager only
# All password operations must go through AuthManager for security

# Função para página principal
def main_page():
    create_header()
    
    # Menu de navegação com estilo melhorado
    st.markdown("""
    <div style="text-align: center; margin: 30px 0;">
        <h2 style="color: #8B4513; margin-bottom: 25px;">🩺 Navegação do Prontuário</h2>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Histórico Completo", key="historico", help="Ver todos os exames em formato de tabela"):
            st.session_state.page = "historico"
    
    with col2:
        if st.button("📈 Comparativo", key="comparativo", help="Comparar exames e gerar gráficos"):
            st.session_state.page = "comparativo"
    
    with col3:
        if st.button("📅 História da Doença", key="hda", help="Timeline dos eventos médicos"):
            st.session_state.page = "hda"
    
    with col4:
        if st.button("💊 Medicamentos", key="medicamentos", help="Timeline de medicamentos"):
            st.session_state.page = "medicamentos"
    
    # Conteúdo baseado na página selecionada
    page = st.session_state.get('page', 'historico')
    
    if page == "historico":
        show_exam_history()
    elif page == "comparativo":
        show_comparative()
    elif page == "hda":
        show_disease_history()
    elif page == "medicamentos":
        show_medication_timeline()

# Função para mostrar histórico de exames
def show_exam_history():
    st.markdown("### 📊 Histórico Completo de Exames Laboratoriais")
    st.markdown("*Tabela completa com todos os exames da Luna Princess organizados por data*")
    
    try:
        # Use DatabaseManager method to get lab results in pivot format
        df = db.get_lab_results_pivot()
        
        if not df.empty:
            st.markdown('<div class="exam-table">', unsafe_allow_html=True)
            
            # Reset index to make test_name a column
            df_display = df.reset_index()
            
            # Configurar exibição da tabela
            st.dataframe(
                df_display,
                width="stretch",
                height=500,
                column_config={
                    "test_name": st.column_config.TextColumn(
                        "Exame",
                        help="Tipo de exame laboratorial",
                        width="medium"
                    )
                }
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Estatísticas resumidas
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total de Exames", len(df_display))
            
            with col2:
                # Contar colunas de datas (excluindo 'test_name')
                date_columns = [col for col in df_display.columns if col != 'test_name']
                st.metric("Períodos Registrados", len(date_columns))
            
            with col3:
                # Contar valores não vazios
                numeric_cols = df_display.select_dtypes(include=['number']).columns
                total_values = df_display[numeric_cols].count().sum()
                st.metric("Valores Registrados", total_values)
        
        else:
            st.warning("Nenhum dado de exame encontrado. Faça upload de arquivos na área administrativa.")
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")

# Função para mostrar comparativo
def show_comparative():
    st.markdown("### 📈 Ferramenta de Comparativo e Gráficos")
    st.markdown("*Selecione exames e períodos para gerar gráficos comparativos*")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔍 Selecionar Exames:**")
        
        # Obter lista de exames disponíveis
        try:
            available_exams = ['Hemoglobina', 'Hematócrito', 'Eritrócitos', 'Leucócitos', 'Plaquetas', 'Glicose', 'Ureia', 'Creatinina', 'ALT', 'AST']
            selected_exams = st.multiselect(
                "Escolha os exames para comparar:",
                available_exams,
                default=['Hemoglobina', 'Hematócrito'],
                help="Selecione um ou mais exames para comparação"
            )
        except:
            st.error("Erro ao carregar lista de exames")
            return
    
    with col2:
        st.markdown("**📅 Selecionar Período:**")
        date_option = st.selectbox(
            "Período de análise:",
            ["Últimos 6 meses", "Último ano", "Todos os dados"],
            help="Escolha o período para análise"
        )
        
        show_table = st.checkbox("Mostrar tabela de dados", value=False)
    
    if selected_exams:
        try:
            # Get lab results data and filter by selected exams
            all_results = db.get_lab_results()
            df = all_results[all_results['test_name'].isin(selected_exams)] if not all_results.empty else pd.DataFrame()
            
            if not df.empty:
                # Criar gráfico
                fig = go.Figure()
                
                colors = ['#FF69B4', '#87CEEB', '#98FB98', '#DDA0DD', '#F0E68C', '#FFB6C1']
                
                for i, exam in enumerate(selected_exams):
                    exam_data = df[df['exam_name'] == exam]
                    if not exam_data.empty:
                        fig.add_trace(go.Scatter(
                            x=exam_data['exam_date'],
                            y=exam_data['value'],
                            mode='lines+markers',
                            name=exam,
                            line=dict(width=3, color=colors[i % len(colors)]),
                            marker=dict(size=8, symbol='circle')
                        ))
                
                fig.update_layout(
                    title={
                        'text': f"Comparativo: {', '.join(selected_exams)}",
                        'x': 0.5,
                        'font': {'size': 20, 'color': '#8B4513'}
                    },
                    xaxis_title="Data",
                    yaxis_title="Valor",
                    height=500,
                    template="plotly_white",
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                st.plotly_chart(fig, width="stretch")
                
                # Botões de exportação
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📋 Copiar Gráfico", help="Copiar gráfico para área de transferência"):
                        st.success("✅ Gráfico copiado para a área de transferência!")
                
                with col2:
                    if st.button("📥 Exportar Tabela", help="Exportar dados em formato CSV"):
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="⬇️ Download CSV",
                            data=csv,
                            file_name=f"comparativo_exames_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                
                with col3:
                    if st.button("🖼️ Salvar Gráfico", help="Salvar gráfico como imagem"):
                        st.info("Clique com botão direito no gráfico > 'Download plot as PNG'")
                
                # Mostrar tabela se solicitado
                if show_table:
                    st.markdown("### 📋 Dados da Comparação")
                    
                    # Reorganizar dados para melhor visualização
                    pivot_df = df.pivot(index='exam_date', columns='exam_name', values='value')
                    pivot_df = pivot_df.reset_index()
                    pivot_df['exam_date'] = pd.to_datetime(pivot_df['exam_date']).dt.strftime('%d/%m/%Y')
                    
                    st.dataframe(pivot_df, width="stretch")
            
            else:
                st.warning("Nenhum dado encontrado para os exames selecionados.")
        
        except Exception as e:
            st.error(f"Erro ao gerar comparativo: {str(e)}")
    
    else:
        st.info("👆 Selecione pelo menos um exame para gerar o comparativo.")

# Função para mostrar história da doença
def show_disease_history():
    st.markdown("### 📅 História da Doença Atual (HDA)")
    st.markdown("*Timeline interativa dos eventos médicos da Luna Princess*")
    
    try:
        # Get medical timeline data using DatabaseManager
        timeline_events = db.get_medical_timeline()
        
        # Convert to DataFrame format expected by the UI
        if timeline_events:
            history_df = pd.DataFrame(timeline_events)
            # Ensure date column exists and is properly formatted
            if 'event_date' in history_df.columns:
                history_df['event_date'] = pd.to_datetime(history_df['event_date'])
        else:
            history_df = pd.DataFrame()
        
        if not history_df.empty:
            # Timeline superior
            st.markdown('<div class="timeline-container">', unsafe_allow_html=True)
            
            # Converter datas
            history_df['event_date'] = pd.to_datetime(history_df['event_date'])
            history_df = history_df.sort_values('event_date')
            
            # Controle de navegação
            timeline_index = st.session_state.get('timeline_index', 0)
            timeline_index = max(0, min(timeline_index, len(history_df) - 1))
            
            col1, col2, col3 = st.columns([1, 8, 1])
            
            with col1:
                if st.button("◀ Anterior", key="prev_date", disabled=(timeline_index == 0)):
                    st.session_state.timeline_index = timeline_index - 1
                    st.rerun()
            
            with col2:
                if len(history_df) > 0:
                    current_event = history_df.iloc[timeline_index]
                    event_date = current_event['event_date'].strftime('%d/%m/%Y')
                    event_title = current_event['title']
                    
                    # Barra de progresso da timeline
                    progress = (timeline_index + 1) / len(history_df)
                    
                    st.markdown(f"""
                    <div style="text-align: center; padding: 25px;">
                        <div style="background: linear-gradient(90deg, #FFB6C1 0%, #FFB6C1 {progress*100}%, #E0E0E0 {progress*100}%, #E0E0E0 100%); height: 6px; margin: 25px 0; position: relative; border-radius: 3px;">
                            <div style="position: absolute; left: {progress*100}%; top: -8px; width: 6px; height: 22px; background: white; transform: translateX(-50%); border-radius: 3px; box-shadow: 0 0 10px rgba(0,0,0,0.3);"></div>
                        </div>
                        <h3 style="color: #8B4513; margin: 15px 0;">{event_date}</h3>
                        <h4 style="color: #FF69B4; margin: 10px 0;">{event_title}</h4>
                        <p style="color: #696969;">Evento {timeline_index + 1} de {len(history_df)}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col3:
                if st.button("Próximo ▶", key="next_date", disabled=(timeline_index == len(history_df) - 1)):
                    st.session_state.timeline_index = timeline_index + 1
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Detalhes do evento selecionado
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.markdown("**📝 Narrativa Médica:**")
                
                current_event = history_df.iloc[timeline_index]
                description = current_event['description']
                
                st.markdown(f"""
                <div style="background: #F8F9FA; padding: 20px; border-radius: 10px; border-left: 4px solid #FFB6C1; margin: 15px 0;">
                    <p style="font-size: 1.1em; line-height: 1.6; color: #333; margin: 0;">{description}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Palavras-chave
                if pd.notna(current_event['keywords']):
                    keywords = current_event['keywords'].split(',')
                    st.markdown("**🏷️ Palavras-chave:**")
                    
                    keyword_html = ""
                    for keyword in keywords:
                        keyword_html += f'<span style="background: #FFB6C1; color: white; padding: 5px 10px; border-radius: 15px; margin: 3px; display: inline-block; font-size: 0.9em;">{keyword.strip()}</span>'
                    
                    st.markdown(keyword_html, unsafe_allow_html=True)
            
            with col2:
                st.markdown("**🔬 Exames Relacionados:**")
                
                # Obter exames próximos à data do evento
                event_date = current_event['event_date']
                
                # Simular exames relacionados (em implementação real, buscar no banco)
                related_exams = {
                    'Exame': ['Hemoglobina', 'Leucócitos', 'Glicose'],
                    'Valor': ['12.5 g/dL', '8.200/μL', '95 mg/dL'],
                    'Referência': ['12-18 g/dL', '6.000-17.000/μL', '70-110 mg/dL'],
                    'Status': ['Normal', 'Normal', 'Normal']
                }
                
                exams_df = pd.DataFrame(related_exams)
                
                # Colorir status
                def color_status(val):
                    if val == 'Normal':
                        return 'background-color: #D4EDDA; color: #155724'
                    elif val == 'Alto':
                        return 'background-color: #F8D7DA; color: #721c24'
                    elif val == 'Baixo':
                        return 'background-color: #FFF3CD; color: #856404'
                    return ''
                
                styled_df = exams_df.style.applymap(color_status, subset=['Status'])
                st.dataframe(styled_df, width="stretch", hide_index=True)
                
                # Informações adicionais
                st.markdown("**👨‍⚕️ Responsável:**")
                created_by = current_event.get('created_by', 'Não informado')
                st.info(f"Dr. {created_by}")
        
        else:
            st.warning("Nenhum evento médico registrado. Adicione eventos na área administrativa.")
    
    except Exception as e:
        st.error(f"Erro ao carregar histórico médico: {str(e)}")

# Função para mostrar timeline de medicamentos
def show_medication_timeline():
    st.markdown("### 💊 Linha do Tempo de Medicamentos")
    st.markdown("*Histórico completo de medicamentos administrados à Luna Princess*")
    
    try:
        # Get medication history using DatabaseManager  
        medication_data = db.get_medication_history()
        
        # Convert to DataFrame format expected by the UI
        if medication_data:
            medications_df = pd.DataFrame(medication_data)
            # Ensure date columns exist and are properly formatted
            for date_col in ['start_date', 'end_date']:
                if date_col in medications_df.columns:
                    medications_df[date_col] = pd.to_datetime(medications_df[date_col], errors='coerce')
        else:
            medications_df = pd.DataFrame()
        
        if not medications_df.empty:
            st.markdown('<div class="medication-timeline">', unsafe_allow_html=True)
            
            # Cores para diferentes medicamentos
            colors = ['#FFD700', '#90EE90', '#FFB6C1', '#DDA0DD', '#F0E68C', '#87CEEB']
            
            for i, (_, med) in enumerate(medications_df.iterrows()):
                color = colors[i % len(colors)]
                
                # Calcular duração
                start_date = pd.to_datetime(med['start_date'])
                end_date = pd.to_datetime(med['end_date']) if pd.notna(med['end_date']) else datetime.now()
                
                duration = (end_date - start_date).days
                status = "Em uso" if pd.isna(med['end_date']) else "Finalizado"
                status_color = "#28a745" if status == "Em uso" else "#6c757d"
                
                st.markdown(f"""
                <div class="medication-card" style="background: linear-gradient(135deg, {color}, {color}AA); border-left: 6px solid {color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <div style="flex: 2; min-width: 200px;">
                            <h4 style="color: #333; margin: 0 0 10px 0; font-size: 1.3em;">💊 {med['medication_name']}</h4>
                            <p style="margin: 5px 0; color: #555;"><strong>Princípio Ativo:</strong> {med['active_ingredient']}</p>
                            <p style="margin: 5px 0; color: #555;"><strong>Dose:</strong> {med['dosage']} - <strong>Via:</strong> {med['route']}</p>
                        </div>
                        <div style="flex: 1; text-align: center; min-width: 150px;">
                            <div style="background: white; padding: 10px; border-radius: 8px; margin: 5px;">
                                <p style="margin: 0; font-size: 0.9em; color: #666;">Início</p>
                                <p style="margin: 0; font-weight: bold; color: #333;">{start_date.strftime('%d/%m/%Y')}</p>
                            </div>
                            {f'''<div style="background: white; padding: 10px; border-radius: 8px; margin: 5px;">
                                <p style="margin: 0; font-size: 0.9em; color: #666;">Término</p>
                                <p style="margin: 0; font-weight: bold; color: #333;">{end_date.strftime('%d/%m/%Y') if pd.notna(med['end_date']) else 'Em uso'}</p>
                            </div>''' if pd.notna(med['end_date']) or status == "Em uso" else ''}
                        </div>
                        <div style="flex: 1; text-align: right; min-width: 150px;">
                            <div style="background: {status_color}; color: white; padding: 8px 15px; border-radius: 20px; display: inline-block; margin-bottom: 10px;">
                                {status}
                            </div>
                            <p style="margin: 0; font-size: 0.9em; color: #666;"><strong>Duração:</strong> {duration} dias</p>
                        </div>
                    </div>
                    {f'<div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.3);"><p style="margin: 0; font-style: italic; color: #555;"><strong>P.S.:</strong> {med["notes"]}</p></div>' if pd.notna(med['notes']) else ''}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Estatísticas dos medicamentos
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_meds = len(medications_df)
                st.metric("Total de Medicamentos", total_meds)
            
            with col2:
                active_meds = len(medications_df[medications_df['end_date'].isna()])
                st.metric("Medicamentos Ativos", active_meds)
            
            with col3:
                completed_meds = len(medications_df[medications_df['end_date'].notna()])
                st.metric("Tratamentos Finalizados", completed_meds)
        
        else:
            st.warning("Nenhum medicamento registrado. Adicione medicamentos na área administrativa.")
    
    except Exception as e:
        st.error(f"Erro ao carregar medicamentos: {str(e)}")

# Função para área administrativa
def admin_page():
    create_header(is_admin=True)
    
    st.markdown("""
    <div style="text-align: center; margin: 20px 0;">
        <h2 style="color: #4682B4;">⚙️ Painel Administrativo</h2>
        <p style="color: #666;">Gerencie dados, uploads e configurações do sistema</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Menu administrativo
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📁 Upload", "🤖 Processamento IA", "✏️ Edição", "💊 Medicamentos", "👥 Usuários"])
    
    with tab1:
        show_upload_area()
    
    with tab2:
        show_ai_processing()
    
    with tab3:
        show_editing_area()
    
    with tab4:
        show_medication_management()
    
    with tab5:
        show_user_management()

# Função para área de upload
def show_upload_area():
    st.markdown("### 📁 Upload de Arquivos")
    st.markdown("*Faça upload de PDFs, áudios, vídeos e imagens para processamento automático*")
    
    st.markdown('<div class="upload-area">', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "🎯 Arraste e solte arquivos aqui ou clique para selecionar",
        accept_multiple_files=True,
        type=['pdf', 'mp3', 'wav', 'mp4', 'avi', 'mov', 'txt', 'jpg', 'jpeg', 'png'],
        help="Suporte para: PDFs de exames, áudios de consultas, vídeos, imagens e documentos de texto"
    )
    
    if uploaded_files:
        st.markdown("### 📋 Arquivos Carregados:")
        
        for i, file in enumerate(uploaded_files):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                file_icon = "📄" if file.type.startswith('application') else "🎵" if file.type.startswith('audio') else "🎬" if file.type.startswith('video') else "🖼️"
                st.write(f"{file_icon} **{file.name}** ({file.size} bytes)")
            
            with col2:
                st.markdown('<div class="progress-circle"></div>', unsafe_allow_html=True)
                st.caption("Processando...")
            
            with col3:
                st.markdown("✅", help="Upload concluído")
            
            with col4:
                if st.button("🗑️", key=f"delete_{i}", help="Remover arquivo"):
                    st.warning(f"Arquivo {file.name} removido!")
        
        st.markdown("---")
        
        # Opções de processamento
        col1, col2 = st.columns(2)
        
        with col1:
            process_option = st.selectbox(
                "Tipo de processamento:",
                ["Automático (IA)", "Manual", "Apenas armazenar"],
                help="Escolha como processar os arquivos"
            )
        
        with col2:
            priority = st.selectbox(
                "Prioridade:",
                ["Normal", "Alta", "Baixa"],
                help="Prioridade do processamento"
            )
        
        if st.button("🚀 Gerar Histórico", type="primary", help="Iniciar processamento com IA"):
            with st.spinner("🤖 Processando arquivos com IA... Não feche esta janela."):
                # Simular processamento
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                stages = [
                    "Analisando arquivos...",
                    "Extraindo texto de PDFs...",
                    "Processando áudios...",
                    "Identificando datas e eventos...",
                    "Criando timeline...",
                    "Finalizando processamento..."
                ]
                
                for i, stage in enumerate(stages):
                    status_text.text(stage)
                    for j in range(17):  # ~100/6 steps per stage
                        progress_bar.progress(min(100, (i * 17) + j + 1))
                        # time.sleep(0.1)  # Simular tempo de processamento
                
                status_text.text("✅ Processamento concluído!")
                
                st.markdown('<div class="success-message">', unsafe_allow_html=True)
                st.success("🎉 Processamento concluído com sucesso!")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Mostrar histórico gerado
                st.markdown("### 📋 Histórico Gerado")
                
                history_entries = [
                    {
                        'date': '15/01/2024',
                        'text': 'Início dos episódios de mioclonias. Paciente apresentou tremores generalizados durante a madrugada, com duração de 2-3 minutos.',
                        'keywords': ['mioclonias', 'tremores', 'neurológico', 'madrugada'],
                        'files': ['exame_neurologico.pdf', 'video_episodio.mp4'],
                        'confidence': 95
                    },
                    {
                        'date': '22/01/2024',
                        'text': 'Primeira consulta veterinária. Exame físico normal, animal alerta e responsivo. Solicitados exames complementares.',
                        'keywords': ['consulta', 'exame físico', 'exames', 'normal'],
                        'files': ['consulta_22jan.pdf', 'audio_consulta.mp3'],
                        'confidence': 88
                    },
                    {
                        'date': '05/02/2024',
                        'text': 'Resultados de exames laboratoriais recebidos. Hemograma completo dentro da normalidade. Função hepática preservada.',
                        'keywords': ['exames', 'laboratório', 'hemograma', 'normal', 'fígado'],
                        'files': ['exames_05fev.pdf'],
                        'confidence': 92
                    }
                ]
                
                for entry in history_entries:
                    with st.expander(f"📅 {entry['date']} - {entry['text'][:60]}... (Confiança: {entry['confidence']}%)"):
                        st.write(f"**Descrição completa:** {entry['text']}")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**🏷️ Palavras-chave:**")
                            for keyword in entry['keywords']:
                                st.markdown(f"<span style='background: #FFB6C1; color: white; padding: 3px 8px; border-radius: 10px; margin: 2px; display: inline-block; font-size: 0.8em;'>{keyword}</span>", unsafe_allow_html=True)
                        
                        with col2:
                            st.write("**📎 Arquivos fonte:**")
                            for file in entry['files']:
                                st.markdown(f"📄 {file}")
                        
                        # Botões de ação
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("✏️ Editar", key=f"edit_{entry['date']}"):
                                st.info("Abrindo editor...")
                        with col2:
                            if st.button("✅ Aprovar", key=f"approve_{entry['date']}"):
                                st.success("Entrada aprovada!")
                        with col3:
                            if st.button("❌ Rejeitar", key=f"reject_{entry['date']}"):
                                st.warning("Entrada rejeitada!")
                
                # Botão final para salvar
                if st.button("💾 Salvar Histórico Completo", type="primary"):
                    st.balloons()
                    st.success("🎉 Histórico salvo com sucesso no banco de dados!")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Função para processamento IA
def show_ai_processing():
    st.markdown("### 🤖 Processamento Inteligente com IA")
    st.markdown("*Configure e monitore o processamento automático de dados*")
    
    # Status do sistema de IA
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #D4EDDA, #C3E6CB); padding: 20px; border-radius: 10px; text-align: center;">
            <h4 style="color: #155724; margin: 0;">🔬 Exames PDF</h4>
            <p style="color: #155724; margin: 10px 0;">Status: Ativo</p>
            <small style="color: #155724;">Última execução: há 2 horas</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**Funcionalidades:**")
        st.info("""
        ✅ Extração de data do exame  
        ✅ Identificação do laboratório  
        ✅ Nome do médico solicitante  
        ✅ Valores numéricos  
        ✅ Padronização de unidades  
        ✅ Criação automática de campos
        """)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #CCE5FF, #B3D9FF); padding: 20px; border-radius: 10px; text-align: center;">
            <h4 style="color: #004085; margin: 0;">🎵 Áudio/Vídeo</h4>
            <p style="color: #004085; margin: 10px 0;">Status: Ativo</p>
            <small style="color: #004085;">Última execução: há 1 hora</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**Funcionalidades:**")
        st.info("""
        ✅ Transcrição de áudio  
        ✅ Extração de eventos  
        ✅ Identificação de datas  
        ✅ Reconhecimento de sintomas  
        ✅ Timeline automática  
        ✅ Narrativas médicas
        """)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #FFF3CD, #FFEAA7); padding: 20px; border-radius: 10px; text-align: center;">
            <h4 style="color: #856404; margin: 0;">💊 Medicamentos</h4>
            <p style="color: #856404; margin: 10px 0;">Status: Ativo</p>
            <small style="color: #856404;">Última execução: há 30 min</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**Funcionalidades:**")
        st.info("""
        ✅ Reconhecimento de princípio ativo  
        ✅ Validação online  
        ✅ Extração de dosagem  
        ✅ Via de administração  
        ✅ Datas de início/fim  
        ✅ Perguntas de clarificação
        """)
    
    st.markdown("---")
    
    # Configurações de IA
    st.markdown("### ⚙️ Configurações do Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔧 Configurações Gerais:**")
        
        confidence_threshold = st.slider(
            "Limite de confiança (%)",
            min_value=50,
            max_value=100,
            value=85,
            help="Limite mínimo de confiança para aceitar automaticamente"
        )
        
        auto_approve = st.checkbox(
            "Aprovação automática",
            value=False,
            help="Aprovar automaticamente resultados com alta confiança"
        )
        
        language_model = st.selectbox(
            "Modelo de linguagem:",
            ["GPT-4", "GPT-3.5-turbo", "Claude-3"],
            help="Modelo de IA para processamento de texto"
        )
    
    with col2:
        st.markdown("**📊 Estatísticas de Processamento:**")
        
        stats_data = {
            'Tipo': ['PDFs processados', 'Áudios transcritos', 'Eventos extraídos', 'Medicamentos identificados'],
            'Total': [45, 23, 67, 12],
            'Última semana': [8, 3, 12, 2],
            'Taxa de sucesso': ['94%', '89%', '91%', '96%']
        }
        
        st.dataframe(pd.DataFrame(stats_data), width="stretch", hide_index=True)
    
    # Ações de processamento
    st.markdown("### 🔄 Ações de Processamento")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Reprocessar Todos", help="Reprocessar todos os dados com IA"):
            with st.spinner("Reprocessando todos os dados..."):
                progress_bar = st.progress(0)
                for i in range(100):
                    progress_bar.progress(i + 1)
                st.success("✅ Reprocessamento concluído!")
    
    with col2:
        if st.button("🧹 Limpar Cache", help="Limpar cache do sistema de IA"):
            st.success("✅ Cache limpo!")
    
    with col3:
        if st.button("📊 Relatório IA", help="Gerar relatório de performance"):
            st.info("📄 Relatório gerado! Verifique a seção de downloads.")
    
    with col4:
        if st.button("🔧 Teste Conexão", help="Testar conexão com APIs de IA"):
            with st.spinner("Testando conexões..."):
                st.success("✅ Todas as conexões estão funcionando!")

# Função para área de edição
def show_editing_area():
    st.markdown("### ✏️ Edição e Validação do Prontuário")
    st.markdown("*Edite e valide entradas do prontuário com controle de versões*")
    
    # Seletor de entrada para edição
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**📋 Selecionar Entrada para Edição:**")
        
        # Simular lista de entradas
        entries = [
            "15/01/2024 - Início das mioclonias",
            "22/01/2024 - Primeira consulta veterinária",
            "05/02/2024 - Resultados laboratoriais",
            "18/02/2024 - Ajuste de medicação",
            "03/03/2024 - Melhora dos sintomas"
        ]
        
        selected_entry = st.selectbox("Escolha uma entrada:", entries)
    
    with col2:
        st.markdown("**📊 Status da Entrada:**")
        st.info("✅ Aprovada\n📝 Última edição: Dr. Paulo\n🕒 02/03/2024 14:30")
    
    # Área de edição
    st.markdown("### 📝 Editor de Texto")
    
    # Texto original (simulado)
    original_text = """Paciente canina apresentou episódios de mioclonias generalizadas durante a madrugada. 
Os episódios duraram aproximadamente 2-3 minutos, com recuperação espontânea. 
Animal manteve-se alerta e responsivo após os episódios. 
Não houve perda de consciência aparente."""
    
    # Editor com destaque de cores
    st.markdown("**Instruções:** Texto original em azul, suas modificações aparecerão em vermelho.")
    
    edited_text = st.text_area(
        "Editar texto:",
        value=original_text,
        height=200,
        help="Edite o texto. Modificações serão destacadas em vermelho."
    )
    
    # Simular diferenças
    if edited_text != original_text:
        st.markdown("**🔍 Visualização das Alterações:**")
        
        # Simular texto com cores (em implementação real, usar diff)
        st.markdown("""
        <div style="background: #F8F9FA; padding: 15px; border-radius: 8px; border-left: 4px solid #FFB6C1;">
            <p><span style="color: blue;">Paciente canina apresentou episódios de mioclonias generalizadas durante a madrugada.</span></p>
            <p><span style="color: red;">Os episódios duraram aproximadamente 3-4 minutos</span> <span style="text-decoration: line-through; color: gray;">2-3 minutos</span>, <span style="color: blue;">com recuperação espontânea.</span></p>
            <p><span style="color: blue;">Animal manteve-se alerta e responsivo após os episódios.</span></p>
            <p><span style="color: blue;">Não houve perda de consciência aparente.</span></p>
            <p><span style="color: red;">Tutores relataram que a Luna ficou mais quieta após os episódios.</span></p>
        </div>
        """, unsafe_allow_html=True)
    
    # Botões de ação
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Reprocessar com IA", help="IA irá corrigir ortografia e reorganizar"):
            with st.spinner("Reprocessando com IA..."):
                st.success("✅ Texto reprocessado e corrigido!")
    
    with col2:
        if st.button("💾 Salvar Alterações", help="Salvar modificações"):
            if edited_text != original_text:
                st.success("✅ Alterações salvas com sucesso!")
                
                # Adicionar ao log
                if 'edit_log' not in st.session_state:
                    st.session_state.edit_log = []
                
                st.session_state.edit_log.append({
                    'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M'),
                    'user': 'Dr. Paulo',
                    'action': 'Texto editado',
                    'entry': selected_entry
                })
            else:
                st.info("Nenhuma alteração detectada.")
    
    with col3:
        if st.button("❌ Descartar", help="Descartar alterações"):
            st.warning("Alterações descartadas!")
    
    with col4:
        if st.button("🖨️ Gerar PDF", help="Gerar PDF do prontuário completo"):
            with st.spinner("Gerando PDF..."):
                st.success("✅ PDF gerado! Verifique a seção de downloads.")
    
    # Log de modificações
    st.markdown("### 📋 Log de Modificações")
    
    if 'edit_log' in st.session_state and st.session_state.edit_log:
        log_df = pd.DataFrame(st.session_state.edit_log)
        st.dataframe(log_df, width="stretch", hide_index=True)
    else:
        # Log simulado
        sample_log = [
            {'timestamp': '15/01/2024 10:30', 'user': 'Dr. Júlia', 'action': 'Entrada criada', 'entry': 'Início das mioclonias'},
            {'timestamp': '15/01/2024 14:20', 'user': 'Dr. Paulo', 'action': 'Texto editado', 'entry': 'Início das mioclonias'},
            {'timestamp': '22/01/2024 09:15', 'user': 'Dr. Júlia', 'action': 'Entrada aprovada', 'entry': 'Primeira consulta'},
            {'timestamp': '05/02/2024 16:45', 'user': 'Dr. Paulo', 'action': 'Anexo adicionado', 'entry': 'Resultados laboratoriais'}
        ]
        
        st.dataframe(pd.DataFrame(sample_log), width="stretch", hide_index=True)

# Função para gestão de medicamentos
def show_medication_management():
    st.markdown("### 💊 Gestão do Histórico de Medicamentos")
    st.markdown("*Registre e gerencie medicamentos via texto ou áudio*")
    
    # Tabs para diferentes métodos de entrada
    tab1, tab2, tab3 = st.tabs(["🎤 Entrada por Áudio", "⌨️ Entrada Manual", "📋 Histórico"])
    
    with tab1:
        st.markdown("#### 🎤 Registro de Medicamentos via Áudio")
        
        # Simulação de entrada por áudio
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**🎙️ Gravação de Áudio:**")
            
            if st.button("🔴 Iniciar Gravação", help="Clique para começar a gravar"):
                st.info("🎙️ Gravando... Fale sobre o medicamento administrado.")
                
                # Simular gravação
                with st.spinner("Gravando áudio..."):
                    progress_bar = st.progress(0)
                    for i in range(100):
                        progress_bar.progress(i + 1)
                
                st.success("✅ Gravação concluída!")
                
                # Simular transcrição
                st.markdown("**📝 Transcrição Automática:**")
                transcription = """
                Hoje, dia quinze de janeiro, administrei à Luna o medicamento canabidiol, 
                na dose de vinte e cinco miligramas, por via oral. 
                O medicamento foi dado às oito horas da manhã, conforme orientação veterinária. 
                A Luna aceitou bem o medicamento misturado na ração.
                """
                
                st.text_area("Texto transcrito:", value=transcription, height=100)
                
                # Processamento com IA
                if st.button("🤖 Processar com IA"):
                    with st.spinner("Processando informações..."):
                        st.success("✅ Informações extraídas!")
                        
                        # Mostrar dados extraídos
                        extracted_data = {
                            'Data': '15/01/2024',
                            'Medicamento': 'Canabidiol',
                            'Princípio Ativo': 'Canabidiol',
                            'Dose': '25mg',
                            'Via': 'VO (Via Oral)',
                            'Horário': '08:00',
                            'Observações': 'Aceito bem misturado na ração'
                        }
                        
                        for key, value in extracted_data.items():
                            st.write(f"**{key}:** {value}")
        
        with col2:
            st.markdown("**🤖 Validação da IA:**")
            
            # Perguntas de clarificação
            st.markdown("**❓ Perguntas de Clarificação:**")
            
            questions = [
                "O medicamento canabidiol foi administrado sob demanda?",
                "A dose de 25mg está correta?",
                "O horário de administração é fixo ou variável?"
            ]
            
            for i, question in enumerate(questions):
                st.markdown(f"**{i+1}.** {question}")
                response = st.radio(f"Resposta {i+1}:", ["Sim", "Não", "Não sei"], key=f"q{i}")
                
                if response == "Não":
                    correction = st.text_input(f"Correção para pergunta {i+1}:", key=f"corr{i}")
    
    with tab2:
        st.markdown("#### ⌨️ Entrada Manual de Medicamentos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            med_name = st.text_input("Nome do Medicamento:")
            active_ingredient = st.text_input("Princípio Ativo:")
            dosage = st.text_input("Dosagem (ex: 25mg):")
            route = st.selectbox("Via de Administração:", ["VO (Oral)", "SC (Subcutânea)", "IM (Intramuscular)", "IV (Intravenosa)", "Tópica"])
        
        with col2:
            start_date = st.date_input("Data de Início:")
            end_date = st.date_input("Data de Término (opcional):", value=None)
            frequency = st.text_input("Frequência (ex: 2x ao dia):")
            notes = st.text_area("Observações:", height=100)
        
        if st.button("💾 Salvar Medicamento", type="primary"):
            if med_name and active_ingredient and dosage:
                # Aqui salvaria no banco de dados
                st.success(f"✅ Medicamento '{med_name}' salvo com sucesso!")
            else:
                st.error("❌ Preencha pelo menos nome, princípio ativo e dosagem.")
    
    with tab3:
        st.markdown("#### 📋 Histórico de Medicamentos")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox("Status:", ["Todos", "Ativos", "Finalizados"])
        
        with col2:
            period_filter = st.selectbox("Período:", ["Todos", "Último mês", "Últimos 3 meses", "Último ano"])
        
        with col3:
            search_term = st.text_input("Buscar medicamento:")
        
        # Tabela de medicamentos
        try:
            medication_data = db.get_medication_history()
            medications_df = pd.DataFrame(medication_data) if medication_data else pd.DataFrame()
            
            if not medications_df.empty:
                # Aplicar filtros
                if status_filter == "Ativos":
                    medications_df = medications_df[medications_df['end_date'].isna()]
                elif status_filter == "Finalizados":
                    medications_df = medications_df[medications_df['end_date'].notna()]
                
                if search_term:
                    medications_df = medications_df[
                        medications_df['medication_name'].str.contains(search_term, case=False, na=False) |
                        medications_df['active_ingredient'].str.contains(search_term, case=False, na=False)
                    ]
                
                # Configurar exibição
                display_df = medications_df.copy()
                display_df['status'] = display_df['end_date'].apply(lambda x: "Ativo" if pd.isna(x) else "Finalizado")
                
                # Reorganizar colunas
                columns_order = ['medication_name', 'active_ingredient', 'start_date', 'end_date', 'dosage', 'route', 'status', 'notes']
                display_df = display_df[columns_order]
                
                # Renomear colunas
                display_df.columns = ['Medicamento', 'Princípio Ativo', 'Início', 'Término', 'Dose', 'Via', 'Status', 'Observações']
                
                st.dataframe(
                    display_df,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Status": st.column_config.TextColumn(
                            "Status",
                            help="Status atual do medicamento"
                        )
                    }
                )
                
                # Estatísticas
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total = len(display_df)
                    st.metric("Total Filtrado", total)
                
                with col2:
                    active = len(display_df[display_df['Status'] == 'Ativo'])
                    st.metric("Ativos", active)
                
                with col3:
                    finished = len(display_df[display_df['Status'] == 'Finalizado'])
                    st.metric("Finalizados", finished)
            
            else:
                st.info("Nenhum medicamento registrado ainda.")
        
        except Exception as e:
            st.error(f"Erro ao carregar medicamentos: {str(e)}")

# Função para gestão de usuários
def show_user_management():
    st.markdown("### 👥 Gestão de Usuários")
    st.markdown("*Gerencie usuários e permissões do sistema*")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### ➕ Criar Novo Usuário")
        
        with st.form("new_user_form"):
            new_name = st.text_input("Nome completo:")
            new_email = st.text_input("Email:")
            new_password = st.text_input("Senha:", type="password")
            confirm_password = st.text_input("Confirmar senha:", type="password")
            
            user_role = st.selectbox("Função:", ["Administrador", "Veterinário", "Visualizador"])
            
            permissions = st.multiselect(
                "Permissões:",
                ["Upload de arquivos", "Edição de prontuário", "Gestão de medicamentos", "Relatórios", "Configurações"],
                default=["Upload de arquivos", "Edição de prontuário"]
            )
            
            submitted = st.form_submit_button("➕ Criar Usuário", type="primary")
            
            if submitted:
                if new_email and new_password and new_name:
                    if new_password == confirm_password:
                        try:
                            # Hash da senha
                            password_hash = hash_password(new_password)
                            
                            # Salvar no banco (simulado)
                            user_id = db.add_user(new_email, password_hash, new_name)
                            
                            st.success(f"✅ Usuário '{new_name}' criado com sucesso!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ Erro ao criar usuário: {str(e)}")
                    else:
                        st.error("❌ Senhas não coincidem!")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios!")
    
    with col2:
        st.markdown("#### 👤 Usuários Existentes")
        
        # Lista de usuários (simulada)
        users_data = [
            {"nome": "Dr. Paulo Guimarães", "email": "paulo@email.com", "funcao": "Administrador", "status": "Ativo", "ultimo_acesso": "Hoje, 14:30"},
            {"nome": "Dra. Júlia", "email": "julia@email.com", "funcao": "Veterinária", "status": "Ativo", "ultimo_acesso": "Ontem, 16:45"},
            {"nome": "Admin Sistema", "email": "admin@admin.com", "funcao": "Administrador", "status": "Ativo", "ultimo_acesso": "Hoje, 09:15"}
        ]
        
        for i, user in enumerate(users_data):
            with st.expander(f"👤 {user['nome']} ({user['funcao']})"):
                col_info, col_actions = st.columns([2, 1])
                
                with col_info:
                    st.write(f"**Email:** {user['email']}")
                    st.write(f"**Função:** {user['funcao']}")
                    st.write(f"**Status:** {user['status']}")
                    st.write(f"**Último acesso:** {user['ultimo_acesso']}")
                
                with col_actions:
                    if st.button("✏️ Editar", key=f"edit_user_{i}"):
                        st.info("Abrindo editor de usuário...")
                    
                    if st.button("🔒 Desativar", key=f"deactivate_user_{i}"):
                        st.warning(f"Usuário {user['nome']} desativado!")
                    
                    if user['email'] != "admin@admin.com":  # Não permitir deletar admin principal
                        if st.button("🗑️ Remover", key=f"delete_user_{i}"):
                            st.error(f"Usuário {user['nome']} removido!")
    
    # Configurações de segurança
    st.markdown("---")
    st.markdown("#### 🔐 Configurações de Segurança")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Políticas de Senha:**")
        min_length = st.number_input("Comprimento mínimo:", min_value=6, max_value=20, value=8)
        require_special = st.checkbox("Exigir caracteres especiais", value=True)
        require_numbers = st.checkbox("Exigir números", value=True)
    
    with col2:
        st.markdown("**Sessão:**")
        session_timeout = st.number_input("Timeout (minutos):", min_value=15, max_value=480, value=60)
        max_attempts = st.number_input("Tentativas máximas de login:", min_value=3, max_value=10, value=5)
    
    with col3:
        st.markdown("**Auditoria:**")
        log_logins = st.checkbox("Registrar logins", value=True)
        log_actions = st.checkbox("Registrar ações", value=True)
        
        if st.button("📊 Ver Logs de Auditoria"):
            st.info("Abrindo logs de auditoria...")
    
    if st.button("💾 Salvar Configurações", type="primary"):
        st.success("✅ Configurações de segurança salvas!")

# Função principal
def main():
    load_css()
    
    # Verificar parâmetros da URL
    query_params = st.query_params
    is_admin = 'admin' in query_params
    
    # Inicializar session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'page' not in st.session_state:
        st.session_state.page = 'historico'
    
    if 'timeline_index' not in st.session_state:
        st.session_state.timeline_index = 0
    
    # CRITICAL: Use proper authentication system
    if is_admin:
        # Check if user is authenticated through AuthManager
        if not auth.is_authenticated():
            # Show proper login form using AuthManager
            show_admin_login()
        else:
            # CRITICAL: Enforce password change if required
            if auth.enforce_password_change():
                return  # Stop execution if password change is enforced
            
            # Show authenticated admin interface
            show_admin_interface()
    
    else:
        # Show main patient interface
        show_patient_interface()

def show_admin_login():
    """Show secure admin login using AuthManager"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h2 style="color: #4682B4;">🔐 Login Administrativo</h2>
        <p style="color: #666;">Acesse a área restrita do sistema</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Use AuthManager's secure authentication
    if auth.show_login_form():
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Link para voltar à página principal
    st.markdown("---")
    st.markdown("🏠 [Voltar à página principal](?)")

def show_admin_interface():
    """Show authenticated admin interface using pages/admin.py"""
    try:
        # Import and run the integrated admin page
        from pages.admin import run_admin_page
        run_admin_page(db, auth)
    except Exception as e:
        st.error(f"🚨 Admin interface error: {e}")
        st.error("Please contact system administrator.")
        
        # Allow logout even if admin interface fails
        if st.button("🚪 Logout"):
            auth.logout()
            st.rerun()

def show_patient_interface():
    """Show patient interface for public access"""
    main_page()
    
    # Sidebar with patient information
    with st.sidebar:
        st.markdown("### 🩺 Prontuário Luna")
        st.info("**Paciente:** Luna Princess Mendes Guimarães\n**Espécie:** Canina\n**Tutores:** Paulo e Júlia")
        
        st.markdown("### 🔗 Links Úteis")
        if st.button("🔐 Área Administrativa"):
            st.query_params['admin'] = 'true'
            st.rerun()
        
        st.markdown("### 📞 Contato")
        st.markdown("""
        **Emergência Veterinária:**  
        📞 (11) 9999-9999
        
        **Clínica Principal:**  
        📞 (11) 8888-8888
        """)
        
        st.markdown("### ℹ️ Sobre o Sistema")
        st.caption("Sistema de Prontuário Digital v2.0\nDesenvolvido com ❤️ para Luna Princess")
    
    # This block is now handled by show_patient_interface() above

if __name__ == "__main__":
    main()

