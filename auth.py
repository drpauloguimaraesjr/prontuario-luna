import bcrypt
import streamlit as st
import psycopg2
import os
from typing import Optional, Dict, Any

# Import role constants from database module
from database import ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER, ALL_ROLES

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
                SELECT id, email, password_hash, name, role, is_active 
                FROM users 
                WHERE email = %s AND is_active = TRUE
            """, (email,))
            
            user_data = cursor.fetchone()
            cursor.close()
            
            if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data[2].encode('utf-8')):
                return {
                    'id': user_data[0],
                    'email': user_data[1],
                    'name': user_data[3],
                    'role': user_data[4] or ROLE_USER,
                    'is_active': user_data[5]
                }
            
            return None
            
        except Exception as e:
            st.error(f"Erro na autenticação: {e}")
            return None
        finally:
            conn.close()
    
    def create_user(self, email: str, password: str, name: str, role: str = ROLE_USER, is_active: bool = True) -> bool:
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
            
            # Validar role
            if role not in ALL_ROLES:
                st.error(f"Role inválido: {role}")
                return False
            
            # Criptografar senha e criar usuário
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                INSERT INTO users (email, password_hash, name, role, is_active)
                VALUES (%s, %s, %s, %s, %s)
            """, (email, password_hash, name, role, is_active))
            
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
    
    def has_permission(self, required_role: str) -> bool:
        """Verificar se o usuário atual tem permissão para o role especificado"""
        current_user = self.get_current_user()
        if not current_user:
            return False
        
        user_role = current_user.get('role', ROLE_USER)
        
        # SUPER_ADMIN tem acesso a tudo
        if user_role == ROLE_SUPER_ADMIN:
            return True
        
        # ADMIN tem acesso a funções de ADMIN e USER
        if user_role == ROLE_ADMIN and required_role in [ROLE_ADMIN, ROLE_USER]:
            return True
        
        # USER só tem acesso a funções de USER
        if user_role == ROLE_USER and required_role == ROLE_USER:
            return True
        
        return False
    
    def is_super_admin(self) -> bool:
        """Verificar se o usuário atual é SUPER_ADMIN"""
        return self.has_permission(ROLE_SUPER_ADMIN)
    
    def is_admin(self) -> bool:
        """Verificar se o usuário atual é ADMIN ou superior"""
        current_user = self.get_current_user()
        if not current_user:
            return False
        
        user_role = current_user.get('role', ROLE_USER)
        return user_role in [ROLE_ADMIN, ROLE_SUPER_ADMIN]
    
    def is_user(self) -> bool:
        """Verificar se o usuário atual é um USER autenticado"""
        return self.has_permission(ROLE_USER)
    
    def require_role(self, required_role: str, redirect_to_login: bool = True) -> bool:
        """Exigir que o usuário tenha um role específico"""
        if not self.require_auth(redirect_to_login):
            return False
        
        if not self.has_permission(required_role):
            st.error(f"Acesso negado. Você precisa do nível de acesso '{required_role}' para acessar esta funcionalidade.")
            return False
        
        return True
    
    def update_user_role(self, user_id: int, new_role: str, db_manager=None) -> bool:
        """Atualizar o role de um usuário (apenas SUPER_ADMIN) com proteções anti-lockout"""
        current_user = self.get_current_user()
        if not current_user or not self.is_super_admin():
            st.error("Apenas SUPER_ADMIN pode alterar roles de usuários.")
            return False
        
        if new_role not in ALL_ROLES:
            st.error(f"Role inválido: {new_role}")
            return False
        
        # PROTEÇÃO 1: Prevenir auto-modificação
        if user_id == current_user['id']:
            st.error("🚫 Proteção Anti-Lockout: Você não pode alterar seu próprio role. Peça para outro SUPER_ADMIN fazer esta alteração.")
            return False
        
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Obter informações atuais do usuário alvo
            cursor.execute("SELECT name, email, role FROM users WHERE id = %s", (user_id,))
            target_user = cursor.fetchone()
            if not target_user:
                st.error("Usuário não encontrado.")
                return False
            
            old_role = target_user[2]
            target_name = target_user[0]
            target_email = target_user[1]
            
            # PROTEÇÃO 2: Prevenir remoção do último SUPER_ADMIN
            if old_role == ROLE_SUPER_ADMIN and new_role != ROLE_SUPER_ADMIN:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM users 
                    WHERE role = %s AND is_active = TRUE
                """, (ROLE_SUPER_ADMIN,))
                super_admin_count = cursor.fetchone()[0]
                
                if super_admin_count <= 1:
                    st.error("🚫 Proteção Anti-Lockout: Não é possível remover o último SUPER_ADMIN do sistema. Crie outro SUPER_ADMIN primeiro.")
                    return False
            
            # Executar a atualização
            cursor.execute("""
                UPDATE users 
                SET role = %s 
                WHERE id = %s
            """, (new_role, user_id))
            
            # Log da ação administrativa
            if db_manager:
                db_manager.log_admin_action(
                    admin_user_id=current_user['id'],
                    target_user_id=user_id,
                    action=f"UPDATE_USER_ROLE",
                    old_value=old_role,
                    new_value=new_role,
                    details=f"Role alterado de {old_role} para {new_role} para {target_name} ({target_email})"
                )
            
            conn.commit()
            cursor.close()
            st.success(f"✅ Role do usuário {target_name} alterado de {old_role} para {new_role}")
            return True
            
        except Exception as e:
            st.error(f"Erro ao atualizar role do usuário: {e}")
            return False
        finally:
            conn.close()
    
    def deactivate_user(self, user_id: int, db_manager=None) -> bool:
        """Desativar um usuário (apenas SUPER_ADMIN) com proteções anti-lockout"""
        current_user = self.get_current_user()
        if not current_user or not self.is_super_admin():
            st.error("Apenas SUPER_ADMIN pode desativar usuários.")
            return False
        
        # PROTEÇÃO 1: Prevenir auto-desativação
        if user_id == current_user['id']:
            st.error("🚫 Proteção Anti-Lockout: Você não pode desativar sua própria conta. Peça para outro SUPER_ADMIN fazer esta alteração.")
            return False
        
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Obter informações do usuário alvo
            cursor.execute("SELECT name, email, role, is_active FROM users WHERE id = %s", (user_id,))
            target_user = cursor.fetchone()
            if not target_user:
                st.error("Usuário não encontrado.")
                return False
            
            target_name, target_email, target_role, is_active = target_user
            
            if not is_active:
                st.warning(f"Usuário {target_name} já está desativado.")
                return True
            
            # PROTEÇÃO 2: Prevenir desativação do último SUPER_ADMIN
            if target_role == ROLE_SUPER_ADMIN:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM users 
                    WHERE role = %s AND is_active = TRUE
                """, (ROLE_SUPER_ADMIN,))
                super_admin_count = cursor.fetchone()[0]
                
                if super_admin_count <= 1:
                    st.error("🚫 Proteção Anti-Lockout: Não é possível desativar o último SUPER_ADMIN ativo do sistema.")
                    return False
            
            # Executar a desativação
            cursor.execute("""
                UPDATE users 
                SET is_active = FALSE 
                WHERE id = %s
            """, (user_id,))
            
            # Log da ação administrativa
            if db_manager:
                db_manager.log_admin_action(
                    admin_user_id=current_user['id'],
                    target_user_id=user_id,
                    action="DEACTIVATE_USER",
                    old_value="ACTIVE",
                    new_value="INACTIVE",
                    details=f"Usuário {target_name} ({target_email}) desativado"
                )
            
            conn.commit()
            cursor.close()
            st.success(f"✅ Usuário {target_name} foi desativado com sucesso.")
            return True
            
        except Exception as e:
            st.error(f"Erro ao desativar usuário: {e}")
            return False
        finally:
            conn.close()
    
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
    
    def show_user_management(self, db_manager=None):
        """Exibir interface de gerenciamento de usuários (apenas admin)"""
        current_user = self.get_current_user()
        if not current_user:
            return
        
        # Verificar se o usuário tem permissão para gerenciar usuários
        if not self.is_admin():
            st.error("Acesso negado. Apenas administradores podem gerenciar usuários.")
            return
        
        st.subheader("👥 Gerenciamento de Usuários")
        
        # Criar formulário de novo usuário
        with st.expander("Criar Novo Usuário"):
            with st.form("create_user_form"):
                new_email = st.text_input("Email do novo usuário")
                new_password = st.text_input("Senha", type="password")
                new_name = st.text_input("Nome completo")
                
                # Seleção de role - apenas SUPER_ADMIN pode criar outros ADMIN
                current_role = current_user.get('role', ROLE_USER)
                if current_role == ROLE_SUPER_ADMIN:
                    available_roles = ALL_ROLES
                else:
                    available_roles = [ROLE_USER]  # ADMIN só pode criar USER
                
                new_role = st.selectbox(
                    "Nível de Acesso",
                    available_roles,
                    index=available_roles.index(ROLE_USER) if ROLE_USER in available_roles else 0,
                    help="SUPER_ADMIN: Acesso total | ADMIN: Gerencia usuários e dados | USER: Acesso básico"
                )
                
                new_is_active = st.checkbox("Usuário ativo", value=True)
                
                if st.form_submit_button("Criar Usuário"):
                    if new_email and new_password and new_name:
                        if self.create_user(new_email, new_password, new_name, new_role, new_is_active):
                            # Log da criação de usuário
                            if db_manager:
                                db_manager.log_admin_action(
                                    admin_user_id=current_user['id'],
                                    action="CREATE_USER",
                                    details=f"Usuário criado: {new_name} ({new_email}) com role {new_role}"
                                )
                            st.success("Usuário criado com sucesso!")
                            st.rerun()
                    else:
                        st.error("Por favor, preencha todos os campos.")
        
        # Listar usuários existentes
        self._show_user_list(db_manager)
    
    def _show_user_list(self, db_manager=None):
        """Mostrar lista de usuários existentes"""
        conn = self.get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, name, role, is_active, created_at 
                FROM users 
                ORDER BY created_at DESC
            """)
            
            users = cursor.fetchall()
            cursor.close()
            
            if users:
                st.write("**Usuários Cadastrados:**")
                
                # Headers
                col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 1.5, 1, 1, 1])
                with col1:
                    st.write("**Nome**")
                with col2:
                    st.write("**Email**")
                with col3:
                    st.write("**Role**")
                with col4:
                    st.write("**Status**")
                with col5:
                    st.write("**Data**")
                with col6:
                    st.write("**Ações**")
                
                st.markdown("---")
                
                current_user = self.get_current_user()
                current_user_id = current_user.get('id') if current_user else None
                
                for user in users:
                    user_id, email, name, role, is_active, created_at = user
                    role = role or ROLE_USER
                    
                    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 1.5, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{name}**")
                    
                    with col2:
                        st.write(email)
                    
                    with col3:
                        role_color = {
                            ROLE_SUPER_ADMIN: "🔴",
                            ROLE_ADMIN: "🟡",
                            ROLE_USER: "🟢"
                        }.get(role, "⚪")
                        st.write(f"{role_color} {role}")
                    
                    with col4:
                        status_icon = "✅" if is_active else "❌"
                        status_text = "Ativo" if is_active else "Inativo"
                        st.write(f"{status_icon} {status_text}")
                    
                    with col5:
                        st.write(created_at.strftime('%d/%m/%Y'))
                    
                    with col6:
                        # Apenas SUPER_ADMIN pode editar outros usuários
                        # e não pode editar a si próprio (para evitar lockout)
                        if self.is_super_admin() and user_id != current_user_id:
                            if st.button(f"✏️", key=f"edit_{user_id}", help="Editar usuário"):
                                self._show_user_edit_modal(user_id, name, email, role, is_active, db_manager)
                        elif user_id == current_user_id:
                            # Indicar proteção anti-lockout
                            st.write("🔒 *Você* (protegido)")
                        else:
                            st.write("-")
            else:
                st.info("Nenhum usuário cadastrado.")
                
        except Exception as e:
            st.error(f"Erro ao listar usuários: {e}")
        finally:
            conn.close()
    
    def _show_user_edit_modal(self, user_id: int, name: str, email: str, current_role: str, is_active: bool, db_manager=None):
        """Mostrar modal de edição de usuário com proteções de segurança"""
        st.write(f"**Editando usuário:** {name}")
        
        with st.form(f"edit_user_{user_id}"):
            # Role selection
            new_role = st.selectbox(
                "Role",
                ALL_ROLES,
                index=ALL_ROLES.index(current_role) if current_role in ALL_ROLES else 0,
                help="SUPER_ADMIN: Acesso total | ADMIN: Gerencia usuários e dados | USER: Acesso básico"
            )
            
            # Active status
            new_is_active = st.checkbox("Usuário ativo", value=is_active)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Salvar", type="primary"):
                    success = True
                    
                    # Update role if changed
                    if new_role != current_role:
                        if not self.update_user_role(user_id, new_role, db_manager):
                            success = False
                    
                    # Update active status if changed
                    if new_is_active != is_active and not new_is_active:
                        if not self.deactivate_user(user_id, db_manager):
                            success = False
                    elif new_is_active != is_active and new_is_active:
                        # Reactivate user with proper security checks
                        if not self.reactivate_user(user_id, db_manager):
                            success = False
                    
                    if success:
                        st.success("Usuário atualizado com sucesso!")
                        st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Cancelar"):
                    st.rerun()
    
    def reactivate_user(self, user_id: int, db_manager=None) -> bool:
        """Reativar um usuário desativado (apenas SUPER_ADMIN)"""
        current_user = self.get_current_user()
        if not current_user or not self.is_super_admin():
            st.error("Apenas SUPER_ADMIN pode reativar usuários.")
            return False
        
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Obter informações do usuário alvo
            cursor.execute("SELECT name, email, role, is_active FROM users WHERE id = %s", (user_id,))
            target_user = cursor.fetchone()
            if not target_user:
                st.error("Usuário não encontrado.")
                return False
            
            target_name, target_email, target_role, is_active = target_user
            
            if is_active:
                st.warning(f"Usuário {target_name} já está ativo.")
                return True
            
            # Executar a reativação
            cursor.execute("""
                UPDATE users 
                SET is_active = TRUE 
                WHERE id = %s
            """, (user_id,))
            
            # Log da ação administrativa
            if db_manager:
                db_manager.log_admin_action(
                    admin_user_id=current_user['id'],
                    target_user_id=user_id,
                    action="REACTIVATE_USER",
                    old_value="INACTIVE",
                    new_value="ACTIVE",
                    details=f"Usuário {target_name} ({target_email}) reativado"
                )
            
            conn.commit()
            cursor.close()
            st.success(f"✅ Usuário {target_name} foi reativado com sucesso.")
            return True
            
        except Exception as e:
            st.error(f"Erro ao reativar usuário: {e}")
            return False
        finally:
            conn.close()
