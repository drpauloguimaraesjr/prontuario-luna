import bcrypt
import streamlit as st
import psycopg2
import os
from typing import Optional, Dict, Any

class AuthManager:
    """Gerencia autenticação de usuário e gerenciamento de sessão"""
    
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('PGHOST'),
            'database': os.getenv('PGDATABASE'),
            'user': os.getenv('PGUSER'),
            'password': os.getenv('PGPASSWORD'),
            'port': os.getenv('PGPORT', 5432)
        }
    
    def get_connection(self):
        """Obter conexão com o banco de dados"""
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            st.error(f"Erro ao conectar com o banco de dados: {e}")
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Autenticar usuário com email e senha"""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, password_hash, name 
                FROM users 
                WHERE email = %s
            """, (email,))
            
            user_data = cursor.fetchone()
            cursor.close()
            
            if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data[2].encode('utf-8')):
                return {
                    'id': user_data[0],
                    'email': user_data[1],
                    'name': user_data[3]
                }
            
            return None
            
        except Exception as e:
            st.error(f"Erro na autenticação: {e}")
            return None
        finally:
            conn.close()
    
    def create_user(self, email: str, password: str, name: str) -> bool:
        """Criar um novo usuário"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Verificar se o usuário já existe
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                st.error("Usuário já existe com este email.")
                return False
            
            # Criptografar senha e criar usuário
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                INSERT INTO users (email, password_hash, name)
                VALUES (%s, %s, %s)
            """, (email, password_hash, name))
            
            conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            st.error(f"Erro ao criar usuário: {e}")
            return False
        finally:
            conn.close()
    
    def is_authenticated(self) -> bool:
        """Verificar se o usuário está autenticado na sessão atual"""
        return st.session_state.get('authenticated', False)
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Obter usuário autenticado atual"""
        if self.is_authenticated():
            return st.session_state.get('user')
        return None
    
    def login(self, user_data: Dict[str, Any]):
        """Fazer login do usuário (definir estado da sessão)"""
        st.session_state['authenticated'] = True
        st.session_state['user'] = user_data
    
    def logout(self):
        """Fazer logout do usuário (limpar estado da sessão)"""
        if 'authenticated' in st.session_state:
            del st.session_state['authenticated']
        if 'user' in st.session_state:
            del st.session_state['user']
    
    def require_auth(self, redirect_to_login: bool = True) -> bool:
        """Exigir autenticação para acessar uma página"""
        if not self.is_authenticated():
            if redirect_to_login:
                st.warning("Acesso não autorizado. Faça login para continuar.")
                self.show_login_form()
            return False
        return True
    
    def show_login_form(self):
        """Exibir formulário de login"""
        st.markdown("### 🔐 Login Administrativo")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="admin@admin.com")
            password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            
            col1, col2 = st.columns(2)
            with col1:
                login_button = st.form_submit_button("Entrar", type="primary")
            with col2:
                cancel_button = st.form_submit_button("Cancelar")
            
            if login_button:
                if email and password:
                    user = self.authenticate_user(email, password)
                    if user:
                        self.login(user)
                        st.success(f"Bem-vindo, {user['name']}!")
                        st.rerun()
                    else:
                        st.error("Email ou senha incorretos.")
                else:
                    st.error("Por favor, preencha todos os campos.")
            
            if cancel_button:
                st.query_params.clear()
                st.rerun()
    
    def show_user_management(self):
        """Exibir interface de gerenciamento de usuários (apenas admin)"""
        current_user = self.get_current_user()
        if not current_user:
            return
        
        st.subheader("👥 Gerenciamento de Usuários")
        
        # Criar formulário de novo usuário
        with st.expander("Criar Novo Usuário"):
            with st.form("create_user_form"):
                new_email = st.text_input("Email do novo usuário")
                new_password = st.text_input("Senha", type="password")
                new_name = st.text_input("Nome completo")
                
                if st.form_submit_button("Criar Usuário"):
                    if new_email and new_password and new_name:
                        if self.create_user(new_email, new_password, new_name):
                            st.success("Usuário criado com sucesso!")
                            st.rerun()
                    else:
                        st.error("Por favor, preencha todos os campos.")
        
        # Listar usuários existentes
        self._show_user_list()
    
    def _show_user_list(self):
        """Mostrar lista de usuários existentes"""
        conn = self.get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, name, created_at 
                FROM users 
                ORDER BY created_at DESC
            """)
            
            users = cursor.fetchall()
            cursor.close()
            
            if users:
                st.write("**Usuários Cadastrados:**")
                for user in users:
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"**{user[2]}**")
                    with col2:
                        st.write(user[1])
                    with col3:
                        st.write(user[3].strftime('%d/%m/%Y'))
            else:
                st.info("Nenhum usuário cadastrado.")
                
        except Exception as e:
            st.error(f"Erro ao listar usuários: {e}")
        finally:
            conn.close()
