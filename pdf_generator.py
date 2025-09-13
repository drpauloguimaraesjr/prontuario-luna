"""
Gerador de PDF para prontuários médicos
Funcionalidade completa de exportação de registros médicos para PDF
"""

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime
import io
import pandas as pd
from typing import Dict, List, Any, Optional
from utils import format_date, format_lab_value

class MedicalRecordPDFGenerator:
    """Gerador de PDF para prontuários médicos completos"""
    
    def __init__(self, db):
        self.db = db
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Criar estilos personalizados para o PDF"""
        
        # Estilo para cabeçalho principal
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.HexColor('#FF69B4'),
            alignment=1  # Centro
        )
        
        # Estilo para seções
        self.section_style = ParagraphStyle(
            'CustomSection',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#FF1493'),
            borderWidth=1,
            borderColor=colors.HexColor('#FF69B4'),
            borderPadding=5
        )
        
        # Estilo para texto normal
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            textColor=colors.black
        )
        
        # Estilo para dados clínicos
        self.clinical_style = ParagraphStyle(
            'Clinical',
            parent=self.styles['Normal'],
            fontSize=9,
            leftIndent=20,
            spaceAfter=4,
            textColor=colors.HexColor('#333333')
        )
    
    def generate_complete_medical_record(self) -> bytes:
        """Gerar PDF completo do prontuário médico"""
        
        # Criar buffer para o PDF
        buffer = io.BytesIO()
        
        # Configurar documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Lista para elementos do documento
        story = []
        
        # Adicionar conteúdo
        self._add_header(story)
        self._add_patient_info(story)
        self._add_lab_results_summary(story)
        self._add_lab_results_table(story)
        self._add_timeline_section(story)
        self._add_medication_history(story)
        self._add_footer_info(story)
        
        # Gerar PDF
        doc.build(story)
        
        # Retornar bytes
        buffer.seek(0)
        return buffer.getvalue()
    
    def _add_header(self, story: List):
        """Adicionar cabeçalho do documento"""
        
        # Título principal
        story.append(Paragraph("🐕 PRONTUÁRIO MÉDICO VETERINÁRIO", self.header_style))
        story.append(Paragraph("Luna Princess Mendes Guimarães", self.header_style))
        story.append(Paragraph("<i>Deus opera milagres</i>", self.normal_style))
        story.append(Spacer(1, 20))
        
        # Data de geração
        generation_date = datetime.now().strftime("%d/%m/%Y às %H:%M")
        story.append(Paragraph(f"<b>Relatório gerado em:</b> {generation_date}", self.normal_style))
        story.append(Spacer(1, 20))
    
    def _add_patient_info(self, story: List):
        """Adicionar informações do paciente"""
        
        story.append(Paragraph("📋 INFORMAÇÕES DO PACIENTE", self.section_style))
        
        # Obter informações do paciente
        patient_info = self.db.get_patient_info()
        
        # Criar tabela de informações
        patient_data = [
            ["Nome Completo:", patient_info.get('name', 'Luna Princess Mendes Guimarães')],
            ["Espécie:", patient_info.get('species', 'Canina')],
            ["Raça:", patient_info.get('breed', 'Não especificado')],
            ["Data de Nascimento:", format_date(patient_info.get('birth_date', '')) if patient_info.get('birth_date') else 'Não informado']
        ]
        
        patient_table = Table(patient_data, colWidths=[4*cm, 10*cm])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF0F5')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#FF69B4')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(patient_table)
        story.append(Spacer(1, 20))
    
    def _add_lab_results_summary(self, story: List):
        """Adicionar resumo dos resultados laboratoriais"""
        
        story.append(Paragraph("🔬 RESUMO DOS EXAMES LABORATORIAIS", self.section_style))
        
        # Obter resultados laboratoriais
        lab_results = self.db.get_lab_results()
        
        if not lab_results.empty:
            # Estatísticas gerais
            total_tests = len(lab_results)
            unique_test_types = lab_results['test_name'].nunique()
            date_range = f"{lab_results['test_date'].min()} a {lab_results['test_date'].max()}"
            
            summary_data = [
                ["Total de Exames Realizados:", str(total_tests)],
                ["Tipos de Exames Únicos:", str(unique_test_types)],
                ["Período dos Exames:", date_range],
                ["Laboratórios Envolvidos:", str(lab_results['lab_name'].nunique()) if 'lab_name' in lab_results.columns else "N/A"]
            ]
            
            summary_table = Table(summary_data, colWidths=[6*cm, 8*cm])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0F8FF')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#4169E1')),
            ]))
            
            story.append(summary_table)
        else:
            story.append(Paragraph("Nenhum resultado laboratorial registrado.", self.normal_style))
        
        story.append(Spacer(1, 20))
    
    def _add_lab_results_table(self, story: List):
        """Adicionar tabela detalhada dos resultados laboratoriais"""
        
        story.append(Paragraph("📊 RESULTADOS LABORATORIAIS DETALHADOS", self.section_style))
        
        lab_results = self.db.get_lab_results()
        
        if not lab_results.empty:
            # Preparar dados para tabela
            table_data = [['Data', 'Exame', 'Valor', 'Unidade', 'Laboratório']]
            
            for _, row in lab_results.iterrows():
                table_data.append([
                    format_date(row['test_date']) if pd.notna(row['test_date']) else '',
                    str(row['test_name']) if pd.notna(row['test_name']) else '',
                    format_lab_value(row['test_value']) if pd.notna(row['test_value']) else '',
                    str(row['unit']) if pd.notna(row['unit']) else '',
                    str(row['lab_name']) if pd.notna(row.get('lab_name', '')) else ''
                ])
            
            # Criar tabela
            lab_table = Table(table_data, colWidths=[2.5*cm, 4*cm, 2*cm, 2*cm, 3.5*cm])
            lab_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF69B4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(lab_table)
        else:
            story.append(Paragraph("Nenhum resultado laboratorial para exibir.", self.normal_style))
        
        story.append(Spacer(1, 20))
    
    def _add_timeline_section(self, story: List):
        """Adicionar seção da linha do tempo médica"""
        
        story.append(Paragraph("📅 LINHA DO TEMPO MÉDICA (HDA)", self.section_style))
        
        # Obter eventos da linha do tempo
        events = self.db.get_medical_timeline()
        
        if events:
            story.append(Paragraph(f"<b>Total de eventos registrados:</b> {len(events)}", self.normal_style))
            story.append(Spacer(1, 10))
            
            # Ordenar eventos por data
            sorted_events = sorted(events, key=lambda x: x['event_date'])
            
            for event in sorted_events:
                # Data e título
                story.append(Paragraph(
                    f"<b>📅 {format_date(event['event_date'])} - {event['title']}</b>", 
                    self.normal_style
                ))
                
                # Descrição
                if event.get('description'):
                    story.append(Paragraph(
                        f"<i>Resumo:</i> {event['description']}", 
                        self.clinical_style
                    ))
                
                # Sintomas
                if event.get('symptoms'):
                    symptoms_text = ", ".join(event['symptoms'])
                    story.append(Paragraph(
                        f"<i>Sintomas:</i> {symptoms_text}", 
                        self.clinical_style
                    ))
                
                # Notas clínicas
                if event.get('clinical_notes'):
                    # Truncar notas longas para o PDF
                    notes = event['clinical_notes']
                    if len(notes) > 300:
                        notes = notes[:300] + "..."
                    
                    story.append(Paragraph(
                        f"<i>Notas Clínicas:</i> {notes}", 
                        self.clinical_style
                    ))
                
                story.append(Spacer(1, 10))
        
        else:
            story.append(Paragraph("Nenhum evento registrado na linha do tempo.", self.normal_style))
        
        story.append(Spacer(1, 20))
    
    def _add_medication_history(self, story: List):
        """Adicionar histórico de medicamentos"""
        
        story.append(Paragraph("💊 HISTÓRICO DE MEDICAMENTOS", self.section_style))
        
        # Obter histórico de medicamentos
        medications = self.db.get_medication_history()
        
        if medications:
            # Criar tabela de medicamentos
            med_data = [['Medicamento', 'Dose', 'Via', 'Início', 'Término', 'Observações']]
            
            for med in medications:
                med_data.append([
                    str(med.get('name', 'N/A')),
                    f"{med.get('dosage', 'N/A')} {med.get('unit', '')}".strip(),
                    str(med.get('route', 'N/A')),
                    format_date(med.get('start_date', '')) if med.get('start_date') else 'N/A',
                    format_date(med.get('end_date', '')) if med.get('end_date') else 'Contínuo',
                    str(med.get('notes', ''))[:50] + ('...' if len(str(med.get('notes', ''))) > 50 else '') if med.get('notes') else ''
                ])
            
            med_table = Table(med_data, colWidths=[2.5*cm, 2*cm, 1.5*cm, 2*cm, 2*cm, 4*cm])
            med_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#32CD32')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F0FFF0')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            story.append(med_table)
        else:
            story.append(Paragraph("Nenhum medicamento registrado.", self.normal_style))
        
        story.append(Spacer(1, 20))
    
    def _add_footer_info(self, story: List):
        """Adicionar informações de rodapé"""
        
        story.append(Spacer(1, 30))
        
        # Linha separadora
        story.append(Paragraph("_" * 80, self.normal_style))
        story.append(Spacer(1, 10))
        
        # Informações técnicas
        story.append(Paragraph(
            "<b>Prontuário Digital Veterinário</b> - Sistema de Gerenciamento de Registros Médicos", 
            self.normal_style
        ))
        story.append(Paragraph(
            f"Documento gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}", 
            self.clinical_style
        ))
        story.append(Paragraph(
            "Este documento contém informações médicas confidenciais de Luna Princess Mendes Guimarães", 
            self.clinical_style
        ))
    
    def generate_lab_results_only(self) -> bytes:
        """Gerar PDF apenas com resultados laboratoriais"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Cabeçalho simplificado
        story.append(Paragraph("🔬 RESULTADOS LABORATORIAIS - LUNA", self.header_style))
        story.append(Spacer(1, 20))
        
        self._add_lab_results_summary(story)
        self._add_lab_results_table(story)
        self._add_footer_info(story)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_timeline_only(self) -> bytes:
        """Gerar PDF apenas com linha do tempo"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Cabeçalho simplificado
        story.append(Paragraph("📅 LINHA DO TEMPO MÉDICA - LUNA", self.header_style))
        story.append(Spacer(1, 20))
        
        self._add_timeline_section(story)
        self._add_footer_info(story)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()