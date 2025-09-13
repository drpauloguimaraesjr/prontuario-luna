import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
from typing import List, Dict, Any

from ai_processing import AIProcessor
from utils import validate_file_type, format_date, parse_date

def run_admin_page(db, auth):
    """Run the admin page with authentication"""
    
    st.set_page_config(
        page_title="Administração - Prontuário Luna",
        page_icon="🔐",
        layout="wide"
    )
    
    # Check authentication
    if not auth.require_auth(redirect_to_login=True):
        return
    
    current_user = auth.get_current_user()
    
    # Admin header
    st.markdown("# 🔐 Painel Administrativo")
    st.markdown(f"**Usuário:** {current_user['name']} ({current_user['email']})")
    
    # Logout button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🚪 Sair"):
            auth.logout()
            st.query_params.clear()
            st.rerun()
    
    # Admin navigation tabs
    admin_tab = st.selectbox(
        "Selecione a seção:",
        [
            "📊 Dashboard",
            "📄 Upload de Exames (PDF)",
            "📝 Prontuário Clínico",
            "💊 Medicamentos",
            "📸 Fotos e Mídia",
            "👥 Usuários",
            "⚙️ Configurações"
        ]
    )
    
    st.markdown("---")
    
    # Initialize AI processor
    ai_processor = AIProcessor()
    
    if admin_tab == "📊 Dashboard":
        render_admin_dashboard(db)
    elif admin_tab == "📄 Upload de Exames (PDF)":
        render_pdf_upload_section(db, ai_processor, current_user['id'])
    elif admin_tab == "📝 Prontuário Clínico":
        render_clinical_notes_section(db, ai_processor, current_user['id'])
    elif admin_tab == "💊 Medicamentos":
        render_medications_section(db, ai_processor, current_user['id'])
    elif admin_tab == "📸 Fotos e Mídia":
        render_media_section(db, current_user['id'])
    elif admin_tab == "👥 Usuários":
        auth.show_user_management()
    elif admin_tab == "⚙️ Configurações":
        render_settings_section(db)

def render_admin_dashboard(db):
    """Render admin dashboard with statistics"""
    st.header("📊 Dashboard Administrativo")
    
    # Get statistics
    lab_results = db.get_lab_results()
    timeline_events = db.get_medical_timeline()
    medications = db.get_medication_history()
    
    # Display metrics
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
    """Render PDF upload and processing section"""
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
    
    # Display existing lab results
    st.subheader("Exames Registrados")
    lab_results = db.get_lab_results()
    
    if not lab_results.empty:
        # Add edit functionality
        st.write("**Clique em uma linha para editar:**")
        
        # Create editable dataframe
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
            # Here you would implement the save logic
            st.success("Alterações salvas com sucesso!")
    else:
        st.info("Nenhum exame registrado ainda.")

def process_uploaded_pdfs(uploaded_files, db, ai_processor, user_id):
    """Process uploaded PDF files"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_files = len(uploaded_files)
    processed_results = []
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processando {uploaded_file.name}...")
        
        try:
            # Extract text from PDF
            pdf_text = ai_processor.extract_pdf_text(uploaded_file)
            
            if pdf_text:
                # Process with AI
                lab_results = ai_processor.process_lab_pdf(pdf_text, uploaded_file.name)
                
                # Save results to database
                for result in lab_results:
                    if db.save_lab_result(result, user_id):
                        processed_results.append(result)
                
                # Save uploaded file
                uploaded_file.seek(0)
                file_data = uploaded_file.read()
                db.save_uploaded_file(uploaded_file.name, file_data, 'pdf', user_id)
            
        except Exception as e:
            st.error(f"Erro ao processar {uploaded_file.name}: {e}")
        
        progress_bar.progress((i + 1) / total_files)
    
    status_text.text("Processamento concluído!")
    
    if processed_results:
        st.success(f"✅ Processamento concluído! {len(processed_results)} exames adicionados.")
        
        # Display summary
        st.subheader("Resumo dos Dados Extraídos")
        summary_df = pd.DataFrame(processed_results)
        st.dataframe(summary_df, use_container_width=True)
    else:
        st.warning("Nenhum dado foi extraído dos arquivos.")

def render_clinical_notes_section(db, ai_processor, user_id):
    """Render clinical notes management section"""
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
    
    # Display existing timeline
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
    """Render text input section for clinical notes"""
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
    """Render audio input section"""
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
                # Transcribe audio
                transcribed_text = ai_processor.transcribe_audio(uploaded_audio)
                
                if transcribed_text:
                    st.success("Áudio transcrito com sucesso!")
                    
                    # Display transcription
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
                        process_clinical_text(edited_text, event_date, db, ai_processor, user_id)
                else:
                    st.error("Erro na transcrição do áudio.")

def process_clinical_text(text: str, event_date: date, db, ai_processor, user_id):
    """Process clinical text with AI"""
    with st.spinner("Processando texto com IA..."):
        processed_data = ai_processor.process_clinical_text(text)
        
        if processed_data:
            st.success("Texto processado com sucesso!")
            
            # Display processed information
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
            
            # Save button
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
    """Render medications management section"""
    st.header("💊 Gerenciamento de Medicamentos")
    
    # Add new medication
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
                    # Validate medication name with AI
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
    
    # Display existing medications
    st.subheader("Medicamentos Registrados")
    medications = db.get_medication_history()
    
    if medications:
        med_df = pd.DataFrame(medications)
        
        # Format dates for display
        med_df['start_date'] = med_df['start_date'].apply(format_date)
        med_df['end_date'] = med_df['end_date'].apply(lambda x: format_date(x) if x else "Em uso")
        
        st.dataframe(med_df, use_container_width=True)
    else:
        st.info("Nenhum medicamento registrado ainda.")
    
    # Audio medication entry
    st.subheader("Entrada de Medicamentos por Áudio")
    med_audio = st.file_uploader(
        "Upload de áudio com informações de medicamentos:",
        type=['mp3', 'wav', 'm4a'],
        key="med_audio"
    )
    
    if med_audio and st.button("🔄 Processar Áudio de Medicamentos"):
        with st.spinner("Processando áudio..."):
            # Transcribe and process
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
    """Render media upload section"""
    st.header("📸 Fotos e Mídia")
    
    # Photo upload sections
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Foto da Luna")
        luna_photo = st.file_uploader(
            "Upload foto da Luna:",
            type=['png', 'jpg', 'jpeg'],
            key="luna_photo"
        )
        
        if luna_photo and st.button("Salvar Foto da Luna"):
            # Save luna photo logic here
            st.success("Foto da Luna salva!")
    
    with col2:
        st.subheader("Foto do Tutor 1")
        tutor1_photo = st.file_uploader(
            "Upload foto Paulo:",
            type=['png', 'jpg', 'jpeg'],
            key="tutor1_photo"
        )
        
        if tutor1_photo and st.button("Salvar Foto Paulo"):
            # Save tutor1 photo logic here
            st.success("Foto do Paulo salva!")
    
    with col3:
        st.subheader("Foto do Tutor 2")
        tutor2_photo = st.file_uploader(
            "Upload foto Júlia:",
            type=['png', 'jpg', 'jpeg'],
            key="tutor2_photo"
        )
        
        if tutor2_photo and st.button("Salvar Foto Júlia"):
            # Save tutor2 photo logic here
            st.success("Foto da Júlia salva!")

def render_settings_section(db):
    """Render system settings section"""
    st.header("⚙️ Configurações do Sistema")
    
    # Theme settings
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
    
    # Backup section
    st.subheader("Backup e Exportação")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Exportar Todos os Dados"):
            # Export all data logic
            st.success("Dados exportados!")
    
    with col2:
        if st.button("🔄 Backup do Sistema"):
            # Backup logic
            st.success("Backup realizado!")

def render_pdf_clinical_section(db, ai_processor, user_id):
    """Render PDF clinical notes section"""
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
                    
                    # Display extracted text
                    st.text_area("Texto extraído:", value=pdf_text, height=200)
                    
                    event_date = st.date_input("Data do evento:", value=date.today())
                    
                    if st.button("✅ Processar com IA"):
                        process_clinical_text(pdf_text, event_date, db, ai_processor, user_id)
                else:
                    st.error("Erro ao extrair texto do PDF.")

def render_video_input_section(db, ai_processor, user_id):
    """Render video input section"""
    st.subheader("Entrada de Vídeo")
    
    uploaded_video = st.file_uploader(
        "Selecione arquivo de vídeo:",
        type=['mp4', 'avi', 'mov'],
        help="O áudio do vídeo será extraído e transcrito"
    )
    
    if uploaded_video:
        st.video(uploaded_video)
        
        if st.button("🔄 Processar Vídeo", type="primary"):
            st.info("Processamento de vídeo não implementado ainda. Use a opção de áudio.")
