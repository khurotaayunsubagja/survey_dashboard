import streamlit as st
import pandas as pd
import altair as alt

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
# COLOR CONFIG
# ============================================================

MAIN_BLUE = "#7695B7"

CALM_COLORS = [
    "#7695B7",
    "#8FB9AA",
    "#A8B8D0",
    "#91A8A4",
    "#A89DB8",
    "#93B7BE"
]


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* =====================================================
       GENERAL
    ===================================================== */

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    section[data-testid="stSidebar"] {
        background-color: #ffffff;
    }

    /* =====================================================
       HERO
    ===================================================== */

    .hero {
        padding: 28px 32px;
        border-radius: 20px;
        background:
            linear-gradient(
                135deg,
                #7895B2 0%,
                #94A7AE 100%
            );
        color: white;
        margin-bottom: 25px;
        box-shadow:
            0 8px 25px
            rgba(60, 80, 100, 0.15);
    }

    .hero-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 6px;
    }

    .hero-subtitle {
        font-size: 15px;
        opacity: 0.92;
    }

    /* =====================================================
       METRIC
    ===================================================== */

    .metric-card {
        padding: 20px;
        border-radius: 17px;
        background: white;
        border: 1px solid #e7ebef;
        box-shadow:
            0 5px 18px
            rgba(0, 0, 0, 0.04);
    }

    .metric-label {
        font-size: 13px;
        color: #777;
        font-weight: 600;
        margin-bottom: 7px;
    }

    .metric-value {
        font-size: 27px;
        font-weight: 800;
        color: #252525;
        line-height: 1.15;
        overflow-wrap: anywhere;
    }

    /* =====================================================
       INFO
    ===================================================== */

    .info-box {
        padding: 14px 17px;
        border-radius: 12px;
        background: #F4F7FA;
        border-left: 4px solid #7695B7;
        margin: 12px 0;
    }

    /* =====================================================
       ANALYSIS
    ===================================================== */

    .analysis-card {
        background: white;
        padding: 14px 18px;
        border-radius: 14px;
        border: 1px solid #e7ebef;
        margin-top: 8px;
        margin-bottom: 4px;
        box-shadow:
            0 3px 12px
            rgba(0, 0, 0, 0.03);
    }

    .analysis-question {
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 4px;
        line-height: 1.45;
    }

    .analysis-small {
        font-size: 12px;
        color: #777;
    }

    /* =====================================================
       BUTTON
    ===================================================== */

    .stButton > button {
        border-radius: 11px;
        font-weight: 650;
        min-height: 41px;
    }

    /* =====================================================
       DATAFRAME
    ===================================================== */

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    /* =====================================================
       EXPANDER
       Membuat View Absolute Results lebih dekat ke chart
    ===================================================== */

    div[data-testid="stExpander"] {
        margin-top: -6px;
        margin-bottom: 5px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HELPER — METRIC CARD
# ============================================================

def metric_card(
    label,
    value
):

    st.markdown(
        f"""
        <div class="metric-card">

            <div class="metric-label">
                {label}
            </div>

            <div class="metric-value">
                {value}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# HELPER — VARIABLE CHART
# ============================================================

def show_variable_chart(
    result_df
):
    """
    Menampilkan horizontal bar chart
    dengan warna yang lebih soft.

    Label opsi diberikan ruang besar agar tidak terpotong.
    """

    if result_df.empty:
        return

    chart_df = (
        result_df[
            [
                "Option",
                "Percentage"
            ]
        ]
        .copy()
    )

    chart_df["Option"] = (
        chart_df["Option"]
        .astype(str)
    )

    chart_df["Percentage"] = (
        pd.to_numeric(
            chart_df[
                "Percentage"
            ],
            errors="coerce"
        )
        .fillna(0)
    )

    chart_height = max(
        180,
        len(chart_df) * 37
    )

    chart = (
        alt.Chart(
            chart_df
        )
        .mark_bar(
            cornerRadiusEnd=4,
            color=MAIN_BLUE
        )
        .encode(

            x=alt.X(
                "Percentage:Q",
                title="Percentage (%)",
                axis=alt.Axis(
                    grid=True,
                    tickCount=6
                )
            ),

            y=alt.Y(
                "Option:N",
                title=None,
                sort="-x",
                axis=alt.Axis(
                    labelLimit=500,
                    labelPadding=8
                )
            ),

            tooltip=[
                alt.Tooltip(
                    "Option:N",
                    title="Option"
                ),
                alt.Tooltip(
                    "Percentage:Q",
                    title="Percentage",
                    format=".1f"
                )
            ]
        )
        .properties(
            height=chart_height
        )
    )

    st.altair_chart(
        chart,
        use_container_width=True
    )


# ============================================================
# HELPER — CROSSTAB CHART
# ============================================================

def show_crosstab_chart(
    percentage_df
):
    """
    Crosstab visualization dengan warna soft.
    """

    if percentage_df.empty:
        return

    plot_df = (
        percentage_df
        .copy()
        .round(1)
        .reset_index()
    )

    first_column = (
        plot_df.columns[0]
    )

    plot_df = (
        plot_df.rename(
            columns={
                first_column:
                    "Row Option"
            }
        )
    )

    plot_df = (
        plot_df.melt(
            id_vars=[
                "Row Option"
            ],
            var_name="Column Option",
            value_name="Percentage"
        )
    )

    plot_df["Row Option"] = (
        plot_df[
            "Row Option"
        ]
        .astype(str)
    )

    plot_df["Column Option"] = (
        plot_df[
            "Column Option"
        ]
        .astype(str)
    )

    chart_height = max(
        200,
        plot_df[
            "Row Option"
        ]
        .nunique()
        * 42
    )

    chart = (
        alt.Chart(
            plot_df
        )
        .mark_bar(
            cornerRadiusEnd=3
        )
        .encode(

            x=alt.X(
                "Percentage:Q",
                title="Percentage (%)"
            ),

            y=alt.Y(
                "Row Option:N",
                title=None,
                axis=alt.Axis(
                    labelLimit=500,
                    labelPadding=8
                )
            ),

            yOffset=alt.YOffset(
                "Column Option:N"
            ),

            color=alt.Color(
                "Column Option:N",
                title=None,
                scale=alt.Scale(
                    range=CALM_COLORS
                )
            ),

            tooltip=[
                alt.Tooltip(
                    "Row Option:N",
                    title="Row"
                ),
                alt.Tooltip(
                    "Column Option:N",
                    title="Column"
                ),
                alt.Tooltip(
                    "Percentage:Q",
                    title="Percentage",
                    format=".1f"
                )
            ]
        )
        .properties(
            height=chart_height
        )
    )

    st.altair_chart(
        chart,
        use_container_width=True
    )


# ============================================================
# HELPER — PREPARE EXCEL DATAFRAME
# ============================================================

def prepare_excel_df(
    df
):
    """
    Flatten MultiIndex agar bisa disimpan ke Excel.
    """

    export_df = df.copy()

    # ========================================================
    # MULTIINDEX
    # ========================================================

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

                text = str(
                    part
                ).strip()

                if not text:
                    continue

                if text.lower() == "nan":
                    continue

                if text.lower().startswith(
                    "unnamed:"
                ):
                    continue

                parts.append(
                    text
                )

            if parts:

                new_columns.append(
                    " | ".join(parts)
                )

            else:

                new_columns.append(
                    "Unnamed"
                )

        # ----------------------------------------------------
        # Make unique
        # ----------------------------------------------------

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
            for column
            in export_df.columns
        ]

    return export_df


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


for key, value in (
    DEFAULT_STATE.items()
):

    if key not in st.session_state:

        st.session_state[
            key
        ] = value


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
    <div class="hero">

        <div class="hero-title">
            📊 Survey Insight Dashboard
        </div>

        <div class="hero-subtitle">
            Clean survey data, detect duplicates,
            configure routing, create crosstabs,
            and generate analysis-ready reports.
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## ⚙️ Data Setup"
    )

    st.caption(
        "Upload your survey dataset."
    )

    platform = st.selectbox(
        "Survey Platform",
        [
            "SurveyMonkey",
            "Google Forms"
        ]
    )

    uploaded_file = (
        st.file_uploader(
            "Upload Excel File",
            type=[
                "xlsx",
                "xls"
            ]
        )
    )

    load_button = st.button(
        "🚀 Load Data",
        type="primary",
        use_container_width=True
    )

    st.divider()

    if st.session_state[
        "data_loaded"
    ]:

        st.success(
            "Dataset loaded"
        )

        st.caption(
            f"Platform: "
            f"{st.session_state['platform']}"
        )

        st.caption(
            f"Respondents: "
            f"{len(st.session_state['analysis_df']):,}"
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

            # ------------------------------------------------
            # Save dataset
            # ------------------------------------------------

            st.session_state[
                "raw_df"
            ] = raw_df

            st.session_state[
                "analysis_df"
            ] = analysis_df

            st.session_state[
                "metadata"
            ] = metadata

            st.session_state[
                "respondent_count"
            ] = respondent_count

            st.session_state[
                "platform"
            ] = platform

            st.session_state[
                "data_loaded"
            ] = True

            # ------------------------------------------------
            # Contact tidak menjadi active variable
            # ------------------------------------------------

            st.session_state[
                "active_questions"
            ] = [
                item["question"]
                for item in metadata
                if item["type"]
                != "Contact"
            ]

            # ------------------------------------------------
            # Reset previous state
            # ------------------------------------------------

            st.session_state[
                "removed_questions"
            ] = []

            st.session_state[
                "routing_config"
            ] = {}

            st.session_state[
                "applied_routing_config"
            ] = {}

            st.session_state[
                "duplicate_question"
            ] = None

            st.session_state[
                "duplicate_df"
            ] = None

            st.session_state[
                "crosstab_results"
            ] = []

            st.session_state[
                "variable_analysis_result"
            ] = {}

            st.success(
                "Data loaded successfully."
            )

            st.rerun()

        except Exception as error:

            st.error(
                f"Failed to load data: "
                f"{error}"
            )


# ============================================================
# REQUIRE DATA
# ============================================================

if not st.session_state[
    "data_loaded"
]:

    st.info(
        "Upload a survey Excel file "
        "and click 'Load Data' to start."
    )

    st.stop()


# ============================================================
# GLOBAL VARIABLES
# ============================================================

raw_df = (
    st.session_state[
        "raw_df"
    ]
)

analysis_df = (
    st.session_state[
        "analysis_df"
    ]
)

metadata = (
    st.session_state[
        "metadata"
    ]
)


# ============================================================
# TABS
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

    st.header(
        "Data Overview"
    )

    total_questions = len(
        metadata
    )

    active_questions = len(
        st.session_state[
            "active_questions"
        ]
    )

    open_questions = sum(
        1
        for item in metadata
        if item["type"] == "Open"
    )

    contact_questions = sum(
        1
        for item in metadata
        if item["type"] == "Contact"
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    with col1:

        metric_card(
            "Platform",
            st.session_state[
                "platform"
            ]
        )

    with col2:

        metric_card(
            "Respondents",
            f"{len(analysis_df):,}"
        )

    with col3:

        metric_card(
            "Questions",
            total_questions
        )

    with col4:

        metric_card(
            "Open Questions",
            open_questions
        )

    st.write("")

    st.markdown(
        f"""
        <div class="info-box">

            <b>{active_questions}</b>
            active variables are currently included
            in the analysis.

            <br>

            <b>{contact_questions}</b>
            contact variable(s) are excluded automatically.

        </div>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # QUESTION OVERVIEW
    # ========================================================

    st.subheader(
        "Question Overview"
    )

    overview_rows = []

    for item in metadata:

        overview_rows.append(
            {
                "Question":
                    item["question"],

                "Type":
                    item["type"],

                "Number of Options":
                    len(
                        item.get(
                            "options",
                            []
                        )
                    ),

                "Active":
                    (
                        "Yes"
                        if (
                            item["question"]
                            in st.session_state[
                                "active_questions"
                            ]
                        )
                        else "No"
                    )
            }
        )

    st.dataframe(
        pd.DataFrame(
            overview_rows
        ),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # ========================================================
    # RAW DATA
    # ========================================================

    st.subheader(
        "Raw Data Preview"
    )

    st.caption(
        "Original structure from uploaded Excel."
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

    st.header(
        "🔍 Duplicate Detection"
    )

    st.markdown(
        """
        <div class="info-box">

            Duplicate detection only checks
            <b>Open-ended questions</b>.

            Contact variables such as phone numbers
            are excluded automatically.

        </div>
        """,
        unsafe_allow_html=True
    )

    open_questions = [
        item["question"]
        for item in metadata
        if item["type"] == "Open"
    ]

    if not open_questions:

        st.info(
            "No Open-ended questions available."
        )

    else:

        selected_question = (
            st.selectbox(
                "Select Open Question",
                [
                    "Select a question"
                ]
                + open_questions
            )
        )

        if st.button(
            "🔎 Detect Duplicates",
            type="primary",
            use_container_width=True
        ):

            if (
                selected_question
                == "Select a question"
            ):

                st.warning(
                    "Please select an Open-ended question."
                )

            else:

                item = (
                    get_question_metadata(
                        metadata,
                        selected_question
                    )
                )

                duplicate_df = (
                    detect_open_duplicates(
                        st.session_state[
                            "analysis_df"
                        ],
                        item
                    )
                )

                st.session_state[
                    "duplicate_question"
                ] = selected_question

                st.session_state[
                    "duplicate_df"
                ] = duplicate_df

                if duplicate_df.empty:

                    st.success(
                        "No duplicate responses found."
                    )

                else:

                    group_count = (
                        duplicate_df[
                            "Duplicate Group"
                        ]
                        .nunique()
                    )

                    row_count = len(
                        duplicate_df
                    )

                    st.success(
                        f"{row_count} duplicate row(s) "
                        f"found across "
                        f"{group_count} group(s)."
                    )

        # ====================================================
        # DUPLICATE RESULT
        # ====================================================

        duplicate_df = (
            st.session_state[
                "duplicate_df"
            ]
        )

        if (
            duplicate_df is not None
            and not duplicate_df.empty
        ):

            st.divider()

            st.subheader(
                "Duplicate Responses"
            )

            display_df = (
                duplicate_df[
                    [
                        "_original_index",
                        "Response",
                        "Duplicate Group",
                        "Duplicate Count"
                    ]
                ]
                .copy()
            )

            display_df[
                "Row"
            ] = (
                display_df[
                    "_original_index"
                ]
                + 1
            )

            display_df = (
                display_df[
                    [
                        "Row",
                        "Response",
                        "Duplicate Group",
                        "Duplicate Count"
                    ]
                ]
            )

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=400
            )

            st.divider()

            st.subheader(
                "Select Rows to Delete"
            )

            available_indices = (
                duplicate_df[
                    "_original_index"
                ]
                .tolist()
            )

            response_mapping = dict(
                zip(
                    duplicate_df[
                        "_original_index"
                    ],
                    duplicate_df[
                        "Response"
                    ]
                )
            )

            selected_rows = (
                st.multiselect(
                    "Rows",
                    options=
                        available_indices,
                    format_func=
                        lambda index:
                        (
                            f"Row {index + 1} — "
                            f"{str(response_mapping.get(index, ''))[:100]}"
                        )
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
                        "Please select at least one row."
                    )

                else:

                    before_count = len(
                        st.session_state[
                            "analysis_df"
                        ]
                    )

                    st.session_state[
                        "analysis_df"
                    ] = (
                        st.session_state[
                            "analysis_df"
                        ]
                        .drop(
                            index=selected_rows,
                            errors="ignore"
                        )
                    )

                    after_count = len(
                        st.session_state[
                            "analysis_df"
                        ]
                    )

                    deleted_count = (
                        before_count
                        - after_count
                    )

                    st.session_state[
                        "duplicate_df"
                    ] = None

                    # Crosstab lama tidak lagi valid
                    st.session_state[
                        "crosstab_results"
                    ] = []

                    st.success(
                        f"{deleted_count} respondent(s) "
                        f"deleted successfully."
                    )

                    st.rerun()


# ============================================================
# TAB 3 — ROUTING
# ============================================================

with tabs[2]:

    st.header(
        "🔀 Routing Variable"
    )

    st.caption(
        "Configure respondents included "
        "for each variable."
    )

    # ========================================================
    # RESTORE VARIABLE
    # ========================================================

    if st.session_state[
        "removed_questions"
    ]:

        st.subheader(
            "Restore Variables"
        )

        restore_question = (
            st.selectbox(
                "Select Variable",
                [
                    "Select a variable"
                ]
                + st.session_state[
                    "removed_questions"
                ]
            )
        )

        if st.button(
            "↩️ Restore Variable",
            use_container_width=True
        ):

            if (
                restore_question
                != "Select a variable"
            ):

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

                st.rerun()

    st.divider()

    # ========================================================
    # ROUTING CONFIG
    # ========================================================

    routing_config = {}

    for index, question in enumerate(
        st.session_state[
            "active_questions"
        ]
    ):

        item = (
            get_question_metadata(
                metadata,
                question
            )
        )

        if item is None:
            continue

        col_title, col_remove = (
            st.columns(
                [9, 1]
            )
        )

        with col_title:

            st.markdown(
                f"### {question}"
            )

            st.caption(
                f"Question Type: "
                f"{item['type']}"
            )

        with col_remove:

            if st.button(
                "✕",
                key=
                    f"remove_question_{index}"
            ):

                st.session_state[
                    "active_questions"
                ].remove(
                    question
                )

                st.session_state[
                    "removed_questions"
                ].append(
                    question
                )

                st.rerun()

        # ----------------------------------------------------
        # Hanya SA / MA boleh menjadi routing variable
        # ----------------------------------------------------

        routing_variables = [
            metadata_item[
                "question"
            ]
            for metadata_item
            in metadata
            if (
                metadata_item[
                    "question"
                ]
                != question

                and metadata_item[
                    "type"
                ]
                in ["SA", "MA"]

                and metadata_item[
                    "question"
                ]
                in st.session_state[
                    "active_questions"
                ]
            )
        ]

        base_options = (
            ["All Respondents"]
            + routing_variables
        )

        selected_base = (
            st.selectbox(
                "Base Variable",
                base_options,
                key=
                    f"routing_base_{index}"
            )
        )

        # ----------------------------------------------------
        # All respondents
        # ----------------------------------------------------

        if (
            selected_base
            == "All Respondents"
        ):

            routing_config[
                question
            ] = {
                "base_question":
                    "All Respondents",

                "values": []
            }

        else:

            base_item = (
                get_question_metadata(
                    metadata,
                    selected_base
                )
            )

            selected_values = (
                st.multiselect(
                    "Routing Values",
                    base_item[
                        "options"
                    ],
                    key=
                        f"routing_values_{index}"
                )
            )

            routing_config[
                question
            ] = {
                "base_question":
                    selected_base,

                "values":
                    selected_values
            }

        st.divider()

    st.session_state[
        "routing_config"
    ] = routing_config

    # ========================================================
    # APPLY ROUTING
    # ========================================================

    if st.button(
        "✅ Apply Routing",
        type="primary",
        use_container_width=True
    ):

        st.session_state[
            "applied_routing_config"
        ] = {
            question:
                config.copy()
            for question, config
            in routing_config.items()
        }

        st.session_state[
            "crosstab_results"
        ] = []

        st.success(
            "Routing configuration applied."
        )

    # ========================================================
    # ROUTING SUMMARY
    # ========================================================

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

            values = config.get(
                "values",
                []
            )

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
                        (
                            ", ".join(values)
                            if values
                            else "All Respondents"
                        )
                }
            )

        st.dataframe(
            pd.DataFrame(
                summary_rows
            ),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TAB 4 — CROSSTAB
# ============================================================

with tabs[3]:

    st.header(
        "📊 Crosstab"
    )

    st.caption(
        "Create up to 10 crosstab configurations."
    )

    crosstab_configs = []

    # --------------------------------------------------------
    # Crosstab hanya boleh menggunakan SA / MA
    # --------------------------------------------------------

    crosstab_questions = [
        question
        for question
        in st.session_state[
            "active_questions"
        ]
        if (
            get_question_metadata(
                metadata,
                question
            )["type"]
            in ["SA", "MA"]
        )
    ]

    for index in range(10):

        with st.expander(
            f"Crosstab {index + 1}",
            expanded=(
                index == 0
            )
        ):

            crosstab_name = (
                st.text_input(
                    "Crosstab Name",
                    value=
                        f"Crosstab {index + 1}",
                    key=
                        f"ct_name_{index}"
                )
            )

            col1, col2, col3 = (
                st.columns(3)
            )

            with col1:

                row_question = (
                    st.selectbox(
                        "Row Variable",
                        [
                            "Select Variable"
                        ]
                        + crosstab_questions,
                        key=
                            f"ct_row_{index}"
                    )
                )

            with col2:

                column_question = (
                    st.selectbox(
                        "Column Variable",
                        [
                            "Select Variable"
                        ]
                        + crosstab_questions,
                        key=
                            f"ct_column_{index}"
                    )
                )

            with col3:

                metric = (
                    st.selectbox(
                        "Metric",
                        [
                            "Absolute",
                            "Percentage"
                        ],
                        key=
                            f"ct_metric_{index}"
                    )
                )

            column_option = None

            # =================================================
            # VALID CONFIGURATION
            # =================================================

            if (
                row_question
                != "Select Variable"

                and column_question
                != "Select Variable"
            ):

                row_item = (
                    get_question_metadata(
                        metadata,
                        row_question
                    )
                )

                column_item = (
                    get_question_metadata(
                        metadata,
                        column_question
                    )
                )

                row_type = (
                    row_item["type"]
                )

                column_type = (
                    column_item["type"]
                )

                # ---------------------------------------------
                # MA × MA
                # ---------------------------------------------

                if (
                    row_type == "MA"
                    and column_type == "MA"
                ):

                    st.error(
                        "MA × MA cannot be performed."
                    )

                # ---------------------------------------------
                # MA × SA
                # ---------------------------------------------

                elif (
                    row_type == "MA"
                    and column_type == "SA"
                ):

                    st.warning(
                        "Please place SA as Row Variable "
                        "and MA as Column Variable."
                    )

                # ---------------------------------------------
                # SA × MA
                # ---------------------------------------------

                elif (
                    row_type == "SA"
                    and column_type == "MA"
                ):

                    column_option = (
                        st.selectbox(
                            "MA Option",
                            column_item[
                                "options"
                            ],
                            key=
                                f"ct_ma_option_{index}"
                        )
                    )

                    crosstab_configs.append(
                        {
                            "name":
                                crosstab_name.strip()
                                or
                                f"Crosstab {index + 1}",

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

                # ---------------------------------------------
                # SA × SA
                # ---------------------------------------------

                elif (
                    row_type == "SA"
                    and column_type == "SA"
                ):

                    crosstab_configs.append(
                        {
                            "name":
                                crosstab_name.strip()
                                or
                                f"Crosstab {index + 1}",

                            "row_question":
                                row_question,

                            "column_question":
                                column_question,

                            "column_option":
                                None,

                            "metric":
                                metric
                        }
                    )

    # ========================================================
    # APPLY CROSSTAB
    # ========================================================

    if st.button(
        "🚀 Apply All Crosstabs",
        type="primary",
        use_container_width=True
    ):

        results = []

        for config in crosstab_configs:

            row_item = (
                get_question_metadata(
                    metadata,
                    config[
                        "row_question"
                    ]
                )
            )

            column_item = (
                get_question_metadata(
                    metadata,
                    config[
                        "column_question"
                    ]
                )
            )

            filtered_df = (
                get_filtered_df(
                    st.session_state[
                        "analysis_df"
                    ],
                    config[
                        "row_question"
                    ],
                    metadata,
                    st.session_state[
                        "applied_routing_config"
                    ]
                )
            )

            try:

                result = (
                    calculate_crosstab(
                        filtered_df,
                        row_item,
                        column_item,
                        config[
                            "column_option"
                        ]
                    )
                )

                results.append(
                    {
                        **config,
                        "result":
                            result
                    }
                )

            except ValueError as error:

                st.error(
                    str(error)
                )

        st.session_state[
            "crosstab_results"
        ] = results

        st.success(
            f"{len(results)} crosstab(s) applied."
        )


# ============================================================
# TAB 5 — ANALYZE RESULT
# ============================================================

with tabs[4]:

    st.header(
        "📈 Analyze Result"
    )

    st.caption(
        "Analysis based on cleaned respondents "
        "and applied routing configuration."
    )

    # ========================================================
    # CALCULATE VARIABLES
    # ========================================================

    all_results = {}

    for question in (
        st.session_state[
            "active_questions"
        ]
    ):

        item = (
            get_question_metadata(
                metadata,
                question
            )
        )

        if item is None:
            continue

        if item["type"] == "Contact":
            continue

        filtered_df = (
            get_filtered_df(
                st.session_state[
                    "analysis_df"
                ],
                question,
                metadata,
                st.session_state[
                    "applied_routing_config"
                ]
            )
        )

        result = (
            calculate_variable_analysis(
                filtered_df,
                item
            )
        )

        all_results[
            question
        ] = result

    st.session_state[
        "variable_analysis_result"
    ] = all_results

    # ========================================================
    # SUMMARY
    # ========================================================

    st.subheader(
        "Analysis Summary"
    )

    total_cleaned = len(
        st.session_state[
            "analysis_df"
        ]
    )

    total_variables = len(
        all_results
    )

    total_open = sum(
        1
        for result
        in all_results.values()
        if result["type"]
        == "Open"
    )

    total_crosstabs = len(
        st.session_state[
            "crosstab_results"
        ]
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    with col1:

        metric_card(
            "Final Respondents",
            f"{total_cleaned:,}"
        )

    with col2:

        metric_card(
            "Active Variables",
            total_variables
        )

    with col3:

        metric_card(
            "Crosstabs",
            total_crosstabs
        )

    with col4:

        metric_card(
            "Open Questions",
            total_open
        )

    st.write("")

    # ========================================================
    # VARIABLE ANALYSIS
    # ========================================================

    st.subheader(
        "Variable Analysis"
    )

    chart_questions = [
        question
        for question, result
        in all_results.items()
        if (
            result["type"]
            in ["SA", "MA"]

            and not result[
                "result"
            ].empty
        )
    ]

    if not chart_questions:

        st.info(
            "No variable analysis available."
        )

    # --------------------------------------------------------
    # 1 chart per row
    # Agar label jawaban tidak terpotong.
    # --------------------------------------------------------

    for question in chart_questions:

        result = (
            all_results[
                question
            ]
        )

        st.markdown(
            f"""
            <div class="analysis-card">

                <div class="analysis-question">
                    {question}
                </div>

                <div class="analysis-small">

                    Base N:
                    {result["base_n"]}

                    &nbsp; • &nbsp;

                    {result["type"]}

                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        show_variable_chart(
            result[
                "result"
            ]
        )

    # ========================================================
    # CROSSTAB ANALYSIS
    # ========================================================

    st.divider()

    st.subheader(
        "Crosstab Analysis"
    )

    crosstab_results = (
        st.session_state[
            "crosstab_results"
        ]
    )

    if not crosstab_results:

        st.info(
            "No crosstab results available."
        )

    else:

        for index, item in enumerate(
            crosstab_results
        ):

            result = (
                item["result"]
            )

            title = item.get(
                "name",
                f"Crosstab {index + 1}"
            )

            st.markdown(
                f"""
                <div class="analysis-card">

                    <div class="analysis-question">
                        {title}
                    </div>

                    <div class="analysis-small">

                        Row:
                        {item["row_question"]}

                        &nbsp; • &nbsp;

                        Column:
                        {item["column_question"]}

                        &nbsp; • &nbsp;

                        Base N:
                        {result["base_n"]}

                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

            # ------------------------------------------------
            # Chart
            # ------------------------------------------------

            show_crosstab_chart(
                result[
                    "percentage"
                ]
            )

            # ------------------------------------------------
            # Result tables
            # ------------------------------------------------

            with st.expander(
                "View Absolute Results"
            ):

                st.dataframe(
                    result[
                        "absolute"
                    ],
                    use_container_width=True
                )

            with st.expander(
                "View Percentage Results"
            ):

                st.dataframe(
                    result[
                        "percentage"
                    ].round(1),
                    use_container_width=True
                )

            st.divider()

    # ========================================================
    # OPEN FEEDBACK
    # ========================================================

    st.subheader(
        "Open Feedback"
    )

    feedback_list = []

    for question in (
        st.session_state[
            "active_questions"
        ]
    ):

        item = (
            get_question_metadata(
                metadata,
                question
            )
        )

        if item is None:
            continue

        # ----------------------------------------------------
        # Hanya Open.
        # Nomor HP sudah Contact sehingga tidak masuk.
        # ----------------------------------------------------

        if item["type"] != "Open":
            continue

        filtered_df = (
            get_filtered_df(
                st.session_state[
                    "analysis_df"
                ],
                question,
                metadata,
                st.session_state[
                    "applied_routing_config"
                ]
            )
        )

        question_feedback = (
            collect_open_feedback(
                filtered_df,
                item
            )
        )

        if not question_feedback.empty:

            feedback_list.append(
                question_feedback
            )

    if feedback_list:

        feedback_df = (
            pd.concat(
                feedback_list,
                ignore_index=True
            )
        )

        st.caption(
            f"{len(feedback_df):,} "
            f"open feedback response(s)"
        )

        st.dataframe(
            feedback_df,
            use_container_width=True,
            hide_index=True,
            height=450
        )

    else:

        st.info(
            "No open-ended feedback available."
        )


# ============================================================
# TAB 6 — DOWNLOAD
# ============================================================

with tabs[5]:

    st.header(
        "📥 Download Result"
    )

    st.caption(
        "Export raw data, variable analysis, "
        "crosstab and open feedback."
    )

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
            # SHEET 1 — RAW DATA
            # =================================================

            raw_export_df = (
                prepare_excel_df(
                    raw_df
                )
            )

            raw_export_df.to_excel(
                writer,
                sheet_name="1_Raw_Data",
                index=False
            )

            # =================================================
            # SHEET 2 — VARIABLE ANALYSIS
            # =================================================

            variable_sheet = (
                "2_Variable_Analysis"
            )

            pd.DataFrame().to_excel(
                writer,
                sheet_name=
                    variable_sheet,
                index=False
            )

            row_position = 0

            for question in (
                st.session_state[
                    "active_questions"
                ]
            ):

                item = (
                    get_question_metadata(
                        metadata,
                        question
                    )
                )

                if item is None:
                    continue

                # Contact tidak diexport sebagai analysis
                if item["type"] == "Contact":
                    continue

                filtered_df = (
                    get_filtered_df(
                        st.session_state[
                            "analysis_df"
                        ],
                        question,
                        metadata,
                        st.session_state[
                            "applied_routing_config"
                        ]
                    )
                )

                result = (
                    calculate_variable_analysis(
                        filtered_df,
                        item
                    )
                )

                # ---------------------------------------------
                # Header
                # ---------------------------------------------

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
                    sheet_name=
                        variable_sheet,
                    startrow=
                        row_position,
                    index=False
                )

                row_position += 2

                # ---------------------------------------------
                # Result
                # ---------------------------------------------

                export_df = (
                    prepare_excel_df(
                        result[
                            "result"
                        ]
                    )
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
                        sheet_name=
                            variable_sheet,
                        startrow=
                            row_position,
                        index=False
                    )

                    row_position += (
                        len(
                            export_df
                        )
                        + 3
                    )

            # =================================================
            # SHEET 3 — CROSSTAB
            # =================================================

            crosstab_sheet = (
                "3_Crosstab"
            )

            pd.DataFrame().to_excel(
                writer,
                sheet_name=
                    crosstab_sheet,
                index=False
            )

            row_position = 0

            for index, item in enumerate(
                st.session_state[
                    "crosstab_results"
                ]
            ):

                result = (
                    item["result"]
                )

                title = item.get(
                    "name",
                    f"Crosstab {index + 1}"
                )

                # ---------------------------------------------
                # Crosstab title
                # ---------------------------------------------

                pd.DataFrame(
                    {
                        "Crosstab": [
                            title
                        ]
                    }
                ).to_excel(
                    writer,
                    sheet_name=
                        crosstab_sheet,
                    startrow=
                        row_position,
                    index=False
                )

                row_position += 2

                # ---------------------------------------------
                # Crosstab metadata
                # ---------------------------------------------

                info_df = pd.DataFrame(
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
                        ],

                        "MA Option": [
                            item.get(
                                "column_option"
                            )
                            or ""
                        ],

                        "Base N": [
                            result[
                                "base_n"
                            ]
                        ]
                    }
                )

                info_df.to_excel(
                    writer,
                    sheet_name=
                        crosstab_sheet,
                    startrow=
                        row_position,
                    index=False
                )

                row_position += 3

                # ---------------------------------------------
                # Absolute
                # ---------------------------------------------

                pd.DataFrame(
                    {
                        "Result Type": [
                            "Absolute"
                        ]
                    }
                ).to_excel(
                    writer,
                    sheet_name=
                        crosstab_sheet,
                    startrow=
                        row_position,
                    index=False
                )

                row_position += 1

                absolute_df = (
                    result[
                        "absolute"
                    ]
                    .reset_index()
                )

                absolute_df = (
                    prepare_excel_df(
                        absolute_df
                    )
                )

                absolute_df.to_excel(
                    writer,
                    sheet_name=
                        crosstab_sheet,
                    startrow=
                        row_position,
                    index=False
                )

                row_position += (
                    len(
                        absolute_df
                    )
                    + 2
                )

                # ---------------------------------------------
                # Percentage
                # ---------------------------------------------

                pd.DataFrame(
                    {
                        "Result Type": [
                            "Percentage"
                        ]
                    }
                ).to_excel(
                    writer,
                    sheet_name=
                        crosstab_sheet,
                    startrow=
                        row_position,
                    index=False
                )

                row_position += 1

                percentage_df = (
                    result[
                        "percentage"
                    ]
                    .round(1)
                    .reset_index()
                )

                percentage_df = (
                    prepare_excel_df(
                        percentage_df
                    )
                )

                percentage_df.to_excel(
                    writer,
                    sheet_name=
                        crosstab_sheet,
                    startrow=
                        row_position,
                    index=False
                )

                row_position += (
                    len(
                        percentage_df
                    )
                    + 4
                )

            # =================================================
            # SHEET 4 — OPEN FEEDBACK
            # =================================================

            feedback_list = []

            for question in (
                st.session_state[
                    "active_questions"
                ]
            ):

                item = (
                    get_question_metadata(
                        metadata,
                        question
                    )
                )

                if item is None:
                    continue

                # ---------------------------------------------
                # PENTING:
                # hanya Open.
                # Contact/nomor HP tidak akan masuk.
                # ---------------------------------------------

                if item["type"] != "Open":
                    continue

                filtered_df = (
                    get_filtered_df(
                        st.session_state[
                            "analysis_df"
                        ],
                        question,
                        metadata,
                        st.session_state[
                            "applied_routing_config"
                        ]
                    )
                )

                feedback_df = (
                    collect_open_feedback(
                        filtered_df,
                        item
                    )
                )

                if not feedback_df.empty:

                    feedback_list.append(
                        feedback_df
                    )

            # ------------------------------------------------
            # Combine feedback
            # ------------------------------------------------

            if feedback_list:

                open_feedback_df = (
                    pd.concat(
                        feedback_list,
                        ignore_index=True
                    )
                )

            else:

                open_feedback_df = (
                    pd.DataFrame(
                        columns=[
                            "Question",
                            "Open Feedback"
                        ]
                    )
                )

            # ------------------------------------------------
            # Clean blank values
            # ------------------------------------------------

            if not open_feedback_df.empty:

                open_feedback_df = (
                    open_feedback_df[
                        open_feedback_df[
                            "Open Feedback"
                        ]
                        .notna()
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
                sheet_name=
                    "4_Open_Feedback",
                index=False
            )

        output.seek(0)

        return output

    # ========================================================
    # DOWNLOAD BUTTON
    # ========================================================

    try:

        excel_file = (
            generate_excel()
        )

        st.success(
            "Your Excel report is ready."
        )

        st.download_button(
            "⬇️ Download Excel Result",
            data=excel_file,
            file_name=
                "survey_analysis_result.xlsx",
            mime=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            type="primary",
            use_container_width=True
        )

    except Exception as error:

        st.error(
            f"Failed to generate Excel report: "
            f"{error}"
        )
