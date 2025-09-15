import psycopg2
import pandas as pd
import json
from datetime import datetime
import os
from typing import Dict, List, Optional, Any
import streamlit as st
from sqlalchemy import create_engine, text
from encryption_utils import get_encryption_manager, should_encrypt_config, is_sensitive_config

# Role constants
ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_ADMIN = "ADMIN"
ROLE_USER = "USER"

# All available roles
ALL_ROLES = [ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER]

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
        
        # Create SQLAlchemy engine for pandas operations
        database_url = f"postgresql://{self.connection_params['user']}:{self.connection_params['password']}@{self.connection_params['host']}:{self.connection_params['port']}/{self.connection_params['database']}"
        self.engine = create_engine(database_url)
        
        # Validate database connectivity
        self._validate_database_connectivity()
        self.init_database()
    
    def _validate_database_connectivity(self):
        """Validar conectividade do banco de dados na inicialização"""
        try:
            # Test connection with SQLAlchemy engine
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
        except Exception as e:
            app_env = os.getenv('APP_ENV', '').lower()
            is_production = app_env == 'production'
            error_msg = f"FALHA CRÍTICA: Não foi possível conectar ao banco de dados: {e}"
            
            if is_production:
                raise ConnectionError(error_msg)
            else:
                st.error(f"⚠️ WARNING: {error_msg}")
    
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
                    role VARCHAR(50) DEFAULT 'USER',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Adicionar colunas role, is_active, last_login e security se não existirem (para compatibilidade)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'USER'")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_change_required BOOLEAN DEFAULT FALSE")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP")
            except Exception as e:
                # Ignorar erro se as colunas já existem
                pass
            
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
            
            # Logs de auditoria administrativa
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_audit_logs (
                    id SERIAL PRIMARY KEY,
                    admin_user_id INTEGER REFERENCES users(id) NOT NULL,
                    target_user_id INTEGER REFERENCES users(id),
                    action VARCHAR(100) NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(45)
                )
            """)
            
            # Configurações do sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    id SERIAL PRIMARY KEY,
                    category VARCHAR(50) NOT NULL,
                    config_key VARCHAR(100) NOT NULL,
                    config_value JSON NOT NULL,
                    description TEXT,
                    is_encrypted BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER REFERENCES users(id),
                    UNIQUE(category, config_key)
                )
            """)
            
            # Inserir informações padrão do paciente se não existir
            cursor.execute("SELECT COUNT(*) FROM patient_info")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO patient_info (name, species, breed)
                    VALUES (%s, %s, %s)
                """, ("Luna Princess Mendes Guimarães", "Canina", "Não especificado"))
            
            # Verificar se existe um admin seguro, se não, criar admin temporário
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = %s", (ROLE_SUPER_ADMIN,))
            if cursor.fetchone()[0] == 0:
                import bcrypt
                import secrets
                
                # Gerar senha temporária segura
                temp_password = secrets.token_urlsafe(16)
                password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                cursor.execute("""
                    INSERT INTO users (email, password_hash, name, role, is_active, password_change_required)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ("admin@admin.com", password_hash, "ADMIN TEMPORÁRIO", ROLE_SUPER_ADMIN, True, True))
                
                # Log da senha temporária (APENAS PARA DEBUG - REMOVER EM PRODUÇÃO)
                print(f"🚨 ADMIN TEMPORÁRIO CRIADO:")
                print(f"   Email: admin@admin.com")
                print(f"   Senha: {temp_password}")
                print(f"   ⚠️  MUDE IMEDIATAMENTE NO PRIMEIRO LOGIN!")
                
                # Salvar informação de setup inicial necessário
                cursor.execute("""
                    INSERT INTO system_config (category, config_key, config_value, description, is_encrypted)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (category, config_key) DO NOTHING
                """, (
                    'SECURITY', 
                    'initial_setup_required', 
                    '{"value": true}',
                    'Sistema requer configuração inicial de segurança',
                    False
                ))
            
            # Atualizar usuários existentes sem role para USER (compatibilidade)
            cursor.execute("UPDATE users SET role = %s WHERE role IS NULL", (ROLE_USER,))
            cursor.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")
            
            # Inserir configurações padrão do sistema se não existirem
            cursor.execute("SELECT COUNT(*) FROM system_config")
            if cursor.fetchone()[0] == 0:
                default_configs = [
                    # Configurações SMTP/Email
                    ('SMTP', 'smtp_enabled', '{"value": false}', 'Habilitar envio de emails via SMTP'),
                    ('SMTP', 'smtp_host', '{"value": "smtp.gmail.com"}', 'Servidor SMTP'),
                    ('SMTP', 'smtp_port', '{"value": 587}', 'Porta do servidor SMTP'),
                    ('SMTP', 'smtp_username', '{"value": ""}', 'Usuário SMTP'),
                    ('SMTP', 'smtp_password', '{"value": ""}', 'Senha SMTP', True),
                    ('SMTP', 'smtp_use_tls', '{"value": true}', 'Usar TLS/SSL'),
                    ('SMTP', 'from_email', '{"value": ""}', 'Email remetente padrão'),
                    ('SMTP', 'from_name', '{"value": "Sistema Prontuário Luna"}', 'Nome do remetente'),
                    
                    # Configurações API/Integrações
                    ('API', 'openai_enabled', '{"value": true}', 'Habilitar integração OpenAI'),
                    ('API', 'openai_api_key', '{"value": ""}', 'Chave da API OpenAI', True),
                    ('API', 'openai_model', '{"value": "gpt-4"}', 'Modelo OpenAI padrão'),
                    ('API', 'openai_max_tokens', '{"value": 4000}', 'Limite máximo de tokens'),
                    ('API', 'api_rate_limit', '{"value": 100}', 'Limite de requisições por hora'),
                    ('API', 'webhook_url', '{"value": ""}', 'URL do webhook para notificações'),
                    
                    # Configurações de Segurança
                    ('SECURITY', 'password_min_length', '{"value": 8}', 'Comprimento mínimo da senha'),
                    ('SECURITY', 'password_require_special', '{"value": true}', 'Requer caracteres especiais'),
                    ('SECURITY', 'password_require_numbers', '{"value": true}', 'Requer números na senha'),
                    ('SECURITY', 'password_expiry_days', '{"value": 90}', 'Dias para expiração da senha (0 = nunca)'),
                    ('SECURITY', 'session_timeout_minutes', '{"value": 480}', 'Timeout da sessão em minutos'),
                    ('SECURITY', 'max_login_attempts', '{"value": 5}', 'Tentativas máximas de login'),
                    ('SECURITY', 'audit_log_retention_days', '{"value": 365}', 'Retenção de logs de auditoria em dias'),
                    ('SECURITY', 'enable_2fa', '{"value": false}', 'Habilitar autenticação de dois fatores'),
                    
                    # Configurações Gerais
                    ('GENERAL', 'app_name', '{"value": "Prontuário Médico Digital - Luna"}', 'Nome da aplicação'),
                    ('GENERAL', 'app_version', '{"value": "1.0.0"}', 'Versão da aplicação'),
                    ('GENERAL', 'timezone', '{"value": "America/Sao_Paulo"}', 'Fuso horário padrão'),
                    ('GENERAL', 'date_format', '{"value": "DD/MM/YYYY"}', 'Formato de data padrão'),
                    ('GENERAL', 'max_file_size_mb', '{"value": 50}', 'Tamanho máximo de arquivo em MB'),
                    ('GENERAL', 'allowed_file_types', '{"value": ["pdf", "jpg", "jpeg", "png", "mp3", "wav", "mp4"]}', 'Tipos de arquivo permitidos'),
                    ('GENERAL', 'backup_enabled', '{"value": true}', 'Habilitar backup automático'),
                    ('GENERAL', 'backup_frequency_hours', '{"value": 24}', 'Frequência de backup em horas'),
                    ('GENERAL', 'maintenance_mode', '{"value": false}', 'Modo de manutenção ativo'),
                ]
                
                for config in default_configs:
                    is_encrypted = len(config) > 4 and config[4]
                    cursor.execute("""
                        INSERT INTO system_config (category, config_key, config_value, description, is_encrypted)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (config[0], config[1], config[2], config[3], is_encrypted))
            
            conn.commit()
            cursor.close()
            
        except Exception as e:
            st.error(f"Erro ao inicializar banco de dados: {e}")
        finally:
            conn.close()
    
    def get_lab_results(self) -> pd.DataFrame:
        """Obter todos os resultados laboratoriais como DataFrame"""
        try:
            query = """
                SELECT test_date, test_name, test_value, unit, lab_name, doctor_name, reference_range
                FROM lab_results
                ORDER BY test_date DESC, test_name
            """
            df = pd.read_sql_query(query, self.engine)
            # Normalize column names to strings to prevent mixed-type warnings
            df.columns = df.columns.astype(str)
            return df
        except Exception as e:
            st.error(f"Erro ao buscar resultados de exames: {e}")
            return pd.DataFrame()
    
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
            # Normalize column names to strings to prevent mixed-type warnings
            pivot_df.columns = pivot_df.columns.astype(str)
            # Normalize index to strings as well
            pivot_df.index = pivot_df.index.astype(str)
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
    
    def save_uploaded_file(self, filename: str, file_data: bytes, file_type: str, user_id: int = 1) -> Optional[int]:
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
    
    def log_admin_action(self, admin_user_id: int, action: str, target_user_id: Optional[int] = None, 
                        old_value: Optional[str] = None, new_value: Optional[str] = None, 
                        details: Optional[str] = None) -> bool:
        """Registrar ação administrativa no log de auditoria"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO admin_audit_logs 
                (admin_user_id, target_user_id, action, old_value, new_value, details)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (admin_user_id, target_user_id, action, old_value, new_value, details))
            
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            st.error(f"Erro ao registrar log de auditoria: {e}")
            return False
        finally:
            conn.close()
    
    def get_admin_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obter logs de auditoria administrativa"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    al.id,
                    al.timestamp,
                    al.action,
                    al.old_value,
                    al.new_value,
                    al.details,
                    admin_user.name as admin_name,
                    admin_user.email as admin_email,
                    target_user.name as target_name,
                    target_user.email as target_email
                FROM admin_audit_logs al
                LEFT JOIN users admin_user ON al.admin_user_id = admin_user.id
                LEFT JOIN users target_user ON al.target_user_id = target_user.id
                ORDER BY al.timestamp DESC
                LIMIT %s
            """, (limit,))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'action': row[2],
                    'old_value': row[3],
                    'new_value': row[4],
                    'details': row[5],
                    'admin_name': row[6],
                    'admin_email': row[7],
                    'target_name': row[8],
                    'target_email': row[9]
                })
            
            cursor.close()
            return logs
        except Exception as e:
            st.error(f"Erro ao buscar logs de auditoria: {e}")
            return []
        finally:
            conn.close()
    
    def count_active_super_admins(self) -> int:
        """Contar número de SUPER_ADMINs ativos"""
        conn = self.get_connection()
        if not conn:
            return 0
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM users 
                WHERE role = %s AND is_active = TRUE
            """, (ROLE_SUPER_ADMIN,))
            
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            st.error(f"Erro ao contar SUPER_ADMINs ativos: {e}")
            return 0
        finally:
            conn.close()

    def update_last_login(self, user_id: int) -> bool:
        """Atualizar timestamp do último login do usuário"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (user_id,))
            
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            st.error(f"Erro ao atualizar último login: {e}")
            return False
        finally:
            conn.close()

    def get_users_with_filters(self, search_term: str = "", role_filter: str = "", status_filter: str = "", offset: int = 0, limit: int = 20) -> Dict[str, Any]:
        """Buscar usuários com filtros e paginação"""
        conn = self.get_connection()
        if not conn:
            return {'users': [], 'total': 0}
        
        try:
            cursor = conn.cursor()
            
            # Construir query com filtros
            where_conditions = []
            params = []
            
            if search_term:
                where_conditions.append("(LOWER(name) LIKE %s OR LOWER(email) LIKE %s)")
                search_pattern = f"%{search_term.lower()}%"
                params.extend([search_pattern, search_pattern])
            
            if role_filter and role_filter != "ALL":
                where_conditions.append("role = %s")
                params.append(role_filter)
            
            if status_filter == "ACTIVE":
                where_conditions.append("is_active = TRUE")
            elif status_filter == "INACTIVE":
                where_conditions.append("is_active = FALSE")
            
            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Query para contar total
            count_query = f"SELECT COUNT(*) FROM users{where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Query para buscar usuários com paginação
            users_query = f"""
                SELECT id, email, name, role, is_active, created_at, last_login 
                FROM users{where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(users_query, params + [limit, offset])
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'id': row[0],
                    'email': row[1],
                    'name': row[2],
                    'role': row[3] or ROLE_USER,
                    'is_active': row[4],
                    'created_at': row[5],
                    'last_login': row[6]
                })
            
            cursor.close()
            return {'users': users, 'total': total}
        except Exception as e:
            st.error(f"Erro ao buscar usuários: {e}")
            return {'users': [], 'total': 0}
        finally:
            conn.close()

    def get_user_statistics(self) -> Dict[str, int]:
        """Obter estatísticas dos usuários"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total de usuários
            cursor.execute("SELECT COUNT(*) FROM users")
            stats['total'] = cursor.fetchone()[0]
            
            # Usuários ativos
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
            stats['active'] = cursor.fetchone()[0]
            
            # Usuários inativos
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = FALSE")
            stats['inactive'] = cursor.fetchone()[0]
            
            # Por role
            for role in ALL_ROLES:
                cursor.execute("SELECT COUNT(*) FROM users WHERE role = %s", (role,))
                stats[f'role_{role.lower()}'] = cursor.fetchone()[0]
            
            cursor.close()
            return stats
        except Exception as e:
            st.error(f"Erro ao obter estatísticas: {e}")
            return {}
        finally:
            conn.close()

    def update_user_profile(self, user_id: int, name: str, email: str, admin_user_id: int) -> bool:
        """Atualizar perfil do usuário (nome e email)"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Verificar se o email já está em uso por outro usuário
            cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, user_id))
            if cursor.fetchone():
                st.error("Este email já está em uso por outro usuário.")
                return False
            
            # Obter dados atuais para log
            cursor.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
            old_data = cursor.fetchone()
            if not old_data:
                st.error("Usuário não encontrado.")
                return False
            
            old_name, old_email = old_data
            
            # Atualizar usuário
            cursor.execute("""
                UPDATE users 
                SET name = %s, email = %s 
                WHERE id = %s
            """, (name, email, user_id))
            
            # Log da ação
            self.log_admin_action(
                admin_user_id=admin_user_id,
                target_user_id=user_id,
                action="UPDATE_USER_PROFILE",
                old_value=f"name: {old_name}, email: {old_email}",
                new_value=f"name: {name}, email: {email}",
                details=f"Perfil atualizado: {old_name} → {name}, {old_email} → {email}"
            )
            
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            st.error(f"Erro ao atualizar perfil: {e}")
            return False
        finally:
            conn.close()

    def reset_user_password(self, user_id: int, new_password_hash: str, admin_user_id: int) -> bool:
        """Resetar senha do usuário (apenas administradores)"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Obter dados do usuário para log
            cursor.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if not user_data:
                st.error("Usuário não encontrado.")
                return False
            
            user_name, user_email = user_data
            
            # Atualizar senha
            cursor.execute("""
                UPDATE users 
                SET password_hash = %s 
                WHERE id = %s
            """, (new_password_hash, user_id))
            
            # Log da ação
            self.log_admin_action(
                admin_user_id=admin_user_id,
                target_user_id=user_id,
                action="RESET_PASSWORD",
                details=f"Senha resetada para {user_name} ({user_email})"
            )
            
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            st.error(f"Erro ao resetar senha: {e}")
            return False
        finally:
            conn.close()
    
    # MÉTODOS AVANÇADOS PARA DASHBOARD ADMINISTRATIVO
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Obter métricas completas para o dashboard administrativo"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            metrics = {}
            
            # Métricas de usuários
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
            metrics['total_active_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE last_login >= NOW() - INTERVAL '24 hours'")
            metrics['users_last_24h'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '30 days'")
            metrics['new_users_30d'] = cursor.fetchone()[0]
            
            # Métricas de dados médicos
            cursor.execute("SELECT COUNT(*) FROM lab_results")
            metrics['total_lab_results'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT test_name) FROM lab_results")
            metrics['unique_test_types'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM medical_timeline")
            metrics['total_medical_events'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM medication_history")
            metrics['total_medications'] = cursor.fetchone()[0]
            
            # Métricas de arquivos
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(OCTET_LENGTH(file_data)), 0) FROM uploaded_files")
            file_stats = cursor.fetchone()
            metrics['total_files'] = file_stats[0]
            metrics['total_file_size'] = file_stats[1]
            
            # Atividade recente (últimos 7 dias)
            cursor.execute("SELECT COUNT(*) FROM lab_results WHERE created_at >= NOW() - INTERVAL '7 days'")
            metrics['recent_lab_results'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM uploaded_files WHERE uploaded_at >= NOW() - INTERVAL '7 days'")
            metrics['recent_uploads'] = cursor.fetchone()[0]
            
            cursor.close()
            return metrics
            
        except Exception as e:
            st.error(f"Erro ao obter métricas do dashboard: {e}")
            return {}
        finally:
            conn.close()
    
    def get_login_activity_data(self, days: int = 30) -> pd.DataFrame:
        """Obter dados de atividade de login dos últimos N dias"""
        try:
            query = text("""
                SELECT DATE(last_login) as login_date, COUNT(*) as login_count
                FROM users 
                WHERE last_login >= NOW() - INTERVAL :days_param
                  AND last_login IS NOT NULL
                GROUP BY DATE(last_login)
                ORDER BY login_date
            """)
            df = pd.read_sql_query(query, self.engine, params={'days_param': f'{days} days'})
            # Normalize column names to strings to prevent mixed-type warnings
            df.columns = df.columns.astype(str)
            return df
        except Exception as e:
            st.error(f"Erro ao obter dados de login: {e}")
            return pd.DataFrame()
    
    def get_medical_trends_data(self) -> Dict[str, pd.DataFrame]:
        """Obter dados de tendências médicas para gráficos"""
        try:
            data = {}
            
            # Tendência de exames por mês
            query = """
                SELECT DATE_TRUNC('month', test_date) as month, COUNT(*) as exam_count
                FROM lab_results
                GROUP BY DATE_TRUNC('month', test_date)
                ORDER BY month
            """
            df = pd.read_sql_query(query, self.engine)
            df.columns = df.columns.astype(str)
            data['exams_by_month'] = df
            
            # Tipos de exames mais comuns
            query = """
                SELECT test_name, COUNT(*) as count
                FROM lab_results
                GROUP BY test_name
                ORDER BY count DESC
                LIMIT 10
            """
            df = pd.read_sql_query(query, self.engine)
            df.columns = df.columns.astype(str)
            data['common_tests'] = df
            
            # Timeline de eventos médicos
            query = """
                SELECT DATE_TRUNC('month', event_date) as month, COUNT(*) as event_count
                FROM medical_timeline
                GROUP BY DATE_TRUNC('month', event_date)
                ORDER BY month
            """
            df = pd.read_sql_query(query, self.engine)
            df.columns = df.columns.astype(str)
            data['medical_events_by_month'] = df
            
            # Medicamentos por categoria (usando route como proxy)
            query = """
                SELECT route, COUNT(*) as count
                FROM medication_history
                WHERE route IS NOT NULL
                GROUP BY route
                ORDER BY count DESC
            """
            df = pd.read_sql_query(query, self.engine)
            df.columns = df.columns.astype(str)
            data['medication_routes'] = df
            
            return data
            
        except Exception as e:
            st.error(f"Erro ao obter dados de tendências: {e}")
            return {}
    
    def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Obter atividade recente do sistema"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            activities = []
            
            # Últimos resultados de exames
            cursor.execute("""
                SELECT 'lab_result' as type, 
                       'Exame adicionado: ' || test_name as description,
                       created_at as timestamp,
                       created_by as user_id
                FROM lab_results
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit//4,))
            
            for row in cursor.fetchall():
                activities.append({
                    'type': row[0],
                    'description': row[1],
                    'timestamp': row[2],
                    'user_id': row[3]
                })
            
            # Últimos uploads
            cursor.execute("""
                SELECT 'file_upload' as type,
                       'Arquivo carregado: ' || filename as description,
                       uploaded_at as timestamp,
                       uploaded_by as user_id
                FROM uploaded_files
                ORDER BY uploaded_at DESC
                LIMIT %s
            """, (limit//4,))
            
            for row in cursor.fetchall():
                activities.append({
                    'type': row[0],
                    'description': row[1],
                    'timestamp': row[2],
                    'user_id': row[3]
                })
            
            # Últimos eventos médicos
            cursor.execute("""
                SELECT 'medical_event' as type,
                       'Evento médico: ' || title as description,
                       created_at as timestamp,
                       created_by as user_id
                FROM medical_timeline
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit//4,))
            
            for row in cursor.fetchall():
                activities.append({
                    'type': row[0],
                    'description': row[1],
                    'timestamp': row[2],
                    'user_id': row[3]
                })
            
            # Últimas ações administrativas (se existirem logs)
            cursor.execute("""
                SELECT 'admin_action' as type,
                       'Ação admin: ' || action as description,
                       timestamp,
                       admin_user_id as user_id
                FROM admin_audit_logs
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit//4,))
            
            for row in cursor.fetchall():
                activities.append({
                    'type': row[0],
                    'description': row[1],
                    'timestamp': row[2],
                    'user_id': row[3]
                })
            
            # Ordenar todas as atividades por timestamp
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            
            cursor.close()
            return activities[:limit]
            
        except Exception as e:
            st.error(f"Erro ao obter atividade recente: {e}")
            return []
        finally:
            conn.close()
    
    def get_system_alerts(self) -> List[Dict[str, Any]]:
        """Obter alertas e notificações do sistema"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            alerts = []
            
            # Verificar espaço de arquivos
            cursor.execute("SELECT COALESCE(SUM(OCTET_LENGTH(file_data)), 0) FROM uploaded_files")
            total_file_size = cursor.fetchone()[0]
            
            # Simular limite de 100MB
            max_size = 100 * 1024 * 1024  # 100MB
            if total_file_size > max_size * 0.8:  # 80% do limite
                alerts.append({
                    'type': 'warning',
                    'title': 'Espaço de Arquivos',
                    'message': f'Uso de arquivos próximo ao limite: {total_file_size / (1024*1024):.1f}MB de {max_size / (1024*1024)}MB',
                    'timestamp': datetime.now()
                })
            
            # Verificar atividade recente
            cursor.execute("SELECT COUNT(*) FROM users WHERE last_login >= NOW() - INTERVAL '7 days'")
            recent_logins = cursor.fetchone()[0]
            
            if recent_logins == 0:
                alerts.append({
                    'type': 'info',
                    'title': 'Baixa Atividade',
                    'message': 'Nenhum login nos últimos 7 dias',
                    'timestamp': datetime.now()
                })
            
            # Verificar uploads recentes
            cursor.execute("SELECT COUNT(*) FROM uploaded_files WHERE uploaded_at >= NOW() - INTERVAL '30 days'")
            recent_uploads = cursor.fetchone()[0]
            
            if recent_uploads > 50:  # Muitos uploads
                alerts.append({
                    'type': 'info',
                    'title': 'Alta Atividade de Upload',
                    'message': f'{recent_uploads} arquivos carregados nos últimos 30 dias',
                    'timestamp': datetime.now()
                })
            
            cursor.close()
            return alerts
            
        except Exception as e:
            st.error(f"Erro ao obter alertas: {e}")
            return []
        finally:
            conn.close()
    
    def get_database_size_info(self) -> Dict[str, Any]:
        """Obter informações sobre o tamanho do banco de dados"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            
            # Tamanho do banco atual
            cursor.execute("SELECT pg_database_size(current_database())")
            db_size = cursor.fetchone()[0]
            
            # Informações das tabelas
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)
            
            tables_info = []
            for row in cursor.fetchall():
                tables_info.append({
                    'schema': row[0],
                    'table': row[1],
                    'size_pretty': row[2],
                    'size_bytes': row[3]
                })
            
            cursor.close()
            
            return {
                'total_size_bytes': db_size,
                'total_size_pretty': self._format_bytes(db_size),
                'tables': tables_info
            }
            
        except Exception as e:
            st.error(f"Erro ao obter informações do banco: {e}")
            return {}
        finally:
            conn.close()
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Formatar bytes em formato legível"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value = int(bytes_value / 1024)
        return f"{bytes_value:.1f} TB"
    
    # ================================
    # SISTEMA DE CONFIGURAÇÕES
    # ================================
    
    def get_config(self, category: str, config_key: str) -> Optional[Any]:
        """Obter uma configuração específica do sistema"""
        conn = self.get_connection()
        if not conn:
            return None
        
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT config_value, is_encrypted
                FROM system_config 
                WHERE category = %s AND config_key = %s AND is_active = TRUE
            """, (category, config_key))
            
            result = cursor.fetchone()
            if result:
                config_value, is_encrypted = result
                config_data = json.loads(config_value)
                value = config_data.get('value')
                
                # Descriptografar se necessário
                if is_encrypted and value and is_sensitive_config(category, config_key):
                    encryption_manager = get_encryption_manager()
                    if encryption_manager.is_encryption_available():
                        decrypted_value = encryption_manager.decrypt(value)
                        return decrypted_value
                    else:
                        st.warning(f"⚠️ Valor criptografado encontrado mas sistema de criptografia indisponível para {category}.{config_key}")
                        return None
                
                return value
            return None
            
        except Exception as e:
            st.error(f"Erro ao obter configuração {category}.{config_key}: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            conn.close()
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Obter todas as configurações do sistema agrupadas por categoria"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category, config_key, config_value, description, is_encrypted
                FROM system_config 
                WHERE is_active = TRUE
                ORDER BY category, config_key
            """)
            
            configs = {}
            encryption_manager = get_encryption_manager()
            
            for row in cursor.fetchall():
                category, key, value, description, is_encrypted = row
                
                if category not in configs:
                    configs[category] = {}
                
                config_data = json.loads(value)
                raw_value = config_data.get('value')
                
                # Descriptografar se necessário
                if is_encrypted and raw_value and is_sensitive_config(category, key):
                    if encryption_manager.is_encryption_available():
                        decrypted_value = encryption_manager.decrypt(raw_value)
                        display_value = encryption_manager.mask_sensitive_value(decrypted_value) if decrypted_value else ""
                    else:
                        decrypted_value = None
                        display_value = "*** CRIPTOGRAFADO ***"
                else:
                    decrypted_value = raw_value
                    display_value = raw_value
                
                configs[category][key] = {
                    'value': decrypted_value,
                    'display_value': display_value,
                    'description': description,
                    'is_encrypted': is_encrypted,
                    'is_sensitive': is_sensitive_config(category, key)
                }
            
            return configs
            
        except Exception as e:
            st.error(f"Erro ao obter configurações: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()
            conn.close()
    
    def save_config(self, category: str, config_key: str, value: Any, user_id: int, description: Optional[str] = None) -> bool:
        """Salvar/atualizar uma configuração do sistema com BLOQUEIO CRÍTICO contra plaintext sensível"""
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = None
        try:
            cursor = conn.cursor()
            
            # VERIFICAÇÃO CRÍTICA DE SEGURANÇA
            is_sensitive = is_sensitive_config(category, config_key)
            should_encrypt = should_encrypt_config(category, config_key)
            stored_value = value
            is_encrypted = False
            
            # BLOQUEIO CRÍTICO: Nunca permitir armazenamento plaintext de configs sensíveis
            if is_sensitive and value and str(value).strip():
                st.error(f"🚨 BLOQUEIO DE SEGURANÇA: Tentativa de salvar configuração sensível {category}.{config_key}")
                
                encryption_manager = get_encryption_manager()
                if not encryption_manager.is_encryption_available():
                    critical_error = (
                        f"🚨 ERRO CRÍTICO DE SEGURANÇA: Sistema de criptografia indisponível!\n\n"
                        f"Não é possível salvar configuração sensível {category}.{config_key} sem criptografia.\n"
                        f"Configure ENCRYPTION_KEY no ambiente antes de continuar."
                    )
                    st.error(critical_error)
                    return False
                
                # Forçar criptografia para configs sensíveis
                encrypted_value = encryption_manager.encrypt(str(value))
                if not encrypted_value:
                    st.error(f"🚨 FALHA CRÍTICA: Não foi possível criptografar {category}.{config_key}")
                    st.error("Configurações sensíveis DEVEM ser criptografadas - operação bloqueada!")
                    return False
                
                stored_value = encrypted_value
                is_encrypted = True
                
                # Log crítico de segurança
                st.success(f"🔒 Configuração sensível {category}.{config_key} criptografada com sucesso")
                
            elif should_encrypt and value and str(value).strip():
                # Para outras configs que devem ser criptografadas
                encryption_manager = get_encryption_manager()
                if encryption_manager.is_encryption_available():
                    encrypted_value = encryption_manager.encrypt(str(value))
                    if encrypted_value:
                        stored_value = encrypted_value
                        is_encrypted = True
                    else:
                        st.error(f"Falha ao criptografar {category}.{config_key}")
                        return False
                else:
                    st.warning(f"Sistema de criptografia indisponível para {category}.{config_key}")
                    # Para configs não-sensíveis, permitir armazenar sem criptografia com aviso
            
            # VALIDAÇÃO FINAL: Dupla verificação antes de salvar
            if is_sensitive and not is_encrypted and value and str(value).strip():
                critical_error = (
                    f"🚨 BLOQUEIO FINAL DE SEGURANÇA: Tentativa de bypass detectada!\n\n"
                    f"Configuração sensível {category}.{config_key} não pode ser salva sem criptografia."
                )
                st.error(critical_error)
                return False
            
            # Verificar se a configuração já existe
            cursor.execute("""
                SELECT id FROM system_config 
                WHERE category = %s AND config_key = %s
            """, (category, config_key))
            
            config_value_json = json.dumps({'value': stored_value})
            
            if cursor.fetchone():
                # Atualizar configuração existente
                cursor.execute("""
                    UPDATE system_config 
                    SET config_value = %s, is_encrypted = %s, updated_at = CURRENT_TIMESTAMP, updated_by = %s
                    WHERE category = %s AND config_key = %s
                """, (config_value_json, is_encrypted, user_id, category, config_key))
            else:
                # Inserir nova configuração
                cursor.execute("""
                    INSERT INTO system_config (category, config_key, config_value, description, is_encrypted, updated_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (category, config_key, config_value_json, description, is_encrypted, user_id))
            
            conn.commit()
            
            # Log da auditoria (não logar valores sensíveis)
            log_value = "[SENSITIVE]" if is_sensitive_config(category, config_key) else str(value)
            self.log_admin_action(user_id, f"CONFIG_UPDATE_{category}", None,
                                 "", f"{config_key}={log_value}", f"Configuração {category}.{config_key} atualizada")
            
            return True
            
        except Exception as e:
            st.error(f"Erro ao salvar configuração {category}.{config_key}: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()
    
    def delete_config(self, category: str, config_key: str, user_id: int) -> bool:
        """Deletar uma configuração do sistema"""
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE system_config 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP, updated_by = %s
                WHERE category = %s AND config_key = %s
            """, (user_id, category, config_key))
            
            conn.commit()
            
            # Log da auditoria
            self.log_admin_action(user_id, f"CONFIG_DELETE_{category}", None,
                                 f"{config_key}", "", f"Configuração {category}.{config_key} removida")
            
            return True
            
        except Exception as e:
            st.error(f"Erro ao deletar configuração {category}.{config_key}: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()
    
    
    def reset_configs_to_default(self, user_id: int) -> bool:
        """Resetar todas as configurações para os valores padrão"""
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = None
        try:
            cursor = conn.cursor()
            
            # Deletar todas as configurações atuais
            cursor.execute("DELETE FROM system_config")
            
            # Recriar configurações padrão (reutilizar código do init_database)
            default_configs = [
                # Configurações SMTP/Email
                ('SMTP', 'smtp_enabled', '{"value": false}', 'Habilitar envio de emails via SMTP'),
                ('SMTP', 'smtp_host', '{"value": "smtp.gmail.com"}', 'Servidor SMTP'),
                ('SMTP', 'smtp_port', '{"value": 587}', 'Porta do servidor SMTP'),
                ('SMTP', 'smtp_username', '{"value": ""}', 'Usuário SMTP'),
                ('SMTP', 'smtp_password', '{"value": ""}', 'Senha SMTP', True),
                ('SMTP', 'smtp_use_tls', '{"value": true}', 'Usar TLS/SSL'),
                ('SMTP', 'from_email', '{"value": ""}', 'Email remetente padrão'),
                ('SMTP', 'from_name', '{"value": "Sistema Prontuário Luna"}', 'Nome do remetente'),
                
                # Configurações API/Integrações
                ('API', 'openai_enabled', '{"value": true}', 'Habilitar integração OpenAI'),
                ('API', 'openai_api_key', '{"value": ""}', 'Chave da API OpenAI', True),
                ('API', 'openai_model', '{"value": "gpt-4"}', 'Modelo OpenAI padrão'),
                ('API', 'openai_max_tokens', '{"value": 4000}', 'Limite máximo de tokens'),
                ('API', 'api_rate_limit', '{"value": 100}', 'Limite de requisições por hora'),
                ('API', 'webhook_url', '{"value": ""}', 'URL do webhook para notificações'),
                
                # Configurações de Segurança
                ('SECURITY', 'password_min_length', '{"value": 8}', 'Comprimento mínimo da senha'),
                ('SECURITY', 'password_require_special', '{"value": true}', 'Requer caracteres especiais'),
                ('SECURITY', 'password_require_numbers', '{"value": true}', 'Requer números na senha'),
                ('SECURITY', 'password_expiry_days', '{"value": 90}', 'Dias para expiração da senha (0 = nunca)'),
                ('SECURITY', 'session_timeout_minutes', '{"value": 480}', 'Timeout da sessão em minutos'),
                ('SECURITY', 'max_login_attempts', '{"value": 5}', 'Tentativas máximas de login'),
                ('SECURITY', 'audit_log_retention_days', '{"value": 365}', 'Retenção de logs de auditoria em dias'),
                ('SECURITY', 'enable_2fa', '{"value": false}', 'Habilitar autenticação de dois fatores'),
                
                # Configurações Gerais
                ('GENERAL', 'app_name', '{"value": "Prontuário Médico Digital - Luna"}', 'Nome da aplicação'),
                ('GENERAL', 'app_version', '{"value": "1.0.0"}', 'Versão da aplicação'),
                ('GENERAL', 'timezone', '{"value": "America/Sao_Paulo"}', 'Fuso horário padrão'),
                ('GENERAL', 'date_format', '{"value": "DD/MM/YYYY"}', 'Formato de data padrão'),
                ('GENERAL', 'max_file_size_mb', '{"value": 50}', 'Tamanho máximo de arquivo em MB'),
                ('GENERAL', 'allowed_file_types', '{"value": ["pdf", "jpg", "jpeg", "png", "mp3", "wav", "mp4"]}', 'Tipos de arquivo permitidos'),
                ('GENERAL', 'backup_enabled', '{"value": true}', 'Habilitar backup automático'),
                ('GENERAL', 'backup_frequency_hours', '{"value": 24}', 'Frequência de backup em horas'),
                ('GENERAL', 'maintenance_mode', '{"value": false}', 'Modo de manutenção ativo'),
            ]
            
            for config in default_configs:
                is_encrypted = len(config) > 4 and config[4]
                cursor.execute("""
                    INSERT INTO system_config (category, config_key, config_value, description, is_encrypted, updated_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (config[0], config[1], config[2], config[3], is_encrypted, user_id))
            
            conn.commit()
            
            # Log da auditoria
            self.log_admin_action(user_id, "CONFIG_RESET_ALL", None,
                                 "all_configs", "default_values", "Reset completo das configurações para padrão")
            
            return True
            
        except Exception as e:
            st.error(f"Erro ao resetar configurações: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()
    
    def test_smtp_connection(self, smtp_config: Dict[str, Any]) -> Dict[str, Any]:
        """Testar conectividade SMTP com as configurações fornecidas"""
        import smtplib
        from email.mime.text import MIMEText
        
        try:
            # Extrair configurações
            host = smtp_config.get('smtp_host', '')
            port = int(smtp_config.get('smtp_port', 587))
            username = smtp_config.get('smtp_username', '')
            password = smtp_config.get('smtp_password', '')
            use_tls = smtp_config.get('smtp_use_tls', True)
            
            if not all([host, port, username, password]):
                return {
                    'success': False,
                    'message': 'Configurações SMTP incompletas',
                    'details': 'Host, porta, usuário e senha são obrigatórios'
                }
            
            # Tentar conectar
            server = smtplib.SMTP(host, port)
            
            if use_tls:
                server.starttls()
            
            server.login(username, password)
            server.quit()
            
            return {
                'success': True,
                'message': 'Conexão SMTP estabelecida com sucesso',
                'details': f'Conectado ao {host}:{port}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': 'Falha na conexão SMTP',
                'details': str(e)
            }
    
    def export_configs(self) -> Dict[str, Any]:
        """Exportar todas as configurações para backup"""
        try:
            all_configs = self.get_all_configs()
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'export_version': '1.0',
                'configs': all_configs
            }
            
            return export_data
            
        except Exception as e:
            st.error(f"Erro ao exportar configurações: {e}")
            return {}
    
    def import_configs(self, import_data: Dict[str, Any], user_id: int) -> bool:
        """Importar configurações de backup"""
        try:
            if 'configs' not in import_data:
                st.error("Dados de importação inválidos")
                return False
            
            imported_count = 0
            
            for category, configs in import_data['configs'].items():
                for config_key, config_data in configs.items():
                    if self.save_config(category, config_key, config_data['value'], user_id, config_data.get('description')):
                        imported_count += 1
            
            # Log da auditoria
            self.log_admin_action(user_id, "CONFIG_IMPORT", None,
                                 "", f"{imported_count}_configs", f"Importação de {imported_count} configurações")
            
            st.success(f"Importação concluída: {imported_count} configurações restauradas")
            return True
            
        except Exception as e:
            st.error(f"Erro ao importar configurações: {e}")
            return False
    
    def validate_config(self, category: str, config_key: str, value: Any) -> Dict[str, Any]:
        """Validar uma configuração antes de salvar"""
        try:
            validation_rules = {
                'SMTP': {
                    'smtp_port': lambda v: isinstance(v, int) and 1 <= v <= 65535,
                    'smtp_enabled': lambda v: isinstance(v, bool),
                    'smtp_use_tls': lambda v: isinstance(v, bool),
                    'smtp_host': lambda v: isinstance(v, str) and len(v.strip()) > 0,
                    'smtp_username': lambda v: isinstance(v, str),
                    'smtp_password': lambda v: isinstance(v, str),
                    'from_email': lambda v: isinstance(v, str) and ('@' in v or v == ''),
                },
                'API': {
                    'openai_enabled': lambda v: isinstance(v, bool),
                    'openai_max_tokens': lambda v: isinstance(v, int) and v > 0,
                    'api_rate_limit': lambda v: isinstance(v, int) and v > 0,
                },
                'SECURITY': {
                    'password_min_length': lambda v: isinstance(v, int) and v >= 4,
                    'password_require_special': lambda v: isinstance(v, bool),
                    'password_require_numbers': lambda v: isinstance(v, bool),
                    'password_expiry_days': lambda v: isinstance(v, int) and v >= 0,
                    'session_timeout_minutes': lambda v: isinstance(v, int) and v > 0,
                    'max_login_attempts': lambda v: isinstance(v, int) and v > 0,
                    'audit_log_retention_days': lambda v: isinstance(v, int) and v > 0,
                    'enable_2fa': lambda v: isinstance(v, bool),
                },
                'GENERAL': {
                    'max_file_size_mb': lambda v: isinstance(v, int) and v > 0,
                    'backup_frequency_hours': lambda v: isinstance(v, int) and v > 0,
                    'maintenance_mode': lambda v: isinstance(v, bool),
                    'backup_enabled': lambda v: isinstance(v, bool),
                }
            }
            
            if category in validation_rules and config_key in validation_rules[category]:
                validator = validation_rules[category][config_key]
                if validator(value):
                    return {'valid': True, 'message': 'Configuração válida'}
                else:
                    return {'valid': False, 'message': 'Valor inválido para esta configuração'}
            
            # Se não há regra específica, aceitar
            return {'valid': True, 'message': 'Configuração aceita'}
            
        except Exception as e:
            return {'valid': False, 'message': f'Erro na validação: {e}'}
    
