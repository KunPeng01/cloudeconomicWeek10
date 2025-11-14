import pandas as pd
import io
import streamlit as st
import plotly.express as px

# Page layout
st.set_page_config(page_title="CloudMart Tagging Dashboard", layout="wide")

# File path
file_path = "cloudmart_multi_account.csv"

try:
    # --- Pre-process the file ---
    # Read the file line by line
    with open(file_path, "r") as f:
        lines = f.readlines()

    # Strip the surrounding quotes and newline characters from each line
    cleaned_lines = [line.strip().strip('"') for line in lines]

    # Join the cleaned lines back into a single string
    # and read it into pandas using io.StringIO
    csv_in_memory = io.StringIO("\n".join(cleaned_lines))

    # Read the CSV from the in-memory string
    df = pd.read_csv(csv_in_memory)

    # --- Data Type Conversion ---
    # Convert MonthlyCostUSD to numeric
    if "MonthlyCostUSD" in df.columns:
        df["MonthlyCostUSD"] = pd.to_numeric(df["MonthlyCostUSD"], errors="coerce")

    # --------------------------------------------------
    # Task Set 1 – Data Exploration
    # --------------------------------------------------
    st.header("Task Set 1 – Data Exploration")

    # --- Task 1.1: Display the first 5 rows ---
    st.subheader("Task 1.1: First 5 Rows")
    st.dataframe(df.head())

    # DataFrame Info (user-friendly table)
    st.subheader("DataFrame Info")
    df_info = pd.DataFrame(
        {
            "Column": df.columns,
            "Non-Null Count": df.notnull().sum().values,
            "Dtype": df.dtypes.astype(str).values,
        }
    )
    st.dataframe(df_info)

    # --- Task 1.2: Check for missing values ---
    st.subheader("Task 1.2: Missing Values Count")
    missing_values = df.isnull().sum()
    st.dataframe(missing_values.to_frame(name="MissingCount"))

    # --- Task 1.3: Identify column with most missing values ---
    st.subheader("Task 1.3: Columns with Most Missing Values")
    sorted_missing = missing_values.sort_values(ascending=False)
    st.dataframe(sorted_missing.to_frame(name="MissingCount"))

    # --- Task 1.4: Count tagged vs. untagged resources ---
    st.subheader("Task 1.4: Tagged vs. Untagged Resource Count")
    if "Tagged" in df.columns:
        tagged_counts = df["Tagged"].value_counts(dropna=False)
        st.dataframe(tagged_counts.to_frame(name="Count"))

        # --- Task 1.5: Percentage of untagged resources ---
        st.subheader("Task 1.5: Percentage of Untagged Resources")
        if "No" in tagged_counts.index:
            untagged_count = tagged_counts["No"]
            total_resources = len(df)
            percentage_untagged = (untagged_count / total_resources) * 100
            st.metric("Untagged Resources (%)", f"{percentage_untagged:.2f}%")
        else:
            st.write("No 'Untagged' ('No') resources found.")
    else:
        st.write("\n'Tagged' column not found. Cannot perform tasks 1.4 and 1.5.")

    # --------------------------------------------------
    # Task Set 2 – Cost Visibility
    # --------------------------------------------------
    st.header("Task Set 2 – Cost Visibility")

    if "MonthlyCostUSD" not in df.columns:
        st.error(
            "The dataset does not contain a 'MonthlyCostUSD' column, so cost visibility tasks cannot be calculated."
        )
    else:
        # 2.1 – Total cost of tagged vs untagged resources
        st.subheader("2.1 – Total Cost of Tagged vs Untagged Resources")

        cost_by_tag = (
            df.groupby("Tagged", dropna=False)["MonthlyCostUSD"]
            .sum()
            .reset_index()
            .rename(columns={"MonthlyCostUSD": "TotalCostUSD"})
        )
        st.dataframe(cost_by_tag)

        # 2.2 – Percentage of total cost that is untagged
        st.subheader("2.2 – Percentage of Total Cost that is Untagged")

        total_cost = df["MonthlyCostUSD"].sum()
        untagged_cost = df.loc[df["Tagged"] == "No", "MonthlyCostUSD"].sum()

        if total_cost > 0:
            pct_untagged_cost = (untagged_cost / total_cost) * 100
        else:
            pct_untagged_cost = 0.0

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Cost (All Resources)", f"${total_cost:,.2f}")
        col_b.metric("Untagged Cost", f"${untagged_cost:,.2f}")
        col_c.metric("Untagged Cost (%)", f"{pct_untagged_cost:.2f}%")

        # 2.3 – Department with the most untagged cost
        st.subheader("2.3 – Department with the Most Untagged Cost")

        if "Department" in df.columns:
            dept_untagged = (
                df[df["Tagged"] == "No"]
                .groupby("Department")["MonthlyCostUSD"]
                .sum()
                .sort_values(ascending=False)
            )

            if not dept_untagged.empty:
                st.write("Untagged cost by department (sorted descending):")
                st.dataframe(dept_untagged.to_frame(name="UntaggedCostUSD"))

                top_dept = dept_untagged.index[0]
                top_cost = dept_untagged.iloc[0]
                st.markdown(
                    f"**Department with highest untagged cost:** `{top_dept}` "
                    f"with **${top_cost:,.2f}** untagged."
                )
            else:
                st.write("There are no untagged resources to analyze by department.")
        else:
            st.write("Column 'Department' not found in the dataset.")

        # 2.4 – Project that consumes the most cost overall
        st.subheader("2.4 – Project with the Highest Total Cost")

        if "Project" in df.columns:
            project_cost = (
                df.groupby("Project")["MonthlyCostUSD"]
                .sum()
                .sort_values(ascending=False)
            )
            st.dataframe(project_cost.to_frame(name="TotalCostUSD"))

            if not project_cost.empty:
                top_project = project_cost.index[0]
                top_project_cost = project_cost.iloc[0]
                st.markdown(
                    f"**Project with highest total cost:** `{top_project}` "
                    f"with **${top_project_cost:,.2f}**."
                )
        else:
            st.write("Column 'Project' not found in the dataset.")

        # 2.5 – Compare Prod vs Dev environments in terms of cost and tagging quality
        st.subheader("2.5 – Prod vs Dev: Cost and Tagging Quality")

        if "Environment" in df.columns:
            env_filter = df["Environment"].isin(["Prod", "Dev"])
            df_env = df[env_filter].copy()

            if df_env.empty:
                st.write("No Prod or Dev environment data found.")
            else:
                env_tag_cost = (
                    df_env.groupby(["Environment", "Tagged"])["MonthlyCostUSD"]
                    .sum()
                    .reset_index()
                    .rename(columns={"MonthlyCostUSD": "TotalCostUSD"})
                )

                st.write("Total cost by Environment and Tagging status:")
                st.dataframe(env_tag_cost)

                env_tag_pivot = env_tag_cost.pivot(
                    index="Environment", columns="Tagged", values="TotalCostUSD"
                )
                st.write("Pivot view (Environment x Tagged):")
                st.dataframe(env_tag_pivot)

                env_tag_counts = (
                    df_env.groupby(["Environment", "Tagged"])["ResourceID"]
                    .count()
                    .reset_index()
                    .rename(columns={"ResourceID": "ResourceCount"})
                )
                st.write("Resource counts by Environment and Tagging status:")
                st.dataframe(env_tag_counts)
        else:
            st.write("Column 'Environment' not found in the dataset.")

    # --------------------------------------------------
    # Task Set 3 – Tagging Compliance
    # --------------------------------------------------
    st.header("Task Set 3 – Tagging Compliance")

    # Define which columns count as tag fields
    candidate_tag_fields = [
        "Department",
        "Project",
        "Environment",
        "Owner",
        "CostCenter",
        "CreatedBy",
    ]
    tag_fields = [col for col in candidate_tag_fields if col in df.columns]

    if not tag_fields:
        st.error("No tag fields found in the dataset for compliance analysis.")
    else:
        st.write(
            "Tag fields considered for completeness score:", ", ".join(tag_fields)
        )

        # 3.1 – Create a “Tag Completeness Score” per resource
        st.subheader("3.1 – Tag Completeness Score per Resource")

        df["TagCompletenessScore"] = df[tag_fields].notnull().sum(axis=1)

        cols_to_show = ["ResourceID"] if "ResourceID" in df.columns else []
        cols_to_show += tag_fields + ["TagCompletenessScore"]

        st.dataframe(df[cols_to_show])

        # 3.2 – Top 5 resources with lowest completeness scores
        st.subheader("3.2 – Top 5 Resources with Lowest Completeness Scores")

        df_lowest = df.sort_values(by="TagCompletenessScore", ascending=True)
        top5_lowest = df_lowest[cols_to_show].head(5)
        st.dataframe(top5_lowest)

        # 3.3 – Most frequently missing tag fields
        st.subheader("3.3 – Most Frequently Missing Tag Fields")

        missing_tag_counts = df[tag_fields].isnull().sum().sort_values(ascending=False)
        missing_tag_df = missing_tag_counts.to_frame(name="MissingCount")
        missing_tag_df["MissingPercentage"] = (
            missing_tag_df["MissingCount"] / len(df) * 100
        )
        st.dataframe(missing_tag_df)

        # 3.4 – List all untagged resources and their costs
        st.subheader("3.4 – Untagged Resources and Their Costs")

        if "Tagged" in df.columns:
            untagged_resources = df[df["Tagged"] == "No"].copy()

            if not untagged_resources.empty:
                cols_untagged = ["ResourceID", "MonthlyCostUSD"]
                for col in tag_fields:
                    if col not in cols_untagged:
                        cols_untagged.append(col)

                cols_untagged = [
                    c for c in cols_untagged if c in untagged_resources.columns
                ]

                st.dataframe(untagged_resources[cols_untagged])

                # 3.5 – Export untagged resources to a new CSV file
                st.subheader("3.5 – Export Untagged Resources to CSV")

                csv_buffer = io.StringIO()
                untagged_resources.to_csv(csv_buffer, index=False)
                csv_bytes = csv_buffer.getvalue().encode("utf-8")

                st.download_button(
                    label="Download untagged_resources.csv",
                    data=csv_bytes,
                    file_name="untagged_resources.csv",
                    mime="text/csv",
                )
            else:
                st.write("There are no untagged resources in the dataset.")
        else:
            st.write("Column 'Tagged' not found in the dataset; cannot list untagged resources.")

    # --------------------------------------------------
    # Task Set 4 – Visualization Dashboard
    # --------------------------------------------------
    st.header("Task Set 4 – Visualization Dashboard")

    # 4.5 – Interactive filters
    st.subheader("4.5 – Interactive Filters")
    st.write("Use the filters on the left sidebar to slice the data.")

    with st.sidebar.expander("Filters", expanded=True):
        service_options = (
            sorted(df["Service"].dropna().unique()) if "Service" in df.columns else []
        )
        region_options = (
            sorted(df["Region"].dropna().unique()) if "Region" in df.columns else []
        )
        dept_options = (
            sorted(df["Department"].dropna().unique())
            if "Department" in df.columns
            else []
        )

        selected_services = (
            st.multiselect(
                "Filter by Service",
                options=service_options,
                default=service_options,
            )
            if service_options
            else []
        )

        selected_regions = (
            st.multiselect(
                "Filter by Region",
                options=region_options,
                default=region_options,
            )
            if region_options
            else []
        )

        selected_departments = (
            st.multiselect(
                "Filter by Department",
                options=dept_options,
                default=dept_options,
            )
            if dept_options
            else []
        )

    # Apply filters
    df_filtered = df.copy()

    if "Service" in df.columns and selected_services:
        df_filtered = df_filtered[df_filtered["Service"].isin(selected_services)]

    if "Region" in df.columns and selected_regions:
        df_filtered = df_filtered[df_filtered["Region"].isin(selected_regions)]

    if "Department" in df.columns and selected_departments:
        df_filtered = df_filtered[df_filtered["Department"].isin(selected_departments)]

    st.write(f"Filtered rows: {len(df_filtered)} of {len(df)} total.")

    if df_filtered.empty:
        st.warning("No data to display with the current filters.")
    else:
        # 4.1 – Pie chart of tagged vs untagged resources
        if "Tagged" in df_filtered.columns:
            st.subheader("4.1 – Tagged vs Untagged Resources (Count)")
            tag_counts = df_filtered["Tagged"].value_counts().reset_index()
            tag_counts.columns = ["Tagged", "Count"]

            fig_pie = px.pie(
                tag_counts,
                names="Tagged",
                values="Count",
                hole=0.3,
                title="Tagged vs Untagged Resources",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # 4.2 – Bar chart: cost per department by tagging status
        if {"Department", "Tagged", "MonthlyCostUSD"}.issubset(df_filtered.columns):
            st.subheader("4.2 – Cost per Department by Tagging Status")

            dept_cost = (
                df_filtered.groupby(["Department", "Tagged"])["MonthlyCostUSD"]
                .sum()
                .reset_index()
            )

            fig_bar_dept = px.bar(
                dept_cost,
                x="Department",
                y="MonthlyCostUSD",
                color="Tagged",
                barmode="group",
                labels={"MonthlyCostUSD": "Total Cost (USD)"},
                title="Cost per Department by Tagging Status",
            )
            st.plotly_chart(fig_bar_dept, use_container_width=True)

        # 4.3 – Horizontal bar chart: total cost per service
        if {"Service", "MonthlyCostUSD"}.issubset(df_filtered.columns):
            st.subheader("4.3 – Total Cost per Service")

            svc_cost = (
                df_filtered.groupby("Service")["MonthlyCostUSD"]
                .sum()
                .reset_index()
            )

            fig_bar_svc = px.bar(
                svc_cost,
                x="MonthlyCostUSD",
                y="Service",
                orientation="h",
                labels={"MonthlyCostUSD": "Total Cost (USD)", "Service": "Service"},
                title="Total Cost per Service",
            )
            st.plotly_chart(fig_bar_svc, use_container_width=True)

        # 4.4 – Cost by environment (Prod, Dev, Test)
        if {"Environment", "MonthlyCostUSD"}.issubset(df_filtered.columns):
            st.subheader("4.4 – Cost by Environment (Prod, Dev, Test)")

            env_cost = (
                df_filtered.groupby("Environment")["MonthlyCostUSD"]
                .sum()
                .reset_index()
            )

            fig_env = px.bar(
                env_cost,
                x="Environment",
                y="MonthlyCostUSD",
                labels={"MonthlyCostUSD": "Total Cost (USD)", "Environment": "Environment"},
                title="Total Cost by Environment",
            )
            st.plotly_chart(fig_env, use_container_width=True)

    # --------------------------------------------------
    # Task Set 5 – Tag Remediation Workflow
    # --------------------------------------------------
    st.header("Task Set 5 – Tag Remediation Workflow")

    if "Tagged" not in df.columns:
        st.error(
            "Column 'Tagged' not found in the dataset; cannot perform remediation workflow."
        )
    elif "ResourceID" not in df.columns:
        st.error(
            "Column 'ResourceID' not found in the dataset; cannot safely merge edits back."
        )
    else:
        # 5.1 & 5.2 – Editable table for untagged resources (simulate remediation)
        st.subheader("5.1 & 5.2 – Edit Untagged Resources")

        untagged_original = df[df["Tagged"] == "No"].copy()

        if untagged_original.empty:
            st.write("There are no untagged resources to remediate.")
        else:
            # Add a unique RowID based on the original index
            untagged_original["RowID"] = untagged_original.index

            # Reuse tag_fields from Task Set 3 if available, otherwise infer basic tag fields
            try:
                current_tag_fields = tag_fields
            except NameError:
                candidate_tag_fields = [
                    "Department",
                    "Project",
                    "Environment",
                    "Owner",
                    "CostCenter",
                    "CreatedBy",
                ]
                current_tag_fields = [
                    c for c in candidate_tag_fields if c in df.columns
                ]

            editable_cols = [
                c for c in current_tag_fields if c in untagged_original.columns
            ]

            base_cols = ["RowID", "ResourceID"]
            if "MonthlyCostUSD" in untagged_original.columns:
                base_cols.append("MonthlyCostUSD")

            columns_for_editor = base_cols + editable_cols

            st.write("Update missing or incorrect tags directly in the table below:")
            edited_untagged = st.data_editor(
                untagged_original[columns_for_editor],
                num_rows="dynamic",
                key="untagged_editor",
            )

            # 5.3 – Download the updated (remediated) dataset
            st.subheader("5.3 – Download Updated Dataset (After Remediation)")

            # Build a remediated copy of the full dataset by updating tag columns using RowID (unique per row)
            df_remediated = df.copy()
            edited_for_update = edited_untagged.set_index("RowID")

            for col in editable_cols:
                if col in edited_for_update.columns and col in df_remediated.columns:
                    df_remediated.loc[edited_for_update.index, col] = edited_for_update[
                        col
                    ]

            # Write CSV (no RowID column)
            csv_buf_remediated = io.StringIO()
            df_remediated.to_csv(
                csv_buf_remediated,
                index=False,
                columns=[c for c in df_remediated.columns if c != "RowID"],
            )
            csv_bytes_remediated = csv_buf_remediated.getvalue().encode("utf-8")

            st.download_button(
                label="Download remediated_dataset.csv",
                data=csv_bytes_remediated,
                file_name="remediated_dataset.csv",
                mime="text/csv",
            )

            # 5.4 – Compare cost visibility before and after remediation
            st.subheader("5.4 – Cost Visibility: Before vs After Remediation")

            if "MonthlyCostUSD" in df.columns:
                # Before remediation
                before_total_cost = df["MonthlyCostUSD"].sum()
                before_untagged_cost = df.loc[
                    df["Tagged"] == "No", "MonthlyCostUSD"
                ].sum()
                before_untagged_resources = (df["Tagged"] == "No").sum()
                before_pct_untagged_cost = (
                    before_untagged_cost / before_total_cost * 100
                    if before_total_cost > 0
                    else 0.0
                )

                # After remediation: mark resources as tagged if all tag fields are now filled
                df_after = df_remediated.copy()

                if current_tag_fields:
                    completeness_mask = df_after[current_tag_fields].notnull().all(
                        axis=1
                    )
                    df_after.loc[completeness_mask, "Tagged"] = "Yes"

                after_total_cost = df_after["MonthlyCostUSD"].sum()
                after_untagged_cost = df_after.loc[
                    df_after["Tagged"] == "No", "MonthlyCostUSD"
                ].sum()
                after_untagged_resources = (df_after["Tagged"] == "No").sum()
                after_pct_untagged_cost = (
                    after_untagged_cost / after_total_cost * 100
                    if after_total_cost > 0
                    else 0.0
                )

                col_before, col_after = st.columns(2)

                with col_before:
                    st.markdown("**Before Remediation**")
                    st.metric("Untagged Cost (USD)", f"${before_untagged_cost:,.2f}")
                    st.metric("Untagged Cost (%)", f"{before_pct_untagged_cost:.2f}%")
                    st.metric(
                        "Untagged Resources (count)", int(before_untagged_resources)
                    )

                with col_after:
                    st.markdown("**After Remediation**")
                    st.metric("Untagged Cost (USD)", f"${after_untagged_cost:,.2f}")
                    st.metric("Untagged Cost (%)", f"{after_pct_untagged_cost:.2f}%")
                    st.metric(
                        "Untagged Resources (count)", int(after_untagged_resources)
                    )

                st.write(
                    "Use these metrics to explain in your report how improving tagging "
                    "reduces hidden (untagged) cost and increases accountability."
                )
            else:
                st.write(
                    "Column 'MonthlyCostUSD' not found; cannot compare cost visibility."
                )

            # 5.5 – Reflection prompt
            st.subheader("5.5 – Reflection")
            st.write(
                "Use this space to draft your short reflection for the report (text is not saved):"
            )
            st.text_area(
                "Reflection (copy-paste this into your report document):",
                height=150,
                placeholder=(
                    "Example ideas:\n"
                    "- How much did untagged cost decrease after remediation?\n"
                    "- Which departments or projects were most affected?\n"
                    "- Why is consistent tagging important for cost governance?"
                ),
            )

except FileNotFoundError:
    st.error(f"Error: File '{file_path}' not found.")
except Exception as e:
    st.error(f"An error occurred: {e}")