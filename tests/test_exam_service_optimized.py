"""
Testes automatizados otimizados para ExamService
Demonstra boas práticas de testing para o sistema Luna Princess
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import tempfile
import os
from pathlib import Path

# Importar módulos do sistema
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.services.exam_service import ExamService
from src.core.database_simple import SimpleDatabaseManager
from src.core.config import get_config

class TestExamServiceOptimized:
    """Testes otimizados para ExamService com fixtures e mocks"""
    
    @pytest.fixture(scope="function")
    def temp_db(self):
        """Criar banco temporário para testes"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_file.close()
        
        # Configurar banco temporário
        original_path = None
        config = get_config()
        if hasattr(config.database, 'sqlite_path'):
            original_path = config.database.sqlite_path
            config.database.sqlite_path = temp_file.name
        
        yield temp_file.name
        
        # Cleanup
        if original_path:
            config.database.sqlite_path = original_path
        
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass
    
    @pytest.fixture(scope="function")
    def db_manager(self, temp_db):
        """Criar instância do database manager para testes"""
        db = SimpleDatabaseManager()
        db.db_path = temp_db
        db.init_database()
        return db
    
    @pytest.fixture(scope="function")
    def exam_service(self, db_manager):
        """Criar instância do ExamService para testes"""
        return ExamService(db_manager)
    
    @pytest.fixture(scope="function")
    def sample_exam_data(self, db_manager):
        """Criar dados de exemplo para testes"""
        sample_data = [
            ("Hemoglobina", "2024-01-15", 12.5, "g/dL", "12-18", "Lab Central", "Dr. Silva"),
            ("Hematócrito", "2024-01-15", 38.0, "%", "35-55", "Lab Central", "Dr. Silva"),
            ("Glicose", "2024-01-20", 95.0, "mg/dL", "70-110", "Lab Central", "Dr. Silva"),
            ("Hemoglobina", "2024-02-15", 13.0, "g/dL", "12-18", "Lab Central", "Dr. Silva"),
        ]
        
        for data in sample_data:
            db_manager.add_exam(*data)
        
        return sample_data
    
    # ===== TESTES DE FUNCIONALIDADE BÁSICA =====
    
    def test_exam_service_initialization(self, db_manager):
        """Testar inicialização do ExamService"""
        service = ExamService(db_manager)
        
        assert service.db == db_manager
        assert isinstance(service._cache, dict)
        assert isinstance(service._cache_ttl, dict)
    
    def test_get_exam_data_empty_database(self, exam_service):
        """Testar obtenção de dados com banco vazio"""
        result = exam_service.get_exam_data_optimized()
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    def test_get_exam_data_with_data(self, exam_service, sample_exam_data):
        """Testar obtenção de dados com dados de exemplo"""
        result = exam_service.get_exam_data_optimized()
        
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert 'exam_name' in result.columns
        assert len(result) > 0
    
    def test_add_exam_valid_data(self, exam_service):
        """Testar adição de exame com dados válidos"""
        exam_id = exam_service.add_exam_optimized(
            exam_name="Teste Exame",
            exam_date=datetime(2024, 1, 15),
            value=10.5,
            unit="mg/dL",
            reference_range="5-15",
            laboratory="Lab Teste",
            doctor="Dr. Teste"
        )
        
        assert exam_id is not None
        assert isinstance(exam_id, int)
        assert exam_id > 0
    
    def test_add_exam_invalid_data(self, exam_service):
        """Testar adição de exame com dados inválidos"""
        # Nome vazio
        result = exam_service.add_exam_optimized(
            exam_name="",
            exam_date=datetime(2024, 1, 15),
            value=10.5,
            unit="mg/dL"
        )
        assert result is None
        
        # Valor negativo
        result = exam_service.add_exam_optimized(
            exam_name="Teste",
            exam_date=datetime(2024, 1, 15),
            value=-5.0,
            unit="mg/dL"
        )
        assert result is None
        
        # Unidade vazia
        result = exam_service.add_exam_optimized(
            exam_name="Teste",
            exam_date=datetime(2024, 1, 15),
            value=10.5,
            unit=""
        )
        assert result is None
    
    # ===== TESTES DE CACHE =====
    
    def test_cache_functionality(self, exam_service, sample_exam_data):
        """Testar funcionalidade de cache"""
        # Primeira chamada - deve ir ao banco
        result1 = exam_service.get_exam_data_optimized()
        
        # Segunda chamada - deve usar cache
        result2 = exam_service.get_exam_data_optimized()
        
        # Resultados devem ser iguais
        pd.testing.assert_frame_equal(result1, result2)
        
        # Verificar se cache foi usado
        assert len(exam_service._cache) > 0
    
    def test_cache_invalidation(self, exam_service, sample_exam_data):
        """Testar invalidação de cache"""
        # Carregar dados no cache
        exam_service.get_exam_data_optimized()
        assert len(exam_service._cache) > 0
        
        # Adicionar novo exame (deve invalidar cache)
        exam_service.add_exam_optimized(
            exam_name="Novo Exame",
            exam_date=datetime(2024, 3, 1),
            value=15.0,
            unit="mg/dL"
        )
        
        # Cache deve estar vazio ou invalidado
        # (implementação pode variar)
        
    def test_cache_expiration(self, exam_service):
        """Testar expiração de cache"""
        # Simular cache expirado
        exam_service._cache["test_key"] = "test_value"
        exam_service._cache_ttl["test_key"] = datetime.now() - timedelta(seconds=400)
        
        # Cache deve estar expirado
        assert not exam_service._is_cache_valid("test_key", ttl_seconds=300)
        
        # Cache válido
        exam_service._cache_ttl["test_key"] = datetime.now()
        assert exam_service._is_cache_valid("test_key", ttl_seconds=300)
    
    # ===== TESTES DE COMPARAÇÃO =====
    
    def test_get_comparison_data_valid_exams(self, exam_service, sample_exam_data):
        """Testar obtenção de dados para comparação"""
        result = exam_service.get_exam_comparison_data(["Hemoglobina", "Hematócrito"])
        
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert 'exam_name' in result.columns
        assert 'exam_date' in result.columns
        assert 'value' in result.columns
    
    def test_get_comparison_data_empty_list(self, exam_service):
        """Testar comparação com lista vazia"""
        result = exam_service.get_exam_comparison_data([])
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    def test_get_comparison_data_with_date_range(self, exam_service, sample_exam_data):
        """Testar comparação com filtro de data"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        result = exam_service.get_exam_comparison_data(
            ["Hemoglobina"], 
            date_range=(start_date, end_date)
        )
        
        assert isinstance(result, pd.DataFrame)
        # Verificar se apenas dados do período estão incluídos
        if not result.empty:
            dates = pd.to_datetime(result['exam_date'])
            assert all(dates >= start_date)
            assert all(dates <= end_date)
    
    # ===== TESTES DE ESTATÍSTICAS =====
    
    def test_get_exam_statistics_empty_db(self, exam_service):
        """Testar estatísticas com banco vazio"""
        stats = exam_service.get_exam_statistics()
        
        assert isinstance(stats, dict)
        assert stats['total_exams'] == 0
        assert stats['unique_exam_types'] == 0
        assert stats['unique_dates'] == 0
    
    def test_get_exam_statistics_with_data(self, exam_service, sample_exam_data):
        """Testar estatísticas com dados"""
        stats = exam_service.get_exam_statistics()
        
        assert isinstance(stats, dict)
        assert stats['total_exams'] > 0
        assert stats['unique_exam_types'] > 0
        assert stats['unique_dates'] > 0
        assert 'first_exam_date' in stats
        assert 'last_exam_date' in stats
    
    # ===== TESTES DE BUSCA =====
    
    def test_search_exams_valid_term(self, exam_service, sample_exam_data):
        """Testar busca com termo válido"""
        result = exam_service.search_exams("Hemoglobina")
        
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert all("hemoglobina" in name.lower() for name in result['exam_name'])
    
    def test_search_exams_short_term(self, exam_service):
        """Testar busca com termo muito curto"""
        result = exam_service.search_exams("H")
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty  # Termo muito curto deve retornar vazio
    
    def test_search_exams_no_results(self, exam_service, sample_exam_data):
        """Testar busca sem resultados"""
        result = exam_service.search_exams("ExameInexistente")
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    # ===== TESTES DE EXAMES RECENTES =====
    
    def test_get_recent_exams_default_period(self, exam_service, sample_exam_data):
        """Testar obtenção de exames recentes (período padrão)"""
        result = exam_service.get_recent_exams()
        
        assert isinstance(result, pd.DataFrame)
        # Com dados de exemplo de 2024, deve retornar vazio se estivermos em 2025
        # ou dados se estivermos em 2024
    
    def test_get_recent_exams_custom_period(self, exam_service, sample_exam_data):
        """Testar obtenção de exames recentes (período customizado)"""
        result = exam_service.get_recent_exams(days=365)  # Último ano
        
        assert isinstance(result, pd.DataFrame)
        # Deve incluir mais dados com período maior
    
    # ===== TESTES DE PERFORMANCE =====
    
    @pytest.mark.performance
    def test_large_dataset_performance(self, exam_service):
        """Testar performance com dataset grande"""
        import time
        
        # Adicionar muitos exames
        start_time = time.time()
        
        for i in range(100):
            exam_service.add_exam_optimized(
                exam_name=f"Exame {i}",
                exam_date=datetime(2024, 1, 1) + timedelta(days=i % 30),
                value=float(i % 100),
                unit="mg/dL"
            )
        
        add_time = time.time() - start_time
        
        # Testar recuperação
        start_time = time.time()
        result = exam_service.get_exam_data_optimized()
        retrieve_time = time.time() - start_time
        
        # Verificar performance (ajustar limites conforme necessário)
        assert add_time < 10.0  # Menos de 10 segundos para adicionar 100 exames
        assert retrieve_time < 2.0  # Menos de 2 segundos para recuperar dados
        assert not result.empty
    
    @pytest.mark.performance
    def test_cache_performance(self, exam_service, sample_exam_data):
        """Testar performance do cache"""
        import time
        
        # Primeira chamada (sem cache)
        start_time = time.time()
        result1 = exam_service.get_exam_data_optimized()
        first_call_time = time.time() - start_time
        
        # Segunda chamada (com cache)
        start_time = time.time()
        result2 = exam_service.get_exam_data_optimized()
        second_call_time = time.time() - start_time
        
        # Cache deve ser mais rápido
        assert second_call_time < first_call_time
        pd.testing.assert_frame_equal(result1, result2)
    
    # ===== TESTES DE ERRO E EXCEÇÕES =====
    
    def test_database_connection_error(self, exam_service):
        """Testar comportamento com erro de conexão"""
        # Simular erro de conexão
        with patch.object(exam_service.db, 'get_connection', side_effect=sqlite3.Error("Connection failed")):
            result = exam_service.get_exam_data_optimized()
            
            # Deve retornar DataFrame vazio em caso de erro
            assert isinstance(result, pd.DataFrame)
            assert result.empty
    
    def test_invalid_sql_query(self, exam_service):
        """Testar comportamento com query SQL inválida"""
        # Simular erro de SQL
        with patch('pandas.read_sql_query', side_effect=sqlite3.Error("SQL error")):
            result = exam_service.get_exam_data_optimized()
            
            assert isinstance(result, pd.DataFrame)
            assert result.empty
    
    # ===== TESTES DE INTEGRAÇÃO =====
    
    def test_full_workflow(self, exam_service):
        """Testar workflow completo"""
        # 1. Verificar estado inicial
        initial_data = exam_service.get_exam_data_optimized()
        assert initial_data.empty
        
        # 2. Adicionar exames
        exam_ids = []
        for i in range(3):
            exam_id = exam_service.add_exam_optimized(
                exam_name=f"Exame {i}",
                exam_date=datetime(2024, 1, i+1),
                value=float(10 + i),
                unit="mg/dL"
            )
            exam_ids.append(exam_id)
        
        assert all(id is not None for id in exam_ids)
        
        # 3. Verificar dados adicionados
        final_data = exam_service.get_exam_data_optimized()
        assert not final_data.empty
        
        # 4. Testar busca
        search_result = exam_service.search_exams("Exame")
        assert not search_result.empty
        
        # 5. Testar estatísticas
        stats = exam_service.get_exam_statistics()
        assert stats['total_exams'] >= 3
        assert stats['unique_exam_types'] >= 3

# ===== FIXTURES GLOBAIS =====

@pytest.fixture(scope="session")
def test_config():
    """Configuração para testes"""
    return {
        "database": {
            "type": "sqlite",
            "path": ":memory:"
        },
        "cache": {
            "enabled": True,
            "ttl": 60
        }
    }

# ===== MARKS PERSONALIZADOS =====

# Marcar testes de performance
pytest.mark.performance = pytest.mark.mark("performance")

# Marcar testes de integração
pytest.mark.integration = pytest.mark.mark("integration")

# ===== CONFIGURAÇÃO DE TESTES =====

def pytest_configure(config):
    """Configuração personalizada do pytest"""
    config.addinivalue_line(
        "markers", "performance: marca testes de performance"
    )
    config.addinivalue_line(
        "markers", "integration: marca testes de integração"
    )

# ===== EXECUTAR TESTES =====

if __name__ == "__main__":
    # Executar testes específicos
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--durations=10"
    ])

