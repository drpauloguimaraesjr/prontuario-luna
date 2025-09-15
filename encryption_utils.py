import os
import base64
import re
import secrets
from typing import Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import streamlit as st
import logging
import sys


class EncryptionManager:
    """Gerencia criptografia de dados sensíveis usando Fernet"""
    
    def __init__(self):
        """Inicializar o gerenciador de criptografia com chave derivada"""
        self._fernet = None
        self._init_encryption_key()
    
    def _validate_encryption_key_strength(self, key: str, is_production: bool) -> tuple[bool, str]:
        """Validar força e entropia da ENCRYPTION_KEY"""
        if not key or not key.strip():
            return False, "ENCRYPTION_KEY não pode estar vazia"
        
        key = key.strip()
        
        # CRITICAL: Comprimento mínimo de 32 caracteres
        if len(key) < 32:
            return False, f"ENCRYPTION_KEY deve ter pelo menos 32 caracteres (atual: {len(key)})"
        
        # PRODUCTION: Verificações adicionais de entropia e qualidade
        if is_production:
            # Verificar se a chave não é muito simples ou repetitiva
            if len(set(key)) < 10:  # Pelo menos 10 caracteres únicos
                return False, "ENCRYPTION_KEY deve ter maior diversidade de caracteres"
            
            # Verificar se não é apenas base64 fraco (muitos '=' ou padrão simples)
            if key.count('=') > len(key) // 4:  # Muitos padding chars
                return False, "ENCRYPTION_KEY parece ter entropia insuficiente"
            
            # Verificar se não contém apenas caracteres alfabéticos simples
            if re.match(r'^[a-zA-Z]+$', key):
                return False, "ENCRYPTION_KEY deve incluir caracteres especiais e números"
            
            # Verificar se não é uma sequência óbvia
            common_patterns = ['123456', 'abcdef', 'qwerty', '000000', '111111']
            key_lower = key.lower()
            for pattern in common_patterns:
                if pattern in key_lower:
                    return False, "ENCRYPTION_KEY não deve conter padrões comuns"
        
        return True, "Chave válida"
    
    def _init_encryption_key(self):
        """Inicializar chave de criptografia com validação rigorosa para produção"""
        try:
            # Verificar variável de ambiente de produção
            app_env = os.getenv('APP_ENV', '').lower()
            is_production = app_env == 'production'
            
            # Configurar logging seguro
            if is_production:
                logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
            else:
                logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
            
            # Verificar se existe chave no ambiente
            env_key = os.getenv('ENCRYPTION_KEY')
            
            if not env_key or not env_key.strip():
                # CRÍTICO: Sempre falhar se ENCRYPTION_KEY não estiver configurada
                error_msg = "ENCRYPTION_KEY environment variable is required"
                logging.critical("Missing ENCRYPTION_KEY environment variable")
                raise ValueError(error_msg)
            
            # VALIDAÇÃO RIGOROSA: Verificar força da chave
            is_valid, validation_msg = self._validate_encryption_key_strength(env_key, is_production)
            if not is_valid:
                # CRÍTICO: Sempre falhar se ENCRYPTION_KEY for inválida
                logging.critical(f"Invalid ENCRYPTION_KEY: {validation_msg}")
                raise ValueError(f"Invalid ENCRYPTION_KEY: {validation_msg}")
            
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
                            logging.info(f"Criptografia inicializada usando método: {attempt_name}")
                        return
                except:
                    continue
            
            # Se nenhuma tentativa funcionou
            # CRÍTICO: Sempre falhar se formato da chave for inválido
            logging.critical("Invalid ENCRYPTION_KEY format")
            raise ValueError("Invalid ENCRYPTION_KEY format. Please verify the key configuration.")
                             
        except Exception as e:
            # CRÍTICO: Sempre falhar se houver erro na inicialização
            logging.critical(f"Encryption system initialization failed: {str(e)}")
            raise ValueError("Encryption system initialization failed. Contact system administrator.") from None
    
    def is_encryption_available(self) -> bool:
        """Verificar se a criptografia está disponível"""
        return self._fernet is not None
    
    def encrypt(self, data: str) -> Optional[str]:
        """Criptografar dados sensíveis"""
        if not self.is_encryption_available():
            # Mensagem genérica para usuário
            st.error("Encryption system not available")
            return None
            
        try:
            if not data or data.strip() == "":
                return ""
            
            if self._fernet is None:
                st.error("Encryption system not available")
                return None
                
            encrypted_data = self._fernet.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            # Log interno detalhado, mensagem genérica ao usuário
            is_production = os.getenv('APP_ENV', '').lower() == 'production'
            if is_production:
                logging.error(f"Encryption failed: {str(e)}")
                st.error("Encryption operation failed")
            else:
                st.error(f"Encryption error: {e}")
            return None
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """Descriptografar dados sensíveis"""
        if not self.is_encryption_available():
            return None
            
        try:
            if not encrypted_data or encrypted_data.strip() == "":
                return ""
            
            if self._fernet is None:
                st.error("Encryption system not available")
                return None
                
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            # Log interno detalhado, mensagem genérica ao usuário
            is_production = os.getenv('APP_ENV', '').lower() == 'production'
            if is_production:
                logging.error(f"Decryption failed: {str(e)}")
                st.error("Decryption operation failed")
            else:
                st.error(f"Decryption error: {e}")
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
            # Log interno detalhado, mensagem genérica ao usuário
            is_production = os.getenv('APP_ENV', '').lower() == 'production'
            if is_production:
                logging.error(f"Key generation failed: {str(e)}")
                st.error("Key generation failed")
            else:
                st.error(f"Error generating key: {e}")
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
            # Log interno detalhado, mensagem genérica ao usuário
            is_production = os.getenv('APP_ENV', '').lower() == 'production'
            if is_production:
                logging.error(f"Encryption test failed: {str(e)}")
                st.error("Encryption test failed")
            else:
                st.error(f"Encryption test failed: {e}")
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