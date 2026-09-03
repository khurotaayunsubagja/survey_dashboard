import streamlit as st
import pandas as pd
import textwrap
from io import BytesIO

from processing.data_loader import (
    load_survey_data
)

from processing.processing_flow import (
    get_question_metadata,
    get_filtered_df,
    calculate_variable_analysis,
    calculate_crosstab,
    collect_open_feedback,
    detect_open_duplicates
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Survey Insight Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    textwrap.dedent(
        """
        <style>

        /* =========================
           GLOBAL
        ========================= */

        .main {
            background-color: #f7f8fc;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        /* =========================
           HEADER
        ========================= */

        .hero {
            padding: 28px 32px;
            border-radius: 20px;
            background: linear-gradient(
                135deg,
                #667eea 0%,
                #764ba2 100%
            );
            color: white;
            margin-bottom: 25px;
            box-shadow:
                0 10px 30px rgba(
                    102,
                    126,
                    234,
                    0.25
                );
        }

        .hero-title {
            font-size: 34px;
            font-weight: 800;
            margin-bottom: 6px;
        }

        .hero-subtitle {
            font-size: 15px;
            opacity: 0.9;
        }

        /* =========================
           KPI CARDS
        ========================= */

        .metric-card {
            padding: 20px;
            border-radius: 18px;
            background: white;
            border: 1px solid #e9eaf0;
            box-shadow:
                0 6px 20px rgba(
                    0,
                    0,
                    0,
                    0.05
                );
        }

        .metric-label {
            font-size: 13px;
            color: #777;
            font-weight: 600;
            margin-bottom: 7px;
        }

        .metric-value {
            font-size: 28px;
            font-weight: 800;
            color: #222;
            line-height:1.15;
            overflow-wrap:anywhere;
        }

        /* =========================
           SECTION CARD
        ========================= */

        .section-card {
            background: white;
            padding: 22px;
            border-radius: 18px;
            border: 1px solid #e9eaf0;
            margin-bottom: 20px;
            box-shadow:
                0 5px 18px rgba(
                    0,
                    0,
                    0,
                    0.04
                );
        }

        /* =========================
           BADGES
        ========================= */

        .badge {
            display: inline-block;
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            margin-right: 5px;
        }

        .badge-sa {
            background: #e8f0ff;
            color: #315ecb;
        }

        .badge-ma {
            background: #e9f8ef;
            color: #24854d;
        }

        .badge-open {
            background: #fff3df;
            color: #b86b00;
        }

        /* =========================
           INFO BOX
        ========================= */

        .info-box {
            padding: 15px 18px;
            border-radius: 14px;
            background: #f0f4ff;
            border-left: 5px solid #667eea;
            margin: 12px 0;
        }

        /* =========================
           DIVIDER
        ========================= */

        hr {
            border: none;
            border-top: 1px solid #ececf2;
            margin: 25px 0;
        }

        /* =========================
           SIDEBAR
        ========================= */

        section[data-testid="stSidebar"] {
            background-color: #ffffff;
        }

        /* =========================
           BUTTON
        ========================= */

        .stButton > button {
            border-radius: 12px;
            font-weight: 700;
            min-height: 42px;
        }

        /* =========================
           DATAFRAME
        ========================= */

        [data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
        }

        /* =========================
           ANALYZE RESULT
        ========================= */

        .analysis-card {
            background: white;
            padding: 14px 18px;
            border-radius: 16px;
            border: 1px solid #e9eaf0;
            margin-bottom: 12px;
            box-shadow:
                0 4px 14px rgba(
                    0,
                    0,
                    0,
                    0.035
                );
        }

        .analysis-question {
            font-size: 16px;
            font-weight: 750;
            margin-bottom: 3px;
        }

        .analysis-small {
            font-size: 12px;
            color: #777;
        }

        .feedback-box {
            background: #fafbff;
            border: 1px solid #e9eaf0;
            border-radius: 12px;
            padding: 12px 15px;
            margin-bottom: 8px;
        }

        </style>
        """
    ),
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {

    "raw_df": None,

    "analysis_df": None,

    "metadata": None,

    "respondent_count": 0,

    "platform": None,

    "data_loaded": False,

    "active_questions": [],

    "removed_questions": [],

    "routing_config": {},

    "applied_routing_config": {},

    "duplicate_question": None,

    "duplicate_df": None,

    "crosstab_results": [],

    "variable_analysis_result": {}

}


for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# HERO
# ============================================================

st.html("""
<div class="hero">

    <div class="hero-title">
        📊 Survey Insight Dashboard
    </div>

    <div class="hero-subtitle">
        Clean your survey data, detect duplicates,
        configure routing, explore crosstabs,
        and generate analysis-ready reports.
    </div>

</div>
""")


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## ⚙️ Data Setup")

    st.caption(
        "Upload your survey dataset to begin."
    )

    platform = st.selectbox(
        "Survey Platform",
        [
            "SurveyMonkey",
            "Google Forms"
        ]
    )

    uploaded_file = st.file_uploader(
        "Upload Excel File",
        type=[
            "xlsx",
            "xls"
        ]
    )

    load_button = st.button(
        "🚀 Load Data",
        type="primary",
        use_container_width=True
    )

    st.divider()

    if st.session_state["data_loaded"]:

        st.success("Dataset loaded")

        st.caption(
            f"Platform: "
            f"{st.session_state['platform']}"
        )

        st.caption(
            f"Respondents: "
            f"{st.session_state['respondent_count']:,}"
        )


# ============================================================
# LOAD DATA
# ============================================================

if load_button:

    if uploaded_file is None:

        st.warning(
            "Please upload an Excel file first."
        )

    else:

        try:

            (
                raw_df,
                analysis_df,
                metadata,
                respondent_count
            ) = load_survey_data(
                uploaded_file,
                platform
            )

            st.session_state["raw_df"] = raw_df
            st.session_state["analysis_df"] = analysis_df
            st.session_state["metadata"] = metadata
            st.session_state["respondent_count"] = respondent_count
            st.session_state["platform"] = platform
            st.session_state["data_loaded"] = True

            st.session_state["active_questions"] = [
                item["question"]
                for item in metadata
            ]

            st.session_state["removed_questions"] = []
            st.session_state["routing_config"] = {}
            st.session_state["applied_routing_config"] = {}
            st.session_state["duplicate_question"] = None
            st.session_state["duplicate_df"] = None
            st.session_state["crosstab_results"] = []
            st.session_state["variable_analysis_result"] = {}

            st.success(
                "Data loaded successfully."
            )

            st.rerun()

        except Exception as e:

            st.error(
                f"Failed to load data: {e}"
            )


# ============================================================
# REQUIRE DATA
# ============================================================

if not st.session_state["data_loaded"]:

    st.info(
        "Upload a survey Excel file and click "
        "'Load Data' to start."
    )

    st.stop()


# ============================================================
# VARIABLES
# ============================================================

raw_df = st.session_state["raw_df"]
analysis_df = st.session_state["analysis_df"]
metadata = st.session_state["metadata"]


# ============================================================
# TAB NAVIGATION
# ============================================================

tabs = st.tabs(
    [
        "🏠 Overview",
        "🔍 Duplicate",
        "🔀 Routing",
        "📊 Crosstab",
        "📈 Analyze Result",
        "📥 Download"
    ]
)


# ============================================================
# TAB 1 — OVERVIEW
# ============================================================

with tabs[0]:

    st.header("Data Overview")

    total_questions = len(metadata)

    active_questions = len(
        st.session_state["active_questions"]
    )

    open_questions = sum(
        1
        for item in metadata
        if item["type"] == "Open"
    )

    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        (
            col1,
            "Platform",
            st.session_state["platform"]
        ),
        (
            col2,
            "Respondents",
            f"{st.session_state['respondent_count']:,}"
        ),
        (
            col3,
            "Questions",
            f"{total_questions}"
        ),
        (
            col4,
            "Open Questions",
            f"{open_questions}"
        )
    ]

    for column, label, value in metrics:

        with column:

            st.html(
                    f"""
                    <div class="metric-card">

                        <div class="metric-label">
                            {label}
                        </div>

                        <div class="metric-value">
                            {value}
                        </div>

                    </div>
                    """
                )

    st.write("")

    st.markdown(
        textwrap.dedent(
            f"""
            <div class="info-box">
                <b>{active_questions}</b>
                active variables are currently included
                in the analysis.
            </div>
            """
        ),
        unsafe_allow_html=True
    )

    st.subheader("Question Overview")

    overview_rows = []

    for item in metadata:

        overview_rows.append(
            {
                "Question": item["question"],
                "Type": item["type"],
                "Number of Options": len(
                    item.get("options", [])
                ),
                "Active":
                    "Yes"
                    if item["question"]
                    in st.session_state[
                        "active_questions"
                    ]
                    else "No"
            }
        )

    overview_df = pd.DataFrame(
        overview_rows
    )

    st.dataframe(
        overview_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("Raw Data Preview")

    st.caption(
        "This preview preserves the original "
        "uploaded data structure."
    )

    st.dataframe(
        raw_df,
        use_container_width=True,
        height=420
    )


# ============================================================
# TAB 2 — DUPLICATE
# ============================================================

with tabs[1]:

    st.header("🔍 Duplicate Detection")

    st.html(
            """
            <div class="info-box" style="margin-top:0px;">

                <b>
                    Duplicate detection is only available
                    for Open-ended questions.
                </b>

                <br>

                SA and MA questions are excluded because
                their responses are already structured.

            </div>
            """
        )

    open_questions = [
        item["question"]
        for item in metadata
        if item["type"] == "Open"
    ]

    if not open_questions:

        st.info(
            "No Open-ended questions are available "
            "for duplicate detection."
        )

    else:

        selected_question = st.selectbox(
            "Select Open Question",
            [
                "Select a question"
            ] + open_questions
        )

        if st.button(
            "🔎 Detect Duplicates",
            type="primary",
            use_container_width=True
        ):

            if selected_question == "Select a question":

                st.warning(
                    "Please select an Open-ended question first."
                )

            else:

                item = get_question_metadata(
                    metadata,
                    selected_question
                )

                duplicate_df = detect_open_duplicates(
                    st.session_state["analysis_df"],
                    item
                )

                st.session_state["duplicate_question"] = (
                    selected_question
                )

                st.session_state["duplicate_df"] = (
                    duplicate_df
                )

                if duplicate_df.empty:

                    st.success(
                        "No duplicate responses were found."
                    )

                else:

                    group_count = (
                        duplicate_df[
                            "Duplicate Group"
                        ].nunique()
                    )

                    row_count = len(
                        duplicate_df
                    )

                    st.success(
                        f"{row_count} duplicate row(s) "
                        f"found across "
                        f"{group_count} duplicate group(s)."
                    )

        # ====================================================
        # RESULT
        # ====================================================

        duplicate_df = st.session_state[
            "duplicate_df"
        ]

        if (
            duplicate_df is not None
            and not duplicate_df.empty
        ):

            st.divider()

            st.subheader(
                "Duplicate Responses"
            )

            group_count = (
                duplicate_df[
                    "Duplicate Group"
                ].nunique()
            )

            row_count = len(
                duplicate_df
            )

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "Duplicate Rows",
                    row_count
                )

            with col2:

                st.metric(
                    "Duplicate Groups",
                    group_count
                )

            st.caption(
                "Text is normalized before comparison. "
                "Capitalization and extra spaces are ignored. "
                "Blank responses are excluded."
            )

            display_df = duplicate_df[
                [
                    "_original_index",
                    "Response",
                    "Duplicate Group",
                    "Duplicate Count"
                ]
            ].copy()

            # Remove rows where Response has no actual value
            display_df = display_df[
                display_df["Response"].notna()
            ]

            display_df = display_df[
                display_df["Response"]
                .astype(str)
                .str.strip()
                .ne("")
            ]

            display_df["Row"] = (
                display_df["_original_index"] + 1
            )

            display_df = display_df[
                [
                    "Row",
                    "Response",
                    "Duplicate Group",
                    "Duplicate Count"
                ]
            ]

            if not display_df.empty:

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )

            else:

                st.info(
                    "No duplicate rows with actual response "
                    "values are available."
                )

            st.divider()

            st.subheader(
                "Select Rows to Delete"
            )

            available_indices = (
                duplicate_df[
                    "_original_index"
                ].tolist()
            )

            selected_rows = st.multiselect(
                "Rows",
                options=available_indices,
                format_func=lambda index:
                    (
                        f"Row {index + 1} — "
                        f"{str(
                            duplicate_df.loc[
                                index,
                                'Response'
                            ]
                        )[:100]}"
                    )
            )

            if selected_rows:

                st.warning(
                    f"{len(selected_rows)} row(s) "
                    f"selected for deletion."
                )

            if st.button(
                "🗑️ Execute Delete",
                type="primary",
                use_container_width=True
            ):

                if not selected_rows:

                    st.warning(
                        "Please select at least one row to delete."
                    )

                else:

                    before_count = len(
                        st.session_state["analysis_df"]
                    )

                    st.session_state["analysis_df"] = (
                        st.session_state["analysis_df"]
                        .drop(
                            index=selected_rows,
                            errors="ignore"
                        )
                    )

                    after_count = len(
                        st.session_state["analysis_df"]
                    )

                    deleted_count = (
                        before_count - after_count
                    )

                    st.session_state[
                        "duplicate_df"
                    ] = None

                    st.success(
                        f"{deleted_count} respondent(s) "
                        f"deleted successfully."
                    )

                    st.subheader(
                        "Cleaned Data Preview"
                    )

                    st.dataframe(
                        st.session_state[
                            "analysis_df"
                        ],
                        use_container_width=True,
                        height=400
                    )


# ============================================================
# TAB 3 — ROUTING
# ============================================================

with tabs[2]:

    st.header("🔀 Routing Variable")

    st.caption(
        "Configure which respondents should be included "
        "for each active variable."
    )

    if st.session_state["removed_questions"]:

        st.subheader("Restore Variables")

        restore_question = st.selectbox(
            "Select a variable",
            [
                "Select a variable"
            ] + st.session_state[
                "removed_questions"
            ]
        )

        if st.button(
            "↩️ Restore Variable",
            use_container_width=True
        ):

            if restore_question != "Select a variable":

                st.session_state[
                    "active_questions"
                ].append(
                    restore_question
                )

                st.session_state[
                    "removed_questions"
                ].remove(
                    restore_question
                )

                st.success(
                    "Variable restored successfully."
                )

                st.rerun()

    st.divider()

    routing_config = {}

    for index, question in enumerate(
        st.session_state["active_questions"]
    ):

        item = get_question_metadata(
            metadata,
            question
        )

        if item is None:
            continue

        st.html(
                f"""
                <div class="section-card">

                    <b>{question}</b>

                </div>
                """
            )

        col1, col2 = st.columns([6, 1])

        with col1:

            st.markdown(
                textwrap.dedent(
                    f"""
                    <span class="badge badge-{item['type'].lower()}">
                        {item['type']}
                    </span>
                    """
                ),
                unsafe_allow_html=True
            )

        with col2:

            remove_key = (
                f"remove_question_{index}"
            )

            if st.button(
                "✕",
                key=remove_key
            ):

                st.session_state[
                    "active_questions"
                ].remove(question)

                st.session_state[
                    "removed_questions"
                ].append(question)

                st.rerun()

        base_options = [
            "All Respondents"
        ] + [
            x["question"]
            for x in metadata
            if x["question"] != question
        ]

        selected_base = st.selectbox(
            "Base Variable",
            base_options,
            key=f"routing_base_{index}"
        )

        if selected_base == "All Respondents":

            routing_config[question] = {
                "base_question":
                    "All Respondents",
                "values":
                    []
            }

        else:

            base_item = get_question_metadata(
                metadata,
                selected_base
            )

            if base_item is None:
                continue

            if base_item["type"] in ["SA", "MA"]:

                selected_values = st.multiselect(
                    "Routing Values",
                    base_item["options"],
                    key=f"routing_values_{index}"
                )

                routing_config[question] = {
                    "base_question":
                        selected_base,
                    "values":
                        selected_values
                }

            else:

                st.warning(
                    "Open-ended questions cannot be used "
                    "as routing variables."
                )

                routing_config[question] = {
                    "base_question":
                        "All Respondents",
                    "values":
                        []
                }

        st.divider()

    st.session_state[
        "routing_config"
    ] = routing_config

    if st.button(
        "✅ Apply Routing",
        type="primary",
        use_container_width=True
    ):

        st.session_state[
            "applied_routing_config"
        ] = routing_config.copy()

        st.success(
            "Routing configuration applied successfully."
        )

    if st.session_state[
        "applied_routing_config"
    ]:

        st.subheader(
            "Applied Routing Configuration"
        )

        summary_rows = []

        for question, config in (
            st.session_state[
                "applied_routing_config"
            ].items()
        ):

            summary_rows.append(
                {
                    "Question":
                        question,

                    "Base Variable":
                        config.get(
                            "base_question",
                            "All Respondents"
                        ),

                    "Routing Values":
                        ", ".join(
                            config.get(
                                "values",
                                []
                            )
                        )
                        or "All Respondents"
                }
            )

        st.dataframe(
            pd.DataFrame(summary_rows),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TAB 4 — CROSSTAB
# ============================================================

with tabs[3]:

    st.header("📊 Crosstab")

    st.caption(
        "Create up to 10 crosstab configurations."
    )

    crosstab_configs = []

    for index in range(10):

        st.html(
                f"""
                <div class="section-card">

                    <b>Crosstab {index + 1}</b>

                </div>
                """
            )
        # ----------------------------------------------------
        # CUSTOM NAME
        # ----------------------------------------------------

        crosstab_name = st.text_input(
            "Crosstab Name",
            value=f"Crosstab {index + 1}",
            key=f"ct_name_{index}"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            row_question = st.selectbox(
                "Row Variable",
                [
                    "Select Variable"
                ] + st.session_state[
                    "active_questions"
                ],
                key=f"ct_row_{index}"
            )

        with col2:

            column_question = st.selectbox(
                "Column Variable",
                [
                    "Select Variable"
                ] + st.session_state[
                    "active_questions"
                ],
                key=f"ct_column_{index}"
            )

        with col3:

            metric = st.selectbox(
                "Metric",
                [
                    "Absolute",
                    "Percentage"
                ],
                key=f"ct_metric_{index}"
            )

        column_option = None

        if column_question != "Select Variable":

            column_item = get_question_metadata(
                metadata,
                column_question
            )

            if (
                column_item
                and column_item["type"] == "MA"
            ):

                column_option = st.selectbox(
                    "MA Option",
                    column_item["options"],
                    key=f"ct_ma_option_{index}"
                )

        if (
            row_question != "Select Variable"
            and column_question != "Select Variable"
        ):

            row_item = get_question_metadata(
                metadata,
                row_question
            )

            column_item = get_question_metadata(
                metadata,
                column_question
            )

            row_type = row_item["type"]
            column_type = column_item["type"]

            if (
                row_type == "MA"
                and column_type == "MA"
            ):

                st.error(
                    "MA × MA analysis cannot be performed."
                )

            elif (
                row_type == "MA"
                and column_type == "SA"
            ):

                st.warning(
                    "MA × SA is not supported. "
                    "Please use SA as Row Variable "
                    "and MA as Column Variable."
                )

            elif (
                row_type == "Open"
                or column_type == "Open"
            ):

                st.warning(
                    "Open-ended questions cannot be used "
                    "in a crosstab."
                )

            elif (
                row_type == "SA"
                and column_type in ["SA", "MA"]
            ):

                crosstab_configs.append(
                    {
                        "name":
                            crosstab_name.strip()
                            or f"Crosstab {index + 1}",

                        "row_question":
                            row_question,

                        "column_question":
                            column_question,

                        "column_option":
                            column_option,

                        "metric":
                            metric
                    }
                )

    st.divider()

    if st.button(
        "🚀 Apply All Crosstabs",
        type="primary",
        use_container_width=True
    ):

        results = []

        for config in crosstab_configs:

            row_item = get_question_metadata(
                metadata,
                config["row_question"]
            )

            column_item = get_question_metadata(
                metadata,
                config["column_question"]
            )

            filtered_df = get_filtered_df(
                st.session_state["analysis_df"],
                config["row_question"],
                metadata,
                st.session_state[
                    "applied_routing_config"
                ]
            )

            try:

                result = calculate_crosstab(
                    filtered_df,
                    row_item,
                    column_item,
                    config["column_option"]
                )

                results.append(
                    {
                        **config,
                        "result":
                            result
                    }
                )

            except ValueError as error:

                st.error(str(error))

        st.session_state[
            "crosstab_results"
        ] = results

        st.success(
            f"{len(results)} crosstab(s) "
            f"applied successfully."
        )


# ============================================================
# TAB 5 — ANALYZE RESULT
# ============================================================

with tabs[4]:

    st.header("📈 Analyze Result")

    st.caption(
        "Final analysis dashboard based on active variables, "
        "routing configuration, and cleaned respondents."
    )

    # ========================================================
    # CALCULATE ALL RESULTS
    # ========================================================

    all_results = {}

    total_final_base = 0

    for question in st.session_state[
        "active_questions"
    ]:

        item = get_question_metadata(
            metadata,
            question
        )

        if item is None:
            continue

        filtered_df = get_filtered_df(
            st.session_state["analysis_df"],
            question,
            metadata,
            st.session_state[
                "applied_routing_config"
            ]
        )

        result = calculate_variable_analysis(
            filtered_df,
            item
        )

        all_results[question] = result

        total_final_base += result["base_n"]

    st.session_state[
        "variable_analysis_result"
    ] = all_results

    # ========================================================
    # DASHBOARD SCORE CARDS
    # ========================================================

    st.subheader("Analysis Summary")

    total_cleaned = len(
        st.session_state["analysis_df"]
    )

    total_variables = len(all_results)

    total_open = sum(
        1
        for result in all_results.values()
        if result["type"] == "Open"
    )

    total_crosstabs = len(
        st.session_state["crosstab_results"]
    )

    col1, col2, col3, col4 = st.columns(4)

    scorecards = [
        (
            col1,
            "Final Respondents",
            f"{total_cleaned:,}"
        ),
        (
            col2,
            "Active Variables",
            f"{total_variables:,}"
        ),
        (
            col3,
            "Crosstabs",
            f"{total_crosstabs:,}"
        ),
        (
            col4,
            "Open Questions",
            f"{total_open:,}"
        )
    ]

    for column, label, value in scorecards:

        with column:

            st.html(
                    f"""
                    <div class="metric-card">

                        <div class="metric-label">
                            {label}
                        </div>

                        <div class="metric-value">
                            {value}
                        </div>

                    </div>
                    """
                )

    st.write("")

    # ========================================================
    # VARIABLE ANALYSIS CHARTS
    # ========================================================

    st.subheader("Variable Analysis")

    # Put variables into two columns to make the dashboard
    # more compact.

    chart_questions = [
        question
        for question, result in all_results.items()
        if result["type"] != "Open"
        and not result["result"].empty
    ]

    for start in range(
        0,
        len(chart_questions),
        2
    ):

        row_questions = chart_questions[
            start:start + 2
        ]

        chart_columns = st.columns(
            len(row_questions)
        )

        for column, question in zip(
            chart_columns,
            row_questions
        ):

            result = all_results[question]
            result_df = result["result"]

            with column:

                st.html(
                        f"""
                        <div class="analysis-card">

                            <div class="analysis-question">
                                {question}
                            </div>

                            <div class="analysis-small">
                                Base N: {result["base_n"]}
                                &nbsp; • &nbsp;
                                {result["type"]}
                            </div>

                        </div>
                        """
                    )

                chart_df = result_df[
                    [
                        "Option",
                        "Percentage"
                    ]
                ].copy()

                chart_df = chart_df.set_index(
                    "Option"
                )

                st.bar_chart(
                    chart_df,
                    horizontal=True,
                    height=200
                )

    # ========================================================
    # CROSSTAB CHARTS
    # ========================================================

    st.divider()

    st.subheader("Crosstab Analysis")

    crosstab_results = st.session_state[
        "crosstab_results"
    ]

    if not crosstab_results:

        st.info(
            "No crosstab results available."
        )

    else:

        for index, item in enumerate(
            crosstab_results
        ):

            result = item["result"]

            title = item.get(
                "name",
                f"Crosstab {index + 1}"
            )

            st.html(
                    f"""
                    <div class="analysis-card">

                        <div class="analysis-question">
                            {title}
                        </div>

                        <div class="analysis-small">
                            Row: {item["row_question"]}
                            &nbsp; • &nbsp;
                            Column: {item["column_question"]}
                            &nbsp; • &nbsp;
                            Base N: {result["base_n"]}
                        </div>

                    </div>
                    """
                )

            percentage_df = (
                result["percentage"]
                .copy()
                .round(1)
            )

            if not percentage_df.empty:

                st.bar_chart(
                    percentage_df,
                    horizontal=True,
                    height=220
                )

            with st.expander(
                "View Absolute Results"
            ):

                st.dataframe(
                    result["absolute"],
                    use_container_width=True,
                    hide_index=False
                )

            with st.expander(
                "View Percentage Results"
            ):

                st.dataframe(
                    result["percentage"].round(1),
                    use_container_width=True,
                    hide_index=False
                )

    # ========================================================
    # OPEN FEEDBACK
    # ========================================================

    st.divider()

    st.subheader("Open Feedback")

    feedback_list = []

    for question, result in all_results.items():

        if result["type"] != "Open":
            continue

        feedback_df = result["result"].copy()

        if feedback_df.empty:
            continue

        for feedback in feedback_df[
            "Open Feedback"
        ].tolist():

            if (
                pd.isna(feedback)
                or str(feedback).strip() == ""
            ):
                continue

            feedback_list.append(
                {
                    "Question": question,
                    "Open Feedback": feedback
                }
            )

    if not feedback_list:

        st.info(
            "No open-ended feedback available."
        )

    else:

        feedback_df = pd.DataFrame(
            feedback_list
        )

        st.caption(
            f"{len(feedback_df):,} open feedback response(s)"
        )

        # Scrollable table
        st.dataframe(
            feedback_df,
            use_container_width=True,
            hide_index=True,
            height=450
        )


# ============================================================
# TAB 6 — DOWNLOAD
# ============================================================

with tabs[5]:

    st.header("📥 Download Result")

    st.caption(
        "Export your cleaned dataset and analysis "
        "into one Excel workbook."
    )

    # ========================================================
    # PREPARE DATAFRAME FOR EXCEL
    # ========================================================

    def prepare_excel_df(df):

        export_df = df.copy()

        # ----------------------------------------------------
        # Flatten MultiIndex columns
        # ----------------------------------------------------

        if isinstance(
            export_df.columns,
            pd.MultiIndex
        ):

            new_columns = []

            for column in export_df.columns:

                parts = []

                for part in column:

                    if part is None:
                        continue

                    try:

                        if pd.isna(part):
                            continue

                    except Exception:
                        pass

                    part_text = str(part).strip()

                    if not part_text:
                        continue

                    if part_text.lower() == "nan":
                        continue

                    if part_text.lower().startswith(
                        "unnamed:"
                    ):
                        continue

                    parts.append(part_text)

                if parts:

                    new_columns.append(
                        " | ".join(parts)
                    )

                else:

                    new_columns.append(
                        "Unnamed"
                    )

            # ------------------------------------------------
            # Prevent duplicate column names
            # ------------------------------------------------

            seen = {}

            unique_columns = []

            for column in new_columns:

                if column not in seen:

                    seen[column] = 0

                    unique_columns.append(
                        column
                    )

                else:

                    seen[column] += 1

                    unique_columns.append(
                        f"{column}_{seen[column]}"
                    )

            export_df.columns = (
                unique_columns
            )

        else:

            export_df.columns = [
                str(column)
                for column in export_df.columns
            ]

        return export_df


    # ========================================================
    # GENERATE EXCEL
    # ========================================================

    def generate_excel():

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            # =================================================
            # 1. RAW DATA
            # =================================================

            raw_export_df = prepare_excel_df(
                raw_df
            )

            raw_export_df.to_excel(
                writer,
                sheet_name="1_Raw_Data",
                index=False
            )


            # =================================================
            # 2. VARIABLE ANALYSIS
            # =================================================

            variable_sheet = (
                "2_Variable_Analysis"
            )

            # Create sheet first
            pd.DataFrame(
                {
                    "Question": []
                }
            ).to_excel(
                writer,
                sheet_name=variable_sheet,
                index=False
            )

            row_position = 0

            for question in (
                st.session_state[
                    "active_questions"
                ]
            ):

                item = get_question_metadata(
                    metadata,
                    question
                )

                if item is None:
                    continue

                filtered_df = get_filtered_df(
                    st.session_state[
                        "analysis_df"
                    ],
                    question,
                    metadata,
                    st.session_state[
                        "applied_routing_config"
                    ]
                )

                result = (
                    calculate_variable_analysis(
                        filtered_df,
                        item
                    )
                )

                # ------------------------------------------------
                # Question Header
                # ------------------------------------------------

                header_df = pd.DataFrame(
                    {
                        "Question": [
                            question
                        ],
                        "Type": [
                            result["type"]
                        ],
                        "Base N": [
                            result["base_n"]
                        ]
                    }
                )

                header_df.to_excel(
                    writer,
                    sheet_name=variable_sheet,
                    startrow=row_position,
                    index=False
                )

                row_position += 2

                # ------------------------------------------------
                # Analysis Result
                # ------------------------------------------------

                export_df = prepare_excel_df(
                    result["result"]
                )

                if not export_df.empty:

                    if (
                        "Percentage"
                        in export_df.columns
                    ):

                        export_df[
                            "Percentage"
                        ] = (
                            pd.to_numeric(
                                export_df[
                                    "Percentage"
                                ],
                                errors="coerce"
                            )
                            .round(1)
                        )

                    export_df.to_excel(
                        writer,
                        sheet_name=variable_sheet,
                        startrow=row_position,
                        index=False
                    )

                    row_position += (
                        len(export_df) + 3
                    )


            # =================================================
            # 3. CROSSTAB
            # =================================================

            crosstab_sheet = "3_Crosstab"

            # Create sheet first
            pd.DataFrame(
                {
                    "Crosstab": []
                }
            ).to_excel(
                writer,
                sheet_name=crosstab_sheet,
                index=False
            )

            row_position = 0

            for index, item in enumerate(
                st.session_state[
                    "crosstab_results"
                ]
            ):

                title = item.get(
                    "name",
                    f"Crosstab {index + 1}"
                )

                # ------------------------------------------------
                # Crosstab Name
                # ------------------------------------------------

                pd.DataFrame(
                    {
                        "Crosstab": [
                            title
                        ]
                    }
                ).to_excel(
                    writer,
                    sheet_name=crosstab_sheet,
                    startrow=row_position,
                    index=False
                )

                row_position += 2

                # ------------------------------------------------
                # Variables
                # ------------------------------------------------

                pd.DataFrame(
                    {
                        "Row Variable": [
                            item[
                                "row_question"
                            ]
                        ],
                        "Column Variable": [
                            item[
                                "column_question"
                            ]
                        ]
                    }
                ).to_excel(
                    writer,
                    sheet_name=crosstab_sheet,
                    startrow=row_position,
                    index=False
                )

                row_position += 2

                # ------------------------------------------------
                # MA Option
                # ------------------------------------------------

                if item.get(
                    "column_option"
                ):

                    pd.DataFrame(
                        {
                            "MA Option": [
                                item[
                                    "column_option"
                                ]
                            ]
                        }
                    ).to_excel(
                        writer,
                        sheet_name=crosstab_sheet,
                        startrow=row_position,
                        index=False
                    )

                    row_position += 2

                # ------------------------------------------------
                # Base N
                # ------------------------------------------------

                result = item["result"]

                pd.DataFrame(
                    {
                        "Base N": [
                            result["base_n"]
                        ]
                    }
                ).to_excel(
                    writer,
                    sheet_name=crosstab_sheet,
                    startrow=row_position,
                    index=False
                )

                row_position += 2

                # ------------------------------------------------
                # ABSOLUTE
                # ------------------------------------------------

                absolute_df = (
                    result["absolute"]
                    .reset_index()
                )

                absolute_df = (
                    prepare_excel_df(
                        absolute_df
                    )
                )

                if not absolute_df.empty:

                    pd.DataFrame(
                        {
                            "Result Type": [
                                "Absolute"
                            ]
                        }
                    ).to_excel(
                        writer,
                        sheet_name=crosstab_sheet,
                        startrow=row_position,
                        index=False
                    )

                    row_position += 1

                    absolute_df.to_excel(
                        writer,
                        sheet_name=crosstab_sheet,
                        startrow=row_position,
                        index=False
                    )

                    row_position += (
                        len(
                            absolute_df
                        ) + 2
                    )


                # ------------------------------------------------
                # PERCENTAGE
                # ------------------------------------------------

                percentage_df = (
                    result["percentage"]
                    .reset_index()
                    .round(1)
                )

                percentage_df = (
                    prepare_excel_df(
                        percentage_df
                    )
                )

                if not percentage_df.empty:

                    pd.DataFrame(
                        {
                            "Result Type": [
                                "Percentage"
                            ]
                        }
                    ).to_excel(
                        writer,
                        sheet_name=crosstab_sheet,
                        startrow=row_position,
                        index=False
                    )

                    row_position += 1

                    percentage_df.to_excel(
                        writer,
                        sheet_name=crosstab_sheet,
                        startrow=row_position,
                        index=False
                    )

                    row_position += (
                        len(
                            percentage_df
                        ) + 3
                    )


            # =================================================
            # 4. OPEN FEEDBACK
            # =================================================

            feedback_list = []

            for question in (
                st.session_state[
                    "active_questions"
                ]
            ):

                item = get_question_metadata(
                    metadata,
                    question
                )

                if item is None:
                    continue

                if item["type"] != "Open":
                    continue

                filtered_df = get_filtered_df(
                    st.session_state[
                        "analysis_df"
                    ],
                    question,
                    metadata,
                    st.session_state[
                        "applied_routing_config"
                    ]
                )

                feedback_df = (
                    collect_open_feedback(
                        filtered_df,
                        item
                    )
                )

                if not feedback_df.empty:

                    feedback_df = (
                        prepare_excel_df(
                            feedback_df
                        )
                    )

                    feedback_list.append(
                        feedback_df
                    )


            if feedback_list:

                open_feedback_df = (
                    pd.concat(
                        feedback_list,
                        ignore_index=True
                    )
                )

            else:

                open_feedback_df = pd.DataFrame(
                    columns=[
                        "Question",
                        "Open Feedback"
                    ]
                )


            # ------------------------------------------------
            # Remove blank feedback
            # ------------------------------------------------

            if (
                not open_feedback_df.empty
                and "Open Feedback"
                in open_feedback_df.columns
            ):

                open_feedback_df = (
                    open_feedback_df[
                        open_feedback_df[
                            "Open Feedback"
                        ].notna()
                    ]
                )

                open_feedback_df = (
                    open_feedback_df[
                        open_feedback_df[
                            "Open Feedback"
                        ]
                        .astype(str)
                        .str.strip()
                        .ne("")
                    ]
                )


            open_feedback_df.to_excel(
                writer,
                sheet_name="4_Open_Feedback",
                index=False
            )


        output.seek(0)

        return output


    # ========================================================
    # DOWNLOAD BUTTON
    # ========================================================

    try:

        excel_file = generate_excel()

        st.success(
            "Your Excel report is ready."
        )

        st.download_button(
            "⬇️ Download Excel Result",
            data=excel_file,
            file_name=(
                "survey_analysis_result.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            type="primary",
            use_container_width=True
        )

    except Exception as error:

        st.error(
            f"Failed to generate Excel report: {error}"
        )
