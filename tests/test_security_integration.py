#!/usr/bin/env python3
"""
Comprehensive integration tests for critical security enforcement measures.

These tests validate production-ready security fixes:
1. ENCRYPTION_KEY enforcement and startup validation
2. Mandatory password change enforcement and complete lockout 
3. End-to-end secrets verification and encryption
4. UI masking and audit log security
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import tempfile
import json
from datetime import datetime, timedelta
import psycopg2
from contextlib import contextmanager

# Add project modules to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
from encryption_utils import EncryptionManager, is_sensitive_config, should_encrypt_config
from auth import AuthManager
from database import DatabaseManager


class TestCriticalSecurityEnforcement(unittest.TestCase):
    """Test suite for critical security enforcement measures"""
    
    def setUp(self):
        """Set up test environment with clean state"""
        self.test_env = {}
        # Store original environment
        self.original_env = os.environ.copy()
        
    def tearDown(self):
        """Clean up test environment"""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @contextmanager
    def mock_environment(self, env_vars=None):
        """Context manager for mocking environment variables"""
        if env_vars is None:
            env_vars = {}
        
        # Clear environment and set test values
        for key in list(os.environ.keys()):
            if key.startswith(('ENCRYPTION_', 'PG')):
                del os.environ[key]
        
        for key, value in env_vars.items():
            if value is not None:
                os.environ[key] = str(value)
        
        try:
            yield
        finally:
            # Cleanup will happen in tearDown
            pass


class TestEncryptionKeyEnforcement(TestCriticalSecurityEnforcement):
    """Test ENCRYPTION_KEY enforcement and startup validation"""
    
    def test_missing_encryption_key_blocks_startup(self):
        """Test that missing ENCRYPTION_KEY completely blocks application startup"""
        
        with self.mock_environment({}):  # No ENCRYPTION_KEY set
            
            # Should raise RuntimeError when initializing EncryptionManager
            with self.assertRaises(RuntimeError) as context:
                EncryptionManager()
            
            self.assertIn("ENCRYPTION_KEY obrigatória não foi configurada", str(context.exception))
    
    def test_invalid_encryption_key_blocks_startup(self):
        """Test that invalid ENCRYPTION_KEY format blocks startup"""
        
        with self.mock_environment({'ENCRYPTION_KEY': 'invalid-key-format'}):
            
            # Should raise RuntimeError for invalid key
            with self.assertRaises(RuntimeError) as context:
                EncryptionManager()
            
            self.assertIn("ENCRYPTION_KEY inválida", str(context.exception))
    
    def test_empty_encryption_key_blocks_startup(self):
        """Test that empty ENCRYPTION_KEY blocks startup"""
        
        with self.mock_environment({'ENCRYPTION_KEY': ''}):
            
            with self.assertRaises(RuntimeError) as context:
                EncryptionManager()
            
            self.assertIn("ENCRYPTION_KEY obrigatória não foi configurada", str(context.exception))
    
    def test_valid_encryption_key_allows_startup(self):
        """Test that valid ENCRYPTION_KEY allows normal operation"""
        
        # Generate valid key
        from cryptography.fernet import Fernet
        import base64
        
        valid_key = base64.urlsafe_b64encode(Fernet.generate_key()).decode()
        
        with self.mock_environment({'ENCRYPTION_KEY': valid_key}):
            
            # Should not raise exception
            manager = EncryptionManager()
            self.assertTrue(manager.is_encryption_available())
            self.assertTrue(manager.test_encryption())
    
    def test_startup_validation_integration(self):
        """Test that app.py startup validation works correctly"""
        
        with self.mock_environment({}):  # No key
            
            # Mock streamlit to capture error messages
            with patch('streamlit.error') as mock_error, \
                 patch('streamlit.stop') as mock_stop:
                
                # Import and test startup validation
                from app import validate_security_requirements
                
                # Should call st.error and st.stop
                validate_security_requirements()
                
                # Verify error messages were shown
                self.assertTrue(mock_error.called)
                self.assertTrue(mock_stop.called)
                
                # Check error message content
                error_calls = [call[0][0] for call in mock_error.call_args_list]
                self.assertTrue(any("FALHA CRÍTICA DE SEGURANÇA" in msg for msg in error_calls))


class TestPasswordChangeEnforcement(TestCriticalSecurityEnforcement):
    """Test mandatory password change enforcement and complete lockout"""
    
    def setUp(self):
        super().setUp()
        
        # Mock database connection and streamlit
        self.mock_db_conn = Mock()
        self.mock_cursor = Mock()
        self.mock_db_conn.cursor.return_value = self.mock_cursor
        
    @patch('psycopg2.connect')
    @patch('streamlit.error')
    @patch('streamlit.warning') 
    @patch('streamlit.stop')
    def test_password_change_required_blocks_all_functionality(self, mock_stop, mock_warning, mock_error, mock_connect):
        """Test that password_change_required=True blocks ALL functionality"""
        
        mock_connect.return_value = self.mock_db_conn
        
        # Set up user with password change required
        test_user = {
            'id': 1,
            'email': 'test@example.com',
            'name': 'Test User',
            'password_change_required': True,
            'password_expired': False
        }
        
        with patch('streamlit.session_state', {'authenticated': True, 'user': test_user}):
            
            auth_manager = AuthManager()
            
            # Test password change enforcement
            requires_change = auth_manager.requires_password_change()
            self.assertTrue(requires_change)
            
            # Test enforcement blocks functionality
            blocked = auth_manager.enforce_password_change()
            self.assertTrue(blocked)
            
            # Verify blocking messages were shown
            self.assertTrue(mock_error.called)
            self.assertTrue(mock_warning.called)
    
    @patch('psycopg2.connect')
    def test_password_expired_triggers_enforcement(self, mock_connect):
        """Test that expired password triggers enforcement"""
        
        mock_connect.return_value = self.mock_db_conn
        
        test_user = {
            'id': 1,
            'email': 'test@example.com', 
            'name': 'Test User',
            'password_change_required': False,
            'password_expired': True  # Expired password
        }
        
        with patch('streamlit.session_state', {'authenticated': True, 'user': test_user}):
            
            auth_manager = AuthManager()
            
            # Should require password change due to expiration
            requires_change = auth_manager.requires_password_change()
            self.assertTrue(requires_change)
    
    @patch('psycopg2.connect')
    @patch('streamlit.error')
    @patch('streamlit.stop')
    def test_admin_page_blocks_with_password_change_required(self, mock_stop, mock_error, mock_connect):
        """Test that admin pages are blocked when password change is required"""
        
        mock_connect.return_value = self.mock_db_conn
        
        test_user = {
            'id': 1,
            'email': 'admin@example.com',
            'name': 'Admin User', 
            'role': 'SUPER_ADMIN',
            'password_change_required': True
        }
        
        with patch('streamlit.session_state', {'authenticated': True, 'user': test_user}):
            
            auth_manager = AuthManager()
            db_manager = Mock()
            
            # Mock the admin page function
            with patch('pages.admin.auth', auth_manager):
                from pages.admin import run_admin_page
                
                # Should return early due to password change enforcement
                with patch('streamlit.set_page_config'):
                    result = run_admin_page(db_manager, auth_manager)
                    
                    # Function should return early, blocking admin access
                    self.assertIsNone(result)
    
    def test_normal_user_can_access_without_password_change(self):
        """Test that users without password change requirements can access normally"""
        
        test_user = {
            'id': 1,
            'email': 'user@example.com',
            'name': 'Normal User',
            'password_change_required': False,
            'password_expired': False
        }
        
        with patch('streamlit.session_state', {'authenticated': True, 'user': test_user}):
            
            # Mock database connection
            with patch('psycopg2.connect'):
                auth_manager = AuthManager()
                
                # Should not require password change
                requires_change = auth_manager.requires_password_change()
                self.assertFalse(requires_change)
                
                # Should not block functionality
                blocked = auth_manager.enforce_password_change()
                self.assertFalse(blocked)


class TestSensitiveConfigEncryption(TestCriticalSecurityEnforcement):
    """Test end-to-end secrets verification and encryption enforcement"""
    
    def setUp(self):
        super().setUp()
        
        # Set up valid encryption key for these tests
        from cryptography.fernet import Fernet
        import base64
        
        self.valid_key = base64.urlsafe_b64encode(Fernet.generate_key()).decode()
        
        # Mock database
        self.mock_db_conn = Mock()
        self.mock_cursor = Mock()
        self.mock_db_conn.cursor.return_value = self.mock_cursor
    
    def test_sensitive_config_classification(self):
        """Test that sensitive configurations are correctly identified"""
        
        # Test known sensitive configs
        sensitive_tests = [
            ('SMTP', 'smtp_password', True),
            ('API', 'openai_api_key', True), 
            ('API', 'webhook_secret', True),
            ('SECURITY', 'encryption_key', True),
            ('SECURITY', 'jwt_secret', True),
            ('GENERAL', 'database_password', True),
            # Non-sensitive configs
            ('SMTP', 'smtp_enabled', False),
            ('API', 'api_rate_limit', False),
            ('GENERAL', 'max_file_size_mb', False)
        ]
        
        for category, key, expected_sensitive in sensitive_tests:
            with self.subTest(category=category, key=key):
                is_sensitive = is_sensitive_config(category, key)
                should_encrypt = should_encrypt_config(category, key)
                
                self.assertEqual(is_sensitive, expected_sensitive)
                self.assertEqual(should_encrypt, expected_sensitive)
    
    @patch('psycopg2.connect')
    @patch('streamlit.error')
    def test_save_sensitive_config_without_encryption_blocks(self, mock_error, mock_connect):
        """Test that saving sensitive config without encryption is blocked"""
        
        mock_connect.return_value = self.mock_db_conn
        
        with self.mock_environment({}):  # No ENCRYPTION_KEY
            
            db_manager = DatabaseManager()
            
            # Try to save sensitive config - should be blocked
            result = db_manager.save_config('SMTP', 'smtp_password', 'secret123', 1)
            
            # Should fail and show error
            self.assertFalse(result)
            self.assertTrue(mock_error.called)
            
            # Check error message mentions security blocking
            error_calls = [call[0][0] for call in mock_error.call_args_list]
            self.assertTrue(any("BLOQUEIO DE SEGURANÇA" in msg for msg in error_calls))
    
    @patch('psycopg2.connect')
    @patch('streamlit.success')
    def test_save_sensitive_config_with_encryption_succeeds(self, mock_success, mock_connect):
        """Test that saving sensitive config with valid encryption succeeds"""
        
        mock_connect.return_value = self.mock_db_conn
        self.mock_cursor.fetchone.return_value = None  # Config doesn't exist yet
        
        with self.mock_environment({'ENCRYPTION_KEY': self.valid_key}):
            
            db_manager = DatabaseManager()
            
            # Should succeed with encryption
            result = db_manager.save_config('SMTP', 'smtp_password', 'secret123', 1)
            
            # Should succeed and show success message
            self.assertTrue(result)
            self.assertTrue(mock_success.called)
            
            # Verify INSERT was called with is_encrypted=True
            insert_call = None
            for call in self.mock_cursor.execute.call_args_list:
                if 'INSERT INTO system_config' in str(call):
                    insert_call = call
                    break
            
            self.assertIsNotNone(insert_call)
            # Check that is_encrypted parameter is True
            if insert_call:
                params = insert_call[0][1] 
                is_encrypted_param = params[4]  # 5th parameter is is_encrypted
                self.assertTrue(is_encrypted_param)
    
    def test_ui_masking_for_sensitive_values(self):
        """Test that UI properly masks sensitive values"""
        
        with self.mock_environment({'ENCRYPTION_KEY': self.valid_key}):
            
            encryption_manager = EncryptionManager()
            
            # Test masking function
            test_cases = [
                ("secret_password_123", "secr************"),
                ("sk-1234567890abcdef", "sk-1************"),
                ("", ""),
                ("abc", "***"),  # Short values get fully masked
            ]
            
            for original, expected in test_cases:
                with self.subTest(original=original):
                    masked = encryption_manager.mask_sensitive_value(original)
                    self.assertEqual(masked, expected)
    
    @patch('psycopg2.connect')
    def test_audit_log_masks_sensitive_values(self, mock_connect):
        """Test that audit logs properly mask sensitive configuration values"""
        
        mock_connect.return_value = self.mock_db_conn
        self.mock_cursor.fetchone.return_value = None
        
        with self.mock_environment({'ENCRYPTION_KEY': self.valid_key}):
            
            db_manager = DatabaseManager()
            
            # Mock log_admin_action to capture calls
            with patch.object(db_manager, 'log_admin_action') as mock_log:
                
                db_manager.save_config('SMTP', 'smtp_password', 'secret123', 1)
                
                # Verify logging was called
                self.assertTrue(mock_log.called)
                
                # Get the logged value
                log_call = mock_log.call_args
                logged_details = log_call[1]['old_value'] if 'old_value' in log_call[1] else ""
                logged_new_value = log_call[1]['new_value'] if 'new_value' in log_call[1] else ""
                
                # Should contain [SENSITIVE] instead of actual value
                self.assertIn("[SENSITIVE]", logged_new_value)
                self.assertNotIn("secret123", logged_new_value)


class TestIntegrationSecurityFlow(TestCriticalSecurityEnforcement):
    """Test complete end-to-end security flow integration"""
    
    @patch('psycopg2.connect')
    @patch('streamlit.error')
    @patch('streamlit.stop')
    def test_complete_security_enforcement_chain(self, mock_stop, mock_error, mock_connect):
        """Test complete security enforcement from startup to operation"""
        
        mock_connect.return_value = Mock()
        
        # Test 1: Missing encryption key blocks startup
        with self.mock_environment({}):
            
            with self.assertRaises(RuntimeError):
                from app import validate_security_requirements
                validate_security_requirements()
        
        # Test 2: With encryption key but password change required
        from cryptography.fernet import Fernet
        import base64
        valid_key = base64.urlsafe_b64encode(Fernet.generate_key()).decode()
        
        with self.mock_environment({'ENCRYPTION_KEY': valid_key}):
            
            # User with password change required
            test_user = {
                'id': 1,
                'email': 'user@example.com',
                'name': 'Test User',
                'password_change_required': True
            }
            
            with patch('streamlit.session_state', {'authenticated': True, 'user': test_user}):
                
                auth_manager = AuthManager()
                
                # Should block functionality due to password change requirement
                blocked = auth_manager.enforce_password_change()
                self.assertTrue(blocked)
                
                # Error should have been shown
                self.assertTrue(mock_error.called)
    
    def test_security_configuration_complete_cycle(self):
        """Test complete cycle of security configuration management"""
        
        from cryptography.fernet import Fernet
        import base64
        valid_key = base64.urlsafe_b64encode(Fernet.generate_key()).decode()
        
        with self.mock_environment({'ENCRYPTION_KEY': valid_key}):
            
            # Test encryption manager initialization
            encryption_manager = EncryptionManager()
            self.assertTrue(encryption_manager.is_encryption_available())
            
            # Test encryption/decryption cycle
            original_value = "sensitive_api_key_12345"
            encrypted = encryption_manager.encrypt(original_value)
            self.assertIsNotNone(encrypted)
            self.assertNotEqual(encrypted, original_value)
            
            if encrypted is not None:
                decrypted = encryption_manager.decrypt(encrypted)
                self.assertEqual(decrypted, original_value)
            
            # Test masking
            masked = encryption_manager.mask_sensitive_value(original_value)
            self.assertNotEqual(masked, original_value)
            self.assertTrue(masked.endswith("*"))


class TestProductionReadinessValidation(TestCriticalSecurityEnforcement):
    """Test overall production readiness and security compliance"""
    
    def test_no_fallback_encryption_keys_exist(self):
        """Verify no fallback encryption mechanisms exist in production"""
        
        # Read encryption_utils.py to ensure no fallback exists
        with open('encryption_utils.py', 'r') as f:
            content = f.read()
        
        # Should not contain fallback seed or deterministic key generation
        self.assertNotIn('ENCRYPTION_SEED', content)
        self.assertNotIn('medical-system-default-seed', content)
        self.assertNotIn('medical_records_salt', content)
        
        # Should contain mandatory key validation
        self.assertIn('ENCRYPTION_KEY obrigatória não foi configurada', content)
        self.assertIn('RuntimeError', content)
    
    def test_critical_security_functions_exist(self):
        """Verify all critical security functions are implemented"""
        
        # Test EncryptionManager has required methods
        from encryption_utils import EncryptionManager
        
        required_methods = [
            'is_encryption_available',
            'encrypt', 
            'decrypt',
            'mask_sensitive_value',
            'test_encryption'
        ]
        
        for method in required_methods:
            self.assertTrue(hasattr(EncryptionManager, method))
        
        # Test AuthManager has password change enforcement
        from auth import AuthManager
        
        auth_methods = [
            'requires_password_change',
            'enforce_password_change', 
            '_show_mandatory_password_change_form'
        ]
        
        for method in auth_methods:
            self.assertTrue(hasattr(AuthManager, method))
    
    def test_sensitive_config_definitions_complete(self):
        """Verify all sensitive configurations are properly defined"""
        
        from encryption_utils import is_sensitive_config
        
        # Known sensitive configurations that must be defined
        required_sensitive = [
            ('SMTP', 'smtp_password'),
            ('API', 'openai_api_key'),
            ('API', 'webhook_secret'), 
            ('API', 'api_secret_key'),
            ('SECURITY', 'encryption_key'),
            ('SECURITY', 'jwt_secret'),
            ('SECURITY', 'oauth_client_secret'),
            ('GENERAL', 'database_password'),
            ('GENERAL', 'redis_password')
        ]
        
        for category, key in required_sensitive:
            with self.subTest(category=category, key=key):
                self.assertTrue(is_sensitive_config(category, key))


def run_security_tests():
    """Run all security integration tests"""
    
    print("🔒 Running Critical Security Integration Tests")
    print("=" * 60)
    
    # Create test suite
    test_classes = [
        TestEncryptionKeyEnforcement,
        TestPasswordChangeEnforcement, 
        TestSensitiveConfigEncryption,
        TestIntegrationSecurityFlow,
        TestProductionReadinessValidation
    ]
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 40)
        
        # Run tests for this class
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(suite)
        
        total_tests += result.testsRun
        total_failures += len(result.failures)
        total_errors += len(result.errors)
        
        # Show results for this class
        if result.wasSuccessful():
            print(f"✅ {test_class.__name__}: ALL TESTS PASSED")
        else:
            print(f"❌ {test_class.__name__}: {len(result.failures)} failures, {len(result.errors)} errors")
            
            for failure in result.failures:
                print(f"   FAIL: {failure[0]}")
                print(f"   {failure[1]}")
            
            for error in result.errors:
                print(f"   ERROR: {error[0]}")
                print(f"   {error[1]}")
    
    # Final summary
    print(f"\n🎯 SECURITY TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Failures: {total_failures}")  
    print(f"Errors: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("🎉 ALL CRITICAL SECURITY TESTS PASSED!")
        print("✅ System is production-ready from security perspective")
        return True
    else:
        print("🚨 CRITICAL SECURITY ISSUES FOUND!")
        print("❌ System is NOT production-ready")
        return False


if __name__ == "__main__":
    success = run_security_tests()
    sys.exit(0 if success else 1)