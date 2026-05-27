import streamlit as st
import pandas as pd
import os
import psycopg2

# 1. Page Config
st.set_page_config(page_title="FinTech Credit Analytics Engine", layout="wide")
st.title("📊 FinTech Credit Risk Analytics Platform")

# DB Config from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "fintech_analytics")


def write_dataframe_to_postgres(df: pd.DataFrame):
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS credit_analytics (
            customer_id INTEGER,
            income NUMERIC,
            monthly_debt NUMERIC,
            credit_score INTEGER,
            employment_years INTEGER,
            dti DOUBLE PRECISION,
            status TEXT,
            interest_rate DOUBLE PRECISION
        );
        """
    )
    insert_query = """
        INSERT INTO credit_analytics (
            customer_id, income, monthly_debt, credit_score, employment_years, dti, status, interest_rate
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
    for row in df.to_records(index=False):
        cursor.execute(insert_query, tuple(row))
    conn.commit()
    cursor.close()
    conn.close()


# 2. Sidebar: Batch Data Generator
st.sidebar.header("📥 Simulate Financial Batch Ingestion")
if st.sidebar.button("Generate Sample Bulk Data"):
    mock_data = pd.DataFrame({
        "customer_id": [101, 102, 103, 104, 105],
        "income": [45000, 120000, 30000, 85000, 60000],
        "monthly_debt": [2000, 1500, 1800, 2500, 4000],
        "credit_score": [550, 740, 620, 680, 580],
        "employment_years": [1, 5, 2, 4, 0]
    })
    st.session_state['batch_df'] = mock_data


# 3. Main Body Pipeline
if 'batch_df' in st.session_state:
    st.subheader("📋 Ingested Raw Financial Records")
    st.dataframe(st.session_state['batch_df'], use_container_width=True)

    if st.button("🚀 Run Analytics Pipeline"):
        with st.spinner("Running analytics transformations..."):
            processed_pdf = st.session_state['batch_df'].copy()
            processed_pdf['dti'] = processed_pdf['monthly_debt'] / (processed_pdf['income'] / 12)
            processed_pdf['status'] = processed_pdf.apply(
                lambda row: "Rejected" if (row['credit_score'] < 600 or row['dti'] > 0.45) else "Approved",
                axis=1
            )
            processed_pdf['interest_rate'] = 0.0
            approved_mask = processed_pdf['status'] == "Approved"
            processed_pdf.loc[approved_mask, 'interest_rate'] = 0.05 + (0.10 * processed_pdf.loc[approved_mask, 'dti'])

            st.success("✅ Analytics pipeline completed successfully with pandas.")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Records Processed", len(processed_pdf))
                st.subheader("Processed Results")
                st.dataframe(processed_pdf, use_container_width=True)

            with col2:
                st.subheader("Risk Status Distribution")
                st.bar_chart(processed_pdf['status'].value_counts())

            try:
                write_dataframe_to_postgres(processed_pdf)
                st.info("💾 Analytics data successfully logged to AWS RDS.")
            except Exception as e:
                st.warning(f"Database write skipped or failed: {e}")


# 4. History Tab
st.markdown("---")
st.subheader("📜 Historical Database Records (Live from AWS RDS)")
if st.button("Fetch Audit Logs"):
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        query = "SELECT * FROM credit_analytics ORDER BY customer_id DESC LIMIT 10;"
        history_df = pd.read_sql(query, conn)
        st.dataframe(history_df, use_container_width=True)
        conn.close()
    except Exception as e:
        st.error(f"Could not connect to database history: {e}")