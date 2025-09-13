import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
import io
import base64
import numpy as np
from typing import List, Dict, Any, Optional
from utils import format_date, format_lab_value, create_lab_results_chart

class ComparisonComponent:
    """Componente para comparar resultados laboratoriais com gráficos interativos e exportações"""
    
    def __init__(self, db):
        self.db = db
    
    def render(self):
        """Renderizar a interface de comparação"""
        
        # Obter dados disponíveis
        test_names = self.db.get_test_names()
        test_dates = self.db.get_test_dates()
        
        if not test_names:
            st.info("Nenhum exame disponível para comparação. Adicione alguns exames primeiro.")
            return
        
        # Renderizar controles de seleção
        selected_tests, selected_dates = self._render_selection_controls(test_names, test_dates)
        
        if selected_tests:
            # Obter dados filtrados
            lab_results = self._get_filtered_results(selected_tests, selected_dates)
            
            if not lab_results.empty:
                # Renderizar gráfico
                self._render_comparison_chart(lab_results, selected_tests, selected_dates)
                
                # Renderizar tabela de dados
                self._render_comparison_table(lab_results)
                
                # Renderizar opções de exportação
                self._render_export_options(lab_results, selected_tests, selected_dates)
            else:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
        else:
            st.info("Selecione pelo menos um exame para visualizar a comparação.")
    
    def _render_selection_controls(self, test_names: List[str], test_dates: List[str]) -> tuple:
        """Renderizar controles para seleção de exames e datas"""
        
        st.subheader("Seleção de Exames e Datas")
        
        # Seleção de exames
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Selecione os exames para comparar:**")
            
            # Botões de seleção rápida
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("Selecionar Todos"):
                    st.session_state['selected_tests'] = test_names
                    st.rerun()
            
            with col_b:
                if st.button("Limpar Seleção"):
                    st.session_state['selected_tests'] = []
                    st.rerun()
            
            with col_c:
                # Grupos de exames comuns
                if st.button("Hemograma Básico"):
                    common_tests = [name for name in test_names if any(keyword in name.lower() 
                                  for keyword in ['hemoglobin', 'hematócrit', 'eritrócit', 'leucócit'])]
                    st.session_state['selected_tests'] = common_tests
                    st.rerun()
            
            # Seleção múltipla de exames
            selected_tests = st.multiselect(
                "Exames:",
                options=test_names,
                default=st.session_state.get('selected_tests', []),
                key='test_multiselect',
                help="Selecione um ou mais exames para comparar"
            )
            
            # Atualizar estado da sessão
            st.session_state['selected_tests'] = selected_tests
        
        with col2:
            st.markdown("**Selecione o período:**")
            
            # Opções de seleção de datas
            date_option = st.radio(
                "Opções de data:",
                ["Todas as datas", "Período específico", "Datas individuais"],
                key="date_option"
            )
            
            if date_option == "Todas as datas":
                selected_dates = test_dates
            
            elif date_option == "Período específico":
                if test_dates:
                    # Converter datas string para objetos date para input de data
                    date_objects = [datetime.strptime(d, '%Y-%m-%d').date() for d in test_dates]
                    min_date = min(date_objects)
                    max_date = max(date_objects)
                    
                    date_range = st.date_input(
                        "Selecione o período:",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date,
                        key="date_range_input"
                    )
                    
                    if len(date_range) == 2:
                        start_date, end_date = date_range
                        selected_dates = [d for d in test_dates 
                                        if start_date <= datetime.strptime(d, '%Y-%m-%d').date() <= end_date]
                    else:
                        selected_dates = test_dates
                else:
                    selected_dates = []
            
            else:  # Datas individuais
                selected_dates = st.multiselect(
                    "Selecione datas específicas:",
                    options=test_dates,
                    default=test_dates[:5] if len(test_dates) > 5 else test_dates,
                    format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m/%Y'),
                    key="individual_dates"
                )
            
            # Exibir resumo da seleção
            if selected_tests and selected_dates:
                st.success(f"✅ {len(selected_tests)} exame(s) selecionado(s)")
                st.success(f"✅ {len(selected_dates)} data(s) selecionada(s)")
        
        return selected_tests, selected_dates
    
    def _get_filtered_results(self, selected_tests: List[str], selected_dates: List[str]) -> pd.DataFrame:
        """Obter resultados laboratoriais filtrados por exames e datas selecionados"""
        
        # Obter todos os resultados laboratoriais
        all_results = self.db.get_lab_results()
        
        if all_results.empty:
            return pd.DataFrame()
        
        # Filtrar por exames selecionados
        filtered_results = all_results[all_results['test_name'].isin(selected_tests)]
        
        # Filtrar por datas selecionadas
        if selected_dates:
            # Converter test_date para string para comparação
            filtered_results = filtered_results[
                filtered_results['test_date'].astype(str).isin(selected_dates)
            ]
        
        return filtered_results.sort_values(['test_date', 'test_name'])
    
    def _render_comparison_chart(self, lab_results: pd.DataFrame, selected_tests: List[str], selected_dates: List[str]):
        """Renderizar o gráfico de comparação"""
        
        st.subheader("📊 Gráfico Comparativo")
        
        # Opções de configuração do gráfico
        col1, col2, col3 = st.columns(3)
        
        with col1:
            chart_type = st.selectbox(
                "Tipo de gráfico:",
                ["Linha", "Dispersão", "Barras"],
                key="chart_type"
            )
        
        with col2:
            show_markers = st.checkbox("Mostrar marcadores", value=True)
            show_trend = st.checkbox("Mostrar linha de tendência", value=False)
        
        with col3:
            normalize_values = st.checkbox("Normalizar valores", value=False, 
                                         help="Normaliza valores para comparar exames com escalas diferentes")
        
        # Criar o gráfico
        fig = self._create_comparison_chart(
            lab_results, 
            selected_tests, 
            chart_type, 
            show_markers, 
            show_trend,
            normalize_values
        )
        
        # Exibir gráfico
        st.plotly_chart(fig, use_container_width=True)
        
        # Opções de exportação do gráfico
        self._render_chart_export_options(fig, selected_tests, chart_type, show_markers, show_trend, normalize_values)
    
    def _create_comparison_chart(self, lab_results: pd.DataFrame, selected_tests: List[str], 
                               chart_type: str, show_markers: bool, show_trend: bool,
                               normalize_values: bool) -> go.Figure:
        """Criar o gráfico de comparação baseado nos parâmetros"""
        
        fig = go.Figure()
        
        if lab_results.empty:
            fig.add_annotation(
                text="Nenhum dado disponível para exibição",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            return fig
        
        # Paleta de cores
        colors = px.colors.qualitative.Set3
        
        # Processar cada exame
        for i, test_name in enumerate(selected_tests):
            test_data = lab_results[lab_results['test_name'] == test_name].copy()
            if not test_data.empty:
                test_data = test_data.sort_values(by='test_date')
            
            if test_data.empty:
                continue
            
            # Obter valores e datas
            x_values = pd.to_datetime(test_data['test_date'])
            y_values = test_data['test_value'].astype(float)
            
            # Normalizar valores se solicitado
            if normalize_values and len(y_values) > 0:
                y_mean = y_values.mean()
                y_std = y_values.std()
                if y_std > 0:
                    y_values = (y_values - y_mean) / y_std
            
            # Obter unidades para texto de hover
            units = ''
            if len(test_data) > 0 and 'unit' in test_data.columns:
                try:
                    unit_col = test_data['unit']
                    valid_units = unit_col.dropna()
                    if len(valid_units) > 0:
                        units = str(valid_units.iloc[0])
                except (AttributeError, IndexError):
                    units = ''
            
            # Criar rastro baseado no tipo de gráfico
            if chart_type == "Linha":
                mode = 'lines+markers' if show_markers else 'lines'
                fig.add_trace(go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode=mode,
                    name=test_name,
                    line=dict(color=colors[i % len(colors)], width=3),
                    marker=dict(size=8),
                    hovertemplate=f"<b>{test_name}</b><br>" +
                                 "Data: %{x}<br>" +
                                 f"Valor: %{{y}}{' ' + units if units else ''}<br>" +
                                 "<extra></extra>"
                ))
            
            elif chart_type == "Dispersão":
                fig.add_trace(go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode='markers',
                    name=test_name,
                    marker=dict(size=10, color=colors[i % len(colors)]),
                    hovertemplate=f"<b>{test_name}</b><br>" +
                                 "Data: %{x}<br>" +
                                 f"Valor: %{{y}}{' ' + units if units else ''}<br>" +
                                 "<extra></extra>"
                ))
            
            elif chart_type == "Barras":
                fig.add_trace(go.Bar(
                    x=x_values,
                    y=y_values,
                    name=test_name,
                    marker_color=colors[i % len(colors)],
                    hovertemplate=f"<b>{test_name}</b><br>" +
                                 "Data: %{x}<br>" +
                                 f"Valor: %{{y}}{' ' + units if units else ''}<br>" +
                                 "<extra></extra>"
                ))
            
            # Adicionar linha de tendência se solicitado
            if show_trend and chart_type in ["Linha", "Dispersão"] and len(y_values) > 1:
                # Tendência linear simples
                import numpy as np
                x_numeric = np.arange(len(x_values))
                z = np.polyfit(x_numeric, y_values, 1)
                trend_line = np.poly1d(z)(x_numeric)
                
                fig.add_trace(go.Scatter(
                    x=x_values,
                    y=trend_line,
                    mode='lines',
                    name=f"{test_name} (tendência)",
                    line=dict(color=colors[i % len(colors)], width=2, dash='dash'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
        
        # Atualizar layout
        title = "Comparativo de Exames Laboratoriais"
        if normalize_values:
            title += " (Valores Normalizados)"
        
        fig.update_layout(
            title=title,
            xaxis_title="Data do Exame",
            yaxis_title="Valor" + (" (Normalizado)" if normalize_values else ""),
            hovermode='x unified',
            height=500,
            template="plotly_white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    def _render_chart_export_options(self, fig: go.Figure, selected_tests=None, chart_type=None, 
                                    show_markers=None, show_trend=None, normalize_values=None):
        """Renderizar opções de exportação do gráfico"""
        
        st.markdown("---")
        st.markdown("**🔗 Compartilhar e Exportar:**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Link compartilhável
            if st.button("🔗 Criar Link"):
                self._create_shareable_link(selected_tests, chart_type, show_markers, show_trend, normalize_values)
        
        with col2:
            # Exportar como PNG
            if st.button("🖼️ Baixar PNG"):
                img_bytes = fig.to_image(format="png", width=1200, height=600)
                st.download_button(
                    label="Download PNG",
                    data=img_bytes,
                    file_name=f"comparativo_exames_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                    mime="image/png"
                )
        
        with col3:
            # Exportar como HTML
            if st.button("🌐 Baixar HTML"):
                html_str = fig.to_html(include_plotlyjs='cdn')
                st.download_button(
                    label="Download HTML",
                    data=html_str,
                    file_name=f"comparativo_exames_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                    mime="text/html"
                )
        
        with col4:
            # Copiar gráfico
            if st.button("📋 Copiar"):
                self._show_copy_modal(fig)
    
    def _show_copy_modal(self, fig: go.Figure):
        """Mostrar modal para copiar gráfico"""
        
        # Usar expander como interface modal
        with st.expander("📋 Copiar Gráfico", expanded=True):
            st.write("**Opções de cópia:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📋 Copiar como Imagem"):
                    # Gerar imagem base64 para cópia
                    img_bytes = fig.to_image(format="png", width=1200, height=600)
                    img_b64 = base64.b64encode(img_bytes).decode()
                    
                    # JavaScript para copiar para área de transferência
                    copy_js = f"""
                    <script>
                    async function copyImageToClipboard() {{
                        try {{
                            const response = await fetch('data:image/png;base64,{img_b64}');
                            const blob = await response.blob();
                            await navigator.clipboard.write([
                                new ClipboardItem({{ 'image/png': blob }})
                            ]);
                            alert('Gráfico copiado para a área de transferência!');
                        }} catch (err) {{
                            console.error('Erro ao copiar:', err);
                            alert('Erro ao copiar. Use o botão de download.');
                        }}
                    }}
                    copyImageToClipboard();
                    </script>
                    """
                    st.html(copy_js)
                    st.success("Tentando copiar para área de transferência...")
            
            with col2:
                if st.button("🔗 Copiar Link Compartilhável"):
                    st.info("🔗 Use o botão 'Criar Link' na seção de exportação para gerar links compartilháveis")
    
    def _create_shareable_link(self, selected_tests, chart_type, show_markers, show_trend, normalize_values):
        """Criar link compartilhável para o gráfico comparativo"""
        
        try:
            from shareable_links import ShareableLinkManager
            
            # Configuração do gráfico
            chart_config = {
                'selected_tests': selected_tests or [],
                'chart_settings': {
                    'chart_type': chart_type,
                    'show_markers': show_markers,
                    'show_trend': show_trend,
                    'normalize_values': normalize_values
                },
                'date_range': {
                    'start': None,  # Pode ser expandido para incluir filtros de data
                    'end': None
                }
            }
            
            # Criar o link
            link_manager = ShareableLinkManager(self.db)
            link_info = link_manager.generate_comparison_link(
                selected_tests=selected_tests or [],
                date_range={'start': None, 'end': None},
                chart_settings=chart_config['chart_settings']
            )
            
            # Exibir o link
            with st.expander("🔗 Link Compartilhável Criado!", expanded=True):
                st.success("✅ Link criado com sucesso!")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.text_input(
                        "URL Compartilhável:",
                        value=link_info['url'],
                        disabled=True,
                        key=f"share_url_{link_info['share_id']}"
                    )
                
                with col2:
                    # Botão para copiar URL
                    if st.button("📋 Copiar", key=f"copy_url_{link_info['share_id']}"):
                        # JavaScript para copiar URL
                        copy_js = f"""
                        <script>
                        navigator.clipboard.writeText('{link_info["url"]}').then(function() {{
                            alert('URL copiada para área de transferência!');
                        }});
                        </script>
                        """
                        st.html(copy_js)
                        st.success("URL copiada!")
                
                st.info(f"⏰ **Expira em:** {link_info['expires_at']}")
                st.info(f"🆔 **ID do Link:** {link_info['share_id']}")
                
                # Gerar QR Code se possível
                try:
                    qr_data = link_manager.generate_qr_code(link_info['url'])
                    if qr_data != link_info['url']:  # Se conseguiu gerar QR code
                        st.markdown("**📱 QR Code:**")
                        st.markdown(f"![QR Code](data:image/png;base64,{qr_data})")
                    else:
                        st.markdown("**📱 Código QR:** Instale a biblioteca qrcode para gerar códigos QR")
                except Exception as e:
                    st.warning(f"Não foi possível gerar QR code: {e}")
        
        except Exception as e:
            st.error(f"Erro ao criar link compartilhável: {e}")
            st.info("💡 Verifique se o banco de dados está configurado corretamente.")
    
    def _render_comparison_table(self, lab_results: pd.DataFrame):
        """Renderizar tabela de dados de comparação"""
        
        st.subheader("📋 Dados da Comparação")
        
        if lab_results.empty:
            st.info("Nenhum dado para exibir na tabela.")
            return
        
        # Formatar dados para exibição
        display_df = lab_results.copy()
        
        # Formatar datas
        display_df['test_date'] = display_df['test_date'].apply(
            lambda x: datetime.strptime(str(x), '%Y-%m-%d').strftime('%d/%m/%Y') 
            if isinstance(x, str) else x.strftime('%d/%m/%Y')
        )
        
        # Formatar valores com unidades
        display_df['formatted_value'] = display_df.apply(
            lambda row: format_lab_value(row['test_value'], row.get('unit', '')), 
            axis=1
        )
        
        # Selecionar colunas para exibição
        display_columns = ['test_date', 'test_name', 'formatted_value', 'lab_name', 'reference_range']
        # Selecionar e renomear colunas
        display_df = display_df[display_columns].copy()
        column_mapping = {
            'test_date': 'Data',
            'test_name': 'Exame',
            'formatted_value': 'Valor',
            'lab_name': 'Laboratório',
            'reference_range': 'Referência'
        }
        display_df.columns = [column_mapping.get(col, col) for col in display_df.columns]
        
        # Exibir tabela com classificação e filtragem
        st.dataframe(
            display_df,
            use_container_width=True,
            height=min(400, len(display_df) * 35 + 100)
        )
        
        # Estatísticas da tabela
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Registros", len(display_df))
        
        with col2:
            try:
                if 'Exame' in display_df.columns and not display_df.empty:
                    unique_tests = display_df['Exame'].nunique()
                    st.metric("Exames Únicos", int(unique_tests))
                else:
                    st.metric("Exames Únicos", 0)
            except (AttributeError, TypeError):
                st.metric("Exames Únicos", 0)
        
        with col3:
            try:
                if 'Data' in display_df.columns and not display_df.empty:
                    unique_dates = display_df['Data'].nunique()
                    st.metric("Datas Únicas", int(unique_dates))
                else:
                    st.metric("Datas Únicas", 0)
            except (AttributeError, TypeError):
                st.metric("Datas Únicas", 0)
        
        with col4:
            if 'Laboratório' in display_df.columns:
                try:
                    if 'Laboratório' in display_df.columns and not display_df.empty:
                        unique_labs = display_df['Laboratório'].nunique()
                        st.metric("Laboratórios", int(unique_labs))
                    else:
                        st.metric("Laboratórios", 0)
                except (AttributeError, TypeError):
                    st.metric("Laboratórios", 0)
    
    def _render_export_options(self, lab_results: pd.DataFrame, selected_tests: List[str], selected_dates: List[str]):
        """Renderizar opções de exportação para dados de comparação"""
        
        st.subheader("📥 Exportar Dados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Exportar dados filtrados como CSV
            if st.button("📊 Exportar Dados (CSV)"):
                csv_data = lab_results.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"comparativo_dados_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            # Exportar tabela dinâmica
            if st.button("📋 Exportar Tabela Pivô"):
                pivot_data = self._create_pivot_export(lab_results)
                if pivot_data:
                    st.download_button(
                        label="Download Pivô CSV",
                        data=pivot_data,
                        file_name=f"comparativo_pivo_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv"
                    )
        
        with col3:
            # Exportar relatório de comparação
            if st.button("📄 Relatório de Comparação"):
                report = self._generate_comparison_report(lab_results, selected_tests, selected_dates)
                st.download_button(
                    label="Download Relatório",
                    data=report,
                    file_name=f"relatorio_comparativo_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
    
    def _create_pivot_export(self, lab_results: pd.DataFrame) -> Optional[str]:
        """Criar tabela dinâmica para exportação"""
        
        if lab_results.empty:
            return None
        
        try:
            # Criar tabela dinâmica
            pivot_df = lab_results.pivot_table(
                index='test_name',
                columns='test_date',
                values='test_value',
                aggfunc='first'
            )
            
            return pivot_df.to_csv()
            
        except Exception as e:
            st.error(f"Erro ao criar tabela pivô: {e}")
            return None
    
    def _generate_comparison_report(self, lab_results: pd.DataFrame, selected_tests: List[str], selected_dates: List[str]) -> str:
        """Gerar relatório de comparação"""
        
        report_lines = []
        report_lines.append("RELATÓRIO DE COMPARAÇÃO - EXAMES LABORATORIAIS")
        report_lines.append("=" * 60)
        report_lines.append(f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        report_lines.append(f"Paciente: Luna Princess Mendes Guimarães")
        report_lines.append("")
        
        # Resumo da seleção
        report_lines.append("CRITÉRIOS DE SELEÇÃO:")
        report_lines.append(f"Exames selecionados: {len(selected_tests)}")
        for test in selected_tests:
            report_lines.append(f"  • {test}")
        report_lines.append(f"Período: {len(selected_dates)} datas selecionadas")
        if selected_dates:
            first_date = min(selected_dates)
            last_date = max(selected_dates)
            report_lines.append(f"  De: {datetime.strptime(first_date, '%Y-%m-%d').strftime('%d/%m/%Y')}")
            report_lines.append(f"  Até: {datetime.strptime(last_date, '%Y-%m-%d').strftime('%d/%m/%Y')}")
        report_lines.append("")
        
        # Data summary
        report_lines.append("RESUMO DOS DADOS:")
        report_lines.append(f"Total de registros encontrados: {len(lab_results)}")
        
        if not lab_results.empty:
            # Statistics by test
            for test_name in selected_tests:
                test_data = lab_results[lab_results['test_name'] == test_name]
                if not test_data.empty:
                    values = test_data['test_value'].astype(float)
                    unit = ''
                    if len(test_data) > 0 and 'unit' in test_data.columns:
                        try:
                            unit_series = test_data['unit']
                            valid_units = unit_series.dropna()
                            if len(valid_units) > 0:
                                unit = str(valid_units.iloc[0])
                        except (AttributeError, IndexError):
                            unit = ''
                    
                    report_lines.append(f"\n{test_name}:")
                    report_lines.append(f"  Registros: {len(values)}")
                    report_lines.append(f"  Valor mínimo: {values.min():.2f} {unit}")
                    report_lines.append(f"  Valor máximo: {values.max():.2f} {unit}")
                    report_lines.append(f"  Valor médio: {values.mean():.2f} {unit}")
                    
                    if len(values) > 1:
                        report_lines.append(f"  Desvio padrão: {values.std():.2f} {unit}")
                        
                        # Trend analysis
                        values_list = values.tolist()
                        first_value = float(values_list[0])
                        last_value = float(values_list[-1])
                        change = last_value - first_value
                        change_percent = (change / first_value * 100) if first_value != 0 else 0
                        
                        trend = "↗️ Aumento" if change > 0 else "↘️ Diminuição" if change < 0 else "➡️ Estável"
                        report_lines.append(f"  Tendência: {trend} ({change:+.2f} {unit}, {change_percent:+.1f}%)")
        
        # Recent values
        if not lab_results.empty:
            report_lines.append("\nÚLTIMOS VALORES REGISTRADOS:")
            recent_data = lab_results.nlargest(10, 'test_date')
            for _, row in recent_data.iterrows():
                date_str = datetime.strptime(str(row['test_date']), '%Y-%m-%d').strftime('%d/%m/%Y')
                unit_val = str(row.get('unit', '')) if row.get('unit') is not None else ''
                value_str = format_lab_value(row['test_value'], unit_val)
                report_lines.append(f"  {date_str} - {row['test_name']}: {value_str}")
        
        report_lines.append("\n" + "=" * 60)
        report_lines.append("Fim do relatório")
        
        return "\n".join(report_lines)
