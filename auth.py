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
    
    def login(self, user_data: Dict[str, Any], db_manager=None):
        """Fazer login do usuário (definir estado da sessão)"""
        st.session_state['authenticated'] = True
        st.session_state['user'] = user_data
        
        # Atualizar último login no banco de dados
        if db_manager and user_data.get('id'):
            db_manager.update_last_login(user_data['id'])
    
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
        """Exibir interface avançada de gerenciamento de usuários"""
        current_user = self.get_current_user()
        if not current_user:
            return
        
        # Verificar permissões
        if not self.is_admin():
            st.error("🚫 Acesso negado. Apenas administradores podem gerenciar usuários.")
            return
        
        st.markdown("# 👥 Gestão Avançada de Usuários")
        
        # Estatísticas resumidas
        if db_manager:
            self._show_user_statistics(db_manager)
        
        # Filtros e busca
        self._show_user_filters()
        
        # Criar novo usuário
        self._show_create_user_form(current_user, db_manager)
        
        # Lista de usuários com paginação
        self._show_enhanced_user_list(db_manager)
        
        # Funcionalidades extras
        self._show_additional_features(db_manager)
    
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

    def _show_user_statistics(self, db_manager):
        """Exibir estatísticas resumidas dos usuários"""
        st.markdown("## 📊 Estatísticas")
        
        stats = db_manager.get_user_statistics()
        if not stats:
            st.warning("Não foi possível carregar as estatísticas.")
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("👥 Total de Usuários", stats.get('total', 0))
        
        with col2:
            st.metric("✅ Usuários Ativos", stats.get('active', 0))
        
        with col3:
            st.metric("❌ Usuários Inativos", stats.get('inactive', 0))
        
        with col4:
            active_rate = (stats.get('active', 0) / max(stats.get('total', 1), 1)) * 100
            st.metric("📈 Taxa de Atividade", f"{active_rate:.1f}%")
        
        # Estatísticas por role
        st.markdown("### Usuários por Nível de Acesso")
        role_col1, role_col2, role_col3 = st.columns(3)
        
        with role_col1:
            st.metric("🔴 SUPER_ADMIN", stats.get('role_super_admin', 0))
        
        with role_col2:
            st.metric("🟡 ADMIN", stats.get('role_admin', 0))
        
        with role_col3:
            st.metric("🟢 USER", stats.get('role_user', 0))
        
        st.markdown("---")
    
    def _show_user_filters(self):
        """Exibir interface de busca e filtros"""
        st.markdown("## 🔍 Busca e Filtros")
        
        # Inicializar valores de filtro no estado da sessão
        if 'user_search_term' not in st.session_state:
            st.session_state.user_search_term = ""
        if 'user_role_filter' not in st.session_state:
            st.session_state.user_role_filter = "ALL"
        if 'user_status_filter' not in st.session_state:
            st.session_state.user_status_filter = "ALL"
        if 'user_page' not in st.session_state:
            st.session_state.user_page = 0
        
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        
        with col1:
            search_term = st.text_input(
                "🔍 Buscar por nome ou email",
                value=st.session_state.user_search_term,
                placeholder="Digite nome ou email...",
                help="Busca em tempo real por nome ou email"
            )
            if search_term != st.session_state.user_search_term:
                st.session_state.user_search_term = search_term
                st.session_state.user_page = 0  # Reset page on search
        
        with col2:
            role_filter = st.selectbox(
                "👤 Filtrar por Role",
                ["ALL", ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER],
                index=["ALL", ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER].index(st.session_state.user_role_filter),
                help="Filtrar usuários por nível de acesso"
            )
            if role_filter != st.session_state.user_role_filter:
                st.session_state.user_role_filter = role_filter
                st.session_state.user_page = 0  # Reset page on filter change
        
        with col3:
            status_filter = st.selectbox(
                "📊 Filtrar por Status",
                ["ALL", "ACTIVE", "INACTIVE"],
                index=["ALL", "ACTIVE", "INACTIVE"].index(st.session_state.user_status_filter),
                help="Filtrar usuários por status de atividade"
            )
            if status_filter != st.session_state.user_status_filter:
                st.session_state.user_status_filter = status_filter
                st.session_state.user_page = 0  # Reset page on filter change
        
        with col4:
            if st.button("🔄 Limpar Filtros", help="Limpar todos os filtros de busca"):
                st.session_state.user_search_term = ""
                st.session_state.user_role_filter = "ALL"
                st.session_state.user_status_filter = "ALL"
                st.session_state.user_page = 0
                st.rerun()
        
        st.markdown("---")
    
    def _show_create_user_form(self, current_user, db_manager):
        """Exibir formulário aprimorado de criação de usuário"""
        with st.expander("➕ Criar Novo Usuário", expanded=False):
            st.markdown("### Informações do Novo Usuário")
            
            with st.form("create_user_form_enhanced"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_name = st.text_input(
                        "Nome Completo *",
                        placeholder="Ex: João Silva",
                        help="Nome completo do usuário"
                    )
                    new_email = st.text_input(
                        "Email *",
                        placeholder="joao@exemplo.com",
                        help="Email único do usuário para login"
                    )
                
                with col2:
                    new_password = st.text_input(
                        "Senha *",
                        type="password",
                        placeholder="Mínimo 8 caracteres",
                        help="Senha forte recomendada"
                    )
                    confirm_password = st.text_input(
                        "Confirmar Senha *",
                        type="password",
                        placeholder="Digite a senha novamente"
                    )
                
                # Seleção de role com restrições
                current_role = current_user.get('role', ROLE_USER)
                if current_role == ROLE_SUPER_ADMIN:
                    available_roles = ALL_ROLES
                    role_help = "SUPER_ADMIN: Acesso total | ADMIN: Gerencia usuários e dados | USER: Acesso básico"
                else:
                    available_roles = [ROLE_USER]
                    role_help = "Apenas SUPER_ADMIN pode criar outros administradores"
                
                col3, col4 = st.columns(2)
                
                with col3:
                    new_role = st.selectbox(
                        "Nível de Acesso",
                        available_roles,
                        index=available_roles.index(ROLE_USER) if ROLE_USER in available_roles else 0,
                        help=role_help
                    )
                
                with col4:
                    new_is_active = st.checkbox(
                        "Usuário ativo",
                        value=True,
                        help="Desmarque para criar usuário inativo"
                    )
                
                # Botões do formulário
                col5, col6 = st.columns(2)
                
                with col5:
                    create_button = st.form_submit_button(
                        "✅ Criar Usuário",
                        type="primary",
                        use_container_width=True
                    )
                
                with col6:
                    cancel_button = st.form_submit_button(
                        "❌ Cancelar",
                        use_container_width=True
                    )
                
                # Validação e criação
                if create_button:
                    # Validações
                    errors = []
                    
                    if not new_name or len(new_name.strip()) < 2:
                        errors.append("Nome deve ter pelo menos 2 caracteres")
                    
                    if not new_email or '@' not in new_email or '.' not in new_email:
                        errors.append("Email inválido")
                    
                    if not new_password or len(new_password) < 8:
                        errors.append("Senha deve ter pelo menos 8 caracteres")
                    
                    if new_password != confirm_password:
                        errors.append("Senhas não coincidem")
                    
                    if errors:
                        for error in errors:
                            st.error(f"❌ {error}")
                    else:
                        # Criar usuário
                        if self.create_user(new_email.strip(), new_password, new_name.strip(), new_role, new_is_active):
                            # Log da criação
                            if db_manager:
                                db_manager.log_admin_action(
                                    admin_user_id=current_user['id'],
                                    action="CREATE_USER",
                                    details=f"Usuário criado: {new_name.strip()} ({new_email.strip()}) com role {new_role}"
                                )
                            st.success(f"✅ Usuário {new_name.strip()} criado com sucesso!")
                            st.rerun()
                
                if cancel_button:
                    st.info("Criação de usuário cancelada.")
    
    def _show_enhanced_user_list(self, db_manager):
        """Exibir lista avançada de usuários com paginação"""
        if not db_manager:
            st.error("Database manager não disponível.")
            return
        
        st.markdown("## 👥 Lista de Usuários")
        
        # Configurações de paginação
        USERS_PER_PAGE = 10
        current_page = st.session_state.get('user_page', 0)
        offset = current_page * USERS_PER_PAGE
        
        # Buscar usuários com filtros
        result = db_manager.get_users_with_filters(
            search_term=st.session_state.get('user_search_term', ''),
            role_filter=st.session_state.get('user_role_filter', 'ALL'),
            status_filter=st.session_state.get('user_status_filter', 'ALL'),
            offset=offset,
            limit=USERS_PER_PAGE
        )
        
        users = result.get('users', [])
        total_users = result.get('total', 0)
        total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE
        
        # Informações de paginação
        if total_users > 0:
            start_item = offset + 1
            end_item = min(offset + USERS_PER_PAGE, total_users)
            st.info(f"📄 Exibindo {start_item}-{end_item} de {total_users} usuários (Página {current_page + 1} de {total_pages})")
        
        # Controles de paginação (topo)
        if total_pages > 1:
            self._show_pagination_controls(current_page, total_pages, "top")
        
        # Exibir usuários em cards
        if users:
            for user in users:
                self._render_user_card(user, db_manager)
        else:
            st.info("🔍 Nenhum usuário encontrado com os filtros aplicados.")
        
        # Controles de paginação (rodapé)
        if total_pages > 1:
            self._show_pagination_controls(current_page, total_pages, "bottom")
    
    def _show_pagination_controls(self, current_page, total_pages, position):
        """Exibir controles de paginação"""
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if current_page > 0:
                if st.button("⏮️ Primeira", key=f"first_{position}"):
                    st.session_state.user_page = 0
                    st.rerun()
        
        with col2:
            if current_page > 0:
                if st.button("◀️ Anterior", key=f"prev_{position}"):
                    st.session_state.user_page = current_page - 1
                    st.rerun()
        
        with col3:
            st.markdown(f"**Página {current_page + 1} de {total_pages}**")
        
        with col4:
            if current_page < total_pages - 1:
                if st.button("▶️ Próxima", key=f"next_{position}"):
                    st.session_state.user_page = current_page + 1
                    st.rerun()
        
        with col5:
            if current_page < total_pages - 1:
                if st.button("⏭️ Última", key=f"last_{position}"):
                    st.session_state.user_page = total_pages - 1
                    st.rerun()
    
    def _render_user_card(self, user, db_manager):
        """Renderizar card de usuário individual"""
        current_user = self.get_current_user()
        current_user_id = current_user.get('id') if current_user else None
        
        # Determinar se pode editar este usuário
        can_edit = (self.is_super_admin() and user['id'] != current_user_id) or \
                   (self.is_admin() and user['role'] == ROLE_USER)
        
        # Card do usuário
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            # Informações básicas
            with col1:
                role_icons = {
                    ROLE_SUPER_ADMIN: "🔴",
                    ROLE_ADMIN: "🟡",
                    ROLE_USER: "🟢"
                }
                role_icon = role_icons.get(user['role'], "⚪")
                
                st.markdown(f"**{role_icon} {user['name']}**")
                st.markdown(f"📧 {user['email']}")
                st.markdown(f"🎯 Role: {user['role']}")
            
            # Status e datas
            with col2:
                status_icon = "✅" if user['is_active'] else "❌"
                status_text = "Ativo" if user['is_active'] else "Inativo"
                st.markdown(f"**Status:** {status_icon} {status_text}")
                
                if user['created_at']:
                    st.markdown(f"📅 **Criado:** {user['created_at'].strftime('%d/%m/%Y')}")
            
            # Último login
            with col3:
                if user['last_login']:
                    st.markdown(f"🕐 **Último login:** {user['last_login'].strftime('%d/%m/%Y %H:%M')}")
                else:
                    st.markdown("🕐 **Último login:** Nunca")
            
            # Ações
            with col4:
                if can_edit:
                    if st.button(f"✏️ Editar", key=f"edit_user_{user['id']}", use_container_width=True):
                        st.session_state[f'edit_modal_{user["id"]}'] = True
                        st.rerun()
                    
                    if st.button(f"🔑 Reset Senha", key=f"reset_pwd_{user['id']}", use_container_width=True):
                        st.session_state[f'reset_modal_{user["id"]}'] = True
                        st.rerun()
                else:
                    st.markdown("*Sem permissões*")
            
            # Modais de edição
            self._handle_user_modals(user, db_manager)
            
            st.markdown("---")
    
    def _handle_user_modals(self, user, db_manager):
        """Gerenciar modais de edição e reset de senha"""
        user_id = user['id']
        
        # Modal de edição
        if st.session_state.get(f'edit_modal_{user_id}'):
            with st.expander(f"✏️ Editando: {user['name']}", expanded=True):
                self._show_edit_user_modal_new(user, db_manager)
        
        # Modal de reset de senha
        if st.session_state.get(f'reset_modal_{user_id}'):
            with st.expander(f"🔑 Reset de Senha: {user['name']}", expanded=True):
                self._show_reset_password_modal(user, db_manager)
    
    def _show_edit_user_modal_new(self, user, db_manager):
        """Modal para editar usuário"""
        user_id = user['id']
        
        with st.form(f"edit_user_form_{user_id}"):
            st.markdown("### Editar Informações do Usuário")
            
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Nome", value=user['name'])
                new_email = st.text_input("Email", value=user['email'])
            
            with col2:
                new_role = st.selectbox(
                    "Role",
                    ALL_ROLES,
                    index=ALL_ROLES.index(user['role']),
                    disabled=not self.is_super_admin()
                )
                new_is_active = st.checkbox("Usuário ativo", value=user['is_active'])
            
            col3, col4, col5 = st.columns(3)
            
            with col3:
                if st.form_submit_button("💾 Salvar", type="primary"):
                    success = True
                    current_user = self.get_current_user()
                    
                    # Atualizar perfil se nome/email mudaram
                    if new_name != user['name'] or new_email != user['email']:
                        if current_user and not db_manager.update_user_profile(user_id, new_name, new_email, current_user['id']):
                            success = False
                    
                    # Atualizar role se mudou (apenas SUPER_ADMIN)
                    if new_role != user['role'] and self.is_super_admin():
                        if not self.update_user_role(user_id, new_role, db_manager):
                            success = False
                    
                    # Atualizar status se mudou
                    if new_is_active != user['is_active']:
                        if new_is_active:
                            if not self.reactivate_user(user_id, db_manager):
                                success = False
                        else:
                            if not self.deactivate_user(user_id, db_manager):
                                success = False
                    
                    if success:
                        st.success("✅ Usuário atualizado com sucesso!")
                        del st.session_state[f'edit_modal_{user_id}']
                        st.rerun()
            
            with col4:
                if st.form_submit_button("❌ Cancelar"):
                    del st.session_state[f'edit_modal_{user_id}']
                    st.rerun()
    
    def _show_reset_password_modal(self, user, db_manager):
        """Modal para reset de senha"""
        import bcrypt
        
        user_id = user['id']
        
        with st.form(f"reset_password_form_{user_id}"):
            st.markdown("### Reset de Senha")
            st.warning(f"⚠️ Você está prestes a resetar a senha de **{user['name']}**")
            
            new_password = st.text_input("Nova Senha", type="password", placeholder="Mínimo 8 caracteres")
            confirm_password = st.text_input("Confirmar Nova Senha", type="password")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("🔑 Resetar Senha", type="primary"):
                    if len(new_password) < 8:
                        st.error("❌ Senha deve ter pelo menos 8 caracteres")
                    elif new_password != confirm_password:
                        st.error("❌ Senhas não coincidem")
                    else:
                        # Hash da nova senha
                        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        current_user = self.get_current_user()
                        
                        if current_user and db_manager.reset_user_password(user_id, password_hash, current_user['id']):
                            st.success(f"✅ Senha de {user['name']} resetada com sucesso!")
                            del st.session_state[f'reset_modal_{user_id}']
                            st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Cancelar"):
                    del st.session_state[f'reset_modal_{user_id}']
                    st.rerun()
    
    def _show_additional_features(self, db_manager):
        """Exibir funcionalidades adicionais"""
        st.markdown("## 🔧 Funcionalidades Adicionais")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📤 Exportar Lista de Usuários", use_container_width=True):
                self._export_users_list(db_manager)
        
        with col2:
            if st.button("📊 Relatório de Auditoria", use_container_width=True):
                self._show_audit_report(db_manager)
        
        with col3:
            if self.is_super_admin():
                if st.button("🔄 Sincronizar Dados", use_container_width=True):
                    st.info("🔄 Funcionalidade de sincronização em desenvolvimento...")
    
    def _export_users_list(self, db_manager):
        """Exportar lista de usuários em CSV"""
        import pandas as pd
        import io
        
        result = db_manager.get_users_with_filters(limit=1000)  # Exportar até 1000 usuários
        users = result.get('users', [])
        
        if not users:
            st.warning("Nenhum usuário para exportar.")
            return
        
        # Converter para DataFrame
        df_data = []
        for user in users:
            df_data.append({
                'Nome': user['name'],
                'Email': user['email'],
                'Role': user['role'],
                'Status': 'Ativo' if user['is_active'] else 'Inativo',
                'Data_Criacao': user['created_at'].strftime('%d/%m/%Y') if user['created_at'] else '',
                'Ultimo_Login': user['last_login'].strftime('%d/%m/%Y %H:%M') if user['last_login'] else 'Nunca'
            })
        
        df = pd.DataFrame(df_data)
        
        # Criar CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_data = csv_buffer.getvalue()
        
        # Download
        from datetime import datetime
        filename = f"usuarios_sistema_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        
        st.download_button(
            label="📥 Baixar CSV",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            use_container_width=True
        )
        
        st.success(f"✅ Lista de {len(users)} usuários pronta para download!")
    
    def _show_audit_report(self, db_manager):
        """Exibir relatório de auditoria"""
        st.markdown("### 📊 Relatório de Auditoria")
        
        logs = db_manager.get_admin_audit_logs(limit=50)
        
        if logs:
            st.write(f"**Últimas {len(logs)} ações administrativas:**")
            
            for log in logs:
                with st.expander(f"🔸 {log['action']} - {log['timestamp'].strftime('%d/%m/%Y %H:%M')}"):
                    st.write(f"**Administrador:** {log['admin_name']} ({log['admin_email']})")
                    if log.get('target_name'):
                        st.write(f"**Usuário Alvo:** {log['target_name']} ({log['target_email']})")
                    st.write(f"**Detalhes:** {log['details']}")
                    if log.get('old_value'):
                        st.write(f"**Valor Anterior:** {log['old_value']}")
                    if log.get('new_value'):
                        st.write(f"**Novo Valor:** {log['new_value']}")
        else:
            st.info("Nenhum log de auditoria encontrado.")
