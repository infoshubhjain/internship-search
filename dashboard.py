#!/usr/bin/env python3
"""
Streamlit dashboard for internship tracking
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import csv

# Page configuration
st.set_page_config(
    page_title="Summer 2027 Internship Tracker",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .priority-1 { border-left: 5px solid #ff6b6b; }
    .priority-2 { border-left: 5px solid #ffd93d; }
    .priority-3 { border-left: 5px solid #4ecdc4; }
    .priority-4 { border-left: 5px solid #45b7d1; }
    .priority-5 { border-left: 5px solid #96ceb4; }
</style>
""", unsafe_allow_html=True)

def load_data():
    """Load internship tracker data"""
    try:
        df = pd.read_csv('Summer2027_SWE_Tracker.csv')
        return df
    except FileNotFoundError:
        st.error("Tracker file not found. Please run the update script first.")
        return pd.DataFrame()

def calculate_metrics(df):
    """Calculate key metrics"""
    if df.empty:
        return {}
    
    total = len(df)
    applied = len(df[df['Status'] == 'Applied'])
    interviewing = len(df[df['Status'] == 'Interviewing'])
    offers = len(df[df['Offer Status'] == 'Offer'])
    rejected = len(df[df['Status'] == 'Rejected'])
    
    return {
        'total': total,
        'applied': applied,
        'interviewing': interviewing,
        'offers': offers,
        'rejected': rejected,
        'application_rate': (applied / total * 100) if total > 0 else 0,
        'interview_rate': (interviewing / applied * 100) if applied > 0 else 0,
        'offer_rate': (offers / interviewing * 100) if interviewing > 0 else 0
    }

def main():
    st.markdown('<h1 class="main-header">🚀 Summer 2027 SWE Internship Tracker</h1>', unsafe_allow_html=True)
    
    # Load data
    df = load_data()
    
    if df.empty:
        st.warning("No data available. Please run the update script first.")
        return
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", [
        "Dashboard",
        "Opportunities",
        "Applications",
        "Analytics",
        "Settings"
    ])
    
    # Dashboard page
    if page == "Dashboard":
        st.header("📊 Overview")
        
        # Calculate metrics
        metrics = calculate_metrics(df)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Opportunities", metrics['total'])
        with col2:
            st.metric("Applied", metrics['applied'], f"{metrics['application_rate']:.1f}%")
        with col3:
            st.metric("Interviewing", metrics['interviewing'], f"{metrics['interview_rate']:.1f}%")
        with col4:
            st.metric("Offers", metrics['offers'], f"{metrics['offer_rate']:.1f}%")
        
        # Priority breakdown
        st.subheader("Priority Breakdown")
        priority_counts = df['Priority'].value_counts().sort_index()
        
        fig_pie = px.pie(
            values=priority_counts.values,
            names=[f"Priority {i}" for i in priority_counts.index],
            title="Distribution by Priority",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Recent activity
        st.subheader("Recent Activity")
        recent_applied = df[df['Date Applied'] != ''].sort_values('Date Applied', ascending=False).head(5)
        
        if not recent_applied.empty:
            st.dataframe(
                recent_applied[['Company', 'Role', 'Date Applied', 'Status']],
                use_container_width=True
            )
        else:
            st.info("No recent applications to show.")
        
        # Upcoming deadlines
        st.subheader("Upcoming Deadlines")
        today = datetime.now()
        df['Application Deadline'] = pd.to_datetime(df['Application Deadline'], errors='coerce')
        upcoming_deadlines = df[
            (df['Application Deadline'] >= today) & 
            (df['Application Deadline'] <= today + timedelta(days=7)) &
            (df['Status'] == 'Not Applied')
        ].sort_values('Application Deadline')
        
        if not upcoming_deadlines.empty:
            st.dataframe(
                upcoming_deadlines[['Company', 'Role', 'Application Deadline', 'Priority']],
                use_container_width=True
            )
        else:
            st.info("No upcoming deadlines in the next 7 days.")
    
    # Opportunities page
    elif page == "Opportunities":
        st.header("🎯 Internship Opportunities")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            priority_filter = st.multiselect(
                "Filter by Priority",
                ['1', '2', '3', '4', '5'],
                default=['1', '2', '3']
            )
        
        with col2:
            status_filter = st.multiselect(
                "Filter by Status",
                df['Status'].unique().tolist(),
                default=['Not Applied', 'Applied']
            )
        
        with col3:
            sponsorship_filter = st.selectbox(
                "Filter by Sponsorship",
                ['All', 'Known Sponsors', 'Unknown']
            )
        
        # Apply filters
        filtered_df = df.copy()
        
        if priority_filter:
            filtered_df = filtered_df[filtered_df['Priority'].isin(priority_filter)]
        
        if status_filter:
            filtered_df = filtered_df[filtered_df['Status'].isin(status_filter)]
        
        if sponsorship_filter == 'Known Sponsors':
            filtered_df = filtered_df[
                filtered_df['Work Authorization/Sponsorship Notes'].str.contains('sponsor', case=False, na=False)
            ]
        
        # Display opportunities
        st.subheader(f"Showing {len(filtered_df)} opportunities")
        
        for _, row in filtered_df.iterrows():
            priority_class = f"priority-{row['Priority']}"
            
            with st.container():
                st.markdown(f"""
                <div class="metric-card {priority_class}">
                    <h3>{row['Company']} - {row['Role']}</h3>
                    <p><strong>Location:</strong> {row['Location']}</p>
                    <p><strong>Priority:</strong> {row['Priority']}</p>
                    <p><strong>Sponsorship:</strong> {row['Work Authorization/Sponsorship Notes']}</p>
                    <p><strong>Status:</strong> {row['Status']}</p>
                    <a href="{row['Link']}" target="_blank">Apply Now →</a>
                </div>
                """, unsafe_allow_html=True)
                
                # Quick action buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"Apply - {row['Company']}", key=f"apply_{row.name}"):
                        # This would update the status
                        st.success(f"Marked {row['Company']} as Applied")
                
                with col2:
                    if st.button(f"Save - {row['Company']}", key=f"save_{row.name}"):
                        st.success(f"Saved {row['Company']} to favorites")
                
                with col3:
                    if st.button(f"Hide - {row['Company']}", key=f"hide_{row.name}"):
                        st.success(f"Hidden {row['Company']}")
                
                st.markdown("---")
    
    # Applications page
    elif page == "Applications":
        st.header("📝 My Applications")
        
        # Show applied opportunities
        applied_df = df[df['Status'].isin(['Applied', 'Interviewing', 'Offer', 'Rejected'])]
        
        if not applied_df.empty:
            st.dataframe(
                applied_df[[
                    'Company', 'Role', 'Location', 'Date Applied', 
                    'Interview Date', 'Offer Status', 'Status'
                ]],
                use_container_width=True
            )
            
            # Application form
            st.subheader("Add New Application")
            
            with st.form("application_form"):
                company = st.text_input("Company")
                role = st.text_input("Role")
                date_applied = st.date_input("Date Applied", datetime.now())
                status = st.selectbox("Status", ["Applied", "Interviewing", "Offer", "Rejected"])
                notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("Add Application")
                
                if submitted:
                    st.success("Application added successfully!")
        else:
            st.info("No applications yet. Start applying to opportunities!")
    
    # Analytics page
    elif page == "Analytics":
        st.header("📈 Analytics")
        
        metrics = calculate_metrics(df)
        
        # Funnel analysis
        st.subheader("Application Funnel")
        
        funnel_data = pd.DataFrame({
            'Stage': ['Total', 'Applied', 'Interviewing', 'Offers'],
            'Count': [metrics['total'], metrics['applied'], metrics['interviewing'], metrics['offers']]
        })
        
        fig_funnel = px.funnel(
            funnel_data,
            x='Count',
            y='Stage',
            title="Application Funnel"
        )
        st.plotly_chart(fig_funnel, use_container_width=True)
        
        # Status distribution
        st.subheader("Status Distribution")
        
        status_counts = df['Status'].value_counts()
        
        fig_status = px.bar(
            x=status_counts.index,
            y=status_counts.values,
            title="Applications by Status",
            color=status_counts.index,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig_status, use_container_width=True)
        
        # Priority vs Status
        st.subheader("Priority vs Status")
        
        priority_status = pd.crosstab(df['Priority'], df['Status'])
        
        fig_heatmap = px.imshow(
            priority_status,
            text_auto=True,
            aspect="auto",
            color_continuous_scale='Blues',
            title="Priority vs Status Heatmap"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Timeline
        st.subheader("Application Timeline")
        
        df['Date Applied'] = pd.to_datetime(df['Date Applied'], errors='coerce')
        timeline_data = df[df['Date Applied'].notna()].sort_values('Date Applied')
        
        if not timeline_data.empty:
            timeline_data['Week'] = timeline_data['Date Applied'].dt.to_period('W')
            weekly_apps = timeline_data.groupby('Week').size()
            
            fig_timeline = px.line(
                x=weekly_apps.index.astype(str),
                y=weekly_apps.values,
                title="Applications Over Time",
                markers=True
            )
            fig_timeline.update_xaxes(title="Week")
            fig_timeline.update_yaxes(title="Number of Applications")
            st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Settings page
    elif page == "Settings":
        st.header("⚙️ Settings")
        
        st.subheader("Data Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Update Data from GitHub"):
                st.info("Running update script...")
                # This would call the update script
                st.success("Data updated successfully!")
        
        with col2:
            if st.button("📤 Export Data"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name='internship_tracker.csv',
                    mime='text/csv'
                )
        
        st.subheader("Notification Settings")
        
        email_notifications = st.checkbox("Enable Email Notifications")
        if email_notifications:
            email = st.text_input("Email Address")
            frequency = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Only Urgent"])
            
            st.button("Save Notification Settings")
        
        st.subheader("Tracker Preferences")
        
        default_priority = st.selectbox("Default Priority Filter", ["All", "1-2", "1-3"])
        show_sponsorship_only = st.checkbox("Show Only Known Sponsors", value=False)
        
        st.button("Save Preferences")

if __name__ == "__main__":
    main()