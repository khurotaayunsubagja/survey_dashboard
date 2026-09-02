import streamlit as st

from processing.data_loader import load_survey_data
from processing.processing_flow import run_processing_flow


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Survey Data Processing",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Survey Data Processing Dashboard")

st.write(
    "Dashboard untuk preprocessing, routing, crossing tab, "
    "analysis, dan export hasil survey."
)


# ============================================================
# PLATFORM SELECTION
# ============================================================

platform = st.selectbox(
    "Pilih Platform Survey",
    [
        "SurveyMonkey",
        "Google Forms"
    ]
)


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "Upload file Excel",
    type=["xlsx", "xls"]
)


# ============================================================
# LOAD DATA
# ============================================================

if uploaded_file:

    try:

        raw_df, analysis_df, metadata = load_survey_data(
            uploaded_file,
            platform
        )

        st.success("Data berhasil dimuat.")

        # Simpan ke session state
        st.session_state["raw_df"] = raw_df
        st.session_state["analysis_df"] = analysis_df
        st.session_state["metadata"] = metadata
        st.session_state["platform"] = platform

    except Exception as e:

        st.error(f"Terjadi error saat membaca file: {e}")


# ============================================================
# RUN MAIN PROCESSING
# ============================================================

if "analysis_df" in st.session_state:

    run_processing_flow(
        raw_df=st.session_state["raw_df"],
        analysis_df=st.session_state["analysis_df"],
        metadata=st.session_state["metadata"],
        platform=st.session_state["platform"]
    )