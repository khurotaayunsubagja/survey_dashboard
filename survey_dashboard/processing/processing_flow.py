import streamlit as st
import pandas as pd
import numpy as np
import io


# ============================================================
# MAIN FLOW
# ============================================================

def run_processing_flow(
    raw_df,
    analysis_df,
    metadata,
    platform
):


    tabs = st.tabs([
        "1. Data Overview",
        "2. Duplicate",
        "3. Routing Variable",
        "4. Crossing Tab",
        "5. Analyze Result",
        "6. Download Result"
    ])


    # ========================================================
    # TAB 1 — DATA OVERVIEW
    # ========================================================

    with tabs[0]:

        show_data_overview(
            raw_df,
            metadata,
            platform
        )


    # ========================================================
    # TAB 2 — DUPLICATE
    # ========================================================

    with tabs[1]:

        analysis_df = duplicate_section(
            analysis_df,
            metadata
        )

        st.session_state["analysis_df"] = analysis_df


    # ========================================================
    # TAB 3 — ROUTING
    # ========================================================

    with tabs[2]:

        routing_section(
            metadata
        )


    # ========================================================
    # TAB 4 — CROSSING TAB
    # ========================================================

    with tabs[3]:

        crosstab_section(
            analysis_df,
            metadata
        )


    # ========================================================
    # TAB 5 — ANALYZE RESULT
    # ========================================================

    with tabs[4]:

        analyze_section(
            analysis_df,
            metadata
        )


    # ========================================================
    # TAB 6 — DOWNLOAD
    # ========================================================

    with tabs[5]:

        download_section(
            raw_df,
            analysis_df,
            metadata
        )


# ============================================================
# DATA OVERVIEW
# ============================================================

def show_data_overview(
    raw_df,
    metadata,
    platform
):

    st.subheader("Data Overview")


    # --------------------------------------------------------
    # ROW COUNT
    # --------------------------------------------------------

    total_rows = len(raw_df)

    if platform == "SurveyMonkey":

        respondent_count = max(
            total_rows - 2,
            0
        )

    else:

        respondent_count = max(
            total_rows - 1,
            0
        )


    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Platform",
        platform
    )

    col2.metric(
        "Respondents",
        respondent_count
    )

    col3.metric(
        "Total Questions",
        len(metadata)
    )


    # --------------------------------------------------------
    # QUESTION OVERVIEW
    # --------------------------------------------------------

    st.markdown("### Question Overview")


    overview = []

    for item in metadata:

        overview.append({

            "Question":
                item["question"],

            "Type":
                item["type"],

            "Number of Options":
                len(item["options"])

        })


    st.dataframe(
        pd.DataFrame(overview),
        use_container_width=True
    )


    # --------------------------------------------------------
    # RAW PREVIEW
    # --------------------------------------------------------

    st.markdown("### Raw Data Preview")

    # PENTING:
    # raw_df langsung ditampilkan
    # sehingga SurveyMonkey tetap mempertahankan
    # struktur MultiIndex header.

    st.dataframe(
        raw_df.head(5),
        use_container_width=True
    )


# ============================================================
# DUPLICATE
# ============================================================

def duplicate_section(
    df,
    metadata
):

    st.subheader("Duplicate")


    # --------------------------------------------------------
    # LOGICAL QUESTION DROPDOWN
    # --------------------------------------------------------

    question_list = [
        item["question"]
        for item in metadata
    ]


    selected_keys = st.multiselect(
        "Pilih variabel duplicate key",
        question_list
    )


    if not selected_keys:

        st.info(
            "Pilih minimal satu variabel."
        )

        return df


    # --------------------------------------------------------
    # BUILD DUPLICATE KEY
    # --------------------------------------------------------

    temp_df = df.copy()

    key_columns = []


    for question in selected_keys:

        item = next(
            x for x in metadata
            if x["question"] == question
        )


        if item["type"] == "MA":

            # Semua option MA digunakan
            # sebagai bagian dari duplicate key

            ma_cols = [
                col
                for col in df.columns
                if col.startswith(
                    question + "__"
                )
            ]

            key_columns.extend(
                ma_cols
            )

        else:

            if question in df.columns:

                key_columns.append(
                    question
                )


    if not key_columns:

        st.warning(
            "Kolom duplicate key tidak ditemukan."
        )

        return df


    # --------------------------------------------------------
    # JANGAN ANGGAP BLANK SEBAGAI DUPLICATE
    # --------------------------------------------------------

    valid_key = temp_df[
        key_columns
    ].notna().any(axis=1)


    duplicate_mask = (
        temp_df[
            key_columns
        ]
        .fillna("")
        .astype(str)
        .astype(str)
        .duplicated(
            keep=False
        )
    )


    duplicate_mask = (
        duplicate_mask &
        valid_key
    )


    duplicate_rows = (
        temp_df[
            duplicate_mask
        ]
        .copy()
    )


    if duplicate_rows.empty:

        st.success(
            "Tidak ditemukan duplicate."
        )

        return df


    # --------------------------------------------------------
    # DUPLICATE GROUP
    # --------------------------------------------------------

    duplicate_rows[
        "_duplicate_group"
    ] = (
        duplicate_rows[
            key_columns
        ]
        .fillna("")
        .astype(str)
        .agg(
            " | ".join,
            axis=1
        )
    )


    st.write(
        f"Ditemukan "
        f"**{len(duplicate_rows)}** "
        f"baris duplicate."
    )


    # --------------------------------------------------------
    # PREVIEW
    # --------------------------------------------------------

    st.dataframe(
        duplicate_rows,
        use_container_width=True
    )


    # --------------------------------------------------------
    # ROW SELECTION
    # --------------------------------------------------------

    row_indices = duplicate_rows.index.tolist()


    selected_rows = st.multiselect(
        "Pilih row yang ingin dihapus",
        row_indices
    )


    if st.button(
        "🗑️ Execute Delete",
        key="delete_duplicate"
    ):

        if not selected_rows:

            st.warning(
                "Belum ada row yang dipilih."
            )

        else:

            df = df.drop(
                index=selected_rows
            ).reset_index(
                drop=True
            )

            st.success(
                f"{len(selected_rows)} "
                f"row berhasil dihapus."
            )

            st.rerun()


    return df


# ============================================================
# ROUTING VARIABLE
# ============================================================

def routing_section(metadata):

    st.subheader(
        "Routing Variable"
    )


    logical_questions = [
        item["question"]
        for item in metadata
    ]


    # Session state
    if "routing" not in st.session_state:

        st.session_state[
            "routing"
        ] = {}


    for item in metadata:

        question = item["question"]

        q_type = item["type"]

        st.markdown(
            f"### {question}"
        )

        st.caption(
            f"Type: {q_type}"
        )


        # ----------------------------------------------------
        # BASE QUESTION
        # ----------------------------------------------------

        base_options = [
            "Semua Responden"
        ] + logical_questions


        base = st.selectbox(
            "Base / Routing Question",
            base_options,
            key=f"routing_base_{question}"
        )


        # ----------------------------------------------------
        # ROUTING VALUE
        # ----------------------------------------------------

        if base != "Semua Responden":

            base_item = next(
                x for x in metadata
                if x["question"] == base
            )


            routing_values = (
                base_item["options"]
            )


            values = st.multiselect(
                "Pilih routing value",
                routing_values,
                key=f"routing_values_{question}"
            )

        else:

            values = []


        st.session_state[
            "routing"
        ][question] = {

            "base":
                base,

            "values":
                values
        }


# ============================================================
# CROSSING TAB
# ============================================================

def crosstab_section(
    df,
    metadata
):

    st.subheader(
        "Crossing Tab"
    )


    # --------------------------------------------------------
    # BUILD CROSSING OPTIONS
    # --------------------------------------------------------

    crossing_options = []


    for item in metadata:

        question = item["question"]

        if item["type"] == "MA":

            # MA → OPTION TERPISAH

            for option in item["options"]:

                crossing_options.append({
                    "label":
                        f"{question} - {option}",

                    "question":
                        question,

                    "type":
                        "MA",

                    "option":
                        option
                })

        else:

            crossing_options.append({
                "label":
                    question,

                "question":
                    question,

                "type":
                    "SA",

                "option":
                    None
            })


    labels = [
        x["label"]
        for x in crossing_options
    ]


    # --------------------------------------------------------
    # ROW / COLUMN
    # --------------------------------------------------------

    row_label = st.selectbox(
        "Row Variable",
        labels,
        key="cross_row"
    )


    col_label = st.selectbox(
        "Column Variable",
        labels,
        key="cross_col"
    )


    row_var = next(
        x for x in crossing_options
        if x["label"] == row_label
    )


    col_var = next(
        x for x in crossing_options
        if x["label"] == col_label
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    row_type = row_var["type"]
    col_type = col_var["type"]


    # MA × MA
    if row_type == "MA" and col_type == "MA":

        st.error(
            "Crosstab MA × MA tidak dapat dilakukan. "
            "Silakan pilih kombinasi SA × SA "
            "atau SA × MA."
        )

        return


    # MA × SA
    if row_type == "MA" and col_type == "SA":

        st.warning(
            "Gunakan SA sebagai Row Variable "
            "dan MA sebagai Column Variable."
        )

        return


    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    metrics = st.multiselect(
        "Pilih hasil yang ditampilkan",
        [
            "Absolute",
            "Percentage"
        ],
        default=[
            "Absolute",
            "Percentage"
        ]
    )


    if st.button(
        "Generate Crosstab",
        key="generate_crosstab"
    ):

        result = calculate_crosstab(
            df,
            row_var,
            col_var,
            metadata
        )


        st.session_state[
            "crosstab_result"
        ] = result


    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    if (
        "crosstab_result"
        in st.session_state
    ):

        result = (
            st.session_state[
                "crosstab_result"
            ]
        )


        st.dataframe(
            result,
            use_container_width=True
        )


# ============================================================
# CALCULATE CROSSTAB
# ============================================================

def calculate_crosstab(
    df,
    row_var,
    col_var,
    metadata
):

    # --------------------------------------------------------
    # ROW
    # --------------------------------------------------------

    if row_var["type"] == "SA":

        row_series = df[
            row_var["question"]
        ].fillna("Blank")

    else:

        row_col = (
            f'{row_var["question"]}__'
            f'{row_var["option"]}'
        )

        row_series = df[
            row_col
        ]


    # --------------------------------------------------------
    # COLUMN
    # --------------------------------------------------------

    if col_var["type"] == "SA":

        col_series = df[
            col_var["question"]
        ].fillna("Blank")


    else:

        col_col = (
            f'{col_var["question"]}__'
            f'{col_var["option"]}'
        )

        col_series = df[
            col_col
        ]


    # --------------------------------------------------------
    # SA × SA
    # --------------------------------------------------------

    if (
        row_var["type"] == "SA"
        and
        col_var["type"] == "SA"
    ):

        result = pd.crosstab(
            row_series,
            col_series
        )


    # --------------------------------------------------------
    # SA × MA
    # --------------------------------------------------------

    elif (
        row_var["type"] == "SA"
        and
        col_var["type"] == "MA"
    ):

        temp = pd.DataFrame({

            "row":
                row_series,

            "ma":
                col_series

        })


        result = pd.crosstab(
            temp["row"],
            temp["ma"]
        )


    else:

        return pd.DataFrame()


    return result


# ============================================================
# ANALYZE RESULT
# ============================================================

def analyze_section(
    df,
    metadata
):

    st.subheader(
        "Analyze Result"
    )


    question_options = [
        item["question"]
        for item in metadata
    ]


    selected_question = st.selectbox(
        "Pilih pertanyaan",
        question_options
    )


    item = next(
        x for x in metadata
        if x["question"]
        == selected_question
    )


    metrics = st.multiselect(
        "Pilih metric",
        [
            "Absolute",
            "Percentage",
            "Average"
        ],
        default=[
            "Absolute",
            "Percentage"
        ]
    )


    # --------------------------------------------------------
    # OPEN
    # --------------------------------------------------------

    if item["type"] == "Open":

        st.info(
            "Pertanyaan Open Feedback "
            "ditampilkan pada bagian Download Result."
        )

        return


    # --------------------------------------------------------
    # MA
    # --------------------------------------------------------

    if item["type"] == "MA":

        rows = []

        for option in item["options"]:

            clean_option = str(option)

            col = (
                f"{selected_question}__"
                f"{clean_option}"
            )

            if col not in df.columns:

                continue


            absolute = (
                df[col]
                .sum()
            )


            rows.append({

                "Option":
                    option,

                "Absolute":
                    absolute

            })


        result = pd.DataFrame(rows)


    # --------------------------------------------------------
    # SA
    # --------------------------------------------------------

    else:

        series = df[
            selected_question
        ]


        result = (
            series
            .value_counts(
                dropna=False
            )
            .reset_index()
        )


        result.columns = [
            "Option",
            "Absolute"
        ]


    # --------------------------------------------------------
    # PERCENTAGE
    # --------------------------------------------------------

    if "Percentage" in metrics:

        total = result[
            "Absolute"
        ].sum()

        if total > 0:

            result[
                "Percentage"
            ] = (
                result["Absolute"]
                / total
                * 100
            ).round(1)


    # --------------------------------------------------------
    # AVERAGE
    # --------------------------------------------------------

    if "Average" in metrics:

        if item["type"] == "SA":

            numeric = pd.to_numeric(
                df[selected_question],
                errors="coerce"
            )

            result[
                "Average"
            ] = numeric.mean()


    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    st.dataframe(
        result,
        use_container_width=True
    )


    # --------------------------------------------------------
    # SIMPLE CHART
    # --------------------------------------------------------

    if not result.empty:

        chart_data = result.set_index(
            "Option"
        )["Absolute"]

        st.bar_chart(
            chart_data
        )


# ============================================================
# DOWNLOAD
# ============================================================

def download_section(
    raw_df,
    analysis_df,
    metadata
):

    st.subheader(
        "Download Result"
    )


    # --------------------------------------------------------
    # VARIABLE ANALYSIS
    # --------------------------------------------------------

    variable_results = []


    for item in metadata:

        question = item["question"]

        if item["type"] == "MA":

            for option in item["options"]:

                col = (
                    f"{question}__{option}"
                )

                if col not in analysis_df.columns:

                    continue


                absolute = (
                    analysis_df[col]
                    .sum()
                )


                variable_results.append({

                    "Question":
                        question,

                    "Option":
                        option,

                    "Type":
                        "MA",

                    "Absolute":
                        absolute

                })


        else:

            if question not in analysis_df.columns:

                continue


            series = (
                analysis_df[
                    question
                ]
                .dropna()
            )


            counts = (
                series
                .value_counts()
            )


            for option, count in counts.items():

                variable_results.append({

                    "Question":
                        question,

                    "Option":
                        option,

                    "Type":
                        item["type"],

                    "Absolute":
                        count

                })


    variable_analysis = pd.DataFrame(
        variable_results
    )


    # --------------------------------------------------------
    # OPEN FEEDBACK
    # --------------------------------------------------------

    open_feedback = []


    for item in metadata:

        if item["type"] != "Open":

            continue


        question = item["question"]


        if question not in analysis_df.columns:

            continue


        for value in analysis_df[
            question
        ].dropna():

            value = str(value).strip()


            if value:

                open_feedback.append({

                    "Question":
                        question,

                    "Open Feedback":
                        value

                })


    open_feedback_df = pd.DataFrame(
        open_feedback
    )


    # --------------------------------------------------------
    # EXCEL
    # --------------------------------------------------------

    output = io.BytesIO()


    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:


        # Sheet 1
        raw_df.to_excel(
            writer,
            sheet_name="1_Raw_Data"
        )


        # Sheet 2
        variable_analysis.to_excel(
            writer,
            sheet_name="2_Variable_Analysis",
            index=False
        )


        # Sheet 3
        crosstab_result = (
            st.session_state.get(
                "crosstab_result"
            )
        )


        if crosstab_result is not None:

            crosstab_result.to_excel(
                writer,
                sheet_name="3_Crosstab"
            )

        else:

            pd.DataFrame().to_excel(
                writer,
                sheet_name="3_Crosstab"
            )


        # Sheet 4
        open_feedback_df.to_excel(
            writer,
            sheet_name="4_Open_Feedback",
            index=False
        )


    output.seek(0)


    st.download_button(
        label="📥 Download Excel",
        data=output,
        file_name="survey_result.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )