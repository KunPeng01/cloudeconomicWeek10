import streamlit as st
import pandas as pd
import plotly.express as px
import io

# Set page to wide layout
st.set_page_config(layout="wide")


@st.cache_data
def load_data(file_path):
    """
    Loads and pre-processes the dataset from a file.
    This function is cached for performance.
    """
    try:
        # Open the file and read lines
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Strip surrounding quotes and newlines
        cleaned_lines = [line.strip().strip('"') for line in lines]

        # Use io.StringIO to treat the cleaned text as a file
        csv_in_memory = io.StringIO("\n".join(cleaned_lines))

        # Read the CSV from the in-memory string
        df = pd.read_csv(csv_in_memory)

        # --- Data Type Conversion & Feature Engineering ---
        # Convert cost to numeric
        if 'MonthlyCostUSD' in df.columns:
            df['MonthlyCostUSD'] = pd.to_numeric(df['MonthlyCostUSD'], errors='coerce')

        # --- Task 4: Create status columns for cleaner charts ---
        df['Tagged_Status'] = df['Tagged'].fillna('Missing')
        df['Environment_Status'] = df['Environment'].fillna('Missing')

        # --- Task 3: Create Tag Completeness Score ---
        tag_columns = ['Department', 'Project', 'Environment', 'Owner', 'CostCenter']
        df['TagCompletenessScore'] = len(tag_columns) - df[tag_columns].isnull().sum(axis=1)

        return df.copy()

    except FileNotFoundError:
        st.error(f"Error: File '{file_path}' not found. Please make sure it's in the same directory.")
        return None
    except Exception as e:
        st.error(f"An error occurred while loading the data: {e}")
        return None


@st.cache_data
def df_to_csv(df):
    """Converts a DataFrame to a CSV string for download."""
    return df.to_csv(index=False).encode('utf-8')


# --- Main App ---

# Load the data
df_original = load_data('cloudmart_multi_account.csv')

if df_original is not None:

    # --- Initialize Session State for Remediation (Task 5.1) ---
    if 'edited_df' not in st.session_state:
        st.session_state.edited_df = df_original.copy()

    st.title("☁️ CloudMart Resource Tagging Dashboard")

    # --- Sidebar Filters (Task 4.5) ---
    st.sidebar.header("Filters")

    # Get unique, sorted lists for filters
    services = sorted(st.session_state.edited_df['Service'].dropna().unique())
    regions = sorted(st.session_state.edited_df['Region'].dropna().unique())
    departments = sorted(st.session_state.edited_df['Department'].dropna().unique())

    # Create multiselect widgets
    selected_services = st.sidebar.multiselect("Service", services, default=services)
    selected_regions = st.sidebar.multiselect("Region", regions, default=regions)
    selected_departments = st.sidebar.multiselect("Department", departments, default=departments)

    # --- Filter DataFrames ---
    # We need two dataframes:
    # 1. df_filtered_original: The "Before" state, based on filters.
    # 2. df_filtered_edited: The "After" state, based on filters AND user edits.

    # Base filter criteria
    filter_criteria = (
            (st.session_state.edited_df['Service'].isin(selected_services)) &
            (st.session_state.edited_df['Region'].isin(selected_regions)) &
            (st.session_state.edited_df['Department'].isin(selected_departments) | st.session_state.edited_df[
                'Department'].isnull())  # Include null depts
    )

    # Apply filters to both original and edited data
    df_filtered_original = df_original[filter_criteria].copy()
    df_filtered_edited = st.session_state.edited_df[filter_criteria].copy()

    # --- App Layout (Tabs) ---
    tab1, tab2 = st.tabs(["📊 Visualization Dashboard (Task 4)", "🏷️ Tag Remediation Workflow (Task 5)"])

    # --- TAB 1: VISUALIZATION DASHBOARD (TASK 4) ---
    with tab1:
        st.header("Dashboard")
        st.markdown(
            "This dashboard reflects the **current state** of the data. If you remediate tags in Tab 2, the charts here will update.")

        # --- Key Metrics ---
        total_cost = df_filtered_edited['MonthlyCostUSD'].sum()
        untagged_cost = df_filtered_edited[df_filtered_edited['Tagged_Status'] == 'No']['MonthlyCostUSD'].sum()
        untagged_percent = (untagged_cost / total_cost) * 100 if total_cost > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Cost", f"${total_cost:,.2f}")
        col2.metric("Untagged Cost", f"${untagged_cost:,.2f}")
        col3.metric("Untagged Cost %", f"{untagged_percent:.2f}%")

        st.divider()

        # --- Charts (Task 4.1 - 4.4) ---
        col1, col2 = st.columns(2)

        with col1:
            # 4.1: Pie chart of tagged vs untagged resources
            st.subheader("Tagged vs. Untagged Resource Counts")
            tagged_counts = df_filtered_edited['Tagged_Status'].value_counts().reset_index()
            fig_pie_tagged = px.pie(tagged_counts,
                                    names='Tagged_Status',
                                    values='count',
                                    title="Resource Tagging Status",
                                    color='Tagged_Status',
                                    color_discrete_map={'Yes': '#00B050', 'No': '#FF0000', 'Missing': '#A0A0A0'})
            st.plotly_chart(fig_pie_tagged, width='stretch')  # UPDATED

            # 4.3: Horizontal bar chart of total cost per service
            st.subheader("Total Cost by Service")
            cost_by_service = df_filtered_edited.groupby('Service')['MonthlyCostUSD'].sum().reset_index()
            fig_bar_service = px.bar(cost_by_service.sort_values(by='MonthlyCostUSD', ascending=True),
                                     x='MonthlyCostUSD',
                                     y='Service',
                                     orientation='h',
                                     title='Total Monthly Cost per Service')
            st.plotly_chart(fig_bar_service, width='stretch')  # UPDATED

        with col2:
            # 4.2: Bar chart showing cost per department by tagging status
            st.subheader("Cost per Department by Tagging Status")
            cost_by_dept_tagged = df_filtered_edited.groupby(['Department', 'Tagged_Status'])[
                'MonthlyCostUSD'].sum().reset_index()
            fig_bar_dept = px.bar(cost_by_dept_tagged,
                                  x='Department',
                                  y='MonthlyCostUSD',
                                  color='Tagged_Status',
                                  title='Cost by Department & Tagging Status',
                                  barmode='group',
                                  color_discrete_map={'Yes': '#00B050', 'No': '#FF0000', 'Missing': '#A0A0A0'})
            st.plotly_chart(fig_bar_dept, width='stretch')  # UPDATED

            # 4.4: Visualize cost by environment
            st.subheader("Cost by Environment")
            cost_by_env = df_filtered_edited.groupby('Environment_Status')['MonthlyCostUSD'].sum().reset_index()
            fig_pie_env = px.pie(cost_by_env,
                                 names='Environment_Status',
                                 values='MonthlyCostUSD',
                                 title='Monthly Cost by Environment')
            st.plotly_chart(fig_pie_env, width='stretch')  # UPDATED

    # --- TAB 2: TAG REMEDIATION WORKFLOW (TASK 5) ---
    with tab2:
        st.header("Tag Remediation Workflow")

        # --- Task 5.4: Compare cost visibility before and after ---
        st.subheader("Comparison: Before vs. After Remediation")
        st.markdown("This compares the original filtered data ('Before') with your edited data ('After').")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Before Remediation")
            orig_untagged_cost = df_filtered_original[df_filtered_original['Tagged_Status'] == 'No'][
                'MonthlyCostUSD'].sum()
            orig_missing_owner = df_filtered_original['Owner'].isnull().sum()
            st.metric("Untagged Cost", f"${orig_untagged_cost:,.2f}")
            st.metric("Resources Missing Owner", f"{orig_missing_owner}")

        with col2:
            st.markdown("#### After Remediation")
            edited_untagged_cost = df_filtered_edited[df_filtered_edited['Tagged_Status'] == 'No'][
                'MonthlyCostUSD'].sum()
            edited_missing_owner = df_filtered_edited['Owner'].isnull().sum()
            st.metric("Untagged Cost", f"${edited_untagged_cost:,.2f}",
                      delta=f"{edited_untagged_cost - orig_untagged_cost:,.2f}")
            st.metric("Resources Missing Owner", f"{edited_missing_owner}",
                      delta=f"{edited_missing_owner - orig_missing_owner}")

        st.divider()

        # --- Task 5.1 & 5.2: Editable table for untagged resources ---
        st.subheader("Remediate Untagged Resources")
        st.info(
            "Edit the resources below. Changes are saved as you type and will update the 'After' metrics and the Dashboard tab.")

        # We want to edit resources that are untagged OR have missing key tags
        cols_to_edit = ['ResourceID', 'Service', 'Department', 'Project', 'Environment', 'Owner', 'MonthlyCostUSD',
                        'Tagged']

        # Find the indices in the main session state dataframe that need editing
        # We edit resources where 'Tagged' is 'No' OR key tags are missing
        remediation_mask = (
                (st.session_state.edited_df['Tagged'] == 'No') |
                (st.session_state.edited_df['Department'].isnull()) |
                (st.session_state.edited_df['Project'].isnull()) |
                (st.session_state.edited_df['Owner'].isnull())
        )
        remediation_indices = st.session_state.edited_df[remediation_mask].index

        # Create a view of the dataframe for the editor
        df_for_editor = st.session_state.edited_df.loc[remediation_indices, cols_to_edit]

        # Use st.data_editor to allow edits
        edited_subset = st.data_editor(
            df_for_editor,
            key="data_editor",
            num_rows="dynamic",
            width='stretch',  # UPDATED
            column_config={
                "ResourceID": st.column_config.TextColumn("Resource ID (Read Only)", disabled=True),
                "Service": st.column_config.TextColumn("Service (Read Only)", disabled=True),
                "MonthlyCostUSD": st.column_config.NumberColumn("Cost (Read Only)", disabled=True)
            }
        )

        # --- Update Session State with Edits ---
        # This is the most important part: merge the edits back into the main session state df
        if edited_subset is not None:
            # Update the main dataframe in session state
            st.session_state.edited_df.update(edited_subset)

            # --- Auto-update 'Tagged' status ---
            # If a user fills in key tags, we should consider it 'Tagged'
            # This logic is a business rule: if Dept, Proj, Env, and Owner exist, it's 'Yes'

            # Get the indices that were just edited
            edited_indices = edited_subset.index

            # Check for completeness on the edited rows
            key_tags_filled = (
                    st.session_state.edited_df.loc[edited_indices, 'Department'].notnull() &
                    st.session_state.edited_df.loc[edited_indices, 'Project'].notnull() &
                    st.session_state.edited_df.loc[edited_indices, 'Environment'].notnull() &
                    st.session_state.edited_df.loc[edited_indices, 'Owner'].notnull()
            )

            # Update 'Tagged' status to 'Yes' for rows that are now complete
            st.session_state.edited_df.loc[edited_indices[key_tags_filled], 'Tagged'] = 'Yes'
            # Re-calculate the 'Tagged_Status' helper column
            st.session_state.edited_df['Tagged_Status'] = st.session_state.edited_df['Tagged'].fillna('Missing')

            # Rerun to update the "Before/After" metrics instantly
            st.rerun()

        # --- Task 5.3: Download the updated dataset ---
        st.divider()
        st.subheader("Download Remediated Data")
        st.markdown("Download the *entire* dataset with all your remediations applied.")

        csv_data_edited = df_to_csv(st.session_state.edited_df)
        st.download_button(
            label="Download Remediated Data as CSV",
            data=csv_data_edited,
            file_name="remediated_cloud_costs.csv",
            mime="text/csv",
        )

        # --- Task 5.5: Discuss impact ---
        st.divider()
        st.subheader("Task 5.5: Reflection on Tagging Impact")
        st.markdown("""
        **How does improved tagging affect accountability and reports?**

        This remediation workflow directly demonstrates the business value of tagging:

        * **Accountability:** Before remediation, the "Untagged Cost" metric (e.g., $2,250) represents money spent with **no clear owner**. It's impossible to ask "Why is the Sales team spending so much on RDS?" if the resource isn't tagged 'Sales'. By filling in the `Owner` and `Department` tags, you immediately assign accountability.

        * **Cost Visibility & Reporting:** You cannot build an accurate financial report without good tags.
            * **Missing `Department`:** This cost is "lost" and cannot be allocated to any team's budget, leading to inaccurate P&L reports.
            * **Missing `Project`:** You can't tell which products are profitable. Is 'CampaignApp' (costing $500) worth the investment? It's impossible to know if half its resources are untagged.
            * **Missing `Environment`:** You can't separate 'Prod' (cost of doing business) from 'Dev' (cost of innovation). This was a key finding in our data: **100% of 'Dev' resources were untagged**, making it look like a "shadow" cost center.

        By remediating tags, you turn ambiguous, untracked spending into clear, actionable business intelligence.
        """)

else:
    st.error("Failed to load data. The dashboard cannot be displayed.")