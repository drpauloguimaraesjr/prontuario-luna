import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import PyPDF2
import pdfplumber
import streamlit as st
from openai import OpenAI

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

class AIProcessor:
    """Handles AI-powered processing of medical documents and data"""
    
    def __init__(self):
        self.client = client
        self.unit_conversions = {
            # Common lab value unit conversions
            'ng/dl_to_mmol/l': 0.01,
            'mg/dl_to_mmol/l': 0.055,
            'g/dl_to_g/l': 10,
            'mcg/dl_to_nmol/l': 26.12,
            # Add more conversions as needed
        }
    
    def extract_pdf_text(self, pdf_file) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            
            # Try with pdfplumber first (better for structured documents)
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # If pdfplumber fails, try PyPDF2
            if not text.strip():
                pdf_file.seek(0)  # Reset file pointer
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            return text
        except Exception as e:
            st.error(f"Erro ao extrair texto do PDF: {e}")
            return ""
    
    def process_lab_pdf(self, pdf_text: str, filename: str) -> List[Dict[str, Any]]:
        """Process lab results PDF and extract structured data"""
        try:
            prompt = f"""
            Analise o seguinte texto extraído de um PDF de exame laboratorial e extraia todas as informações relevantes.
            Retorne um JSON com a seguinte estrutura:

            {{
                "exam_date": "YYYY-MM-DD",
                "lab_name": "nome do laboratório",
                "doctor_name": "nome do médico solicitante",
                "patient_name": "nome do paciente",
                "tests": [
                    {{
                        "test_name": "nome do exame",
                        "value": "valor numérico ou resultado",
                        "unit": "unidade de medida",
                        "reference_range": "faixa de referência"
                    }}
                ]
            }}

            Texto do PDF:
            {pdf_text}

            IMPORTANTE: 
            - Extraia TODOS os exames encontrados
            - Se não encontrar alguma informação, use null
            - Para valores numéricos, extraia apenas o número
            - Mantenha as unidades originais
            - Se houver múltiplas datas, use a mais relevante (data do exame)
            """

            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em análise de documentos médicos. Extraia informações de forma precisa e estruturada."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            result = json.loads(response.choices[0].message.content)
            
            # Convert to list of individual lab results
            lab_results = []
            if result.get('tests'):
                for test in result['tests']:
                    lab_result = {
                        'test_date': result.get('exam_date'),
                        'lab_name': result.get('lab_name'),
                        'doctor_name': result.get('doctor_name'),
                        'test_name': test.get('test_name'),
                        'test_value': self._parse_numeric_value(test.get('value')),
                        'unit': test.get('unit'),
                        'reference_range': test.get('reference_range'),
                        'pdf_filename': filename
                    }
                    lab_results.append(lab_result)
            
            return lab_results
            
        except Exception as e:
            st.error(f"Erro ao processar PDF com IA: {e}")
            return []
    
    def process_clinical_text(self, text: str, content_type: str = "text") -> Dict[str, Any]:
        """Process clinical notes and extract timeline information"""
        try:
            prompt = f"""
            Analise o seguinte texto clínico e extraia informações para criação de prontuário médico.
            Retorne um JSON com a seguinte estrutura:

            {{
                "date": "YYYY-MM-DD (data mais provável do evento)",
                "title": "título resumido do evento",
                "description": "descrição breve dos acontecimentos",
                "symptoms": ["lista", "de", "sintomas", "identificados"],
                "clinical_notes": "texto formatado como prontuário médico profissional",
                "medications_mentioned": [
                    {{
                        "name": "nome do medicamento",
                        "dose": "dosagem",
                        "route": "via de administração",
                        "notes": "observações"
                    }}
                ],
                "key_topics": ["tópicos", "importantes", "extraídos"]
            }}

            Texto para análise:
            {text}

            IMPORTANTE:
            - Se não conseguir identificar uma data específica, use a data atual
            - Formate as clinical_notes de forma profissional
            - Identifique todos os medicamentos mencionados
            - Extraia sintomas e eventos importantes
            """

            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um médico especialista em análise de textos clínicos e criação de prontuários médicos."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )

            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            st.error(f"Erro ao processar texto clínico: {e}")
            return {}
    
    def transcribe_audio(self, audio_file) -> str:
        """Transcribe audio file to text"""
        try:
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            return response.text
        except Exception as e:
            st.error(f"Erro ao transcrever áudio: {e}")
            return ""
    
    def validate_medication_name(self, medication_name: str) -> Dict[str, Any]:
        """Validate and get information about a medication"""
        try:
            prompt = f"""
            Analise o nome do medicamento fornecido e retorne informações validadas.
            Retorne um JSON com a seguinte estrutura:

            {{
                "validated_name": "nome validado/corrigido do medicamento",
                "active_ingredient": "princípio ativo principal",
                "common_uses": "usos comuns em medicina veterinária",
                "is_valid": true/false,
                "suggestions": ["medicamentos", "similares", "se", "aplicável"]
            }}

            Medicamento: {medication_name}

            IMPORTANTE: Foque em medicamentos veterinários se possível.
            """

            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em farmacologia veterinária."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            st.error(f"Erro ao validar medicamento: {e}")
            return {"is_valid": False, "validated_name": medication_name}
    
    def convert_units(self, value: float, from_unit: str, to_unit: str) -> Optional[float]:
        """Convert between different units of measurement"""
        try:
            conversion_key = f"{from_unit.lower()}_to_{to_unit.lower()}"
            if conversion_key in self.unit_conversions:
                return value * self.unit_conversions[conversion_key]
            
            # Use AI for unknown conversions
            prompt = f"""
            Converta {value} de {from_unit} para {to_unit}.
            Retorne apenas o valor numérico convertido em formato JSON:
            {{"converted_value": número}}
            
            Se a conversão não for possível, retorne {{"converted_value": null}}
            """

            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em conversões de unidades médicas e laboratoriais."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )

            result = json.loads(response.choices[0].message.content)
            return result.get('converted_value')
            
        except Exception as e:
            st.error(f"Erro na conversão de unidades: {e}")
            return None
    
    def generate_medical_summary(self, timeline_events: List[Dict], lab_results: List[Dict]) -> str:
        """Generate a comprehensive medical summary"""
        try:
            prompt = f"""
            Com base nos seguintes dados médicos, gere um resumo clínico profissional:

            Eventos da linha do tempo:
            {json.dumps(timeline_events, indent=2, default=str)}

            Resultados de exames:
            {json.dumps(lab_results, indent=2, default=str)}

            Gere um relatório médico completo e profissional incluindo:
            1. Resumo do caso
            2. Principais achados clínicos
            3. Evolução temporal
            4. Resultados laboratoriais relevantes
            5. Considerações finais

            Formato: Texto profissional de prontuário médico veterinário.
            """

            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um médico veterinário especialista em redação de prontuários médicos."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            return response.choices[0].message.content
            
        except Exception as e:
            st.error(f"Erro ao gerar resumo médico: {e}")
            return ""
    
    def _parse_numeric_value(self, value_str: str) -> Optional[float]:
        """Parse numeric value from string"""
        if not value_str:
            return None
        
        try:
            # Remove non-numeric characters except decimal point and minus
            cleaned = re.sub(r'[^\d\.\-]', '', str(value_str))
            if cleaned:
                return float(cleaned)
        except:
            pass
        
        return None
    
    def process_medication_audio(self, audio_text: str) -> List[Dict[str, Any]]:
        """Process audio transcription to extract medication information"""
        try:
            prompt = f"""
            Analise a seguinte transcrição de áudio sobre medicamentos e extraia informações estruturadas.
            Retorne um JSON com a seguinte estrutura:

            {{
                "medications": [
                    {{
                        "name": "nome do medicamento",
                        "active_ingredient": "princípio ativo",
                        "dose": "dosagem",
                        "route": "via de administração",
                        "start_date": "YYYY-MM-DD ou null",
                        "end_date": "YYYY-MM-DD ou null",
                        "notes": "observações sobre o medicamento"
                    }}
                ]
            }}

            Transcrição do áudio:
            {audio_text}

            IMPORTANTE:
            - Extraia TODOS os medicamentos mencionados
            - Se não encontrar alguma informação, use null
            - Identifique datas mencionadas
            - Capture observações sobre eficácia, efeitos colaterais, etc.
            """

            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em análise de informações médicas sobre medicamentos."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            result = json.loads(response.choices[0].message.content)
            return result.get('medications', [])
            
        except Exception as e:
            st.error(f"Erro ao processar áudio de medicamentos: {e}")
            return []
