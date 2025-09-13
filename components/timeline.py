import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
from utils import format_date

class TimelineComponent:
    """Component for displaying medical timeline (História da Doença Atual)"""
    
    def __init__(self, db):
        self.db = db
        self.current_event_index = 0
    
    def render(self):
        """Render the timeline interface"""
        
        # Get timeline events
        events = self.db.get_medical_timeline()
        
        if not events:
            st.info("Nenhum evento clínico registrado ainda.")
            return
        
        # Sort events by date
        sorted_events = sorted(events, key=lambda x: x['event_date'])
        
        # Initialize session state for navigation
        if 'timeline_index' not in st.session_state:
            st.session_state.timeline_index = 0
        
        # Ensure index is within bounds
        if st.session_state.timeline_index >= len(sorted_events):
            st.session_state.timeline_index = 0
        
        # Render timeline visualization
        self._render_timeline_chart(sorted_events)
        
        # Render timeline navigation
        self._render_timeline_navigation(sorted_events)
        
        # Render current event details
        if sorted_events:
            current_event = sorted_events[st.session_state.timeline_index]
            self._render_event_details(current_event)
    
    def _render_timeline_chart(self, events):
        """Render the interactive timeline chart"""
        
        if not events:
            return
        
        # Create timeline visualization
        fig = go.Figure()
        
        dates = [event['event_date'] for event in events]
        titles = [event['title'] for event in events]
        
        # Add main timeline line
        fig.add_trace(go.Scatter(
            x=dates,
            y=[1] * len(dates),
            mode='lines',
            line=dict(color='#FF69B4', width=6),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Add event markers
        colors = ['white' if i != st.session_state.timeline_index else '#FF1493' 
                 for i in range(len(events))]
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=[1] * len(dates),
            mode='markers',
            marker=dict(
                size=15,
                color=colors,
                line=dict(color='#FF69B4', width=3)
            ),
            text=titles,
            hovertemplate="<b>%{text}</b><br>Data: %{x}<extra></extra>",
            showlegend=False
        ))
        
        # Highlight current event
        if 0 <= st.session_state.timeline_index < len(events):
            current_date = dates[st.session_state.timeline_index]
            current_title = titles[st.session_state.timeline_index]
            
            # Add vertical line for current event
            fig.add_vline(
                x=current_date,
                line=dict(color='white', width=3, dash='solid'),
                annotation_text=format_date(current_date),
                annotation_position="top"
            )
        
        # Update layout
        fig.update_layout(
            title="Linha do Tempo - História da Doença Atual",
            xaxis_title="Data",
            yaxis=dict(
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                range=[0.5, 1.5]
            ),
            height=200,
            template="plotly_white",
            showlegend=False,
            margin=dict(t=60, b=40, l=40, r=40)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_timeline_navigation(self, events):
        """Render timeline navigation controls"""
        
        if not events:
            return
        
        # Navigation buttons
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if st.button("⏪", disabled=(st.session_state.timeline_index == 0)):
                st.session_state.timeline_index = 0
                st.rerun()
        
        with col2:
            if st.button("◀️", disabled=(st.session_state.timeline_index == 0)):
                st.session_state.timeline_index -= 1
                st.rerun()
        
        with col3:
            # Event selector
            current_event = events[st.session_state.timeline_index]
            event_options = [f"{format_date(event['event_date'])} - {event['title']}" 
                           for event in events]
            
            selected_index = st.selectbox(
                "Evento atual:",
                range(len(events)),
                index=st.session_state.timeline_index,
                format_func=lambda x: event_options[x],
                key="event_selector"
            )
            
            if selected_index != st.session_state.timeline_index:
                st.session_state.timeline_index = selected_index
                st.rerun()
        
        with col4:
            if st.button("▶️", disabled=(st.session_state.timeline_index >= len(events) - 1)):
                st.session_state.timeline_index += 1
                st.rerun()
        
        with col5:
            if st.button("⏩", disabled=(st.session_state.timeline_index >= len(events) - 1)):
                st.session_state.timeline_index = len(events) - 1
                st.rerun()
        
        # Progress indicator
        progress = (st.session_state.timeline_index + 1) / len(events)
        st.progress(progress, text=f"Evento {st.session_state.timeline_index + 1} de {len(events)}")
    
    def _render_event_details(self, event):
        """Render details for the current event"""
        
        # Upper section: Event summary
        st.markdown("---")
        
        # Event header with date and title
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"### 📅 {format_date(event['event_date'])}")
            st.markdown(f"**{event['title']}**")
        
        with col2:
            # Quick stats or actions
            if event.get('symptoms'):
                st.metric("Sintomas Registrados", len(event['symptoms']))
        
        # Brief description/summary
        if event.get('description'):
            st.markdown("**Resumo do dia:**")
            st.info(event['description'])
        
        # Symptoms if available
        if event.get('symptoms'):
            st.markdown("**Sintomas identificados:**")
            cols = st.columns(min(3, len(event['symptoms'])))
            for i, symptom in enumerate(event['symptoms']):
                with cols[i % 3]:
                    st.markdown(f"• {symptom}")
        
        # Lower section: Detailed information
        st.markdown("---")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### 📝 Notas Clínicas")
            if event.get('clinical_notes'):
                # Display clinical notes in a formatted way
                st.markdown(f"""
                <div style="
                    background-color: #f8f9fa;
                    padding: 1rem;
                    border-radius: 5px;
                    border-left: 4px solid #FF69B4;
                    font-family: 'Georgia', serif;
                    line-height: 1.6;
                ">
                {event['clinical_notes'].replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma nota clínica registrada para este evento.")
        
        with col_right:
            st.markdown("#### 🔬 Exames Relacionados")
            self._render_related_exams(event['event_date'])
    
    def _render_related_exams(self, event_date):
        """Render lab results related to the current event date"""
        
        # Get lab results around the event date (±7 days)
        from datetime import timedelta
        
        start_date = event_date - timedelta(days=7)
        end_date = event_date + timedelta(days=7)
        
        # Get all lab results
        lab_results = self.db.get_lab_results()
        
        if not lab_results.empty:
            # Convert test_date to datetime for comparison
            lab_results['test_date'] = pd.to_datetime(lab_results['test_date'])
            event_datetime = pd.to_datetime(event_date)
            
            # Filter results within date range
            related_results = lab_results[
                (lab_results['test_date'] >= pd.to_datetime(start_date)) &
                (lab_results['test_date'] <= pd.to_datetime(end_date))
            ].sort_values('test_date')
            
            if not related_results.empty:
                st.markdown("**Exames no período (±7 dias):**")
                
                for _, result in related_results.iterrows():
                    # Calculate days difference
                    days_diff = (result['test_date'] - event_datetime).days
                    
                    if days_diff == 0:
                        date_label = "no mesmo dia"
                    elif days_diff > 0:
                        date_label = f"{days_diff} dia(s) depois"
                    else:
                        date_label = f"{abs(days_diff)} dia(s) antes"
                    
                    # Format value with unit
                    value_str = f"{result['test_value']}"
                    if pd.notna(result['unit']):
                        value_str += f" {result['unit']}"
                    
                    st.markdown(f"• **{result['test_name']}**: {value_str} ({date_label})")
                
                # Option to create a quick chart
                if len(related_results) > 1:
                    if st.button("📊 Visualizar Exames do Período", key="quick_chart"):
                        self._render_quick_exam_chart(related_results)
            else:
                st.info("Nenhum exame encontrado no período de ±7 dias.")
        else:
            st.info("Nenhum exame laboratorial registrado.")
    
    def _render_quick_exam_chart(self, related_results):
        """Render a quick chart for exams related to current event"""
        
        # Group by test name and create mini charts
        test_groups = related_results.groupby('test_name')
        
        for test_name, group in test_groups:
            if len(group) > 1:  # Only show chart if multiple values
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=group['test_date'],
                    y=group['test_value'],
                    mode='lines+markers',
                    name=test_name,
                    line=dict(color='#FF69B4'),
                    marker=dict(size=8)
                ))
                
                fig.update_layout(
                    title=f"Evolução: {test_name}",
                    xaxis_title="Data",
                    yaxis_title=f"Valor ({group['unit'].iloc[0] if pd.notna(group['unit'].iloc[0]) else ''})",
                    height=250,
                    template="plotly_white",
                    showlegend=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    def get_timeline_summary(self):
        """Get a summary of the timeline for reports"""
        
        events = self.db.get_medical_timeline()
        
        if not events:
            return "Nenhum evento registrado na linha do tempo."
        
        summary_lines = []
        summary_lines.append(f"LINHA DO TEMPO CLÍNICA - {len(events)} eventos registrados")
        summary_lines.append("=" * 50)
        
        sorted_events = sorted(events, key=lambda x: x['event_date'])
        
        for event in sorted_events:
            summary_lines.append(f"\n📅 {format_date(event['event_date'])} - {event['title']}")
            
            if event.get('description'):
                summary_lines.append(f"   Resumo: {event['description']}")
            
            if event.get('symptoms'):
                symptoms_str = ", ".join(event['symptoms'])
                summary_lines.append(f"   Sintomas: {symptoms_str}")
            
            if event.get('clinical_notes'):
                # Truncate clinical notes for summary
                notes = event['clinical_notes'][:200] + "..." if len(event['clinical_notes']) > 200 else event['clinical_notes']
                summary_lines.append(f"   Notas: {notes}")
        
        return "\n".join(summary_lines)
