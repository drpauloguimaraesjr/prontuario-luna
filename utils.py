import pandas as pd
import numpy as np
from datetime import datetime, date
import io
import base64
import streamlit as st
from typing import Any, Dict, List, Optional
import plotly.graph_objects as go
import plotly.express as px

def format_date(date_obj: Any) -> str:
    """Format date object to string"""
    if isinstance(date_obj, str):
        return date_obj
    elif isinstance(date_obj, (date, datetime)):
        return date_obj.strftime('%d/%m/%Y')
    return str(date_obj)

def parse_date(date_str: str) -> Optional[date]:
    """Parse date string to date object"""
    if not date_str:
        return None
    
    # Try different date formats
    formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None

def convert_units(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    """Convert between different units"""
    # Basic unit conversion mappings
    conversions = {
        ('ng/dl', 'mmol/l'): 0.01,
        ('mg/dl', 'mmol/l'): 0.055,
        ('g/dl', 'g/l'): 10,
        ('mcg/dl', 'nmol/l'): 26.12,
        ('iu/l', 'u/l'): 1.0,
        ('pg/ml', 'pmol/l'): 2.61,
    }
    
    key = (from_unit.lower().replace(' ', ''), to_unit.lower().replace(' ', ''))
    if key in conversions:
        return value * conversions[key]
    
    # If reverse conversion exists
    reverse_key = (key[1], key[0])
    if reverse_key in conversions:
        return value / conversions[reverse_key]
    
    return value  # Return original value if no conversion found

def export_dataframe_to_csv(df: pd.DataFrame) -> str:
    """Export DataFrame to CSV string"""
    if df.empty:
        return ""
    
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8')
    return output.getvalue()

def export_dataframe_to_excel(df: pd.DataFrame) -> bytes:
    """Export DataFrame to Excel bytes"""
    if df.empty:
        return b""
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return output.getvalue()

def create_lab_results_chart(df: pd.DataFrame, test_names: List[str], dates: List[str]) -> go.Figure:
    """Create interactive chart for lab results comparison"""
    fig = go.Figure()
    
    if df.empty or not test_names:
        fig.add_annotation(
            text="Nenhum dado disponível para exibição",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        return fig
    
    # Filter data
    filtered_df = df[df['test_name'].isin(test_names)]
    if dates and 'Todos' not in dates:
        filtered_df = filtered_df[filtered_df['test_date'].astype(str).isin(dates)]
    
    colors = px.colors.qualitative.Set3
    
    for i, test_name in enumerate(test_names):
        test_data = filtered_df[filtered_df['test_name'] == test_name].sort_values('test_date')
        
        if not test_data.empty:
            fig.add_trace(go.Scatter(
                x=test_data['test_date'],
                y=test_data['test_value'],
                mode='lines+markers',
                name=test_name,
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=8),
                hovertemplate=f"<b>{test_name}</b><br>" +
                             "Data: %{x}<br>" +
                             "Valor: %{y}<br>" +
                             "<extra></extra>"
            ))
    
    fig.update_layout(
        title="Comparativo de Exames Laboratoriais",
        xaxis_title="Data do Exame",
        yaxis_title="Valor",
        hovermode='x unified',
        showlegend=True,
        height=500,
        template="plotly_white"
    )
    
    return fig

def create_timeline_visualization(events: List[Dict[str, Any]]) -> go.Figure:
    """Create timeline visualization for medical events"""
    if not events:
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhum evento registrado",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        return fig
    
    # Sort events by date
    sorted_events = sorted(events, key=lambda x: x['event_date'])
    
    dates = [event['event_date'] for event in sorted_events]
    titles = [event['title'] for event in sorted_events]
    descriptions = [event.get('description', '') for event in sorted_events]
    
    fig = go.Figure()
    
    # Add timeline line
    fig.add_trace(go.Scatter(
        x=dates,
        y=[1] * len(dates),
        mode='lines+markers',
        line=dict(color='#FF69B4', width=4),
        marker=dict(size=12, color='white', line=dict(color='#FF69B4', width=3)),
        showlegend=False,
        hovertemplate="<b>%{text}</b><br>Data: %{x}<extra></extra>",
        text=titles
    ))
    
    # Add event markers with descriptions
    for i, (date, title, desc) in enumerate(zip(dates, titles, descriptions)):
        fig.add_annotation(
            x=date,
            y=1.2,
            text=f"<b>{title}</b>",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor='#FF69B4',
            bgcolor='white',
            bordercolor='#FF69B4',
            borderwidth=1,
            font=dict(size=10)
        )
    
    fig.update_layout(
        title="Linha do Tempo - História da Doença Atual",
        xaxis_title="Data",
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        height=300,
        template="plotly_white",
        showlegend=False
    )
    
    return fig

def validate_file_type(file, allowed_types: List[str]) -> bool:
    """Validate if uploaded file is of allowed type"""
    if not file:
        return False
    
    file_type = file.type if hasattr(file, 'type') else ''
    file_name = file.name if hasattr(file, 'name') else ''
    
    # Check by MIME type
    for allowed_type in allowed_types:
        if allowed_type in file_type:
            return True
    
    # Check by file extension
    if file_name:
        extension = file_name.lower().split('.')[-1]
        extension_map = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'mp4': 'video/mp4',
            'avi': 'video/avi'
        }
        
        if extension in extension_map:
            return extension_map[extension] in allowed_types
    
    return False

def format_medical_text(text: str) -> str:
    """Format text for medical display"""
    if not text:
        return ""
    
    # Basic formatting for medical text
    formatted = text.replace('\n\n', '\n')
    formatted = formatted.replace('\n', '\n\n')
    
    return formatted

def generate_patient_summary(patient_info: Dict[str, Any], lab_results: pd.DataFrame, 
                           timeline_events: List[Dict], medications: List[Dict]) -> str:
    """Generate a comprehensive patient summary"""
    summary_parts = []
    
    # Patient information
    if patient_info:
        summary_parts.append(f"**Paciente:** {patient_info.get('name', 'N/A')}")
        if patient_info.get('species'):
            summary_parts.append(f"**Espécie:** {patient_info['species']}")
        if patient_info.get('breed'):
            summary_parts.append(f"**Raça:** {patient_info['breed']}")
        if patient_info.get('birth_date'):
            summary_parts.append(f"**Data de Nascimento:** {format_date(patient_info['birth_date'])}")
    
    # Lab results summary
    if not lab_results.empty:
        total_tests = len(lab_results)
        unique_tests = lab_results['test_name'].nunique()
        date_range = f"{lab_results['test_date'].min()} a {lab_results['test_date'].max()}"
        
        summary_parts.append(f"\n**Exames Laboratoriais:**")
        summary_parts.append(f"- Total de exames: {total_tests}")
        summary_parts.append(f"- Tipos diferentes: {unique_tests}")
        summary_parts.append(f"- Período: {date_range}")
    
    # Timeline events summary
    if timeline_events:
        summary_parts.append(f"\n**Eventos Clínicos:** {len(timeline_events)} eventos registrados")
        
        # Most recent event
        latest_event = max(timeline_events, key=lambda x: x['event_date'])
        summary_parts.append(f"- Último evento: {latest_event['title']} ({format_date(latest_event['event_date'])})")
    
    # Medications summary
    if medications:
        active_meds = [med for med in medications if not med.get('end_date')]
        summary_parts.append(f"\n**Medicamentos:**")
        summary_parts.append(f"- Total prescrito: {len(medications)}")
        summary_parts.append(f"- Em uso atual: {len(active_meds)}")
    
    return '\n'.join(summary_parts)

def create_export_button(data: Any, filename: str, file_type: str = 'csv') -> bool:
    """Create export button with download functionality"""
    if file_type == 'csv' and isinstance(data, pd.DataFrame):
        csv_data = export_dataframe_to_csv(data)
        if csv_data:
            st.download_button(
                label=f"📥 Exportar {filename}.csv",
                data=csv_data,
                file_name=f"{filename}.csv",
                mime="text/csv"
            )
            return True
    
    elif file_type == 'excel' and isinstance(data, pd.DataFrame):
        excel_data = export_dataframe_to_excel(data)
        if excel_data:
            st.download_button(
                label=f"📥 Exportar {filename}.xlsx",
                data=excel_data,
                file_name=f"{filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            return True
    
    return False

def safe_convert_to_numeric(value: Any) -> Optional[float]:
    """Safely convert value to numeric"""
    if value is None or value == '':
        return None
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def format_lab_value(value: Any, unit: str = '') -> str:
    """Format lab value for display"""
    if value is None:
        return "N/A"
    
    try:
        numeric_value = float(value)
        formatted = f"{numeric_value:.2f}".rstrip('0').rstrip('.')
        if unit:
            return f"{formatted} {unit}"
        return formatted
    except (ValueError, TypeError):
        return str(value)
