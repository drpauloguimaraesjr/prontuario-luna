import psycopg2
import pandas as pd
import json
from datetime import datetime
import os
from typing import Dict, List, Optional, Any
import streamlit as st

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
                    role VARCHAR(50) DEFAULT 'USER',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Adicionar colunas role, is_active e last_login se não existirem (para compatibilidade)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'USER'")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP")
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
                    INSERT INTO users (email, password_hash, name, role, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """, ("admin@admin.com", password_hash, "Administrador", ROLE_SUPER_ADMIN, True))
            
            # Atualizar usuários existentes sem role para USER (compatibilidade)
            cursor.execute("UPDATE users SET role = %s WHERE role IS NULL", (ROLE_USER,))
            cursor.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")
            
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
        conn = self.get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            query = """
                SELECT DATE(last_login) as login_date, COUNT(*) as login_count
                FROM users 
                WHERE last_login >= NOW() - INTERVAL '%s days'
                  AND last_login IS NOT NULL
                GROUP BY DATE(last_login)
                ORDER BY login_date
            """
            df = pd.read_sql_query(query, conn, params=[days])
            return df
        except Exception as e:
            st.error(f"Erro ao obter dados de login: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def get_medical_trends_data(self) -> Dict[str, pd.DataFrame]:
        """Obter dados de tendências médicas para gráficos"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        try:
            data = {}
            
            # Tendência de exames por mês
            query = """
                SELECT DATE_TRUNC('month', test_date) as month, COUNT(*) as exam_count
                FROM lab_results
                GROUP BY DATE_TRUNC('month', test_date)
                ORDER BY month
            """
            data['exams_by_month'] = pd.read_sql_query(query, conn)
            
            # Tipos de exames mais comuns
            query = """
                SELECT test_name, COUNT(*) as count
                FROM lab_results
                GROUP BY test_name
                ORDER BY count DESC
                LIMIT 10
            """
            data['common_tests'] = pd.read_sql_query(query, conn)
            
            # Timeline de eventos médicos
            query = """
                SELECT DATE_TRUNC('month', event_date) as month, COUNT(*) as event_count
                FROM medical_timeline
                GROUP BY DATE_TRUNC('month', event_date)
                ORDER BY month
            """
            data['medical_events_by_month'] = pd.read_sql_query(query, conn)
            
            # Medicamentos por categoria (usando route como proxy)
            query = """
                SELECT route, COUNT(*) as count
                FROM medication_history
                WHERE route IS NOT NULL
                GROUP BY route
                ORDER BY count DESC
            """
            data['medication_routes'] = pd.read_sql_query(query, conn)
            
            return data
            
        except Exception as e:
            st.error(f"Erro ao obter dados de tendências: {e}")
            return {}
        finally:
            conn.close()
    
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
    
