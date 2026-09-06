#!/usr/bin/env python3
"""
Streamlit dashboard for internship tracking
"""
import os

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

import tracker_io
from intl_tracker import BUCKET_APPLY, BUCKET_INVESTIGATE, BUCKET_ORDER
from tracker_io import INTL_TRACKER_FILE, STATUSES, TRACKER_FILE

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

@st.cache_data
def load_data(mtime):
    """Load the tracker.

    Keyed on the file's mtime so the cache is dropped as soon as anything
    writes to the CSV, whether that is this app or a scheduled update.
    The argument must NOT be named with a leading underscore: Streamlit
    excludes such parameters from the cache key, which would pin the app to
    the first version of the file it ever read.
    """
    try:
        return pd.read_csv(TRACKER_FILE, dtype=str).fillna('')
    except FileNotFoundError:
        return pd.DataFrame()


def tracker_mtime():
    try:
        return os.path.getmtime(TRACKER_FILE)
    except OSError:
        return 0


@st.cache_data
def load_intl(mtime):
    """Load the international tracker (same mtime-keyed cache as the main one)."""
    try:
        return pd.read_csv(INTL_TRACKER_FILE, dtype=str).fillna('')
    except FileNotFoundError:
        return pd.DataFrame()


def intl_mtime():
    try:
        return os.path.getmtime(INTL_TRACKER_FILE)
    except OSError:
        return 0


def save_status(link, updates):
    """Persist a change and refresh the view, or report why it failed."""
    try:
        if tracker_io.update_row(link, updates):
            load_data.clear()
            return True
        st.error("Could not find that listing in the tracker.")
    except (ValueError, OSError) as e:
        st.error(f"Could not save: {e}")
    return False

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
    
    df = load_data(tracker_mtime())

    if df.empty:
        st.warning("No data yet. Run `python3 update_all.py` to populate the tracker.")
        return
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", [
        "Dashboard",
        "Opportunities",
        "Applications",
        "Urgency",
        "International",
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
            # Options come from the canonical status list, not from the values
            # present in the data: deriving them from the CSV crashes whenever
            # a default status happens to have no rows yet.
            status_filter = st.multiselect(
                "Filter by Status",
                STATUSES,
                default=['Not Applied']
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
        
        # Rendering every row at once creates thousands of Streamlit widgets
        # and makes the page unusable, so show one page at a time.
        page_size = 25
        total = len(filtered_df)
        pages = max(1, (total + page_size - 1) // page_size)
        page_num = st.number_input(
            f"Page (of {pages})", min_value=1, max_value=pages, value=1, step=1
        )
        start = (page_num - 1) * page_size
        visible = filtered_df.iloc[start:start + page_size]

        st.subheader(f"Showing {len(visible)} of {total} opportunities")

        for _, row in visible.iterrows():
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

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Mark Applied", key=f"apply_{row.name}",
                                 disabled=row['Status'] != 'Not Applied'):
                        if save_status(row['Link'], {
                            'Status': 'Applied',
                            'Date Applied': datetime.now().strftime('%Y-%m-%d'),
                        }):
                            st.rerun()

                with col2:
                    if st.button("Not Interested", key=f"hide_{row.name}",
                                 disabled=row['Status'] != 'Not Applied'):
                        if save_status(row['Link'], {
                            'Status': 'Closed',
                            'Notes': 'Not interested',
                        }):
                            st.rerun()

                st.markdown("---")

    # Applications page
    elif page == "Applications":
        st.header("📝 My Applications")
        
        # Show applied opportunities
        applied_df = df[df['Status'].isin(['Applied', 'Interviewing', 'Offer', 'Rejected'])]
        
        if not applied_df.empty:
            editable = ['Status', 'Date Applied', 'Interview Date',
                        'Offer Status', 'Follow-up Date', 'Notes']
            shown = applied_df[['Company', 'Role', 'Link'] + editable]

            edited = st.data_editor(
                shown,
                use_container_width=True,
                hide_index=True,
                disabled=['Company', 'Role', 'Link'],
                column_config={
                    'Status': st.column_config.SelectboxColumn(options=STATUSES),
                    'Link': st.column_config.LinkColumn(),
                },
                key='applications_editor',
            )

            if st.button("Save changes"):
                # Write only the rows that actually changed, so a stray click
                # does not rewrite the whole file.
                changed = 0
                for idx, new_row in edited.iterrows():
                    old_row = shown.loc[idx]
                    diff = {c: new_row[c] for c in editable if new_row[c] != old_row[c]}
                    if diff and save_status(new_row['Link'], diff):
                        changed += 1
                if changed:
                    st.success(f"Saved {changed} row(s).")
                    st.rerun()
                else:
                    st.info("Nothing to save.")

            st.subheader("Add an application not in the tracker")

            with st.form("application_form"):
                company = st.text_input("Company")
                role = st.text_input("Role")
                link = st.text_input("Link (job posting URL)")
                date_applied = st.date_input("Date Applied", datetime.now())
                status = st.selectbox("Status", STATUSES[1:])
                notes = st.text_area("Notes")

                if st.form_submit_button("Add Application"):
                    if not company or not link:
                        st.error("Company and link are both required.")
                    elif tracker_io.append_row({
                        'Company': company, 'Role': role, 'Link': link,
                        'Status': status, 'Notes': notes,
                        'Date Applied': date_applied.strftime('%Y-%m-%d'),
                    }):
                        load_data.clear()
                        st.success(f"Added {company}.")
                        st.rerun()
                    else:
                        st.error("That link is already in the tracker.")
        else:
            st.info("No applications yet. Start applying to opportunities!")

    # Urgency page
    elif page == "Urgency":
        st.header("⏳ What's running out of time")
        st.caption("Most employers never publish a deadline. Where one exists it is "
                   "used; otherwise urgency comes from how long this tracker has "
                   "seen the listing against how long comparable listings lasted.")

        import urgency as urgency_mod
        ranked, model = urgency_mod.rank_open_listings()

        st.info(f"Lifetime model: **{round(model['overall'])} days** — "
                f"{model['overall_source']}")

        levels = [urgency_mod.URGENT, urgency_mod.SOON,
                  urgency_mod.COMFORTABLE, urgency_mod.FRESH]
        counts = {lvl: sum(1 for r in ranked if r['level'] == lvl) for lvl in levels}
        cols = st.columns(4)
        for col, lvl in zip(cols, levels):
            col.metric(lvl.title(), counts[lvl])

        chosen = st.multiselect("Show", levels,
                                default=[urgency_mod.URGENT, urgency_mod.SOON])
        shown = [r for r in ranked if r['level'] in chosen] if chosen else ranked

        if not shown:
            st.success("Nothing is time-critical. Every open listing was seen recently.")
        else:
            st.dataframe(pd.DataFrame([{
                'Urgency': r['level'], 'Priority': r['priority'], 'Score': r['score'],
                'Company': r['company'], 'Role': r['role'],
                'Days since first seen': r['age_days'],
                'Expected lifetime (d)': r['expected_days'],
                'Basis': r['basis'], 'Link': r['link'],
            } for r in shown[:200]]), use_container_width=True, hide_index=True,
                column_config={'Link': st.column_config.LinkColumn()})

    # International page
    elif page == "International":
        st.header("🌍 International Summer 2027")
        st.caption("Paid CS internships outside the United States, scored for an "
                   "F-1 student who is an Indian citizen studying in the US.")

        intl = load_intl(intl_mtime())
        if intl.empty:
            st.info("No international data yet. Run `python3 intl_tracker.py`.")
        else:
            live = intl[intl['Status'] != 'Closed']

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Live opportunities", len(live))
            col2.metric("Category A (sponsors)", int((live['Visa Category'] == 'A').sum()))
            col3.metric("Countries", live['Country'].nunique())
            col4.metric("Best match", f"{pd.to_numeric(live['Match Score']).max():.0f}/100"
                        if len(live) else "-")

            buckets = st.multiselect(
                "Show buckets", BUCKET_ORDER,
                default=[BUCKET_APPLY, BUCKET_INVESTIGATE])
            countries = st.multiselect("Countries", sorted(live['Country'].unique()))

            shown = live[live['Bucket'].isin(buckets)] if buckets else live
            if countries:
                shown = shown[shown['Country'].isin(countries)]
            shown = shown.sort_values('Match Score', key=lambda c: pd.to_numeric(c),
                                      ascending=False)

            st.subheader(f"{len(shown)} opportunities")
            for _, row in shown.iterrows():
                header = f"{row['Match Score']}/100 · {row['Company']} — {row['Title']}"
                with st.expander(f"{row['Bucket'][0]} {header}"):
                    st.markdown(
                        f"**{row['City']}, {row['Country']}** · {row['Category']} · "
                        f"{row['Application Status']}\n\n"
                        f"**Visa** {row['Visa Category']} — {row['Visa Explanation']}\n\n"
                        + (f"**Route** {row['Visa Route']}\n\n" if row['Visa Route'] else "")
                        + f"**Paid** {row['Paid']}"
                        + (f" ({row['Compensation']})" if row['Compensation'] else "")
                        + f" · **English** {row['English Environment']}\n\n"
                        f"**Why it fits** {row['Why It Fits']}\n\n"
                        + (f"**Barriers** {row['Barriers']}\n\n" if row['Barriers'] else "")
                        + f"[Apply →]({row['Link']})")
                    if row['Visa Evidence']:
                        st.caption(f"Evidence: \u201c{row['Visa Evidence']}\u201d")

            st.download_button("📤 Export international CSV",
                               data=intl.to_csv(index=False),
                               file_name='international_internships.csv', mime='text/csv')

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
                with st.spinner("Scraping sources and merging..."):
                    import update_all
                    ok = update_all.main() == 0
                if ok:
                    load_data.clear()
                    st.success("Tracker updated. Your application history is preserved.")
                    st.rerun()
                else:
                    st.error("Update failed. See internship_tracker.log for details.")

        with col2:
            st.download_button(
                label="📤 Export tracker as CSV",
                data=df.to_csv(index=False),
                file_name='internship_tracker.csv',
                mime='text/csv',
            )

        st.subheader("Email Alerts")
        st.markdown(
            "Alerts are configured with environment variables, so the same "
            "settings work locally and in GitHub Actions:\n\n"
            "```\n"
            "TRACKER_EMAIL=you@gmail.com\n"
            "TRACKER_EMAIL_PASSWORD=<gmail app password>\n"
            "```\n"
            "A `.env` file in the project directory works too (it is gitignored)."
        )

        from notification_system import config_from_env
        if config_from_env():
            st.success("Email is configured.")
        else:
            st.info("Email is not configured; alerts are skipped.")

if __name__ == "__main__":
    main()