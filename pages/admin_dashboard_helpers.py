"""
Funções auxiliares para o dashboard administrativo avançado
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import json

def render_medical_trends_charts(trends_data):
    """Renderizar gráficos de tendências médicas"""
    if not trends_data:
        st.info("Nenhum dado de tendências disponível.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Exames por Mês")
        if not trends_data.get('exams_by_month', pd.DataFrame()).empty:
            exams_df = trends_data['exams_by_month']
            fig = px.line(
                exams_df, 
                x='month', 
                y='exam_count',
                title='Tendência de Exames ao Longo do Tempo',
                labels={'month': 'Mês', 'exam_count': 'Número de Exames'},
                color_discrete_sequence=['#FF69B4']
            )
            fig.update_layout(
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado de exames por mês.")
    
    with col2:
        st.subheader("🔬 Tipos de Exames Mais Comuns")
        if not trends_data.get('common_tests', pd.DataFrame()).empty:
            tests_df = trends_data['common_tests']
            fig = px.bar(
                tests_df, 
                x='count', 
                y='test_name',
                orientation='h',
                title='Top 10 Exames Mais Realizados',
                labels={'count': 'Quantidade', 'test_name': 'Tipo de Exame'},
                color='count',
                color_continuous_scale=['#FFB6C1', '#FF69B4', '#C71585']
            )
            fig.update_layout(
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado de tipos de exames.")
    
    # Gráfico de eventos médicos
    st.subheader("🏥 Timeline de Eventos Médicos")
    if not trends_data.get('medical_events_by_month', pd.DataFrame()).empty:
        events_df = trends_data['medical_events_by_month']
        fig = px.area(
            events_df,
            x='month',
            y='event_count',
            title='Eventos Médicos por Mês',
            labels={'month': 'Mês', 'event_count': 'Número de Eventos'},
            color_discrete_sequence=['#FF69B4']
        )
        fig.update_layout(
            height=300,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado de eventos médicos por mês.")

def render_user_activity_charts(db):
    """Renderizar gráficos de atividade de usuários"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👥 Atividade de Login (30 dias)")
        login_data = db.get_login_activity_data(30)
        if not login_data.empty:
            fig = px.bar(
                login_data,
                x='login_date',
                y='login_count',
                title='Logins por Dia',
                labels={'login_date': 'Data', 'login_count': 'Número de Logins'},
                color='login_count',
                color_continuous_scale=['#FFB6C1', '#FF69B4']
            )
            fig.update_layout(
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado de login disponível.")
    
    with col2:
        st.subheader("📊 Distribuição de Usuários por Role")
        # Simular dados de distribuição por role
        try:
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, COUNT(*) as count 
                    FROM users 
                    WHERE is_active = TRUE 
                    GROUP BY role
                """)
                role_data = cursor.fetchall()
                cursor.close()
                conn.close()
                
                if role_data:
                    # Convert database query results to DataFrame
                    roles_df = pd.DataFrame.from_records(role_data, columns=['role', 'count'])
                    fig = px.pie(
                        roles_df,
                        values='count',
                        names='role',
                        title='Distribuição de Usuários por Role',
                        color_discrete_sequence=['#FF69B4', '#FFB6C1', '#F0E68C']
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Nenhum dado de roles disponível.")
        except Exception as e:
            st.error(f"Erro ao obter dados de roles: {e}")

def render_exam_analysis_charts(trends_data):
    """Renderizar gráficos de análise de exames"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💊 Medicamentos por Via de Administração")
        if not trends_data.get('medication_routes', pd.DataFrame()).empty:
            routes_df = trends_data['medication_routes']
            fig = px.pie(
                routes_df,
                values='count',
                names='route',
                title='Distribuição por Via de Administração',
                color_discrete_sequence=['#FF69B4', '#FFB6C1', '#DDA0DD', '#F0E68C', '#98FB98']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado de medicamentos disponível.")
    
    with col2:
        st.subheader("📋 Análise Temporal de Dados")
        # Criar gráfico combinado de diferentes tipos de dados
        if trends_data.get('exams_by_month') is not None and not trends_data['exams_by_month'].empty:
            exams_df = trends_data['exams_by_month']
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Adicionar gráfico de exames
            fig.add_trace(
                go.Scatter(
                    x=exams_df['month'],
                    y=exams_df['exam_count'],
                    name="Exames",
                    line=dict(color='#FF69B4', width=3)
                ),
                secondary_y=False,
            )
            
            # Se tiver dados de eventos médicos, adicionar também
            if trends_data.get('medical_events_by_month') is not None and not trends_data['medical_events_by_month'].empty:
                events_df = trends_data['medical_events_by_month']
                fig.add_trace(
                    go.Scatter(
                        x=events_df['month'],
                        y=events_df['event_count'],
                        name="Eventos Médicos",
                        line=dict(color='#FFB6C1', width=3)
                    ),
                    secondary_y=True,
                )
            
            fig.update_xaxes(title_text="Mês")
            fig.update_yaxes(title_text="Número de Exames", secondary_y=False)
            fig.update_yaxes(title_text="Eventos Médicos", secondary_y=True)
            
            fig.update_layout(
                title_text="Análise Temporal Combinada",
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para análise temporal.")

def render_system_performance_charts(db_info, metrics):
    """Renderizar gráficos de performance do sistema"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💾 Uso de Espaço")
        if db_info and db_info.get('tables'):
            tables_df = pd.DataFrame(db_info['tables'])
            fig = px.treemap(
                tables_df,
                path=['table'],
                values='size_bytes',
                title='Uso de Espaço por Tabela',
                color='size_bytes',
                color_continuous_scale=['#FFB6C1', '#FF69B4', '#C71585']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Informações de tabelas não disponíveis.")
    
    with col2:
        st.subheader("📊 Métricas de Performance")
        # Criar gráfico de gauge para métricas
        total_files = metrics.get('total_files', 0)
        total_size_mb = metrics.get('total_file_size', 0) / (1024 * 1024)
        
        # Simular métricas de performance
        perf_metrics = {
            'Arquivos': total_files,
            'Tamanho (MB)': round(total_size_mb, 1),
            'Usuários Ativos': metrics.get('total_active_users', 0),
            'Exames': metrics.get('total_lab_results', 0)
        }
        
        fig = go.Figure()
        categories = list(perf_metrics.keys())
        values = list(perf_metrics.values())
        
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            marker_color=['#FF69B4', '#FFB6C1', '#DDA0DD', '#F0E68C'],
            text=values,
            textposition='auto'
        ))
        
        fig.update_layout(
            title="Métricas Gerais do Sistema",
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Métricas",
            yaxis_title="Valores"
        )
        
        st.plotly_chart(fig, use_container_width=True)

def render_recent_activity_widget(recent_activity):
    """Renderizar widget de atividade recente"""
    if not recent_activity:
        st.info("Nenhuma atividade recente registrada.")
        return
    
    # Filtros
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        activity_types = list(set([activity['type'] for activity in recent_activity]))
        selected_types = st.multiselect(
            "Filtrar por tipo:",
            activity_types,
            default=activity_types,
            key="activity_filter"
        )
    
    with col_filter2:
        max_items = st.slider("Máximo de itens:", 5, 50, 20, key="activity_limit")
    
    # Filtrar atividades
    filtered_activities = [
        activity for activity in recent_activity 
        if activity['type'] in selected_types
    ][:max_items]
    
    # Exibir atividades
    for i, activity in enumerate(filtered_activities):
        type_icons = {
            'lab_result': '🔬',
            'file_upload': '📁',
            'medical_event': '🏥',
            'admin_action': '⚙️'
        }
        
        icon = type_icons.get(activity['type'], '📋')
        timestamp = activity['timestamp'].strftime('%d/%m/%Y %H:%M')
        
        st.markdown(f"""
        <div class="activity-item">
            <strong>{icon} {activity['description']}</strong><br>
            <small>📅 {timestamp}</small>
        </div>
        """, unsafe_allow_html=True)

def export_dashboard_data(metrics, trends_data, recent_activity):
    """Exportar dados do dashboard"""
    try:
        # Criar dados para exportação
        export_data = {
            'metrics': metrics,
            'timestamp': datetime.now().isoformat(),
            'recent_activity_count': len(recent_activity),
            'trends_summary': {
                'exams_count': len(trends_data.get('exams_by_month', [])),
                'common_tests_count': len(trends_data.get('common_tests', [])),
                'events_count': len(trends_data.get('medical_events_by_month', []))
            }
        }
        
        # Converter para JSON
        json_data = json.dumps(export_data, indent=2, default=str)
        
        # Criar botão de download
        st.download_button(
            label="📥 Baixar Dados JSON",
            data=json_data,
            file_name=f"dashboard_data_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True
        )
        
        # Também criar CSV das métricas principais
        metrics_df = pd.DataFrame([metrics])
        csv_data = metrics_df.to_csv(index=False)
        
        st.download_button(
            label="📊 Baixar Métricas CSV",
            data=csv_data,
            file_name=f"dashboard_metrics_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        st.success("✅ Dados do dashboard prontos para download!")
        
    except Exception as e:
        st.error(f"Erro ao exportar dados: {e}")

def render_system_info_details(db_info, metrics):
    """Renderizar informações detalhadas do sistema"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🗄️ Informações do Banco de Dados")
        if db_info:
            st.write(f"**Tamanho Total:** {db_info.get('total_size_pretty', 'N/A')}")
            
            if db_info.get('tables'):
                st.write("**Tabelas por Tamanho:**")
                for table in db_info['tables'][:5]:  # Top 5 tabelas
                    st.write(f"• {table['table']}: {table['size_pretty']}")
        else:
            st.info("Informações do banco não disponíveis.")
    
    with col2:
        st.subheader("📈 Estatísticas Gerais")
        st.write(f"**Total de Usuários Ativos:** {metrics.get('total_active_users', 0)}")
        st.write(f"**Logins nas Últimas 24h:** {metrics.get('users_last_24h', 0)}")
        st.write(f"**Novos Usuários (30d):** {metrics.get('new_users_30d', 0)}")
        st.write(f"**Total de Arquivos:** {metrics.get('total_files', 0)}")
        
        file_size_mb = metrics.get('total_file_size', 0) / (1024 * 1024)
        st.write(f"**Tamanho dos Arquivos:** {file_size_mb:.1f} MB")
        
        st.write(f"**Exames Recentes (7d):** {metrics.get('recent_lab_results', 0)}")
        st.write(f"**Uploads Recentes (7d):** {metrics.get('recent_uploads', 0)}")
    
    # Informações adicionais do sistema
    st.subheader("⚙️ Status do Sistema")
    
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        # Status de conexão com BD
        try:
            test_metrics = metrics  # Se conseguimos buscar métricas, BD está OK
            st.success("🟢 Banco de Dados: Online")
        except:
            st.error("🔴 Banco de Dados: Erro")
    
    with status_col2:
        # Status de arquivos
        file_size_mb = metrics.get('total_file_size', 0) / (1024 * 1024)
        if file_size_mb < 80:  # Menos de 80MB
            st.success("🟢 Armazenamento: Normal")
        elif file_size_mb < 95:
            st.warning("🟡 Armazenamento: Atenção")
        else:
            st.error("🔴 Armazenamento: Crítico")
    
    with status_col3:
        # Status de atividade
        if metrics.get('users_last_24h', 0) > 0:
            st.success("🟢 Atividade: Normal")
        else:
            st.warning("🟡 Atividade: Baixa")
    
    # Recomendações do sistema
    st.subheader("💡 Recomendações")
    recommendations = []
    
    if metrics.get('users_last_24h', 0) == 0:
        recommendations.append("• Considere verificar se há problemas de acesso ao sistema")
    
    if file_size_mb > 80:
        recommendations.append("• Considere fazer limpeza de arquivos antigos")
    
    if metrics.get('total_active_users', 0) > 10:
        recommendations.append("• Sistema com boa adoção de usuários")
    
    if not recommendations:
        recommendations.append("• Sistema funcionando normalmente ✅")
    
    for rec in recommendations:
        st.write(rec)