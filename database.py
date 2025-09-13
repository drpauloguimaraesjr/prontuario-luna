import psycopg2
import pandas as pd
import json
from datetime import datetime
import os
from typing import Dict, List, Optional, Any
import streamlit as st

class DatabaseManager:
    """Gerencia todas as operações de banco de dados para o sistema de prontuário médico"""
    
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('PGHOST'),
            'database': os.getenv('PGDATABASE'),
            'user': os.getenv('PGUSER'),
            'password': os.getenv('PGPASSWORD'),
            'port': os.getenv('PGPORT', 5432)
        }
        self.init_database()
    
    def get_connection(self):
        """Obter conexão com o banco de dados"""
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            st.error(f"Erro ao conectar com o banco de dados: {e}")
            return None
    
    def init_database(self):
        """Inicializar tabelas do banco de dados"""
        conn = self.get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Tabela de usuários para autenticação
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de informações do paciente
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patient_info (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    species VARCHAR(100),
                    breed VARCHAR(100),
                    birth_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de resultados laboratoriais
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lab_results (
                    id SERIAL PRIMARY KEY,
                    test_date DATE NOT NULL,
                    lab_name VARCHAR(255),
                    doctor_name VARCHAR(255),
                    test_name VARCHAR(255) NOT NULL,
                    test_value DECIMAL,
                    unit VARCHAR(50),
                    reference_range VARCHAR(100),
                    pdf_filename VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER REFERENCES users(id)
                )
            """)
            
            # Linha do tempo do histórico médico
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medical_timeline (
                    id SERIAL PRIMARY KEY,
                    event_date DATE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    symptoms TEXT[],
                    clinical_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER REFERENCES users(id)
                )
            """)
            
            # Histórico de medicamentos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medication_history (
                    id SERIAL PRIMARY KEY,
                    medication_name VARCHAR(255) NOT NULL,
                    active_ingredient VARCHAR(255),
                    dose VARCHAR(100),
                    route VARCHAR(100),
                    start_date DATE NOT NULL,
                    end_date DATE,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER REFERENCES users(id)
                )
            """)
            
            # Fotos do paciente
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patient_photos (
                    id SERIAL PRIMARY KEY,
                    photo_type VARCHAR(50) NOT NULL,
                    photo_data BYTEA,
                    filename VARCHAR(255),
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Rastreamento de arquivos enviados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploaded_files (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    file_type VARCHAR(50),
                    file_data BYTEA,
                    processed BOOLEAN DEFAULT FALSE,
                    processing_results JSON,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uploaded_by INTEGER REFERENCES users(id)
                )
            """)
            
            # Inserir informações padrão do paciente se não existir
            cursor.execute("SELECT COUNT(*) FROM patient_info")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO patient_info (name, species, breed)
                    VALUES (%s, %s, %s)
                """, ("Luna Princess Mendes Guimarães", "Canina", "Não especificado"))
            
            # Inserir usuário admin padrão se não existir
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                import bcrypt
                password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute("""
                    INSERT INTO users (email, password_hash, name)
                    VALUES (%s, %s, %s)
                """, ("admin@admin.com", password_hash, "Administrador"))
            
            conn.commit()
            cursor.close()
            
        except Exception as e:
            st.error(f"Erro ao inicializar banco de dados: {e}")
        finally:
            conn.close()
    
    def get_lab_results(self) -> pd.DataFrame:
        """Obter todos os resultados laboratoriais como DataFrame"""
        conn = self.get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            query = """
                SELECT test_date, test_name, test_value, unit, lab_name, doctor_name, reference_range
                FROM lab_results
                ORDER BY test_date DESC, test_name
            """
            df = pd.read_sql_query(query, conn)
            return df
        except Exception as e:
            st.error(f"Erro ao buscar resultados de exames: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def get_lab_results_pivot(self) -> pd.DataFrame:
        """Obter resultados laboratoriais em formato de tabela dinâmica (exames como linhas, datas como colunas)"""
        df = self.get_lab_results()
        if df.empty:
            return df
        
        try:
            # Criar tabela dinâmica
            pivot_df = df.pivot_table(
                index='test_name',
                columns='test_date',
                values='test_value',
                aggfunc='first'
            )
            return pivot_df
        except Exception as e:
            st.error(f"Erro ao criar tabela pivô: {e}")
            return pd.DataFrame()
    
    def save_lab_result(self, result_data: Dict[str, Any], user_id: int = 1) -> bool:
        """Salvar um resultado laboratorial no banco de dados"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO lab_results 
                (test_date, lab_name, doctor_name, test_name, test_value, unit, reference_range, pdf_filename, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                result_data['test_date'],
                result_data.get('lab_name'),
                result_data.get('doctor_name'),
                result_data['test_name'],
                result_data.get('test_value'),
                result_data.get('unit'),
                result_data.get('reference_range'),
                result_data.get('pdf_filename'),
                user_id
            ))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar resultado de exame: {e}")
            return False
        finally:
            conn.close()
    
    def get_medical_timeline(self) -> List[Dict[str, Any]]:
        """Obter eventos da linha do tempo médica"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_date, title, description, symptoms, clinical_notes
                FROM medical_timeline
                ORDER BY event_date
            """)
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    'event_date': row[0],
                    'title': row[1],
                    'description': row[2],
                    'symptoms': row[3] or [],
                    'clinical_notes': row[4]
                })
            
            cursor.close()
            return events
        except Exception as e:
            st.error(f"Erro ao buscar linha do tempo médica: {e}")
            return []
        finally:
            conn.close()
    
    def save_medical_event(self, event_data: Dict[str, Any], user_id: int = 1) -> bool:
        """Salvar um evento da linha do tempo médica"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO medical_timeline 
                (event_date, title, description, symptoms, clinical_notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                event_data['event_date'],
                event_data['title'],
                event_data.get('description'),
                event_data.get('symptoms', []),
                event_data.get('clinical_notes'),
                user_id
            ))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar evento médico: {e}")
            return False
        finally:
            conn.close()
    
    def get_medication_history(self) -> List[Dict[str, Any]]:
        """Obter histórico de medicamentos"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT medication_name, active_ingredient, dose, route, start_date, end_date, notes
                FROM medication_history
                ORDER BY start_date
            """)
            
            medications = []
            for row in cursor.fetchall():
                medications.append({
                    'name': row[0],
                    'active_ingredient': row[1],
                    'dose': row[2],
                    'route': row[3],
                    'start_date': row[4],
                    'end_date': row[5],
                    'notes': row[6]
                })
            
            cursor.close()
            return medications
        except Exception as e:
            st.error(f"Erro ao buscar histórico de medicamentos: {e}")
            return []
        finally:
            conn.close()
    
    def save_medication(self, med_data: Dict[str, Any], user_id: int = 1) -> bool:
        """Salvar medicamento no histórico"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO medication_history 
                (medication_name, active_ingredient, dose, route, start_date, end_date, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                med_data['medication_name'],
                med_data.get('active_ingredient'),
                med_data['dose'],
                med_data['route'],
                med_data['start_date'],
                med_data.get('end_date'),
                med_data.get('notes'),
                user_id
            ))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar medicamento: {e}")
            return False
        finally:
            conn.close()
    
    def get_patient_info(self) -> Dict[str, Any]:
        """Obter informações do paciente"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, species, breed, birth_date FROM patient_info LIMIT 1")
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    'name': row[0],
                    'species': row[1],
                    'breed': row[2],
                    'birth_date': row[3]
                }
            return {}
        except Exception as e:
            st.error(f"Erro ao buscar informações do paciente: {e}")
            return {}
        finally:
            conn.close()
    
    def get_patient_photos(self) -> Dict[str, Any]:
        """Obter fotos do paciente"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT photo_type, photo_data FROM patient_photos")
            rows = cursor.fetchall()
            cursor.close()
            
            photos = {}
            for row in rows:
                if row[1]:  # Se os dados da foto existem
                    photos[row[0]] = row[1]
            
            return photos
        except Exception as e:
            st.error(f"Erro ao buscar fotos do paciente: {e}")
            return {}
        finally:
            conn.close()
    
    def save_patient_photo(self, photo_type: str, photo_data: bytes, filename: str) -> bool:
        """Salvar foto do paciente (Luna, tutor1, tutor2)"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Verificar se já existe uma foto do mesmo tipo
            cursor.execute("SELECT id FROM patient_photos WHERE photo_type = %s", (photo_type,))
            existing = cursor.fetchone()
            
            if existing:
                # Atualizar foto existente
                cursor.execute("""
                    UPDATE patient_photos 
                    SET photo_data = %s, filename = %s, uploaded_at = CURRENT_TIMESTAMP
                    WHERE photo_type = %s
                """, (photo_data, filename, photo_type))
            else:
                # Inserir nova foto
                cursor.execute("""
                    INSERT INTO patient_photos (photo_type, photo_data, filename)
                    VALUES (%s, %s, %s)
                """, (photo_type, photo_data, filename))
            
            conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            st.error(f"Erro ao salvar foto {photo_type}: {e}")
            return False
        finally:
            conn.close()
    
    def save_uploaded_file(self, filename: str, file_data: bytes, file_type: str, user_id: int = 1) -> int:
        """Salvar arquivo enviado e retornar ID do arquivo"""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO uploaded_files (filename, file_type, file_data, uploaded_by)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (filename, file_type, file_data, user_id))
            
            file_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return file_id
        except Exception as e:
            st.error(f"Erro ao salvar arquivo: {e}")
            return None
        finally:
            conn.close()
    
    def get_test_names(self) -> List[str]:
        """Obter nomes únicos de exames para ferramenta de comparação"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT test_name FROM lab_results ORDER BY test_name")
            test_names = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return test_names
        except Exception as e:
            st.error(f"Erro ao buscar nomes de exames: {e}")
            return []
        finally:
            conn.close()
    
    def get_test_dates(self) -> List[str]:
        """Obter datas únicas de exames para ferramenta de comparação"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT test_date FROM lab_results ORDER BY test_date DESC")
            dates = [row[0].strftime('%Y-%m-%d') for row in cursor.fetchall()]
            cursor.close()
            return dates
        except Exception as e:
            st.error(f"Erro ao buscar datas de exames: {e}")
            return []
        finally:
            conn.close()
