#!/usr/bin/env python3
"""
Sistema de migração e verificação de segurança para configurações sensíveis
"""
import os
import sys
from typing import Dict, List, Any, Optional
import psycopg2
import json
from datetime import datetime

# Importar módulos do sistema
from encryption_utils import get_encryption_manager, is_sensitive_config, should_encrypt_config


class SecurityMigrationManager:
    """Gerencia migração e verificação de segurança de configurações"""
    
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('PGHOST'),
            'database': os.getenv('PGDATABASE'),
            'user': os.getenv('PGUSER'),
            'password': os.getenv('PGPASSWORD'),
            'port': os.getenv('PGPORT', 5432)
        }
        self.encryption_manager = get_encryption_manager()
    
    def get_connection(self):
        """Obter conexão com banco de dados"""
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            print(f"❌ Erro ao conectar com banco: {e}")
            return None
    
    def audit_sensitive_configs(self) -> Dict[str, Any]:
        """Auditar todas as configurações sensíveis no sistema"""
        
        print("🔍 Iniciando auditoria de configurações sensíveis...")
        
        conn = self.get_connection()
        if not conn:
            return {'error': 'Falha na conexão com banco'}
        
        cursor = None
        try:
            cursor = conn.cursor()
            
            # Obter todas as configurações
            cursor.execute("""
                SELECT category, config_key, config_value, is_encrypted, is_active
                FROM system_config 
                ORDER BY category, config_key
            """)
            
            results = {
                'total_configs': 0,
                'sensitive_configs': 0,
                'properly_encrypted': 0,
                'needs_encryption': [],
                'encryption_issues': [],
                'summary': {}
            }
            
            for row in cursor.fetchall():
                category, config_key, config_value, is_encrypted, is_active = row
                results['total_configs'] += 1
                
                # Verificar se é sensível
                if is_sensitive_config(category, config_key):
                    results['sensitive_configs'] += 1
                    
                    try:
                        config_data = json.loads(config_value)
                        value = config_data.get('value', '')
                        
                        if is_encrypted:
                            # Verificar se conseguimos descriptografar
                            if self.encryption_manager.is_encryption_available():
                                decrypted = self.encryption_manager.decrypt(value)
                                if decrypted is not None:
                                    results['properly_encrypted'] += 1
                                    print(f"✅ {category}.{config_key}: Corretamente criptografado")
                                else:
                                    results['encryption_issues'].append({
                                        'category': category,
                                        'config_key': config_key,
                                        'issue': 'Falha na descriptografia - valor pode estar corrompido'
                                    })
                                    print(f"⚠️ {category}.{config_key}: Falha na descriptografia")
                            else:
                                results['encryption_issues'].append({
                                    'category': category,
                                    'config_key': config_key,
                                    'issue': 'Sistema de criptografia não disponível'
                                })
                                print(f"❌ {category}.{config_key}: Sistema de criptografia indisponível")
                        else:
                            # Sensível mas não criptografado!
                            results['needs_encryption'].append({
                                'category': category,
                                'config_key': config_key,
                                'has_value': bool(value and str(value).strip()),
                                'is_active': is_active
                            })
                            print(f"🚨 {category}.{config_key}: Sensível mas NÃO CRIPTOGRAFADO!")
                    
                    except Exception as e:
                        results['encryption_issues'].append({
                            'category': category,
                            'config_key': config_key,
                            'issue': f'Erro ao processar: {e}'
                        })
                        print(f"❌ {category}.{config_key}: Erro - {e}")
            
            # Resumo da auditoria
            results['summary'] = {
                'security_status': 'CRÍTICO' if results['needs_encryption'] else ('ATENÇÃO' if results['encryption_issues'] else 'OK'),
                'encryption_coverage': f"{results['properly_encrypted']}/{results['sensitive_configs']} configurações sensíveis criptografadas",
                'critical_issues': len(results['needs_encryption']),
                'warnings': len(results['encryption_issues'])
            }
            
            print(f"\n📊 RESUMO DA AUDITORIA:")
            print(f"   Total de configurações: {results['total_configs']}")
            print(f"   Configurações sensíveis: {results['sensitive_configs']}")
            print(f"   Corretamente criptografadas: {results['properly_encrypted']}")
            print(f"   Precisam de criptografia: {len(results['needs_encryption'])}")
            print(f"   Problemas de criptografia: {len(results['encryption_issues'])}")
            print(f"   Status: {results['summary']['security_status']}")
            
            return results
            
        except Exception as e:
            print(f"❌ Erro na auditoria: {e}")
            return {'error': str(e)}
        finally:
            if cursor:
                cursor.close()
            conn.close()
    
    def migrate_plaintext_configs(self, dry_run: bool = True) -> Dict[str, Any]:
        """Migrar configurações sensíveis em texto plano para criptografadas"""
        
        print(f"🔄 {'SIMULAÇÃO DE' if dry_run else 'EXECUTANDO'} migração de configurações sensíveis...")
        
        if not self.encryption_manager.is_encryption_available():
            error = "❌ Sistema de criptografia não disponível - migração impossível!"
            print(error)
            return {'error': error}
        
        conn = self.get_connection()
        if not conn:
            return {'error': 'Falha na conexão com banco'}
        
        cursor = None
        try:
            cursor = conn.cursor()
            
            results = {
                'migrated': [],
                'failed': [],
                'skipped': [],
                'total_processed': 0
            }
            
            # Encontrar configurações sensíveis não criptografadas
            cursor.execute("""
                SELECT category, config_key, config_value, id
                FROM system_config 
                WHERE is_encrypted = FALSE AND is_active = TRUE
                ORDER BY category, config_key
            """)
            
            for row in cursor.fetchall():
                category, config_key, config_value, config_id = row
                results['total_processed'] += 1
                
                if is_sensitive_config(category, config_key):
                    try:
                        config_data = json.loads(config_value)
                        value = config_data.get('value', '')
                        
                        if not value or not str(value).strip():
                            results['skipped'].append({
                                'category': category,
                                'config_key': config_key,
                                'reason': 'Valor vazio'
                            })
                            print(f"⏭️ {category}.{config_key}: Valor vazio, pulando")
                            continue
                        
                        # Criptografar o valor
                        encrypted_value = self.encryption_manager.encrypt(str(value))
                        
                        if encrypted_value:
                            new_config_data = {'value': encrypted_value}
                            new_config_json = json.dumps(new_config_data)
                            
                            if not dry_run:
                                # Atualizar no banco
                                cursor.execute("""
                                    UPDATE system_config 
                                    SET config_value = %s, is_encrypted = TRUE, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = %s
                                """, (new_config_json, config_id))
                            
                            results['migrated'].append({
                                'category': category,
                                'config_key': config_key,
                                'action': 'Criptografado' if not dry_run else 'Seria criptografado'
                            })
                            print(f"{'✅' if not dry_run else '🔄'} {category}.{config_key}: {'Migrado' if not dry_run else 'Será migrado'}")
                            
                        else:
                            results['failed'].append({
                                'category': category,
                                'config_key': config_key,
                                'reason': 'Falha na criptografia'
                            })
                            print(f"❌ {category}.{config_key}: Falha na criptografia")
                            
                    except Exception as e:
                        results['failed'].append({
                            'category': category,
                            'config_key': config_key,
                            'reason': str(e)
                        })
                        print(f"❌ {category}.{config_key}: Erro - {e}")
                else:
                    results['skipped'].append({
                        'category': category,
                        'config_key': config_key,
                        'reason': 'Não sensível'
                    })
            
            if not dry_run:
                conn.commit()
                print("💾 Alterações commitadas no banco de dados")
            else:
                print("🔍 Simulação concluída - nenhuma alteração feita")
            
            print(f"\n📊 RESULTADO DA MIGRAÇÃO:")
            print(f"   Total processado: {results['total_processed']}")
            print(f"   Migrados: {len(results['migrated'])}")
            print(f"   Falhas: {len(results['failed'])}")
            print(f"   Pulados: {len(results['skipped'])}")
            
            return results
            
        except Exception as e:
            if not dry_run:
                conn.rollback()
            print(f"❌ Erro na migração: {e}")
            return {'error': str(e)}
        finally:
            if cursor:
                cursor.close()
            conn.close()
    
    def add_encryption_validation_trigger(self) -> bool:
        """Adicionar trigger de banco que previne escritas plaintext de configs sensíveis"""
        
        print("🛡️ Adicionando proteção de banco contra escritas plaintext...")
        
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = None
        try:
            cursor = conn.cursor()
            
            # Criar função de validação
            cursor.execute("""
                CREATE OR REPLACE FUNCTION prevent_sensitive_plaintext()
                RETURNS TRIGGER AS $$
                DECLARE
                    sensitive_configs JSONB := '{
                        "SMTP": ["smtp_password"],
                        "API": ["openai_api_key", "webhook_secret", "api_secret_key"],
                        "SECURITY": ["encryption_key", "jwt_secret", "oauth_client_secret"],
                        "GENERAL": ["database_password", "redis_password"]
                    }'::jsonb;
                    config_keys TEXT[];
                BEGIN
                    -- Verificar se é configuração sensível
                    config_keys := ARRAY(SELECT jsonb_array_elements_text(sensitive_configs -> NEW.category));
                    
                    IF NEW.config_key = ANY(config_keys) THEN
                        -- Se é sensível mas não está marcado como criptografado
                        IF NEW.is_encrypted = FALSE THEN
                            -- Verificar se tem valor (permitir valores vazios)
                            IF (NEW.config_value::jsonb->>'value') IS NOT NULL 
                               AND LENGTH(TRIM(NEW.config_value::jsonb->>'value')) > 0 THEN
                                RAISE EXCEPTION 'BLOQUEIO_SEGURANÇA: Configuração sensível %.% deve ser criptografada (is_encrypted=TRUE)', 
                                    NEW.category, NEW.config_key;
                            END IF;
                        END IF;
                    END IF;
                    
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            # Criar trigger
            cursor.execute("""
                DROP TRIGGER IF EXISTS prevent_sensitive_plaintext_trigger ON system_config;
                
                CREATE TRIGGER prevent_sensitive_plaintext_trigger
                    BEFORE INSERT OR UPDATE ON system_config
                    FOR EACH ROW
                    EXECUTE FUNCTION prevent_sensitive_plaintext();
            """)
            
            conn.commit()
            print("✅ Proteção de banco adicionada com sucesso!")
            print("   - Trigger criado: prevent_sensitive_plaintext_trigger")
            print("   - Bloqueia escritas plaintext de configurações sensíveis")
            
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Erro ao adicionar proteção: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()
    
    def run_comprehensive_security_check(self) -> Dict[str, Any]:
        """Executar verificação completa de segurança"""
        
        print("🔒 INICIANDO VERIFICAÇÃO COMPLETA DE SEGURANÇA\n")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'encryption_available': False,
            'audit_results': {},
            'protection_status': False,
            'overall_status': 'FALHA',
            'recommendations': []
        }
        
        # 1. Verificar sistema de criptografia
        print("1️⃣ Verificando sistema de criptografia...")
        results['encryption_available'] = self.encryption_manager.is_encryption_available()
        if results['encryption_available']:
            print("✅ Sistema de criptografia disponível")
        else:
            print("❌ Sistema de criptografia NÃO DISPONÍVEL")
            results['recommendations'].append("CRÍTICO: Configure ENCRYPTION_KEY no ambiente")
            return results
        
        # 2. Auditar configurações
        print("\n2️⃣ Auditando configurações sensíveis...")
        results['audit_results'] = self.audit_sensitive_configs()
        
        # 3. Verificar proteções
        print("\n3️⃣ Verificando proteções do banco...")
        results['protection_status'] = self.add_encryption_validation_trigger()
        
        # 4. Determinar status geral
        if (results['encryption_available'] and 
            not results['audit_results'].get('needs_encryption', []) and
            not results['audit_results'].get('encryption_issues', []) and
            results['protection_status']):
            results['overall_status'] = 'SEGURO'
        elif results['audit_results'].get('needs_encryption', []):
            results['overall_status'] = 'CRÍTICO'
            results['recommendations'].append("CRÍTICO: Criptografar configurações sensíveis em plaintext")
        elif results['audit_results'].get('encryption_issues', []):
            results['overall_status'] = 'ATENÇÃO'
            results['recommendations'].append("ATENÇÃO: Resolver problemas de criptografia")
        else:
            results['overall_status'] = 'ATENÇÃO'
        
        # 5. Resumo final
        print(f"\n🎯 STATUS FINAL DE SEGURANÇA: {results['overall_status']}")
        if results['recommendations']:
            print("📋 RECOMENDAÇÕES:")
            for rec in results['recommendations']:
                print(f"   - {rec}")
        
        return results


def main():
    """Função principal para execução como script"""
    
    print("🛡️ SISTEMA DE VERIFICAÇÃO E MIGRAÇÃO DE SEGURANÇA")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python security_migration.py audit              # Auditar configurações")
        print("  python security_migration.py migrate --dry-run  # Simular migração")
        print("  python security_migration.py migrate            # Executar migração")
        print("  python security_migration.py protect            # Adicionar proteções")
        print("  python security_migration.py check              # Verificação completa")
        return
    
    manager = SecurityMigrationManager()
    command = sys.argv[1]
    
    try:
        if command == "audit":
            manager.audit_sensitive_configs()
        
        elif command == "migrate":
            dry_run = "--dry-run" in sys.argv
            manager.migrate_plaintext_configs(dry_run=dry_run)
        
        elif command == "protect":
            manager.add_encryption_validation_trigger()
        
        elif command == "check":
            results = manager.run_comprehensive_security_check()
            
            # Sair com código de erro se status não for seguro
            if results['overall_status'] != 'SEGURO':
                sys.exit(1)
        
        else:
            print(f"❌ Comando desconhecido: {command}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()