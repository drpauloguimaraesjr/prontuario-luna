import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
import io
import base64
from typing import List, Dict, Any, Optional
from utils import format_date, format_lab_value, create_lab_results_chart

class ComparisonComponent:
    """Component for comparing lab results with interactive charts and exports"""
    
    def __init__(self, db):
        self.db = db
    
    def render(self):
        """Render the comparison interface"""
        
        # Get available data
        test_names = self.db.get_test_names()
        test_dates = self.db.get_test_dates()
        
        if not test_names:
            st.info("Nenhum exame disponível para comparação. Adicione alguns exames primeiro.")
            return
        
        # Render selection controls
        selected_tests, selected_dates = self._render_selection_controls(test_names, test_dates)
        
        if selected_tests:
            # Get filtered data
            lab_results = self._get_filtered_results(selected_tests, selected_dates)
            
            if not lab_results.empty:
                # Render chart
                self._render_comparison_chart(lab_results, selected_tests, selected_dates)
                
                # Render data table
                self._render_comparison_table(lab_results)
                
                # Render export options
                self._render_export_options(lab_results, selected_tests, selected_dates)
            else:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
        else:
            st.info("Selecione pelo menos um exame para visualizar a comparação.")
    
    def _render_selection_controls(self, test_names: List[str], test_dates: List[str]) -> tuple:
        """Render controls for selecting tests and dates"""
        
        st.subheader("Seleção de Exames e Datas")
        
        # Test selection
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Selecione os exames para comparar:**")
            
            # Quick selection buttons
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
                # Common test groups
                if st.button("Hemograma Básico"):
                    common_tests = [name for name in test_names if any(keyword in name.lower() 
                                  for keyword in ['hemoglobin', 'hematócrit', 'eritrócit', 'leucócit'])]
                    st.session_state['selected_tests'] = common_tests
                    st.rerun()
            
            # Multi-select for tests
            selected_tests = st.multiselect(
                "Exames:",
                options=test_names,
                default=st.session_state.get('selected_tests', []),
                key='test_multiselect',
                help="Selecione um ou mais exames para comparar"
            )
            
            # Update session state
            st.session_state['selected_tests'] = selected_tests
        
        with col2:
            st.markdown("**Selecione o período:**")
            
            # Date selection options
            date_option = st.radio(
                "Opções de data:",
                ["Todas as datas", "Período específico", "Datas individuais"],
                key="date_option"
            )
            
            if date_option == "Todas as datas":
                selected_dates = test_dates
            
            elif date_option == "Período específico":
                if test_dates:
                    # Convert string dates to date objects for date input
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
            
            else:  # Individual dates
                selected_dates = st.multiselect(
                    "Selecione datas específicas:",
                    options=test_dates,
                    default=test_dates[:5] if len(test_dates) > 5 else test_dates,
                    format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m/%Y'),
                    key="individual_dates"
                )
            
            # Display selection summary
            if selected_tests and selected_dates:
                st.success(f"✅ {len(selected_tests)} exame(s) selecionado(s)")
                st.success(f"✅ {len(selected_dates)} data(s) selecionada(s)")
        
        return selected_tests, selected_dates
    
    def _get_filtered_results(self, selected_tests: List[str], selected_dates: List[str]) -> pd.DataFrame:
        """Get lab results filtered by selected tests and dates"""
        
        # Get all lab results
        all_results = self.db.get_lab_results()
        
        if all_results.empty:
            return pd.DataFrame()
        
        # Filter by selected tests
        filtered_results = all_results[all_results['test_name'].isin(selected_tests)]
        
        # Filter by selected dates
        if selected_dates:
            # Convert test_date to string for comparison
            filtered_results = filtered_results[
                filtered_results['test_date'].astype(str).isin(selected_dates)
            ]
        
        return filtered_results.sort_values(['test_date', 'test_name'])
    
    def _render_comparison_chart(self, lab_results: pd.DataFrame, selected_tests: List[str], selected_dates: List[str]):
        """Render the comparison chart"""
        
        st.subheader("📊 Gráfico Comparativo")
        
        # Chart configuration options
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
        
        # Create the chart
        fig = self._create_comparison_chart(
            lab_results, 
            selected_tests, 
            chart_type, 
            show_markers, 
            show_trend,
            normalize_values
        )
        
        # Display chart
        st.plotly_chart(fig, use_container_width=True)
        
        # Chart export options
        self._render_chart_export_options(fig)
    
    def _create_comparison_chart(self, lab_results: pd.DataFrame, selected_tests: List[str], 
                               chart_type: str, show_markers: bool, show_trend: bool,
                               normalize_values: bool) -> go.Figure:
        """Create the comparison chart based on parameters"""
        
        fig = go.Figure()
        
        if lab_results.empty:
            fig.add_annotation(
                text="Nenhum dado disponível para exibição",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            return fig
        
        # Color palette
        colors = px.colors.qualitative.Set3
        
        # Process each test
        for i, test_name in enumerate(selected_tests):
            test_data = lab_results[lab_results['test_name'] == test_name].sort_values('test_date')
            
            if test_data.empty:
                continue
            
            # Get values and dates
            x_values = pd.to_datetime(test_data['test_date'])
            y_values = test_data['test_value'].astype(float)
            
            # Normalize values if requested
            if normalize_values and len(y_values) > 0:
                y_mean = y_values.mean()
                y_std = y_values.std()
                if y_std > 0:
                    y_values = (y_values - y_mean) / y_std
            
            # Get units for hover text
            units = test_data['unit'].iloc[0] if not test_data['unit'].isna().all() else ''
            
            # Create trace based on chart type
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
            
            # Add trend line if requested
            if show_trend and chart_type in ["Linha", "Dispersão"] and len(y_values) > 1:
                # Simple linear trend
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
        
        # Update layout
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
    
    def _render_chart_export_options(self, fig: go.Figure):
        """Render chart export options"""
        
        st.markdown("**Exportar Gráfico:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📋 Copiar Gráfico"):
                # This will show a modal with copy options
                self._show_copy_modal(fig)
        
        with col2:
            # Export as PNG
            if st.button("🖼️ Baixar PNG"):
                img_bytes = fig.to_image(format="png", width=1200, height=600)
                st.download_button(
                    label="Download PNG",
                    data=img_bytes,
                    file_name=f"comparativo_exames_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                    mime="image/png"
                )
        
        with col3:
            # Export as HTML
            if st.button("🌐 Baixar HTML"):
                html_str = fig.to_html(include_plotlyjs='cdn')
                st.download_button(
                    label="Download HTML",
                    data=html_str,
                    file_name=f"comparativo_exames_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                    mime="text/html"
                )
    
    def _show_copy_modal(self, fig: go.Figure):
        """Show modal for copying graph"""
        
        # Use expander as modal-like interface
        with st.expander("📋 Copiar Gráfico", expanded=True):
            st.write("**Opções de cópia:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📋 Copiar como Imagem"):
                    # Generate base64 image for copying
                    img_bytes = fig.to_image(format="png", width=1200, height=600)
                    img_b64 = base64.b64encode(img_bytes).decode()
                    
                    # JavaScript to copy to clipboard
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
                    st.components.v1.html(copy_js, height=0)
                    st.success("Tentando copiar para área de transferência...")
            
            with col2:
                if st.button("🔗 Copiar Link Compartilhável"):
                    # In a real implementation, you'd generate a shareable link
                    share_url = f"https://seu-dominio.com/share/chart/{datetime.now().strftime('%Y%m%d_%H%M')}"
                    st.code(share_url)
                    st.info("Link gerado para compartilhamento (funcionalidade simulada)")
            
            if st.button("❌ Fechar"):
                st.rerun()
    
    def _render_comparison_table(self, lab_results: pd.DataFrame):
        """Render comparison data table"""
        
        st.subheader("📋 Dados da Comparação")
        
        if lab_results.empty:
            st.info("Nenhum dado para exibir na tabela.")
            return
        
        # Format data for display
        display_df = lab_results.copy()
        
        # Format dates
        display_df['test_date'] = display_df['test_date'].apply(
            lambda x: datetime.strptime(str(x), '%Y-%m-%d').strftime('%d/%m/%Y') 
            if isinstance(x, str) else x.strftime('%d/%m/%Y')
        )
        
        # Format values with units
        display_df['formatted_value'] = display_df.apply(
            lambda row: format_lab_value(row['test_value'], row.get('unit', '')), 
            axis=1
        )
        
        # Select columns for display
        display_columns = ['test_date', 'test_name', 'formatted_value', 'lab_name', 'reference_range']
        display_df = display_df[display_columns].rename(columns={
            'test_date': 'Data',
            'test_name': 'Exame',
            'formatted_value': 'Valor',
            'lab_name': 'Laboratório',
            'reference_range': 'Referência'
        })
        
        # Display table with sorting and filtering
        st.dataframe(
            display_df,
            use_container_width=True,
            height=min(400, len(display_df) * 35 + 100)
        )
        
        # Table statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Registros", len(display_df))
        
        with col2:
            unique_tests = display_df['Exame'].nunique()
            st.metric("Exames Únicos", unique_tests)
        
        with col3:
            unique_dates = display_df['Data'].nunique()
            st.metric("Datas Únicas", unique_dates)
        
        with col4:
            if 'Laboratório' in display_df.columns:
                unique_labs = display_df['Laboratório'].nunique()
                st.metric("Laboratórios", unique_labs)
    
    def _render_export_options(self, lab_results: pd.DataFrame, selected_tests: List[str], selected_dates: List[str]):
        """Render export options for comparison data"""
        
        st.subheader("📥 Exportar Dados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export filtered data as CSV
            if st.button("📊 Exportar Dados (CSV)"):
                csv_data = lab_results.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"comparativo_dados_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            # Export pivot table
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
            # Export comparison report
            if st.button("📄 Relatório de Comparação"):
                report = self._generate_comparison_report(lab_results, selected_tests, selected_dates)
                st.download_button(
                    label="Download Relatório",
                    data=report,
                    file_name=f"relatorio_comparativo_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
    
    def _create_pivot_export(self, lab_results: pd.DataFrame) -> Optional[str]:
        """Create pivot table for export"""
        
        if lab_results.empty:
            return None
        
        try:
            # Create pivot table
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
        """Generate comparison report"""
        
        report_lines = []
        report_lines.append("RELATÓRIO DE COMPARAÇÃO - EXAMES LABORATORIAIS")
        report_lines.append("=" * 60)
        report_lines.append(f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        report_lines.append(f"Paciente: Luna Princess Mendes Guimarães")
        report_lines.append("")
        
        # Selection summary
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
                    unit = test_data['unit'].iloc[0] if not test_data['unit'].isna().all() else ''
                    
                    report_lines.append(f"\n{test_name}:")
                    report_lines.append(f"  Registros: {len(values)}")
                    report_lines.append(f"  Valor mínimo: {values.min():.2f} {unit}")
                    report_lines.append(f"  Valor máximo: {values.max():.2f} {unit}")
                    report_lines.append(f"  Valor médio: {values.mean():.2f} {unit}")
                    
                    if len(values) > 1:
                        report_lines.append(f"  Desvio padrão: {values.std():.2f} {unit}")
                        
                        # Trend analysis
                        first_value = values.iloc[0]
                        last_value = values.iloc[-1]
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
                value_str = format_lab_value(row['test_value'], row.get('unit', ''))
                report_lines.append(f"  {date_str} - {row['test_name']}: {value_str}")
        
        report_lines.append("\n" + "=" * 60)
        report_lines.append("Fim do relatório")
        
        return "\n".join(report_lines)
