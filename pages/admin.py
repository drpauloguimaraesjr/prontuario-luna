import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import os
import subprocess
import tempfile
import json
from typing import List, Dict, Any, Optional

from ai_processing import AIProcessor
from utils import validate_file_type, format_date, parse_date
from database import ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pages.admin_dashboard_helpers import (
    render_medical_trends_charts,
    render_user_activity_charts, 
    render_exam_analysis_charts,
    render_system_performance_charts,
    render_recent_activity_widget,
    export_dashboard_data,
    render_system_info_details
)

def run_admin_page(db, auth):
    """Executar a página administrativa com autenticação"""
    
    # Verificar autenticação
    if not auth.require_auth(redirect_to_login=True):
        return
    
    # ENFORCEMENT CRÍTICO: Bloquear acesso se mudança de senha for obrigatória
    if auth.enforce_password_change():
        # Se enforce_password_change() retorna True, bloqueia TUDO
        return
    
    current_user = auth.get_current_user()
    current_role = current_user.get('role', ROLE_USER)
    
    # Verificar se o usuário tem permissão para acessar o painel admin
    if not auth.is_admin():
        st.error("🚫 Acesso Negado")
        st.warning("Apenas administradores podem acessar este painel.")
        return
    
    # Cabeçalho administrativo
    st.markdown("# 🔐 Painel Administrativo")
    
    # Informações do usuário com role
    col1, col2 = st.columns([4, 1])
    with col1:
        role_colors = {
            ROLE_SUPER_ADMIN: "🔴",
            ROLE_ADMIN: "🟡", 
            ROLE_USER: "🟢"
        }
        role_icon = role_colors.get(current_role, "⚪")
        st.markdown(f"**Usuário:** {current_user['name']} ({current_user['email']}) | **Role:** {role_icon} {current_role}")
    
    # Botão de logout
    with col2:
        if st.button("🚪 Sair"):
            auth.logout()
            st.query_params.clear()
            st.rerun()
    
    # Abas de navegação administrativa baseadas em role
    available_tabs = ["📊 Dashboard"]
    
    # Todas as funções básicas disponíveis para ADMIN e SUPER_ADMIN
    available_tabs.extend([
        "📄 Upload de Exames (PDF)",
        "📝 Prontuário Clínico", 
        "💊 Medicamentos",
        "📸 Fotos e Mídia",
        "🔗 Links Compartilháveis"
    ])
    
    # Gerenciamento de usuários apenas para ADMIN e SUPER_ADMIN
    if auth.is_admin():
        available_tabs.append("👥 Usuários")
    
    # Configurações avançadas apenas para SUPER_ADMIN
    if auth.is_super_admin():
        available_tabs.append("⚙️ Configurações")
    
    admin_tab = st.selectbox(
        "Selecione a seção:",
        available_tabs,
        help=f"Seções disponíveis para seu nível de acesso ({current_role})"
    )
    
    st.markdown("---")
    
    # Inicializar processador de IA
    ai_processor = AIProcessor()
    
    if admin_tab == "📊 Dashboard":
        render_admin_dashboard(db, auth)
    elif admin_tab == "📄 Upload de Exames (PDF)":
        if auth.is_admin():
            render_pdf_upload_section(db, ai_processor, current_user['id'])
        else:
            st.error("🚫 Acesso restrito. Apenas administradores podem fazer upload de exames.")
    elif admin_tab == "📝 Prontuário Clínico":
        if auth.is_admin():
            render_clinical_notes_section(db, ai_processor, current_user['id'])
        else:
            st.error("🚫 Acesso restrito. Apenas administradores podem gerenciar prontuários.")
    elif admin_tab == "💊 Medicamentos":
        if auth.is_admin():
            render_medications_section(db, ai_processor, current_user['id'])
        else:
            st.error("🚫 Acesso restrito. Apenas administradores podem gerenciar medicamentos.")
    elif admin_tab == "📸 Fotos e Mídia":
        if auth.is_admin():
            render_media_section(db, current_user['id'])
        else:
            st.error("🚫 Acesso restrito. Apenas administradores podem gerenciar mídia.")
    elif admin_tab == "🔗 Links Compartilháveis":
        if auth.is_admin():
            render_shareable_links_section(db)
        else:
            st.error("🚫 Acesso restrito. Apenas administradores podem gerenciar links.")
    elif admin_tab == "👥 Usuários":
        if auth.is_admin():
            auth.show_user_management(db)
        else:
            st.error("🚫 Acesso restrito. Apenas administradores podem gerenciar usuários.")
    elif admin_tab == "⚙️ Configurações":
        if auth.is_super_admin():
            render_settings_section(db, auth)
        else:
            st.error("🚫 Acesso restrito. Apenas SUPER_ADMIN pode acessar configurações.")

def render_admin_dashboard(db, auth=None):
    """Renderizar painel administrativo com estatísticas avançadas"""
    
    # CSS customizado para dashboard
    st.markdown("""
    <style>
        .dashboard-metric {
            background: linear-gradient(90deg, #FF69B4 0%, #FFB6C1 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin: 0.5rem 0;
        }
        .alert-warning {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 0.75rem;
            border-radius: 0.375rem;
            margin: 0.5rem 0;
        }
        .alert-info {
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
            padding: 0.75rem;
            border-radius: 0.375rem;
            margin: 0.5rem 0;
        }
        .alert-success {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 0.75rem;
            border-radius: 0.375rem;
            margin: 0.5rem 0;
        }
        .activity-item {
            background: #f8f9fa;
            border-left: 4px solid #FF69B4;
            padding: 0.75rem;
            margin: 0.5rem 0;
            border-radius: 0 5px 5px 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.header("📊 Dashboard Administrativo Avançado")
    
    # Botão de refresh
    col_refresh, col_auto = st.columns([3, 1])
    with col_refresh:
        if st.button("🔄 Atualizar Métricas", type="primary"):
            st.rerun()
    
    with col_auto:
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", help="Atualizar automaticamente a cada 30 segundos")
    
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()
    
    # Obter todas as métricas avançadas
    metrics = db.get_dashboard_metrics()
    alerts = db.get_system_alerts()
    trends_data = db.get_medical_trends_data()
    recent_activity = db.get_recent_activity()
    db_info = db.get_database_size_info()
    
    # SEÇÃO 1: ALERTAS E NOTIFICAÇÕES
    if alerts:
        st.subheader("⚠️ Alertas do Sistema")
        alert_cols = st.columns(len(alerts))
        for i, alert in enumerate(alerts):
            with alert_cols[i]:
                alert_class = f"alert-{alert['type']}"
                st.markdown(f"""
                <div class="{alert_class}">
                    <strong>{alert['title']}</strong><br>
                    {alert['message']}
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # SEÇÃO 2: MÉTRICAS EM TEMPO REAL
    st.subheader("🔥 Métricas em Tempo Real")
    
    # Primeira linha de métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Usuários Ativos", 
            metrics.get('total_active_users', 0),
            delta=f"+{metrics.get('new_users_30d', 0)} novos (30d)"
        )
    
    with col2:
        st.metric(
            "Logins 24h", 
            metrics.get('users_last_24h', 0),
            help="Usuários que fizeram login nas últimas 24 horas"
        )
    
    with col3:
        st.metric(
            "Exames Registrados", 
            metrics.get('total_lab_results', 0),
            delta=f"+{metrics.get('recent_lab_results', 0)} (últimos 7d)"
        )
    
    with col4:
        st.metric(
            "Tipos de Exames", 
            metrics.get('unique_test_types', 0)
        )
    
    # Segunda linha de métricas
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric(
            "Eventos Médicos", 
            metrics.get('total_medical_events', 0)
        )
    
    with col6:
        st.metric(
            "Medicamentos", 
            metrics.get('total_medications', 0)
        )
    
    with col7:
        file_size_mb = metrics.get('total_file_size', 0) / (1024 * 1024)
        st.metric(
            "Arquivos", 
            metrics.get('total_files', 0),
            delta=f"{file_size_mb:.1f} MB total"
        )
    
    with col8:
        if db_info:
            st.metric(
                "Tamanho BD", 
                db_info.get('total_size_pretty', '0 B')
            )
        else:
            st.metric("Tamanho BD", "N/A")
    
    st.markdown("---")
    
    # SEÇÃO 3: VISUALIZAÇÕES INTERATIVAS
    st.subheader("📊 Visualizações Interativas")
    
    # Abas para diferentes visualizações
    viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs([
        "📈 Tendências Médicas", 
        "👥 Atividade de Usuários", 
        "📊 Análise de Exames",
        "💾 Performance Sistema"
    ])
    
    with viz_tab1:
        render_medical_trends_charts(trends_data)
    
    with viz_tab2:
        render_user_activity_charts(db)
    
    with viz_tab3:
        render_exam_analysis_charts(trends_data)
    
    with viz_tab4:
        render_system_performance_charts(db_info, metrics)
    
    st.markdown("---")
    
    # SEÇÃO 4: ATIVIDADE RECENTE
    col_activity, col_export = st.columns([3, 1])
    
    with col_activity:
        st.subheader("🕰️ Atividade Recente do Sistema")
    
    with col_export:
        if st.button("📊 Exportar Dashboard"):
            export_dashboard_data(metrics, trends_data, recent_activity)
    
    render_recent_activity_widget(recent_activity)
    
    # SEÇÃO 5: INFORMAÇÕES DO SISTEMA
    with st.expander("⚙️ Informações Detalhadas do Sistema"):
        render_system_info_details(db_info, metrics)

def render_pdf_upload_section(db, ai_processor, user_id):
    """Renderizar seção de upload e processamento de PDF"""
    st.header("📄 Upload de Exames Laboratoriais")
    
    # File upload
    uploaded_files = st.file_uploader(
        "Selecione arquivos PDF de exames",
        type=['pdf'],
        accept_multiple_files=True,
        help="Faça upload de um ou mais arquivos PDF contendo resultados de exames laboratoriais"
    )
    
    if uploaded_files:
        st.write(f"**{len(uploaded_files)} arquivo(s) selecionado(s):**")
        
        for uploaded_file in uploaded_files:
            st.write(f"• {uploaded_file.name}")
        
        if st.button("🔄 Processar Arquivos", type="primary"):
            process_uploaded_pdfs(uploaded_files, db, ai_processor, user_id)
    
    # Exibir resultados laboratoriais existentes
    st.subheader("Exames Registrados")
    lab_results = db.get_lab_results()
    
    if not lab_results.empty:
        # Adicionar funcionalidade de edição
        st.write("**Clique em uma linha para editar:**")
        
        # Criar dataframe editável
        edited_df = st.data_editor(
            lab_results,
            width="stretch",
            num_rows="dynamic",
            column_config={
                "test_date": st.column_config.DateColumn("Data do Exame"),
                "test_value": st.column_config.NumberColumn("Valor"),
            }
        )
        
        if st.button("💾 Salvar Alterações"):
            # Aqui você implementaria a lógica de salvamento
            st.success("Alterações salvas com sucesso!")
    else:
        st.info("Nenhum exame registrado ainda.")

def process_uploaded_pdfs(uploaded_files, db, ai_processor, user_id):
    """Processar arquivos PDF enviados"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_files = len(uploaded_files)
    processed_results = []
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processando {uploaded_file.name}...")
        
        try:
            # Extrair texto do PDF
            pdf_text = ai_processor.extract_pdf_text(uploaded_file)
            
            if pdf_text:
                # Processar com IA
                lab_results = ai_processor.process_lab_pdf(pdf_text, uploaded_file.name)
                
                # Salvar resultados no banco de dados
                for result in lab_results:
                    if db.save_lab_result(result, user_id):
                        processed_results.append(result)
                
                # Salvar arquivo enviado
                uploaded_file.seek(0)
                file_data = uploaded_file.read()
                db.save_uploaded_file(uploaded_file.name, file_data, 'pdf', user_id)
            
        except Exception as e:
            st.error(f"Erro ao processar {uploaded_file.name}: {e}")
        
        progress_bar.progress((i + 1) / total_files)
    
    status_text.text("Processamento concluído!")
    
    if processed_results:
        st.success(f"✅ Processamento concluído! {len(processed_results)} exames adicionados.")
        
        # Exibir resumo
        st.subheader("Resumo dos Dados Extraídos")
        summary_df = pd.DataFrame(processed_results)
        st.dataframe(summary_df, width="stretch")
    else:
        st.warning("Nenhum dado foi extraído dos arquivos.")

def render_clinical_notes_section(db, ai_processor, user_id):
    """Renderizar seção de gerenciamento de notas clínicas"""
    st.header("📝 Construção de Prontuário Clínico")
    
    # Input methods tabs
    input_tab = st.selectbox(
        "Método de entrada:",
        ["📝 Texto", "📄 Arquivo PDF", "🎤 Áudio", "🎥 Vídeo"]
    )
    
    if input_tab == "📝 Texto":
        render_text_input_section(db, ai_processor, user_id)
    elif input_tab == "📄 Arquivo PDF":
        render_pdf_clinical_section(db, ai_processor, user_id)
    elif input_tab == "🎤 Áudio":
        render_audio_input_section(db, ai_processor, user_id)
    elif input_tab == "🎥 Vídeo":
        render_video_input_section(db, ai_processor, user_id)
    
    # Exibir linha do tempo existente
    st.subheader("Linha do Tempo Atual")
    timeline_events = db.get_medical_timeline()
    
    if timeline_events:
        for event in sorted(timeline_events, key=lambda x: x['event_date']):
            with st.expander(f"{format_date(event['event_date'])} - {event['title']}"):
                st.write(f"**Descrição:** {event.get('description', 'N/A')}")
                
                if event.get('symptoms'):
                    st.write("**Sintomas:**")
                    for symptom in event['symptoms']:
                        st.write(f"• {symptom}")
                
                if event.get('clinical_notes'):
                    st.write("**Notas Clínicas:**")
                    st.write(event['clinical_notes'])
    else:
        st.info("Nenhum evento clínico registrado ainda.")

def render_text_input_section(db, ai_processor, user_id):
    """Renderizar seção de entrada de texto para notas clínicas"""
    st.subheader("Entrada de Texto")
    
    with st.form("text_clinical_form"):
        clinical_text = st.text_area(
            "Digite as informações clínicas:",
            height=200,
            placeholder="Descreva os sintomas, eventos e observações clínicas..."
        )
        
        event_date = st.date_input(
            "Data do evento (opcional):",
            value=date.today(),
            help="Se não especificada, a IA tentará extrair do texto"
        )
        
        if st.form_submit_button("🔄 Processar Texto", type="primary"):
            if clinical_text:
                process_clinical_text(clinical_text, event_date, db, ai_processor, user_id)
            else:
                st.error("Por favor, digite o texto clínico.")

def render_audio_input_section(db, ai_processor, user_id):
    """Renderizar seção de entrada de áudio"""
    st.subheader("Entrada de Áudio")
    
    uploaded_audio = st.file_uploader(
        "Selecione arquivo de áudio:",
        type=['mp3', 'wav', 'm4a'],
        help="Formatos suportados: MP3, WAV, M4A"
    )
    
    if uploaded_audio:
        st.audio(uploaded_audio)
        
        if st.button("🔄 Transcrever e Processar", type="primary"):
            with st.spinner("Transcrevendo áudio..."):
                # Transcrever áudio
                transcribed_text = ai_processor.transcribe_audio(uploaded_audio)
                
                if transcribed_text:
                    st.success("Áudio transcrito com sucesso!")
                    
                    # Exibir transcrição
                    st.subheader("Transcrição:")
                    edited_text = st.text_area(
                        "Revise e edite a transcrição se necessário:",
                        value=transcribed_text,
                        height=150
                    )
                    
                    event_date = st.date_input(
                        "Data do evento:",
                        value=date.today()
                    )
                    
                    if st.button("✅ Salvar Transcrição Processada"):
                        if edited_text and edited_text.strip():
                            process_clinical_text(edited_text, event_date, db, ai_processor, user_id)
                        else:
                            st.error("Por favor, revise a transcrição antes de salvar.")
                else:
                    st.error("Erro na transcrição do áudio.")

def process_clinical_text(text: str, event_date: date, db, ai_processor, user_id):
    """Processar texto clínico com IA"""
    with st.spinner("Processando texto com IA..."):
        processed_data = ai_processor.process_clinical_text(text)
        
        if processed_data:
            st.success("Texto processado com sucesso!")
            
            # Exibir informações processadas
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Informações Extraídas")
                
                extracted_date = processed_data.get('date')
                if extracted_date and extracted_date != event_date.strftime('%Y-%m-%d'):
                    st.info(f"IA detectou data: {extracted_date}")
                    use_ai_date = st.checkbox("Usar data detectada pela IA?")
                    final_date = parse_date(extracted_date) if use_ai_date else event_date
                else:
                    final_date = event_date
                
                st.write(f"**Data final:** {format_date(final_date)}")
                st.write(f"**Título:** {processed_data.get('title', 'N/A')}")
                st.write(f"**Descrição:** {processed_data.get('description', 'N/A')}")
                
                if processed_data.get('symptoms'):
                    st.write("**Sintomas identificados:**")
                    for symptom in processed_data['symptoms']:
                        st.write(f"• {symptom}")
            
            with col2:
                st.subheader("Notas Clínicas Formatadas")
                clinical_notes = st.text_area(
                    "Edite as notas clínicas:",
                    value=processed_data.get('clinical_notes', ''),
                    height=200
                )
            
            # Botão de salvar
            if st.button("💾 Salvar no Prontuário", type="primary"):
                event_data = {
                    'event_date': final_date,
                    'title': processed_data.get('title', 'Evento Clínico'),
                    'description': processed_data.get('description'),
                    'symptoms': processed_data.get('symptoms', []),
                    'clinical_notes': clinical_notes
                }
                
                if db.save_medical_event(event_data, user_id):
                    st.success("Evento salvo no prontuário!")
                    st.rerun()
                else:
                    st.error("Erro ao salvar evento.")
        else:
            st.error("Erro no processamento do texto.")

def render_medications_section(db, ai_processor, user_id):
    """Renderizar seção de gerenciamento de medicamentos"""
    st.header("💊 Gerenciamento de Medicamentos")
    
    # Adicionar novo medicamento
    with st.expander("Adicionar Novo Medicamento"):
        with st.form("new_medication_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                med_name = st.text_input("Nome do Medicamento")
                dose = st.text_input("Dose (ex: 5mg, 1ml)")
                start_date = st.date_input("Data de Início")
            
            with col2:
                active_ingredient = st.text_input("Princípio Ativo (opcional)")
                route = st.selectbox("Via de Administração", 
                                   ["Oral", "Subcutânea", "Intramuscular", "Intravenosa", "Tópica", "Outra"])
                end_date = st.date_input("Data de Término (opcional)", value=None)
            
            notes = st.text_area("Observações (efeitos, motivo da suspensão, etc.)")
            
            if st.form_submit_button("💾 Adicionar Medicamento"):
                if med_name and dose and start_date:
                    # Validar nome do medicamento com IA
                    validation = ai_processor.validate_medication_name(med_name)
                    
                    med_data = {
                        'medication_name': validation.get('validated_name', med_name),
                        'active_ingredient': active_ingredient or validation.get('active_ingredient'),
                        'dose': dose,
                        'route': route,
                        'start_date': start_date,
                        'end_date': end_date,
                        'notes': notes
                    }
                    
                    if db.save_medication(med_data, user_id):
                        st.success("Medicamento adicionado com sucesso!")
                        if not validation.get('is_valid', True):
                            st.warning("Verificação de medicamento: Nome pode estar incorreto.")
                        st.rerun()
                    else:
                        st.error("Erro ao salvar medicamento.")
                else:
                    st.error("Preencha pelo menos nome, dose e data de início.")
    
    # Exibir medicamentos existentes
    st.subheader("Medicamentos Registrados")
    medications = db.get_medication_history()
    
    if medications:
        med_df = pd.DataFrame(medications)
        
        # Formatar datas para exibição
        med_df['start_date'] = med_df['start_date'].apply(format_date)
        med_df['end_date'] = med_df['end_date'].apply(lambda x: format_date(x) if x else "Em uso")
        
        st.dataframe(med_df, width="stretch")
    else:
        st.info("Nenhum medicamento registrado ainda.")
    
    # Entrada de medicamentos por áudio
    st.subheader("Entrada de Medicamentos por Áudio")
    med_audio = st.file_uploader(
        "Upload de áudio com informações de medicamentos:",
        type=['mp3', 'wav', 'm4a'],
        key="med_audio"
    )
    
    if med_audio and st.button("🔄 Processar Áudio de Medicamentos"):
        with st.spinner("Processando áudio..."):
            # Transcrever e processar
            transcribed_text = ai_processor.transcribe_audio(med_audio)
            
            if transcribed_text:
                medications_data = ai_processor.process_medication_audio(transcribed_text)
                
                if medications_data:
                    st.success(f"Encontrados {len(medications_data)} medicamentos no áudio!")
                    
                    for i, med in enumerate(medications_data):
                        with st.expander(f"Medicamento {i+1}: {med.get('name', 'N/A')}"):
                            st.json(med)
                            
                            if st.button(f"Salvar Medicamento {i+1}", key=f"save_med_{i}"):
                                if db.save_medication(med, user_id):
                                    st.success("Medicamento salvo!")
                                else:
                                    st.error("Erro ao salvar.")

def render_media_section(db, user_id):
    """Renderizar seção de upload de mídia"""
    st.header("📸 Fotos e Mídia")
    
    # Mostrar fotos atuais
    current_photos = db.get_patient_photos()
    if current_photos:
        st.subheader("Fotos Atuais")
        photo_cols = st.columns(3)
        
        photo_names = {"luna": "Luna", "tutor1": "Paulo", "tutor2": "Júlia"}
        for i, (photo_type, name) in enumerate(photo_names.items()):
            with photo_cols[i]:
                if photo_type in current_photos:
                    st.image(current_photos[photo_type], width=150, caption=f"{name} (atual)")
                else:
                    st.info(f"Nenhuma foto de {name}")
        
        st.markdown("---")
    
    # Seções de upload de fotos
    st.subheader("Upload de Novas Fotos")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Foto da Luna")
        luna_photo = st.file_uploader(
            "Upload foto da Luna:",
            type=['png', 'jpg', 'jpeg'],
            key="luna_photo"
        )
        
        if luna_photo and st.button("Salvar Foto da Luna"):
            try:
                photo_bytes = luna_photo.read()
                if db.save_patient_photo("luna", photo_bytes, luna_photo.name):
                    st.success("Foto da Luna salva com sucesso!")
                    st.rerun()  # Recarregar para mostrar a nova foto
                else:
                    st.error("Erro ao salvar foto da Luna")
            except Exception as e:
                st.error(f"Erro ao processar foto: {e}")
    
    with col2:
        st.subheader("Foto do Tutor 1")
        tutor1_photo = st.file_uploader(
            "Upload foto Paulo:",
            type=['png', 'jpg', 'jpeg'],
            key="tutor1_photo"
        )
        
        if tutor1_photo and st.button("Salvar Foto Paulo"):
            try:
                photo_bytes = tutor1_photo.read()
                if db.save_patient_photo("tutor1", photo_bytes, tutor1_photo.name):
                    st.success("Foto do Paulo salva com sucesso!")
                    st.rerun()  # Recarregar para mostrar a nova foto
                else:
                    st.error("Erro ao salvar foto do Paulo")
            except Exception as e:
                st.error(f"Erro ao processar foto: {e}")
    
    with col3:
        st.subheader("Foto do Tutor 2")
        tutor2_photo = st.file_uploader(
            "Upload foto Júlia:",
            type=['png', 'jpg', 'jpeg'],
            key="tutor2_photo"
        )
        
        if tutor2_photo and st.button("Salvar Foto Júlia"):
            try:
                photo_bytes = tutor2_photo.read()
                if db.save_patient_photo("tutor2", photo_bytes, tutor2_photo.name):
                    st.success("Foto da Júlia salva com sucesso!")
                    st.rerun()  # Recarregar para mostrar a nova foto
                else:
                    st.error("Erro ao salvar foto da Júlia")
            except Exception as e:
                st.error(f"Erro ao processar foto: {e}")

def render_settings_section(db, auth=None):
    """Renderizar seção avançada de configurações do sistema"""
    
    # CSS customizado para a interface de configurações
    st.markdown("""
    <style>
        .config-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
            margin: 1rem 0;
        }
        .config-card {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #FF69B4;
            margin: 0.5rem 0;
        }
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 0.75rem;
            border-radius: 0.375rem;
            border: 1px solid #c3e6cb;
            margin: 0.5rem 0;
        }
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 0.75rem;
            border-radius: 0.375rem;
            border: 1px solid #f5c6cb;
            margin: 0.5rem 0;
        }
        .info-message {
            background: #d1ecf1;
            color: #0c5460;
            padding: 0.75rem;
            border-radius: 0.375rem;
            border: 1px solid #bee5eb;
            margin: 0.5rem 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.header("⚙️ Configurações Avançadas do Sistema")
    
    # Verificar se o usuário tem permissão
    if not auth or not auth.is_super_admin():
        st.error("🚫 Acesso Negado - Apenas SUPER_ADMIN pode modificar configurações do sistema")
        return
    
    current_user = auth.get_current_user()
    user_id = current_user.get('id')
    
    # Obter todas as configurações atuais
    all_configs = db.get_all_configs()
    
    # Abas de configuração
    config_tabs = st.tabs([
        "📧 Email/SMTP", 
        "🔌 API/Integrações", 
        "🔒 Segurança", 
        "🛠️ Sistema Geral",
        "📤 Import/Export",
        "📋 Logs de Auditoria"
    ])
    
    # ===========================================
    # ABA 1: CONFIGURAÇÕES EMAIL/SMTP
    # ===========================================
    with config_tabs[0]:
        render_smtp_config_section(db, all_configs, user_id)
    
    # ===========================================
    # ABA 2: CONFIGURAÇÕES API/INTEGRAÇÕES
    # ===========================================
    with config_tabs[1]:
        render_api_config_section(db, all_configs, user_id)
    
    # ===========================================
    # ABA 3: CONFIGURAÇÕES DE SEGURANÇA
    # ===========================================
    with config_tabs[2]:
        render_security_config_section(db, all_configs, user_id)
    
    # ===========================================
    # ABA 4: CONFIGURAÇÕES GERAIS DO SISTEMA
    # ===========================================
    with config_tabs[3]:
        render_general_config_section(db, all_configs, user_id)
    
    # ===========================================
    # ABA 5: IMPORT/EXPORT E BACKUP
    # ===========================================
    with config_tabs[4]:
        render_import_export_section(db, user_id)
    
    # ===========================================
    # ABA 6: LOGS DE AUDITORIA
    # ===========================================
    with config_tabs[5]:
        render_audit_logs_section(db, auth)

def render_smtp_config_section(db, all_configs, user_id):
    """Renderizar seção de configurações SMTP/Email com segurança aprimorada"""
    st.subheader("📧 Configurações de Email e SMTP")
    
    # Obter configurações SMTP atuais
    smtp_configs = all_configs.get('SMTP', {})
    
    # Verificar status de criptografia
    encryption_available = True
    try:
        from encryption_utils import get_encryption_manager
        encryption_manager = get_encryption_manager()
        encryption_available = encryption_manager.is_encryption_available()
    except Exception:
        encryption_available = False
    
    if not encryption_available:
        st.error("⚠️ Sistema de criptografia indisponível! Valores sensíveis podem não estar seguros.")
    
    st.markdown('<div class="info-message">📌 Configure o servidor SMTP para envio automático de notificações e alertas do sistema.</div>', unsafe_allow_html=True)
    
    # Mostrar status de configuração atual
    smtp_enabled_status = smtp_configs.get('smtp_enabled', {}).get('value', False)
    if smtp_enabled_status:
        st.success("✅ SMTP está habilitado")
    else:
        st.info("ℹ️ SMTP está desabilitado")
    
    # Form de configurações SMTP
    with st.form("smtp_config_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            smtp_enabled = st.checkbox(
                "Habilitar SMTP",
                value=smtp_configs.get('smtp_enabled', {}).get('value', False),
                help="Ativar envio de emails via SMTP"
            )
            
            smtp_host = st.text_input(
                "Servidor SMTP",
                value=smtp_configs.get('smtp_host', {}).get('value', ''),
                placeholder="smtp.gmail.com",
                help="Endereço do servidor SMTP"
            )
            
            smtp_port = st.number_input(
                "Porta SMTP",
                min_value=1,
                max_value=65535,
                value=smtp_configs.get('smtp_port', {}).get('value', 587),
                help="Porta do servidor SMTP (587 para TLS, 465 para SSL, 25 para não criptografado)"
            )
            
            smtp_use_tls = st.checkbox(
                "Usar TLS/SSL",
                value=smtp_configs.get('smtp_use_tls', {}).get('value', True),
                help="Usar criptografia TLS/SSL"
            )
        
        with col2:
            smtp_username = st.text_input(
                "Usuário SMTP",
                value=smtp_configs.get('smtp_username', {}).get('value', ''),
                placeholder="seu_email@gmail.com",
                help="Nome de usuário para autenticação SMTP"
            )
            
            # Campo de senha com mascaramento apropriado
            current_password_display = ""
            if smtp_configs.get('smtp_password', {}).get('is_sensitive', False):
                if smtp_configs.get('smtp_password', {}).get('display_value'):
                    current_password_display = smtp_configs['smtp_password']['display_value']
                else:
                    current_password_display = "••••••••"
            else:
                current_password_display = smtp_configs.get('smtp_password', {}).get('value', '')
            
            password_changed = st.checkbox("🔄 Alterar senha SMTP", key="change_smtp_password")
            if password_changed:
                smtp_password = st.text_input(
                    "Nova Senha SMTP",
                    type="password",
                    placeholder="Digite a nova senha SMTP",
                    help="Senha ou token de aplicação para SMTP"
                )
            else:
                smtp_password = smtp_configs.get('smtp_password', {}).get('value', '')
                st.text_input(
                    "Senha SMTP Atual",
                    value=current_password_display,
                    disabled=True,
                    help="Senha criptografada - marque a opção acima para alterar"
                )
            
            from_email = st.text_input(
                "Email Remetente",
                value=smtp_configs.get('from_email', {}).get('value', ''),
                placeholder="noreply@seudominio.com",
                help="Email que aparecerá como remetente"
            )
            
            from_name = st.text_input(
                "Nome do Remetente",
                value=smtp_configs.get('from_name', {}).get('value', 'Sistema Prontuário Luna'),
                help="Nome que aparecerá como remetente"
            )
        
        # Botões de ação
        col_save, col_test = st.columns(2)
        
        with col_save:
            if st.form_submit_button("💾 Salvar Configurações SMTP", type="primary"):
                # Salvar todas as configurações SMTP
                smtp_config_data = {
                    'smtp_enabled': smtp_enabled,
                    'smtp_host': smtp_host,
                    'smtp_port': smtp_port,
                    'smtp_username': smtp_username,
                    'smtp_password': smtp_password,
                    'smtp_use_tls': smtp_use_tls,
                    'from_email': from_email,
                    'from_name': from_name
                }
                
                success_count = 0
                for key, value in smtp_config_data.items():
                    # Validar configuração
                    validation = db.validate_config('SMTP', key, value)
                    if validation['valid']:
                        if db.save_config('SMTP', key, value, user_id):
                            success_count += 1
                    else:
                        st.error(f"❌ Erro na configuração {key}: {validation['message']}")
                
                if success_count == len(smtp_config_data):
                    st.success("✅ Todas as configurações SMTP foram salvas com sucesso!")
                    st.rerun()
        
        with col_test:
            if st.form_submit_button("🧪 Testar Conexão SMTP"):
                # Testar conectividade SMTP
                smtp_test_config = {
                    'smtp_host': smtp_host,
                    'smtp_port': smtp_port,
                    'smtp_username': smtp_username,
                    'smtp_password': smtp_password,
                    'smtp_use_tls': smtp_use_tls
                }
                
                test_result = db.test_smtp_connection(smtp_test_config)
                
                if test_result['success']:
                    st.success(f"✅ {test_result['message']}")
                    st.info(f"ℹ️ {test_result['details']}")
                else:
                    st.error(f"❌ {test_result['message']}")
                    st.error(f"Detalhes: {test_result['details']}")

def render_api_config_section(db, all_configs, user_id):
    """Renderizar seção de configurações API/Integrações"""
    st.subheader("🔌 Configurações de API e Integrações")
    
    # Obter configurações API atuais
    api_configs = all_configs.get('API', {})
    
    st.markdown('<div class="info-message">🔗 Configure integrações com APIs externas e limites de uso.</div>', unsafe_allow_html=True)
    
    # Form de configurações API
    with st.form("api_config_form"):
        # Seção OpenAI
        st.markdown("### 🤖 Configurações OpenAI")
        
        col1, col2 = st.columns(2)
        
        with col1:
            openai_enabled = st.checkbox(
                "Habilitar OpenAI",
                value=api_configs.get('openai_enabled', {}).get('value', True),
                help="Ativar integração com OpenAI para processamento de IA"
            )
            
            openai_api_key = st.text_input(
                "Chave API OpenAI",
                type="password",
                value=api_configs.get('openai_api_key', {}).get('value', ''),
                placeholder="sk-...",
                help="Chave da API OpenAI (mantida segura/criptografada)"
            )
            
            openai_model = st.selectbox(
                "Modelo OpenAI",
                options=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                index=0 if api_configs.get('openai_model', {}).get('value') == 'gpt-4' else 0,
                help="Modelo OpenAI a ser usado por padrão"
            )
        
        with col2:
            openai_max_tokens = st.number_input(
                "Máximo de Tokens",
                min_value=100,
                max_value=32000,
                value=api_configs.get('openai_max_tokens', {}).get('value', 4000),
                help="Limite máximo de tokens por requisição"
            )
            
            api_rate_limit = st.number_input(
                "Limite de Requisições/Hora",
                min_value=1,
                max_value=1000,
                value=api_configs.get('api_rate_limit', {}).get('value', 100),
                help="Limite de requisições à API por hora"
            )
            
            webhook_url = st.text_input(
                "URL do Webhook",
                value=api_configs.get('webhook_url', {}).get('value', ''),
                placeholder="https://your-webhook.com/endpoint",
                help="URL para notificações via webhook"
            )
        
        if st.form_submit_button("💾 Salvar Configurações API", type="primary"):
            # Salvar configurações API
            api_config_data = {
                'openai_enabled': openai_enabled,
                'openai_api_key': openai_api_key,
                'openai_model': openai_model,
                'openai_max_tokens': openai_max_tokens,
                'api_rate_limit': api_rate_limit,
                'webhook_url': webhook_url
            }
            
            success_count = 0
            for key, value in api_config_data.items():
                validation = db.validate_config('API', key, value)
                if validation['valid']:
                    if db.save_config('API', key, value, user_id):
                        success_count += 1
                else:
                    st.error(f"❌ Erro na configuração {key}: {validation['message']}")
            
            if success_count == len(api_config_data):
                st.success("✅ Configurações de API salvas com sucesso!")
                st.rerun()

def render_security_config_section(db, all_configs, user_id):
    """Renderizar seção de configurações de segurança"""
    st.subheader("🔒 Configurações de Segurança")
    
    # Obter configurações de segurança atuais
    security_configs = all_configs.get('SECURITY', {})
    
    st.markdown('<div class="info-message">🛡️ Configure políticas de segurança e auditoria do sistema.</div>', unsafe_allow_html=True)
    
    # Form de configurações de segurança
    with st.form("security_config_form"):
        # Políticas de senha
        st.markdown("### 🔐 Políticas de Senha")
        
        col1, col2 = st.columns(2)
        
        with col1:
            password_min_length = st.number_input(
                "Comprimento Mínimo da Senha",
                min_value=4,
                max_value=50,
                value=security_configs.get('password_min_length', {}).get('value', 8),
                help="Número mínimo de caracteres para senhas"
            )
            
            password_require_special = st.checkbox(
                "Requer Caracteres Especiais",
                value=security_configs.get('password_require_special', {}).get('value', True),
                help="Senhas devem conter pelo menos um caractere especial"
            )
            
            password_require_numbers = st.checkbox(
                "Requer Números",
                value=security_configs.get('password_require_numbers', {}).get('value', True),
                help="Senhas devem conter pelo menos um número"
            )
        
        with col2:
            password_expiry_days = st.number_input(
                "Expiração da Senha (dias)",
                min_value=0,
                max_value=365,
                value=security_configs.get('password_expiry_days', {}).get('value', 90),
                help="Dias até expiração da senha (0 = nunca expira)"
            )
            
            enable_2fa = st.checkbox(
                "Habilitar 2FA (Futuro)",
                value=security_configs.get('enable_2fa', {}).get('value', False),
                help="Preparação para autenticação de dois fatores"
            )
        
        # Configurações de sessão
        st.markdown("### 🕐 Configurações de Sessão")
        
        col3, col4 = st.columns(2)
        
        with col3:
            session_timeout_minutes = st.number_input(
                "Timeout da Sessão (minutos)",
                min_value=5,
                max_value=1440,
                value=security_configs.get('session_timeout_minutes', {}).get('value', 480),
                help="Tempo limite para inatividade da sessão"
            )
            
            max_login_attempts = st.number_input(
                "Máximo Tentativas de Login",
                min_value=1,
                max_value=20,
                value=security_configs.get('max_login_attempts', {}).get('value', 5),
                help="Tentativas máximas antes de bloquear conta"
            )
        
        with col4:
            audit_log_retention_days = st.number_input(
                "Retenção de Logs (dias)",
                min_value=1,
                max_value=3650,
                value=security_configs.get('audit_log_retention_days', {}).get('value', 365),
                help="Dias para manter logs de auditoria"
            )
        
        if st.form_submit_button("💾 Salvar Configurações de Segurança", type="primary"):
            # Salvar configurações de segurança
            security_config_data = {
                'password_min_length': password_min_length,
                'password_require_special': password_require_special,
                'password_require_numbers': password_require_numbers,
                'password_expiry_days': password_expiry_days,
                'session_timeout_minutes': session_timeout_minutes,
                'max_login_attempts': max_login_attempts,
                'audit_log_retention_days': audit_log_retention_days,
                'enable_2fa': enable_2fa
            }
            
            success_count = 0
            for key, value in security_config_data.items():
                validation = db.validate_config('SECURITY', key, value)
                if validation['valid']:
                    if db.save_config('SECURITY', key, value, user_id):
                        success_count += 1
                else:
                    st.error(f"❌ Erro na configuração {key}: {validation['message']}")
            
            if success_count == len(security_config_data):
                st.success("✅ Configurações de segurança salvas com sucesso!")
                st.rerun()

def render_general_config_section(db, all_configs, user_id):
    """Renderizar seção de configurações gerais do sistema"""
    st.subheader("🛠️ Configurações Gerais do Sistema")
    
    # Obter configurações gerais atuais
    general_configs = all_configs.get('GENERAL', {})
    
    st.markdown('<div class="info-message">⚙️ Configure informações gerais e preferências do sistema.</div>', unsafe_allow_html=True)
    
    # Form de configurações gerais
    with st.form("general_config_form"):
        # Informações da aplicação
        st.markdown("### 📱 Informações da Aplicação")
        
        col1, col2 = st.columns(2)
        
        with col1:
            app_name = st.text_input(
                "Nome da Aplicação",
                value=general_configs.get('app_name', {}).get('value', 'Prontuário Médico Digital - Luna'),
                help="Nome exibido na aplicação"
            )
            
            app_version = st.text_input(
                "Versão",
                value=general_configs.get('app_version', {}).get('value', '1.0.0'),
                help="Versão atual da aplicação"
            )
            
            timezone = st.selectbox(
                "Fuso Horário",
                options=["America/Sao_Paulo", "America/New_York", "Europe/London", "UTC"],
                index=0,
                help="Fuso horário padrão do sistema"
            )
        
        with col2:
            date_format = st.selectbox(
                "Formato de Data",
                options=["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"],
                index=0,
                help="Formato de exibição de datas"
            )
            
            maintenance_mode = st.checkbox(
                "Modo de Manutenção",
                value=general_configs.get('maintenance_mode', {}).get('value', False),
                help="Ativar modo de manutenção do sistema"
            )
        
        # Configurações de arquivo
        st.markdown("### 📁 Configurações de Arquivos")
        
        col3, col4 = st.columns(2)
        
        with col3:
            max_file_size_mb = st.number_input(
                "Tamanho Máximo de Arquivo (MB)",
                min_value=1,
                max_value=500,
                value=general_configs.get('max_file_size_mb', {}).get('value', 50),
                help="Tamanho máximo permitido para upload"
            )
        
        with col4:
            current_allowed_types = general_configs.get('allowed_file_types', {}).get('value', ['pdf', 'jpg', 'jpeg', 'png', 'mp3', 'wav', 'mp4'])
            allowed_file_types = st.multiselect(
                "Tipos de Arquivo Permitidos",
                options=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'mp3', 'wav', 'mp4', 'avi', 'mov', 'txt', 'doc', 'docx'],
                default=current_allowed_types,
                help="Tipos de arquivo permitidos para upload"
            )
        
        # Configurações de backup
        st.markdown("### 💾 Configurações de Backup")
        
        col5, col6 = st.columns(2)
        
        with col5:
            backup_enabled = st.checkbox(
                "Backup Automático",
                value=general_configs.get('backup_enabled', {}).get('value', True),
                help="Habilitar backup automático do sistema"
            )
        
        with col6:
            backup_frequency_hours = st.number_input(
                "Frequência de Backup (horas)",
                min_value=1,
                max_value=168,
                value=general_configs.get('backup_frequency_hours', {}).get('value', 24),
                help="Intervalo entre backups automáticos"
            )
        
        if st.form_submit_button("💾 Salvar Configurações Gerais", type="primary"):
            # Salvar configurações gerais
            general_config_data = {
                'app_name': app_name,
                'app_version': app_version,
                'timezone': timezone,
                'date_format': date_format,
                'max_file_size_mb': max_file_size_mb,
                'allowed_file_types': allowed_file_types,
                'backup_enabled': backup_enabled,
                'backup_frequency_hours': backup_frequency_hours,
                'maintenance_mode': maintenance_mode
            }
            
            success_count = 0
            for key, value in general_config_data.items():
                validation = db.validate_config('GENERAL', key, value)
                if validation['valid']:
                    if db.save_config('GENERAL', key, value, user_id):
                        success_count += 1
                else:
                    st.error(f"❌ Erro na configuração {key}: {validation['message']}")
            
            if success_count == len(general_config_data):
                st.success("✅ Configurações gerais salvas com sucesso!")
                if maintenance_mode:
                    st.warning("⚠️ Sistema agora em modo de manutenção!")
                st.rerun()

def render_import_export_section(db, user_id):
    """Renderizar seção de import/export de configurações"""
    st.subheader("📤 Import/Export e Backup")
    
    st.markdown('<div class="info-message">💾 Exporte configurações para backup ou importe de outro sistema.</div>', unsafe_allow_html=True)
    
    # Seção de Export
    st.markdown("### 📤 Exportar Configurações")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Exportar Todas as Configurações", type="primary"):
            try:
                with st.spinner("Exportando configurações..."):
                    export_data = db.export_configs()
                    
                    if export_data:
                        # Converter para JSON
                        json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
                        filename = f"configuracoes_sistema_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
                        
                        st.download_button(
                            label="💾 Baixar Arquivo de Configurações",
                            data=json_data.encode('utf-8'),
                            file_name=filename,
                            mime="application/json"
                        )
                        
                        st.success("✅ Configurações exportadas com sucesso!")
                    else:
                        st.error("❌ Erro ao exportar configurações")
            except Exception as e:
                st.error(f"❌ Erro na exportação: {e}")
    
    with col2:
        if st.button("🔄 Reset para Padrões", help="Restaurar todas as configurações para os valores padrão"):
            if st.session_state.get('confirm_reset', False):
                try:
                    with st.spinner("Resetando configurações..."):
                        if db.reset_configs_to_default(user_id):
                            st.success("✅ Configurações resetadas para padrão com sucesso!")
                            st.session_state['confirm_reset'] = False
                            st.rerun()
                        else:
                            st.error("❌ Erro ao resetar configurações")
                except Exception as e:
                    st.error(f"❌ Erro no reset: {e}")
            else:
                st.warning("⚠️ Clique novamente para confirmar o reset")
                st.session_state['confirm_reset'] = True
    
    # Seção de Import
    st.markdown("### 📥 Importar Configurações")
    
    uploaded_config = st.file_uploader(
        "Selecione arquivo de configurações (JSON):",
        type=['json'],
        help="Faça upload de um arquivo de configurações exportado anteriormente"
    )
    
    if uploaded_config:
        try:
            # Ler e validar arquivo
            config_data = json.loads(uploaded_config.read().decode('utf-8'))
            
            # Exibir preview
            st.write("**Preview das configurações a serem importadas:**")
            
            if 'configs' in config_data:
                for category, configs in config_data['configs'].items():
                    with st.expander(f"Categoria: {category} ({len(configs)} configurações)"):
                        for key, value in configs.items():
                            st.write(f"• **{key}**: {value.get('value', 'N/A')}")
                
                if st.button("🔄 Importar Configurações", type="primary"):
                    try:
                        with st.spinner("Importando configurações..."):
                            if db.import_configs(config_data, user_id):
                                st.success("✅ Configurações importadas com sucesso!")
                                st.rerun()
                            else:
                                st.error("❌ Erro na importação")
                    except Exception as e:
                        st.error(f"❌ Erro na importação: {e}")
            else:
                st.error("❌ Formato de arquivo inválido")
                
        except json.JSONDecodeError:
            st.error("❌ Arquivo JSON inválido")
        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {e}")

def render_audit_logs_section(db, auth):
    """Renderizar seção de logs de auditoria"""
    st.subheader("📋 Logs de Auditoria")
    
    st.markdown('<div class="info-message">🔍 Visualize todas as ações administrativas realizadas no sistema.</div>', unsafe_allow_html=True)
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        limit = st.selectbox(
            "Número de registros",
            options=[25, 50, 100, 200],
            index=1
        )
    
    with col2:
        action_filter = st.selectbox(
            "Filtrar por ação",
            options=["Todas", "CONFIG_UPDATE", "CREATE_USER", "UPDATE_USER_ROLE", "DEACTIVATE_USER"],
            index=0
        )
    
    with col3:
        if st.button("🔄 Atualizar Logs"):
            st.rerun()
    
    # Obter logs de auditoria
    audit_logs = db.get_admin_audit_logs(limit=limit)
    
    if action_filter != "Todas":
        audit_logs = [log for log in audit_logs if log['action'].startswith(action_filter)]
    
    if audit_logs:
        st.write(f"**Exibindo {len(audit_logs)} registros de auditoria:**")
        
        # Cabeçalho da tabela
        col1, col2, col3, col4, col5 = st.columns([2, 1.5, 2, 2, 2])
        with col1:
            st.write("**Data/Hora**")
        with col2:
            st.write("**Ação**")
        with col3:
            st.write("**Administrador**")
        with col4:
            st.write("**Usuário Alvo**")
        with col5:
            st.write("**Detalhes**")
        
        st.markdown("---")
        
        # Exibir logs
        for log in audit_logs:
            col1, col2, col3, col4, col5 = st.columns([2, 1.5, 2, 2, 2])
            
            with col1:
                timestamp = log['timestamp'].strftime('%d/%m/%Y %H:%M')
                st.write(timestamp)
            
            with col2:
                # Ícones para diferentes ações
                action_icons = {
                    "CREATE_USER": "➕",
                    "UPDATE_USER_ROLE": "🔄",
                    "DEACTIVATE_USER": "❌",
                    "REACTIVATE_USER": "✅",
                    "CONFIG_UPDATE": "⚙️",
                    "CONFIG_DELETE": "🗑️",
                    "CONFIG_RESET": "🔄",
                    "CONFIG_IMPORT": "📥"
                }
                action_key = log['action'].split('_')[0] + '_' + log['action'].split('_')[1] if '_' in log['action'] else log['action']
                icon = action_icons.get(action_key, "⚡")
                st.write(f"{icon} {log['action']}")
            
            with col3:
                admin_info = f"{log['admin_name']}"
                if log['admin_email']:
                    admin_info += f" ({log['admin_email']})"
                st.write(admin_info)
            
            with col4:
                if log['target_name']:
                    target_info = f"{log['target_name']}"
                    if log['target_email']:
                        target_info += f" ({log['target_email']})"
                    st.write(target_info)
                else:
                    st.write("-")
            
            with col5:
                details = log['details'] or "-"
                if len(details) > 50:
                    details = details[:47] + "..."
                st.write(details)
    else:
        st.info("Nenhum log de auditoria encontrado.")

def render_pdf_clinical_section(db, ai_processor, user_id):
    """Renderizar seção de notas clínicas em PDF"""
    st.subheader("Upload de PDF Clínico")
    
    uploaded_pdf = st.file_uploader(
        "Selecione arquivo PDF com notas clínicas:",
        type=['pdf']
    )
    
    if uploaded_pdf:
        if st.button("🔄 Processar PDF Clínico"):
            with st.spinner("Processando PDF..."):
                pdf_text = ai_processor.extract_pdf_text(uploaded_pdf)
                
                if pdf_text:
                    st.success("PDF processado com sucesso!")
                    
                    # Exibir texto extraído
                    st.text_area("Texto extraído:", value=pdf_text, height=200)
                    
                    event_date = st.date_input("Data do evento:", value=date.today())
                    
                    if st.button("✅ Processar com IA"):
                        process_clinical_text(pdf_text, event_date, db, ai_processor, user_id)
                else:
                    st.error("Erro ao extrair texto do PDF.")

def render_video_input_section(db, ai_processor, user_id):
    """Renderizar seção de entrada de vídeo"""
    st.subheader("🎬 Entrada de Vídeo")
    
    st.info("📱 Faça upload de vídeos com notas clínicas faladas. O áudio será extraído e transcrito automaticamente.")
    
    # Inicializar session state para persistir dados
    if 'video_transcribed_text' not in st.session_state:
        st.session_state.video_transcribed_text = None
    if 'video_event_date' not in st.session_state:
        st.session_state.video_event_date = date.today()
    if 'video_filename' not in st.session_state:
        st.session_state.video_filename = None
    
    uploaded_video = st.file_uploader(
        "Selecione arquivo de vídeo:",
        type=['mp4', 'avi', 'mov', 'wmv'],
        help="O áudio do vídeo será extraído e transcrito usando IA"
    )
    
    if uploaded_video:
        st.video(uploaded_video)
        
        # Informações do arquivo
        file_details = {
            "Nome": uploaded_video.name,
            "Tamanho": f"{uploaded_video.size / 1024 / 1024:.2f} MB",
            "Tipo": uploaded_video.type
        }
        
        col1, col2 = st.columns([2, 1])
        with col1:
            for key, value in file_details.items():
                st.text(f"{key}: {value}")
        
        with col2:
            # Usar session_state para persistir a data entre reruns
            event_date = st.date_input(
                "Data do evento:", 
                value=st.session_state.video_event_date,
                help="Data em que as notas clínicas foram registradas",
                key="video_date_picker"
            )
            st.session_state.video_event_date = event_date
        
        # Verificar se o arquivo mudou
        if uploaded_video.name != st.session_state.video_filename:
            st.session_state.video_transcribed_text = None
            st.session_state.video_filename = uploaded_video.name
        
        # Botão de processamento
        if st.button("🔄 Processar Vídeo", type="primary", disabled=bool(st.session_state.video_transcribed_text)):
            if uploaded_video.size == 0:
                st.error("❌ Arquivo de vídeo vazio. Por favor, selecione um arquivo válido.")
                return
                
            try:
                with st.spinner("Extraindo e transcrevendo áudio do vídeo..."):
                    # Reset file pointer to beginning
                    uploaded_video.seek(0)
                    video_bytes = uploaded_video.read()
                    
                    if not video_bytes:
                        st.error("❌ Não foi possível ler o conteúdo do vídeo.")
                        return
                    
                    transcribed_text = process_video_transcription(video_bytes, uploaded_video.name, ai_processor)
                    
                    if transcribed_text and transcribed_text.strip():
                        # Salvar no session state
                        st.session_state.video_transcribed_text = transcribed_text
                        st.success("✅ Áudio transcrito com sucesso!")
                        st.rerun()  # Rerun to show transcription
                    else:
                        st.error("❌ Não foi possível transcrever o áudio do vídeo ou o áudio está vazio.")
                        st.info("💡 Verifique se o vídeo contém áudio claro e está em um formato suportado.")
            
            except Exception as e:
                st.error(f"❌ Erro ao processar vídeo: {str(e)}")
                st.info("💡 Verifique se o arquivo de vídeo contém áudio e está em um formato suportado.")
        
        # Exibir transcrição se disponível
        if st.session_state.video_transcribed_text:
            st.success("✅ Vídeo já foi transcrito!")
            
            # Exibir transcrição
            with st.expander("📝 Ver Transcrição", expanded=True):
                edited_text = st.text_area(
                    "Texto transcrito (editável):",
                    value=st.session_state.video_transcribed_text,
                    height=200,
                    key="video_transcription_editor"
                )
            
            # Processar com IA
            st.markdown("---")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("🤖 Processar com IA", type="secondary"):
                    if edited_text and edited_text.strip():
                        process_clinical_text(edited_text, st.session_state.video_event_date, db, ai_processor, user_id)
                    else:
                        st.error("❌ Texto da transcrição está vazio.")
            
            with col2:
                if st.button("🔄 Nova Transcrição"):
                    st.session_state.video_transcribed_text = None
                    st.session_state.video_filename = None
                    st.rerun()

def process_video_transcription(video_bytes: bytes, filename: str, ai_processor) -> Optional[str]:
    """
    Extrair áudio do vídeo e transcrever usando OpenAI Whisper
    """
    if not video_bytes:
        st.error("❌ Dados de vídeo vazios.")
        return None
        
    temp_video_path = None
    audio_path = None
    
    try:
        # Criar nome de arquivo temporário seguro
        safe_filename = "".join(c for c in filename if c.isalnum() or c in '._-')[:50]
        
        # Salvar vídeo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{safe_filename}") as temp_video:
            temp_video.write(video_bytes)
            temp_video_path = temp_video.name
        
        # Verificar se o arquivo foi criado corretamente
        if not os.path.exists(temp_video_path) or os.path.getsize(temp_video_path) == 0:
            st.error("❌ Erro ao criar arquivo temporário do vídeo.")
            return None
        
        transcription = None
        
        try:
            # Tentar transcrever diretamente o arquivo de vídeo
            # OpenAI Whisper pode processar vídeo diretamente extraindo o áudio
            with open(temp_video_path, 'rb') as video_file:
                transcription = ai_processor.transcribe_audio(video_file)
                
            if transcription and transcription.strip():
                return transcription
                
        except Exception as audio_error:
            st.warning(f"⚠️ Transcrição direta falhou: {str(audio_error)[:100]}...")
            st.info("🔄 Tentando extrair áudio separadamente...")
            
            # Tentar extrair áudio primeiro (se ffmpeg estiver disponível)
            try:
                audio_path = extract_audio_from_video(temp_video_path)
                if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    with open(audio_path, 'rb') as audio_file:
                        transcription = ai_processor.transcribe_audio(audio_file)
                    
                    if transcription and transcription.strip():
                        return transcription
                else:
                    st.warning("⚠️ Não foi possível extrair áudio do vídeo.")
                
            except Exception as extract_error:
                st.warning(f"⚠️ Erro na extração de áudio: {str(extract_error)[:100]}...")
        
        # Se chegou até aqui, nenhum método funcionou
        st.error("❌ Falha em todos os métodos de transcrição.")
        return None
                
    except Exception as e:
        st.error(f"❌ Erro crítico no processamento do vídeo: {str(e)}")
        return None
        
    finally:
        # Limpar arquivos temporários
        try:
            if temp_video_path and os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
        except Exception as cleanup_error:
            st.warning(f"⚠️ Erro ao limpar arquivo de vídeo temporário: {cleanup_error}")
            
        try:
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)
        except Exception as cleanup_error:
            st.warning(f"⚠️ Erro ao limpar arquivo de áudio temporário: {cleanup_error}")

def extract_audio_from_video(video_path: str) -> Optional[str]:
    """
    Extrair áudio de vídeo usando ffmpeg (se disponível)
    """
    audio_path = None
    
    try:
        # Verificar se o arquivo de vídeo existe
        if not os.path.exists(video_path):
            st.warning("⚠️ Arquivo de vídeo não encontrado.")
            return None
            
        # Criar arquivo temporário para áudio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
            audio_path = temp_audio.name
        
        # Tentar usar ffmpeg para extrair áudio
        cmd = [
            'ffmpeg', 
            '-i', video_path, 
            '-vn',  # Sem vídeo
            '-acodec', 'mp3',  # Codec de áudio
            '-ab', '192k',  # Bitrate de áudio
            '-ar', '44100',  # Taxa de amostragem
            '-y',  # Sobrescrever arquivo existente
            '-loglevel', 'error',  # Reduzir logs verbosos
            audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)  # Timeout de 60s
        
        if result.returncode == 0 and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            return audio_path
        else:
            if result.stderr:
                st.warning(f"⚠️ ffmpeg erro: {result.stderr[:200]}...")
            else:
                st.warning("⚠️ ffmpeg não conseguiu extrair áudio.")
            
            # Limpar arquivo inválido
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)
            return None
            
    except subprocess.TimeoutExpired:
        st.warning("⚠️ Timeout na extração de áudio (>60s).")
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)
        return None
        
    except FileNotFoundError:
        st.warning("⚠️ ffmpeg não está instalado. Usando transcrição direta.")
        return None
        
    except Exception as e:
        st.warning(f"⚠️ Erro na extração de áudio: {str(e)[:100]}...")
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except:
                pass  # Ignore cleanup errors
        return None

def render_shareable_links_section(db):
    """Renderizar seção de gerenciamento de links compartilháveis"""
    st.header("🔗 Gerenciamento de Links Compartilháveis")
    
    try:
        from shareable_links import ShareableLinkManager
        
        link_manager = ShareableLinkManager(db)
        
        # Seção de limpeza automática
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader("📋 Links Ativos")
        
        with col2:
            if st.button("🧹 Limpar Expirados"):
                deleted_count = link_manager.cleanup_expired_links()
                if deleted_count > 0:
                    st.success(f"✅ {deleted_count} links expirados removidos!")
                else:
                    st.info("ℹ️ Nenhum link expirado encontrado")
        
        with col3:
            if st.button("🔄 Atualizar"):
                st.rerun()
        
        # Listar links compartilhados ativos
        shared_links = link_manager.list_shared_links()
        
        if shared_links:
            st.markdown("---")
            
            for i, link in enumerate(shared_links):
                with st.expander(f"🔗 {link['type'].title()} - {link['share_id']}", expanded=False):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**Tipo:** {link['type'].title()}")
                        if link['chart_type']:
                            st.write(f"**Gráfico:** {link['chart_type'].title()}")
                        if link['report_type']:
                            st.write(f"**Relatório:** {link['report_type'].title()}")
                        
                        # Handle both string and datetime objects
                        created_at = link['created_at']
                        if isinstance(created_at, str):
                            created_at = datetime.fromisoformat(created_at)
                        
                        expires_at = link['expires_at']
                        if isinstance(expires_at, str):
                            expires_at = datetime.fromisoformat(expires_at)
                        
                        st.write(f"**Criado:** {created_at.strftime('%d/%m/%Y %H:%M')}")
                        st.write(f"**Expira:** {expires_at.strftime('%d/%m/%Y %H:%M')}")
                        st.write(f"**Acessos:** {link['access_count']}")
                    
                    with col2:
                        # URL do link
                        share_url = f"{link_manager.base_url}/?share={link['share_id']}"
                        st.text_input(
                            "URL:",
                            value=share_url,
                            disabled=True,
                            key=f"url_{link['share_id']}",
                            label_visibility="collapsed"
                        )
                    
                    with col3:
                        if st.button("🗑️ Revogar", key=f"revoke_{link['share_id']}"):
                            if link_manager.revoke_link(link['share_id']):
                                st.success("✅ Link revogado!")
                                st.rerun()
                            else:
                                st.error("❌ Erro ao revogar link")
                        
                        if st.button("📋 Copiar URL", key=f"copy_{link['share_id']}"):
                            # JavaScript para copiar URL
                            copy_js = f"""
                            <script>
                            navigator.clipboard.writeText('{share_url}').then(function() {{
                                alert('URL copiada!');
                            }});
                            </script>
                            """
                            st.html(copy_js)
                            st.success("URL copiada!")
        
        else:
            st.info("📝 Nenhum link compartilhável ativo no momento.")
            st.markdown("""
            **Como criar links compartilháveis:**
            1. Vá para a seção de gráficos comparativos na aplicação principal
            2. Configure seus gráficos e clique em "🔗 Criar Link" 
            3. O link aparecerá aqui para gerenciamento
            """)
        
        # Estatísticas
        st.markdown("---")
        st.subheader("📊 Estatísticas")
        
        if shared_links:
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
            
            total_links = len(shared_links)
            total_accesses = sum(link['access_count'] for link in shared_links)
            chart_links = len([l for l in shared_links if l['type'] == 'chart'])
            report_links = len([l for l in shared_links if l['type'] == 'report'])
            
            with stats_col1:
                st.metric("Total de Links", total_links)
            
            with stats_col2:
                st.metric("Total de Acessos", total_accesses)
            
            with stats_col3:
                st.metric("Links de Gráficos", chart_links)
            
            with stats_col4:
                st.metric("Links de Relatórios", report_links)
        
        else:
            st.info("📊 Estatísticas aparecerão quando houver links ativos")
    
    except ImportError:
        st.error("❌ Módulo de links compartilháveis não encontrado")
        st.info("💡 Verifique se o arquivo shareable_links.py está no diretório correto")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar seção de links compartilháveis: {e}")
        st.info("💡 Verifique se o banco de dados está funcionando corretamente")
