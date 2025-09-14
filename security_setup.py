#!/usr/bin/env python3
"""
Utilitários de configuração de segurança para produção
"""
import os
import secrets
import base64
from cryptography.fernet import Fernet
from typing import Dict, List, Any
import streamlit as st


class SecuritySetupManager:
    """Gerencia configuração inicial de segurança do sistema"""
    
    @staticmethod
    def generate_production_keys() -> Dict[str, str]:
        """Gerar chaves de segurança para produção"""
        keys = {}
        
        # Gerar chave de criptografia principal
        fernet_key = Fernet.generate_key()
        keys['ENCRYPTION_KEY'] = base64.urlsafe_b64encode(fernet_key).decode('utf-8')
        
        # Gerar seed para derivação de chaves
        keys['ENCRYPTION_SEED'] = secrets.token_urlsafe(64)
        
        # Gerar chave para sessões
        keys['SESSION_SECRET'] = secrets.token_urlsafe(64)
        
        return keys
    
    @staticmethod
    def check_production_readiness() -> List[Dict[str, str]]:
        """Verificar prontidão para produção"""
        issues = []
        
        # Verificar variáveis críticas
        critical_vars = [
            ('PGHOST', 'Host do banco PostgreSQL'),
            ('PGDATABASE', 'Nome do banco de dados'),
            ('PGUSER', 'Usuário do banco'),
            ('PGPASSWORD', 'Senha do banco'),
        ]
        
        for var, desc in critical_vars:
            if not os.getenv(var):
                issues.append({
                    'level': 'CRITICAL',
                    'category': 'database',
                    'message': f"Variável {var} não configurada ({desc})"
                })
        
        # Verificar configuração de criptografia
        if not os.getenv('ENCRYPTION_KEY'):
            issues.append({
                'level': 'HIGH',
                'category': 'security',
                'message': "Chave ENCRYPTION_KEY não configurada - usando padrão inseguro"
            })
        
        # Verificar senha padrão do admin
        # Este será verificado na inicialização do banco
        
        return issues
    
    @staticmethod
    def display_production_setup_guide():
        """Exibir guia de configuração para produção"""
        st.markdown("# 🔐 Configuração de Segurança para Produção")
        
        # Verificar problemas atuais
        issues = SecuritySetupManager.check_production_readiness()
        
        if issues:
            st.error("⚠️ Problemas de segurança detectados!")
            
            critical_issues = [i for i in issues if i['level'] == 'CRITICAL']
            high_issues = [i for i in issues if i['level'] == 'HIGH']
            
            if critical_issues:
                st.markdown("### ❌ Problemas Críticos")
                for issue in critical_issues:
                    st.error(f"**{issue['category'].upper()}**: {issue['message']}")
            
            if high_issues:
                st.markdown("### ⚠️ Problemas de Alta Prioridade")
                for issue in high_issues:
                    st.warning(f"**{issue['category'].upper()}**: {issue['message']}")
        
        # Seção de chaves de produção
        st.markdown("### 🔑 Configuração de Chaves de Segurança")
        
        if st.button("🎲 Gerar Novas Chaves de Produção"):
            keys = SecuritySetupManager.generate_production_keys()
            
            st.markdown("**Configure estas variáveis de ambiente na produção:**")
            st.code(f"""
export ENCRYPTION_KEY="{keys['ENCRYPTION_KEY']}"
export ENCRYPTION_SEED="{keys['ENCRYPTION_SEED']}"
export SESSION_SECRET="{keys['SESSION_SECRET']}"
            """, language="bash")
            
            st.warning("🚨 **ATENÇÃO**: Copie e guarde estas chaves com segurança! Não as compartilhe.")
        
        # Instruções de configuração
        st.markdown("### 📋 Lista de Verificação de Produção")
        
        checklist_items = [
            "✅ Configure ENCRYPTION_KEY com chave única",
            "✅ Mude a senha padrão do admin (admin@admin.com)",
            "✅ Configure servidor SMTP para notificações",
            "✅ Defina políticas de senha apropriadas",
            "✅ Configure timeout de sessão adequado",
            "✅ Habilite logs de auditoria",
            "✅ Configure backup automático do banco",
            "✅ Teste conectividade de todos os serviços",
        ]
        
        for item in checklist_items:
            st.markdown(f"- {item}")
        
        # Aviso final
        st.markdown("---")
        st.error("""
        🚨 **AVISO DE SEGURANÇA CRÍTICO**:
        
        - **NUNCA** use as configurações padrão em produção
        - **SEMPRE** altere a senha do admin padrão imediatamente
        - **CONFIGURE** chaves de criptografia únicas para cada ambiente
        - **MONITORE** logs de segurança regularmente
        - **MANTENHA** backups seguros do banco de dados
        """)


class DefaultAdminSecurityManager:
    """Gerencia segurança do admin padrão"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def check_default_admin_security(self) -> Dict[str, Any]:
        """Verificar se admin padrão ainda está com configurações inseguras"""
        conn = self.db.get_connection()
        if not conn:
            return {'secure': False, 'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor()
            
            # Verificar admin padrão
            cursor.execute("""
                SELECT id, email, name, created_at, last_login, 
                       (password_hash = %s) as using_default_password
                FROM users 
                WHERE email = 'admin@admin.com' AND role = 'SUPER_ADMIN'
            """, ('$2b$12$default_hash_placeholder',))  # Hash do "admin123"
            
            admin_data = cursor.fetchone()
            cursor.close()
            
            if not admin_data:
                return {'secure': True, 'message': 'Default admin not found'}
            
            user_id, email, name, created_at, last_login, using_default = admin_data
            
            security_issues = []
            
            # Verificar senha padrão (isso será implementado com hash real)
            if not last_login:
                security_issues.append("Admin nunca fez login")
            
            if email == 'admin@admin.com':
                security_issues.append("Email padrão ainda em uso")
            
            if name == 'Administrador':
                security_issues.append("Nome padrão ainda em uso")
            
            return {
                'secure': len(security_issues) == 0,
                'admin_data': {
                    'id': user_id,
                    'email': email,
                    'name': name,
                    'created_at': created_at,
                    'last_login': last_login
                },
                'issues': security_issues
            }
            
        except Exception as e:
            return {'secure': False, 'error': f'Security check failed: {e}'}
        finally:
            conn.close()
    
    def force_password_change_on_login(self, user_data: Dict) -> bool:
        """Verificar se usuário precisa alterar senha no próximo login"""
        if user_data.get('email') == 'admin@admin.com':
            # Verificar se ainda não alterou a senha padrão
            return not user_data.get('last_login')  # Se nunca fez login, forçar mudança
        return False
    
    def create_secure_admin_wizard(self):
        """Wizard para configuração inicial segura do admin"""
        st.markdown("# 🛡️ Configuração Inicial de Segurança")
        
        security_status = self.check_default_admin_security()
        
        if not security_status.get('secure', False):
            st.error("⚠️ Configuração de admin insegura detectada!")
            
            if 'issues' in security_status:
                st.markdown("**Problemas encontrados:**")
                for issue in security_status['issues']:
                    st.warning(f"• {issue}")
            
            st.markdown("---")
            st.markdown("### 🔧 Configure um Admin Seguro")
            
            with st.form("secure_admin_setup"):
                st.markdown("**Crie um novo admin com credenciais seguras:**")
                
                new_email = st.text_input("Email do Admin", 
                                         placeholder="admin@empresa.com")
                new_name = st.text_input("Nome Completo", 
                                        placeholder="João Silva")
                new_password = st.text_input("Nova Senha", 
                                           type="password",
                                           help="Mínimo 12 caracteres, incluindo números e símbolos")
                confirm_password = st.text_input("Confirmar Senha", 
                                                type="password")
                
                if st.form_submit_button("🛡️ Criar Admin Seguro"):
                    if self._validate_secure_admin_creation(new_email, new_name, 
                                                           new_password, confirm_password):
                        if self._create_secure_admin(new_email, new_name, new_password):
                            st.success("✅ Admin seguro criado com sucesso!")
                            st.info("⚠️ Lembre-se de remover ou desativar o admin padrão após confirmar o acesso.")
                            st.rerun()
        else:
            st.success("✅ Configuração de admin está segura!")
    
    def _validate_secure_admin_creation(self, email: str, name: str, 
                                       password: str, confirm: str) -> bool:
        """Validar dados para criação de admin seguro"""
        if not email or '@' not in email:
            st.error("Email inválido")
            return False
        
        if not name or len(name.strip()) < 2:
            st.error("Nome deve ter pelo menos 2 caracteres")
            return False
        
        if len(password) < 12:
            st.error("Senha deve ter pelo menos 12 caracteres")
            return False
        
        if password != confirm:
            st.error("Senhas não coincidem")
            return False
        
        # Validar força da senha
        if not any(c.isupper() for c in password):
            st.error("Senha deve conter pelo menos uma letra maiúscula")
            return False
        
        if not any(c.islower() for c in password):
            st.error("Senha deve conter pelo menos uma letra minúscula")
            return False
        
        if not any(c.isdigit() for c in password):
            st.error("Senha deve conter pelo menos um número")
            return False
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            st.error("Senha deve conter pelo menos um caractere especial")
            return False
        
        return True
    
    def _create_secure_admin(self, email: str, name: str, password: str) -> bool:
        """Criar admin seguro"""
        try:
            from auth import AuthManager
            auth = AuthManager()
            
            # Criar usuário com role SUPER_ADMIN
            if auth.create_user(email, password, name, "SUPER_ADMIN"):
                # Log da criação
                self.db.log_admin_action(
                    0,  # Sistema
                    "SECURE_ADMIN_CREATED",
                    None,
                    "",
                    f"email={email}",
                    f"Admin seguro criado: {name} ({email})"
                )
                return True
            return False
        except Exception as e:
            st.error(f"Erro ao criar admin: {e}")
            return False