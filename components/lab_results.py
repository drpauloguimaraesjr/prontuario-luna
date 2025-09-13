import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from utils import format_date, format_lab_value, create_export_button

class LabResultsComponent:
    """Component for displaying lab results in table format"""
    
    def __init__(self, db):
        self.db = db
    
    def render(self):
        """Render the lab results table"""
        
        # Get lab results data
        lab_results = self.db.get_lab_results()
        
        if lab_results.empty:
            st.info("Nenhum exame laboratorial registrado ainda.")
            return
        
        # Create pivot table (tests as rows, dates as columns)
        pivot_df = self._create_pivot_table(lab_results)
        
        if not pivot_df.empty:
            st.subheader("Tabela de Resultados Laboratoriais")
            
            # Display controls
            self._render_table_controls(lab_results)
            
            # Display the main table
            self._render_main_table(pivot_df, lab_results)
            
            # Export options
            self._render_export_options(lab_results, pivot_df)
    
    def _create_pivot_table(self, df):
        """Create pivot table with tests as rows and dates as columns"""
        try:
            # Ensure test_date is datetime
            df['test_date'] = pd.to_datetime(df['test_date'])
            
            # Create pivot table
            pivot_df = df.pivot_table(
                index='test_name',
                columns='test_date',
                values='test_value',
                aggfunc='first'
            )
            
            # Sort columns (dates) in descending order
            pivot_df = pivot_df.reindex(sorted(pivot_df.columns, reverse=True), axis=1)
            
            return pivot_df
            
        except Exception as e:
            st.error(f"Erro ao criar tabela: {e}")
            return pd.DataFrame()
    
    def _render_table_controls(self, lab_results):
        """Render table controls (filters, search, etc.)"""
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Test name filter
            available_tests = sorted(lab_results['test_name'].unique())
            selected_tests = st.multiselect(
                "Filtrar exames:",
                available_tests,
                default=available_tests,
                key="test_filter"
            )
        
        with col2:
            # Date range filter
            min_date = lab_results['test_date'].min()
            max_date = lab_results['test_date'].max()
            
            date_range = st.date_input(
                "Período:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="date_range"
            )
        
        with col3:
            # Display options
            show_units = st.checkbox("Mostrar unidades", value=True)
            show_reference = st.checkbox("Mostrar valores de referência", value=False)
        
        # Store filters in session state
        st.session_state['lab_filters'] = {
            'selected_tests': selected_tests,
            'date_range': date_range,
            'show_units': show_units,
            'show_reference': show_reference
        }
    
    def _render_main_table(self, pivot_df, lab_results):
        """Render the main lab results table"""
        
        filters = st.session_state.get('lab_filters', {})
        
        # Apply filters
        filtered_df = pivot_df.copy()
        
        if filters.get('selected_tests'):
            filtered_df = filtered_df[filtered_df.index.isin(filters['selected_tests'])]
        
        if filters.get('date_range') and len(filters['date_range']) == 2:
            start_date, end_date = filters['date_range']
            # Filter columns by date range
            date_mask = (pivot_df.columns >= pd.Timestamp(start_date)) & (pivot_df.columns <= pd.Timestamp(end_date))
            filtered_df = filtered_df.loc[:, date_mask]
        
        if filtered_df.empty:
            st.warning("Nenhum resultado encontrado com os filtros aplicados.")
            return
        
        # Format the table for display
        display_df = self._format_table_for_display(filtered_df, lab_results, filters)
        
        # Display with custom styling
        st.dataframe(
            display_df,
            use_container_width=True,
            height=min(600, len(display_df) * 35 + 100)
        )
        
        # Display table statistics
        self._render_table_stats(filtered_df, lab_results)
    
    def _format_table_for_display(self, pivot_df, lab_results, filters):
        """Format the pivot table for better display"""
        
        display_df = pivot_df.copy()
        
        # Format column headers (dates)
        display_df.columns = [col.strftime('%d/%m/%Y') for col in display_df.columns]
        
        # Format values with units if requested
        if filters.get('show_units', True):
            for test_name in display_df.index:
                # Get unit for this test
                test_unit = lab_results[lab_results['test_name'] == test_name]['unit'].iloc[0] if not lab_results[lab_results['test_name'] == test_name].empty else ''
                
                # Format values with units
                for col in display_df.columns:
                    value = display_df.loc[test_name, col]
                    if pd.notna(value):
                        display_df.loc[test_name, col] = format_lab_value(value, test_unit)
                    else:
                        display_df.loc[test_name, col] = "-"
        else:
            # Format values without units
            for col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: format_lab_value(x) if pd.notna(x) else "-")
        
        return display_df
    
    def _render_table_stats(self, filtered_df, lab_results):
        """Render table statistics"""
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Tipos de Exames", len(filtered_df.index))
        
        with col2:
            st.metric("Datas Disponíveis", len(filtered_df.columns))
        
        with col3:
            total_values = filtered_df.notna().sum().sum()
            st.metric("Total de Valores", int(total_values))
        
        with col4:
            # Calculate completeness percentage
            total_possible = len(filtered_df.index) * len(filtered_df.columns)
            completeness = (total_values / total_possible * 100) if total_possible > 0 else 0
            st.metric("Completude", f"{completeness:.1f}%")
    
    def _render_export_options(self, lab_results, pivot_df):
        """Render export options"""
        
        st.subheader("Opções de Exportação")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export raw data
            if st.button("📥 Exportar Dados Brutos (CSV)"):
                csv_data = lab_results.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"exames_dados_brutos_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            # Export pivot table
            if st.button("📊 Exportar Tabela Pivô (CSV)"):
                csv_data = pivot_df.to_csv()
                st.download_button(
                    label="Download Tabela Pivô",
                    data=csv_data,
                    file_name=f"exames_tabela_pivo_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
        
        with col3:
            # Export summary report
            if st.button("📄 Gerar Relatório Resumo"):
                report = self._generate_summary_report(lab_results)
                st.download_button(
                    label="Download Relatório",
                    data=report,
                    file_name=f"relatorio_exames_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
    
    def _generate_summary_report(self, lab_results):
        """Generate a summary report of lab results"""
        
        report_lines = []
        report_lines.append("RELATÓRIO RESUMO - EXAMES LABORATORIAIS")
        report_lines.append("=" * 50)
        report_lines.append(f"Data de geração: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")
        report_lines.append(f"Paciente: Luna Princess Mendes Guimarães")
        report_lines.append("")
        
        # General statistics
        report_lines.append("ESTATÍSTICAS GERAIS:")
        report_lines.append(f"Total de exames registrados: {len(lab_results)}")
        report_lines.append(f"Tipos diferentes de exames: {lab_results['test_name'].nunique()}")
        report_lines.append(f"Período: {lab_results['test_date'].min().strftime('%d/%m/%Y')} a {lab_results['test_date'].max().strftime('%d/%m/%Y')}")
        report_lines.append(f"Laboratórios envolvidos: {lab_results['lab_name'].nunique()}")
        report_lines.append("")
        
        # Test frequency
        report_lines.append("FREQUÊNCIA DOS EXAMES:")
        test_counts = lab_results['test_name'].value_counts()
        for test_name, count in test_counts.head(10).items():
            report_lines.append(f"• {test_name}: {count} registros")
        report_lines.append("")
        
        # Recent results
        report_lines.append("ÚLTIMOS RESULTADOS (5 mais recentes):")
        recent_results = lab_results.nlargest(5, 'test_date')
        for _, result in recent_results.iterrows():
            report_lines.append(f"• {result['test_date'].strftime('%d/%m/%Y')} - {result['test_name']}: {format_lab_value(result['test_value'], result.get('unit', ''))}")
        report_lines.append("")
        
        # Labs summary
        if lab_results['lab_name'].notna().any():
            report_lines.append("LABORATÓRIOS:")
            lab_counts = lab_results['lab_name'].value_counts()
            for lab_name, count in lab_counts.items():
                if pd.notna(lab_name):
                    report_lines.append(f"• {lab_name}: {count} exames")
        
        return "\n".join(report_lines)
    
    def export_to_csv(self):
        """Export lab results to CSV"""
        lab_results = self.db.get_lab_results()
        if not lab_results.empty:
            return lab_results.to_csv(index=False)
        return None
