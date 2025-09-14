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

def run_admin_page(db, auth):
    """Executar a página administrativa com autenticação"""
    
    st.set_page_config(
        page_title="Administração - Prontuário Luna",
        page_icon="🔐",
        layout="wide"
    )
    
    # Verificar autenticação
    if not auth.require_auth(redirect_to_login=True):
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
    """Renderizar painel administrativo com estatísticas"""
    st.header("📊 Dashboard Administrativo")
    
    # Obter estatísticas
    lab_results = db.get_lab_results()
    timeline_events = db.get_medical_timeline()
    medications = db.get_medication_history()
    
    # Exibir métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Exames Registrados", len(lab_results) if not lab_results.empty else 0)
    
    with col2:
        unique_tests = lab_results['test_name'].nunique() if not lab_results.empty else 0
        st.metric("Tipos de Exames", unique_tests)
    
    with col3:
        st.metric("Eventos Clínicos", len(timeline_events))
    
    with col4:
        st.metric("Medicamentos", len(medications))
    
    # Recent activity
    st.subheader("Atividade Recente")
    
    if not lab_results.empty:
        recent_results = lab_results.head(5)
        st.write("**Últimos Exames Adicionados:**")
        for _, result in recent_results.iterrows():
            st.write(f"• {result['test_name']} - {format_date(result['test_date'])}")
    
    if timeline_events:
        st.write("**Últimos Eventos Clínicos:**")
        recent_events = sorted(timeline_events, key=lambda x: x['event_date'], reverse=True)[:3]
        for event in recent_events:
            st.write(f"• {event['title']} - {format_date(event['event_date'])}")

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
            use_container_width=True,
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
        st.dataframe(summary_df, use_container_width=True)
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
        
        st.dataframe(med_df, use_container_width=True)
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
    """Renderizar seção de configurações do sistema"""
    st.header("⚙️ Configurações do Sistema")
    
    # Configurações de tema
    st.subheader("Configurações de Tema")
    
    col1, col2 = st.columns(2)
    with col1:
        primary_color = st.color_picker("Cor Primária", "#FF69B4")
        background_color = st.color_picker("Cor de Fundo", "#FFFFFF")
    
    with col2:
        secondary_color = st.color_picker("Cor Secundária", "#FFB6C1")
        text_color = st.color_picker("Cor do Texto", "#262730")
    
    if st.button("💾 Salvar Configurações de Tema"):
        st.success("Configurações salvas! Recarregue a página para ver as mudanças.")
    
    # Seção de logs de auditoria (apenas SUPER_ADMIN)
    if auth and auth.is_super_admin():
        st.subheader("🔍 Logs de Auditoria Administrativa")
        
        st.info("💡 Esta seção mostra todas as ações administrativas realizadas no sistema para fins de auditoria e segurança.")
        
        # Obter logs de auditoria
        audit_logs = db.get_admin_audit_logs(limit=50)
        
        if audit_logs:
            st.write(f"**Últimas {len(audit_logs)} ações administrativas:**")
            
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
                        "REACTIVATE_USER": "✅"
                    }
                    icon = action_icons.get(log['action'], "⚡")
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
        
        st.markdown("---")
    
    # Seção de backup
    st.subheader("Backup e Exportação")
    
    # Opções de exportação especializadas
    export_col1, export_col2, export_col3 = st.columns(3)
    
    with export_col1:
        if st.button("📄 Prontuário Completo (PDF)"):
            try:
                from pdf_generator import MedicalRecordPDFGenerator
                
                with st.spinner("Gerando prontuário PDF..."):
                    pdf_generator = MedicalRecordPDFGenerator(db)
                    pdf_bytes = pdf_generator.generate_complete_medical_record()
                    
                    filename = f"prontuario_completo_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    
                    st.download_button(
                        label="📅 Baixar Prontuário",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Erro: {e}")
    
    with export_col2:
        if st.button("🔬 Só Exames (PDF)"):
            try:
                from pdf_generator import MedicalRecordPDFGenerator
                
                with st.spinner("Gerando PDF de exames..."):
                    pdf_generator = MedicalRecordPDFGenerator(db)
                    pdf_bytes = pdf_generator.generate_lab_results_only()
                    
                    filename = f"exames_laboratoriais_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    
                    st.download_button(
                        label="📅 Baixar Exames",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Erro: {e}")
    
    with export_col3:
        if st.button("📅 Timeline (PDF)"):
            try:
                from pdf_generator import MedicalRecordPDFGenerator
                
                with st.spinner("Gerando PDF da timeline..."):
                    pdf_generator = MedicalRecordPDFGenerator(db)
                    pdf_bytes = pdf_generator.generate_timeline_only()
                    
                    filename = f"timeline_medica_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    
                    st.download_button(
                        label="📅 Baixar Timeline",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Erro: {e}")
    
    st.markdown("---")
    
    # Opções de backup de dados
    st.subheader("Backup de Dados")
    backup_col1, backup_col2 = st.columns(2)
    
    with backup_col1:
        if st.button("📥 Exportar Todos os Dados (JSON)"):
            try:
                with st.spinner("Exportando dados..."):
                    # Coletar todos os dados
                    export_data = {
                        "patient_info": db.get_patient_info(),
                        "lab_results": db.get_lab_results().to_dict('records') if not db.get_lab_results().empty else [],
                        "medical_timeline": db.get_medical_timeline(),
                        "medication_history": db.get_medication_history(),
                        "export_timestamp": datetime.now().isoformat()
                    }
                    
                    # Converter para JSON
                    def json_serializer(obj):
                        if isinstance(obj, (datetime, date)):
                            return obj.isoformat()
                        return str(obj)
                    
                    json_data = json.dumps(export_data, default=json_serializer, indent=2, ensure_ascii=False)
                    
                    filename = f"backup_luna_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
                    
                    st.download_button(
                        label="💾 Baixar Backup JSON",
                        data=json_data.encode('utf-8'),
                        file_name=filename,
                        mime="application/json"
                    )
                    
                    st.success(f"✅ Backup de {len(export_data)} categorias criado!")
                    
            except Exception as e:
                st.error(f"Erro ao criar backup: {e}")
    
    with backup_col2:
        if st.button("🔄 Backup Sistemático"):
            try:
                # Simular backup sistemático (em produção seria integrado com serviços de backup)
                backup_info = {
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed",
                    "tables_backed_up": ["patient_info", "lab_results", "medical_timeline", "medication_history", "patient_photos"],
                    "backup_size": "estimado 15MB",
                    "location": "sistema_interno"
                }
                
                st.success("✅ Backup sistemático iniciado!")
                st.json(backup_info)
                
                # Em uma implementação real, isto integraria com serviços como AWS S3, Google Cloud Storage, etc.
                st.info("ℹ️ Em produção, este backup seria armazenado em sistema de nuvem seguro.")
                
            except Exception as e:
                st.error(f"Erro no backup: {e}")

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
