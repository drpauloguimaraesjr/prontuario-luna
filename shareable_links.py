"""
Sistema de Links Compartilháveis para Prontuário Médico Veterinário
Gera URLs compartilháveis para gráficos, relatórios e visualizações
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import streamlit as st
from urllib.parse import urlencode
import base64


class ShareableLinkManager:
    """Gerenciador de links compartilháveis para gráficos e relatórios"""
    
    def __init__(self, db):
        self.db = db
        self.base_url = self._get_base_url()
    
    def _get_base_url(self) -> str:
        """Obter URL base da aplicação"""
        try:
            # Em produção, isto seria a URL real do deploy
            if hasattr(st, 'config') and hasattr(st.config, 'get_option'):
                port = st.config.get_option('server.port')
                return f"http://0.0.0.0:{port}"
            return "http://0.0.0.0:5000"
        except:
            return "http://0.0.0.0:5000"
    
    def generate_chart_link(self, 
                          chart_type: str,
                          chart_config: Dict[str, Any],
                          expiry_hours: int = 72) -> Dict[str, str]:
        """
        Gerar link compartilhável para gráfico
        
        Args:
            chart_type: Tipo do gráfico ('comparison', 'timeline', 'medication')
            chart_config: Configurações específicas do gráfico
            expiry_hours: Horas até expiração (padrão: 72h)
        
        Returns:
            Dict com 'url', 'share_id', 'expires_at'
        """
        
        # Gerar ID único
        share_id = self._generate_share_id()
        
        # Calcular expiração
        expires_at = datetime.now() + timedelta(hours=expiry_hours)
        
        # Criar configuração completa
        share_data = {
            'id': share_id,
            'type': 'chart',
            'chart_type': chart_type,
            'config': chart_config,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat(),
            'access_count': 0
        }
        
        # Salvar no banco de dados
        self._save_shareable_link(share_data)
        
        # Gerar URL
        url = f"{self.base_url}/?share={share_id}"
        
        return {
            'url': url,
            'share_id': share_id,
            'expires_at': expires_at.strftime('%d/%m/%Y %H:%M')
        }
    
    def generate_report_link(self,
                           report_type: str,
                           report_config: Dict[str, Any],
                           expiry_hours: int = 168) -> Dict[str, str]:
        """
        Gerar link compartilhável para relatório
        
        Args:
            report_type: Tipo do relatório ('lab_summary', 'timeline_summary', 'complete_record')
            report_config: Configurações específicas do relatório
            expiry_hours: Horas até expiração (padrão: 168h = 7 dias)
        """
        
        share_id = self._generate_share_id()
        expires_at = datetime.now() + timedelta(hours=expiry_hours)
        
        share_data = {
            'id': share_id,
            'type': 'report',
            'report_type': report_type,
            'config': report_config,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat(),
            'access_count': 0
        }
        
        self._save_shareable_link(share_data)
        
        url = f"{self.base_url}/?share={share_id}"
        
        return {
            'url': url,
            'share_id': share_id,
            'expires_at': expires_at.strftime('%d/%m/%Y %H:%M')
        }
    
    def generate_comparison_link(self, 
                               selected_tests: List[str],
                               date_range: Dict[str, str],
                               chart_settings: Dict[str, Any]) -> Dict[str, str]:
        """Gerar link para gráfico comparativo específico"""
        
        config = {
            'selected_tests': selected_tests,
            'date_range': date_range,
            'chart_settings': chart_settings
        }
        
        return self.generate_chart_link('comparison', config)
    
    def generate_timeline_link(self,
                             date_range: Optional[Dict[str, str]] = None,
                             event_filters: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Gerar link para timeline específica"""
        
        config = {
            'date_range': date_range,
            'event_filters': event_filters or {}
        }
        
        return self.generate_chart_link('timeline', config)
    
    def generate_qr_code(self, url: str) -> str:
        """Gerar código QR para um link compartilhável"""
        try:
            import qrcode
            from io import BytesIO
            
            # Criar QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Gerar imagem
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Converter para bytes
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_bytes = img_buffer.getvalue()
            
            # Retornar como base64
            return base64.b64encode(img_bytes).decode()
            
        except ImportError:
            # Se qrcode não estiver disponível, retornar URL simples
            return url
        except Exception as e:
            st.warning(f"Erro ao gerar QR code: {e}")
            return url
    
    def get_share_data(self, share_id: str) -> Optional[Dict[str, Any]]:
        """Recuperar dados de um link compartilhado"""
        
        try:
            # Buscar no banco de dados
            query = "SELECT * FROM shareable_links WHERE share_id = %s"
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (share_id,))
            result = cursor.fetchone()
            
            if result:
                # Incrementar contador de acesso
                self._increment_access_count(share_id)
                
                # Converter para dict
                columns = [desc[0] for desc in cursor.description]
                share_data = dict(zip(columns, result))
                
                # Verificar se não expirou
                expires_at = share_data['expires_at']
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                if datetime.now() > expires_at:
                    return None
                
                # Parsear configuração JSON
                share_data['config'] = json.loads(share_data['config'])
                
                return share_data
            
            return None
            
        except Exception as e:
            st.error(f"Erro ao recuperar link compartilhado: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()
    
    def list_shared_links(self) -> List[Dict[str, Any]]:
        """Listar todos os links compartilhados ativos"""
        
        try:
            query = """
            SELECT share_id, type, chart_type, report_type, created_at, expires_at, access_count
            FROM shareable_links 
            WHERE expires_at > %s
            ORDER BY created_at DESC
            """
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (datetime.now().isoformat(),))
            results = cursor.fetchall()
            
            links = []
            for result in results:
                columns = [desc[0] for desc in cursor.description]
                link_data = dict(zip(columns, result))
                links.append(link_data)
            
            return links
            
        except Exception as e:
            st.error(f"Erro ao listar links compartilhados: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
    
    def revoke_link(self, share_id: str) -> bool:
        """Revogar um link compartilhado"""
        
        try:
            query = "DELETE FROM shareable_links WHERE share_id = %s"
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (share_id,))
            conn.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            st.error(f"Erro ao revogar link: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def cleanup_expired_links(self):
        """Limpar links expirados"""
        
        try:
            query = "DELETE FROM shareable_links WHERE expires_at < %s"
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (datetime.now().isoformat(),))
            deleted_count = cursor.rowcount
            conn.commit()
            
            return deleted_count
            
        except Exception as e:
            st.error(f"Erro ao limpar links expirados: {e}")
            return 0
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _generate_share_id(self) -> str:
        """Gerar ID único para compartilhamento"""
        
        # Combinar timestamp com UUID para garantir unicidade
        timestamp = str(int(datetime.now().timestamp() * 1000))
        random_id = str(uuid.uuid4())
        
        # Criar hash SHA256
        combined = f"{timestamp}-{random_id}"
        hash_obj = hashlib.sha256(combined.encode())
        
        # Retornar os primeiros 16 caracteres do hash (mais user-friendly)
        return hash_obj.hexdigest()[:16]
    
    def _save_shareable_link(self, share_data: Dict[str, Any]):
        """Salvar link compartilhável no banco de dados"""
        
        # Criar tabela se não existir
        self._ensure_table_exists()
        
        try:
            query = """
            INSERT INTO shareable_links 
            (share_id, type, chart_type, report_type, config, created_at, expires_at, access_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (
                share_data['id'],
                share_data['type'],
                share_data.get('chart_type'),
                share_data.get('report_type'),
                json.dumps(share_data['config']),
                share_data['created_at'],
                share_data['expires_at'],
                share_data['access_count']
            ))
            conn.commit()
            
        except Exception as e:
            st.error(f"Erro ao salvar link compartilhado: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _increment_access_count(self, share_id: str):
        """Incrementar contador de acesso"""
        
        try:
            query = "UPDATE shareable_links SET access_count = access_count + 1 WHERE share_id = %s"
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (share_id,))
            conn.commit()
            
        except Exception as e:
            # Não é crítico se falhar
            pass
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _ensure_table_exists(self):
        """Garantir que a tabela de links compartilháveis existe"""
        
        try:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS shareable_links (
                id SERIAL PRIMARY KEY,
                share_id VARCHAR(16) UNIQUE NOT NULL,
                type VARCHAR(20) NOT NULL,
                chart_type VARCHAR(20),
                report_type VARCHAR(20),
                config TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 0,
                created_by VARCHAR(100) DEFAULT 'system'
            )
            """
            
            conn = self.db.get_connection()
            if not conn:
                return
                
            cursor = conn.cursor()
            cursor.execute(create_table_query)
            conn.commit()
            
        except Exception as e:
            st.error(f"Erro ao criar tabela de links compartilháveis: {e}")
            raise
        finally:
            if 'conn' in locals() and conn:
                conn.close()


def render_shared_content(share_id: str, db, ai_processor=None):
    """Renderizar conteúdo compartilhado baseado no share_id"""
    
    link_manager = ShareableLinkManager(db)
    share_data = link_manager.get_share_data(share_id)
    
    if not share_data:
        st.error("🔗 Link inválido ou expirado")
        st.info("Este link pode ter expirado ou sido removido.")
        return
    
    st.info(f"🔗 Visualizando conteúdo compartilhado - Acessado {share_data['access_count']} vezes")
    
    # Renderizar baseado no tipo
    if share_data['type'] == 'chart':
        render_shared_chart(share_data, db)
    elif share_data['type'] == 'report':
        render_shared_report(share_data, db)
    else:
        st.error("Tipo de conteúdo não suportado")


def render_shared_chart(share_data: Dict[str, Any], db):
    """Renderizar gráfico compartilhado"""
    
    chart_type = share_data['chart_type']
    config = share_data['config']
    
    st.title(f"📊 {chart_type.title()} - Luna Princess")
    
    if chart_type == 'comparison':
        render_shared_comparison_chart(config, db)
    elif chart_type == 'timeline':
        render_shared_timeline_chart(config, db)
    elif chart_type == 'medication':
        render_shared_medication_chart(config, db)
    else:
        st.error(f"Tipo de gráfico '{chart_type}' não suportado")


def render_shared_comparison_chart(config: Dict[str, Any], db):
    """Renderizar gráfico comparativo compartilhado"""
    
    from components.comparisons import ComparisonComponent
    
    st.subheader("🔬 Comparação de Exames Laboratoriais")
    
    # Recriar o gráfico usando a configuração salva
    comparison = ComparisonComponent(db)
    
    # Obter dados dos exames
    lab_results = db.get_lab_results()
    
    if not lab_results.empty:
        selected_tests = config.get('selected_tests', [])
        chart_settings = config.get('chart_settings', {})
        
        # Aplicar filtros de data se especificados
        date_range = config.get('date_range')
        if date_range:
            start_date = date_range.get('start')
            end_date = date_range.get('end')
            if start_date and end_date:
                lab_results = lab_results[
                    (lab_results['test_date'] >= start_date) & 
                    (lab_results['test_date'] <= end_date)
                ]
        
        # Mostrar informações da configuração
        with st.expander("ℹ️ Configurações do Gráfico"):
            st.write(f"**Exames selecionados:** {', '.join(selected_tests)}")
            if date_range:
                st.write(f"**Período:** {date_range.get('start', 'N/A')} a {date_range.get('end', 'N/A')}")
            st.write(f"**Configurações:** {chart_settings}")
        
        # Renderizar o gráfico
        if selected_tests:
            # Simular o comportamento usando os dados filtrados
            filtered_results = lab_results[lab_results['test_name'].isin(selected_tests)]
            if not filtered_results.empty:
                comparison._render_comparison_chart(filtered_results, selected_tests, [])
            else:
                st.warning("Nenhum dado encontrado para os exames selecionados")
        else:
            st.warning("Nenhum exame selecionado para comparação")
    else:
        st.info("Nenhum resultado laboratorial disponível")


def render_shared_timeline_chart(config: Dict[str, Any], db):
    """Renderizar timeline compartilhada"""
    
    from components.timeline import TimelineComponent
    
    st.subheader("📅 História da Doença Atual")
    
    timeline = TimelineComponent(db)
    
    # Obter eventos da timeline
    events = db.get_medical_timeline()
    
    if events:
        # Aplicar filtros se especificados
        date_range = config.get('date_range')
        event_filters = config.get('event_filters', {})
        
        # Mostrar informações da configuração
        with st.expander("ℹ️ Configurações da Timeline"):
            if date_range:
                st.write(f"**Período:** {date_range.get('start', 'N/A')} a {date_range.get('end', 'N/A')}")
            if event_filters:
                st.write(f"**Filtros:** {event_filters}")
        
        # Renderizar timeline
        timeline._render_timeline_chart(events)
        
        # Mostrar lista de eventos (como não temos _render_timeline_details)
        st.subheader("📋 Detalhes dos Eventos")
        for i, event in enumerate(events):
            with st.expander(f"📅 {event['title']} - {event['event_date']}"):
                if event.get('description'):
                    st.write(f"**Descrição:** {event['description']}")
                if event.get('symptoms'):
                    st.write(f"**Sintomas:** {', '.join(event['symptoms'])}")
                if event.get('clinical_notes'):
                    st.write(f"**Notas Clínicas:** {event['clinical_notes']}")
    else:
        st.info("Nenhum evento na timeline disponível")


def render_shared_medication_chart(config: Dict[str, Any], db):
    """Renderizar gráfico de medicamentos compartilhado"""
    
    st.subheader("💊 Histórico de Medicamentos")
    
    # Obter medicamentos
    medications = db.get_medication_history()
    
    if medications:
        # Implementar visualização de medicamentos
        st.write("**Medicamentos registrados:**")
        for med in medications:
            st.write(f"• **{med.get('name', 'N/A')}** - {med.get('dose', 'N/A')}")
            if med.get('notes'):
                st.write(f"  *{med['notes']}*")
    else:
        st.info("Nenhum medicamento registrado")


def render_shared_report(share_data: Dict[str, Any], db):
    """Renderizar relatório compartilhado"""
    
    report_type = share_data['report_type']
    config = share_data['config']
    
    st.title(f"📄 {report_type.replace('_', ' ').title()} - Luna Princess")
    
    if report_type == 'lab_summary':
        render_shared_lab_summary(config, db)
    elif report_type == 'timeline_summary':
        render_shared_timeline_summary(config, db)
    elif report_type == 'complete_record':
        render_shared_complete_record(config, db)
    else:
        st.error(f"Tipo de relatório '{report_type}' não suportado")


def render_shared_lab_summary(config: Dict[str, Any], db):
    """Renderizar resumo laboratorial compartilhado"""
    
    from components.lab_results import LabResultsComponent
    
    lab_results_component = LabResultsComponent(db)
    lab_results = db.get_lab_results()
    
    if not lab_results.empty:
        summary = lab_results_component._generate_summary_report(lab_results)
        st.text_area("Resumo dos Exames Laboratoriais", summary, height=400, disabled=True)
    else:
        st.info("Nenhum resultado laboratorial disponível")


def render_shared_timeline_summary(config: Dict[str, Any], db):
    """Renderizar resumo da timeline compartilhado"""
    
    from components.timeline import TimelineComponent
    
    timeline = TimelineComponent(db)
    summary = timeline.get_timeline_summary()
    st.text_area("Resumo da Linha do Tempo", summary, height=400, disabled=True)


def render_shared_complete_record(config: Dict[str, Any], db):
    """Renderizar prontuário completo compartilhado"""
    
    st.subheader("📋 Prontuário Médico Completo")
    st.warning("🔒 Esta é uma visualização compartilhada. Funcionalidades de edição estão desabilitadas.")
    
    # Mostrar informações do paciente
    patient_info = db.get_patient_info()
    if patient_info:
        with st.expander("👤 Informações do Paciente", expanded=True):
            for key, value in patient_info.items():
                if value:
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
    
    # Mostrar resumo dos exames
    lab_results = db.get_lab_results()
    if not lab_results.empty:
        with st.expander("🔬 Resumo Laboratorial"):
            from components.lab_results import LabResultsComponent
            lab_component = LabResultsComponent(db)
            summary = lab_component._generate_summary_report(lab_results)
            st.text(summary)
    
    # Mostrar timeline
    timeline_events = db.get_medical_timeline()
    if timeline_events:
        with st.expander("📅 Linha do Tempo"):
            st.write("**Eventos registrados:**")
            for event in timeline_events:
                st.write(f"• **{event['title']}** - {event['event_date']}")
                if event.get('description'):
                    st.write(f"  {event['description']}")
    
    # Mostrar medicamentos
    medications = db.get_medication_history()
    if medications:
        with st.expander("💊 Medicamentos"):
            for med in medications:
                st.write(f"**{med['name']}** - {med.get('dose', 'N/A')}")
                if med.get('notes'):
                    st.write(f"  *{med['notes']}*")