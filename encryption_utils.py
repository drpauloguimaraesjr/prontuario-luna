import os
import base64
from typing import Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import streamlit as st


class EncryptionManager:
    """Gerencia criptografia de dados sensíveis usando Fernet"""
    
    def __init__(self):
        """Inicializar o gerenciador de criptografia com chave derivada"""
        self._fernet = None
        self._init_encryption_key()
    
    def _init_encryption_key(self):
        """Inicializar chave de criptografia com validação rigorosa para produção"""
        try:
            # Verificar variável de ambiente de produção
            app_env = os.getenv('APP_ENV', '').lower()
            is_production = app_env == 'production'
            
            # Verificar se existe chave no ambiente
            env_key = os.getenv('ENCRYPTION_KEY')
            
            if not env_key or not env_key.strip():
                if is_production:
                    # PRODUÇÃO: Falha crítica - não há fallbacks
                    raise ValueError("FALHA CRÍTICA: ENCRYPTION_KEY obrigatória em produção. Configure a chave de criptografia.")
                else:
                    # DESENVOLVIMENTO: Gerar chave temporária (sem logs)
                    temp_key = Fernet.generate_key()
                    self._fernet = Fernet(temp_key)
                    # Não imprimir chaves - apenas avisar
                    import sys
                    sys.stderr.write("WARNING: Usando chave temporária em desenvolvimento. Configure ENCRYPTION_KEY para produção.\n")
                    return
            
            # Múltiplas tentativas de interpretação da chave
            key_attempts = []
            
            # 1. Tentar como base64 direto (formato ideal)
            try:
                key_bytes = base64.urlsafe_b64decode(env_key.encode())
                if len(key_bytes) == 32:  # Fernet precisa de exatamente 32 bytes
                    test_fernet = Fernet(base64.urlsafe_b64encode(key_bytes))
                    key_attempts.append(("base64_direct", test_fernet))
            except:
                pass
            
            # 2. Tentar interpretar como hex e converter
            try:
                clean_hex = env_key.replace('0x', '').replace(' ', '')
                if len(clean_hex) >= 64:  # 32 bytes = 64 chars hex
                    hex_bytes = bytes.fromhex(clean_hex[:64])
                    fernet_key = base64.urlsafe_b64encode(hex_bytes)
                    test_fernet = Fernet(fernet_key)
                    key_attempts.append(("hex_converted", test_fernet))
            except:
                pass
            
            # 3. Usar PBKDF2 para derivar chave da string
            try:
                from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
                from cryptography.hazmat.primitives import hashes
                
                salt = env_key.encode('utf-8')[:16].ljust(16, b'0')
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                derived_key = kdf.derive(env_key.encode('utf-8'))
                fernet_key = base64.urlsafe_b64encode(derived_key)
                test_fernet = Fernet(fernet_key)
                key_attempts.append(("pbkdf2_derived", test_fernet))
            except:
                pass
            
            # Testar cada tentativa de chave
            for attempt_name, test_fernet in key_attempts:
                try:
                    # Teste de validação da criptografia
                    test_data = b"security_validation_test"
                    encrypted = test_fernet.encrypt(test_data)
                    decrypted = test_fernet.decrypt(encrypted)
                    
                    if decrypted == test_data:
                        self._fernet = test_fernet
                        # Log apenas em desenvolvimento
                        if not is_production:
                            import sys
                            sys.stderr.write(f"Criptografia inicializada usando método: {attempt_name}\n")
                        return
                except:
                    continue
            
            # Se nenhuma tentativa funcionou
            if is_production:
                # PRODUÇÃO: Falha crítica - chave inválida
                raise ValueError("FALHA CRÍTICA: ENCRYPTION_KEY inválida em produção. Verifique a configuração da chave.")
            else:
                # DESENVOLVIMENTO: Gerar nova chave (sem logs)
                new_key = Fernet.generate_key()
                self._fernet = Fernet(new_key)
                import sys
                sys.stderr.write("WARNING: Chave inválida. Usando chave temporária em desenvolvimento.\n")
                sys.stderr.write("Configure ENCRYPTION_KEY válida para produção.\n")
                             
        except Exception as e:
            app_env = os.getenv('APP_ENV', '').lower()
            is_production = app_env == 'production'
            
            if is_production:
                # PRODUÇÃO: Falha crítica - não há chaves de emergência
                raise ValueError(f"FALHA CRÍTICA DE CRIPTOGRAFIA EM PRODUÇÃO: {str(e)}") from e
            else:
                # DESENVOLVIMENTO: Log de erro sem expor detalhes sensíveis
                import sys
                sys.stderr.write(f"ERRO: Falha na inicialização da criptografia: {str(e)}\n")
                
                # Último recurso: chave de emergência apenas para desenvolvimento
                try:
                    emergency_key = Fernet.generate_key()
                    self._fernet = Fernet(emergency_key)
                    sys.stderr.write("WARNING: Usando chave de emergência temporária.\n")
                    sys.stderr.write("CRÍTICO: Configure ENCRYPTION_KEY para produção!\n")
                except Exception as emergency_error:
                    sys.stderr.write(f"FALHA TOTAL: {str(emergency_error)}\n")
                    self._fernet = None
                    sys.stderr.write("ERRO: Sistema sem criptografia - APENAS DESENVOLVIMENTO!\n")
                    return
    
    def is_encryption_available(self) -> bool:
        """Verificar se a criptografia está disponível"""
        return self._fernet is not None
    
    def encrypt(self, data: str) -> Optional[str]:
        """Criptografar dados sensíveis"""
        if not self.is_encryption_available():
            st.error("Sistema de criptografia não disponível")
            return None
            
        try:
            if not data or data.strip() == "":
                return ""
            
            if self._fernet is None:
                st.error("Sistema de criptografia não disponível")
                return None
                
            encrypted_data = self._fernet.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            st.error(f"Erro na criptografia: {e}")
            return None
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """Descriptografar dados sensíveis"""
        if not self.is_encryption_available():
            return None
            
        try:
            if not encrypted_data or encrypted_data.strip() == "":
                return ""
            
            if self._fernet is None:
                st.error("Sistema de criptografia não disponível")
                return None
                
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            st.error(f"Erro na descriptografia: {e}")
            return None
    
    def mask_sensitive_value(self, value: str, show_chars: int = 4) -> str:
        """Mascarar valor sensível para exibição segura"""
        if not value or value.strip() == "":
            return ""
            
        if len(value) <= show_chars:
            return "*" * len(value)
        
        return value[:show_chars] + "*" * (len(value) - show_chars)
    
    def generate_encryption_key(self) -> str:
        """Gerar nova chave de criptografia para configuração manual"""
        try:
            key = Fernet.generate_key()
            return base64.urlsafe_b64encode(key).decode('utf-8')
        except Exception as e:
            st.error(f"Erro ao gerar chave: {e}")
            return ""
    
    def test_encryption(self) -> bool:
        """Testar funcionalidade de criptografia"""
        try:
            test_data = "test_encryption_functionality"
            encrypted = self.encrypt(test_data)
            if not encrypted:
                return False
                
            decrypted = self.decrypt(encrypted)
            return decrypted == test_data
            
        except Exception as e:
            st.error(f"Teste de criptografia falhou: {e}")
            return False


# Instância global do gerenciador de criptografia
encryption_manager = EncryptionManager()


def get_encryption_manager() -> EncryptionManager:
    """Obter instância do gerenciador de criptografia"""
    return encryption_manager


def is_sensitive_config(category: str, config_key: str) -> bool:
    """Determinar se uma configuração deve ser criptografada"""
    sensitive_configs = {
        'SMTP': ['smtp_password'],
        'API': ['openai_api_key', 'webhook_secret', 'api_secret_key'],
        'SECURITY': ['encryption_key', 'jwt_secret', 'oauth_client_secret'],
        'GENERAL': ['database_password', 'redis_password']
    }
    
    return config_key in sensitive_configs.get(category, [])


def should_encrypt_config(category: str, config_key: str) -> bool:
    """Verificar se uma configuração deve ser automaticamente criptografada"""
    return is_sensitive_config(category, config_key)