import streamlit as st
import pandas as pd
import altair as alt
import textwrap

from io import BytesIO

from processing.data_loader import (
    load_survey_data
)

from processing.processing_flow import (
    get_question_metadata,
    get_filtered_df,
    apply_global_filters,
    calculate_variable_analysis,
    calculate_crosstab,
    collect_open_feedback,
    detect_contact_duplicates
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

st.html(
        """
        <style>

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

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
                    0,
                    0,
                    0,
                    0.15
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

        .metric-card {
            padding: 20px;
            border-radius: 18px;

            background-color:
                var(--secondary-background-color);

            color:
                var(--text-color);

            border:
                1px solid rgba(
                    128,
                    128,
                    128,
                    0.22
                );

            box-shadow:
                0 6px 20px rgba(
                    0,
                    0,
                    0,
                    0.06
                );
        }

        .metric-label {
            font-size: 13px;
            color: var(--text-color);
            opacity: 0.65;
            font-weight: 600;
            margin-bottom: 7px;
        }

        .metric-value {
            font-size: 28px;
            font-weight: 800;
            color: var(--text-color);
            line-height: 1.15;
            overflow-wrap: anywhere;
        }

        .section-card {
            background-color:
                var(--secondary-background-color);

            color:
                var(--text-color);

            padding: 22px;
            border-radius: 18px;

            border:
                1px solid rgba(
                    128,
                    128,
                    128,
                    0.22
                );

            margin-bottom: 20px;

            box-shadow:
                0 5px 18px rgba(
                    0,
                    0,
                    0,
                    0.04
                );
        }

        .badge {
            display: inline-block;
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            margin-right: 5px;
        }

        .badge-sa {
            background: rgba(
                74,
                121,
                220,
                0.16
            );
            color: #668cff;
        }

        .badge-ma {
            background: rgba(
                56,
                160,
                102,
                0.16
            );
            color: #58b77e;
        }

        .badge-open {
            background: rgba(
                211,
                139,
                40,
                0.16
            );
            color: #d99b45;
        }

        .badge-contact {
            background: rgba(
                133,
                95,
                180,
                0.16
            );
            color: #a17ac7;
        }

        .info-box {
            padding: 15px 18px;
            border-radius: 14px;

            background-color:
                var(--secondary-background-color);

            color:
                var(--text-color);

            border-left:
                5px solid #667eea;

            margin: 12px 0;
        }

        hr {
            border: none;

            border-top:
                1px solid rgba(
                    128,
                    128,
                    128,
                    0.20
                );

            margin: 25px 0;
        }

        .stButton > button {
            border-radius: 12px;
            font-weight: 700;
            min-height: 42px;
        }

        [data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
        }

        .analysis-card {
            background-color:
                var(--secondary-background-color);

            color:
                var(--text-color);

            padding: 14px 18px;
            border-radius: 16px;

            border:
                1px solid rgba(
                    128,
                    128,
                    128,
                    0.22
                );

            margin-bottom: 12px;

            box-shadow:
                0 4px 14px rgba(
                    0,
                    0,
                    0,
                    0.04
                );
        }

        .analysis-question {
            font-size: 16px;
            font-weight: 750;
            margin-bottom: 3px;

            color:
                var(--text-color);

            white-space: normal;
            overflow-wrap: anywhere;
            word-break: normal;

            line-height: 1.45;
            min-height: 46px;
        }

        .analysis-small {
            font-size: 12px;
            color: var(--text-color);
            opacity: 0.65;
        }

        div[data-testid="stExpander"] {
            margin-top: -4px;
            margin-bottom: 4px;
        }

        /* =========================
           OPEN FEEDBACK
        ========================= */

        .feedback-container {
            height: 520px;
            overflow-y: auto;

            padding: 14px;

            background-color:
                var(--secondary-background-color);

            border:
                1px solid rgba(
                    128,
                    128,
                    128,
                    0.22
                );

            border-radius: 16px;

            margin-top: 10px;
        }

        .feedback-card {
            background-color:
                var(--background-color);

            color:
                var(--text-color);

            border:
                1px solid rgba(
                    128,
                    128,
                    128,
                    0.18
                );

            border-radius: 12px;

            padding: 15px 17px;

            margin-bottom: 12px;
        }

        .feedback-number {
            font-size: 12px;
            font-weight: 700;

            color:
                var(--text-color);

            opacity: 0.55;

            margin-bottom: 5px;
        }

        .feedback-question {
            font-size: 13px;
            font-weight: 700;

            color:
                var(--text-color);

            opacity: 0.75;

            font-style: italic;

            margin-bottom: 8px;
        }

        .feedback-text {
            font-size: 15px;

            color:
                var(--text-color);

            line-height: 1.65;

            

            white-space: normal;
            overflow-wrap: anywhere;
            word-break: normal;
        }

        /* =========================
           CONTINUE BUTTON
        ========================= */

        div[data-testid="stButton"] button[kind="secondary"] {
            background-color: #4F6D8A;
            color: white;

            border:
                1px solid #4F6D8A;

            border-radius: 12px;

            font-weight: 700;
        }

        div[data-testid="stButton"] button[kind="secondary"]:hover {
            background-color: #3F5B75;
            color: white;

            border:
                1px solid #3F5B75;
        }

        </style>
        """
    )


# ============================================================
# WORKFLOW
# ============================================================

STEPS = [
    "🏠 Overview",
    "🔍 Duplicate",
    "🎯 Filtering",
    "🔀 Routing",
    "📊 Crosstab",
    "📈 Analyze Result",
    "📥 Download"
]


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

    "global_filters": [],

    "routing_config": {},
    "applied_routing_config": {},

    "duplicate_question": None,
    "duplicate_df": None,
    "duplicate_cleared": False,

    "crosstab_results": [],
    "variable_analysis_result": {},

    "current_step": 0,
    "change_step_requested": False
}


for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:

        st.session_state[
            key
        ] = value


# ============================================================
# CONTINUE BUTTON
# ============================================================

def continue_button(
    next_step_index
):

    st.divider()

    if st.button(
        "Continue to Next Step →",
        use_container_width=True,
        key=
            f"continue_step_{next_step_index}"
    ):

        st.session_state[
            "current_step"
        ] = (
            next_step_index
        )

        st.session_state[
            "change_step_requested"
        ] = True

        st.rerun()


# ============================================================
# VARIABLE CHART
# ============================================================

def render_variable_chart(
    result_df
):

    if result_df.empty:

        return

    chart_df = (
        result_df[
            [
                "Option",
                "Absolute",
                "Percentage"
            ]
        ]
        .copy()
    )

    chart_df[
        "Absolute"
    ] = (
        pd.to_numeric(
            chart_df[
                "Absolute"
            ],
            errors="coerce"
        )
        .fillna(0)
    )

    chart_df[
        "Percentage"
    ] = (
        pd.to_numeric(
            chart_df[
                "Percentage"
            ],
            errors="coerce"
        )
        .fillna(0)
    )

    # ========================================================
    # 2 OPTIONS → PIE
    # ========================================================

    if len(
        chart_df
    ) == 2:

        chart = (
            alt.Chart(
                chart_df
            )
            .mark_arc(
                innerRadius=30
            )
            .encode(

                theta=alt.Theta(
                    "Absolute:Q"
                ),

                color=alt.Color(
                    "Option:N",
                    title=None,

                    scale=alt.Scale(
                        range=[
                            "#7FA6B8",
                            "#9CB9A8"
                        ]
                    )
                ),

                tooltip=[
                    alt.Tooltip(
                        "Option:N",
                        title="Option"
                    ),

                    alt.Tooltip(
                        "Absolute:Q",
                        title="Absolute",
                        format=",.0f"
                    ),

                    alt.Tooltip(
                        "Percentage:Q",
                        title="Percentage",
                        format=".1f"
                    )
                ]
            )
            .properties(
                height=220
            )
        )

        st.altair_chart(
            chart,
            use_container_width=True
        )

    # ========================================================
    # >2 OPTIONS → BAR
    # ========================================================

    else:

        chart_height = max(
            200,
            len(
                chart_df
            ) * 36
        )

        chart = (
            alt.Chart(
                chart_df
            )
            .mark_bar(
                cornerRadiusEnd=4
            )
            .encode(

                x=alt.X(
                    "Percentage:Q",
                    title=
                        "Percentage (%)"
                ),

                y=alt.Y(
                    "Option:N",
                    title=None,
                    sort="-x",

                    axis=alt.Axis(
                        labelLimit=350,
                        labelPadding=8
                    )
                ),

                color=alt.value(
                    "#7FA6B8"
                ),

                tooltip=[
                    alt.Tooltip(
                        "Option:N",
                        title="Option"
                    ),

                    alt.Tooltip(
                        "Absolute:Q",
                        title="Absolute",
                        format=",.0f"
                    ),

                    alt.Tooltip(
                        "Percentage:Q",
                        title="Percentage",
                        format=".1f"
                    )
                ]
            )
            .properties(
                height=
                    chart_height
            )
        )

        st.altair_chart(
            chart,
            use_container_width=True
        )


# ============================================================
# CROSSTAB CHART
# ============================================================

def render_crosstab_chart(
    percentage_df
):

    if percentage_df.empty:

        return

    row_count = (
        percentage_df.shape[0]
    )

    column_count = (
        percentage_df.shape[1]
    )

    chart_df = (
        percentage_df
        .copy()
        .round(1)
        .reset_index()
    )

    first_column = (
        chart_df.columns[0]
    )

    chart_df = (
        chart_df.rename(
            columns={
                first_column:
                    "Row Option"
            }
        )
    )

    chart_df = (
        chart_df.melt(
            id_vars=[
                "Row Option"
            ],
            var_name=
                "Column Option",
            value_name=
                "Percentage"
        )
    )

    # ========================================================
    # <=3 x 3 → VERTICAL
    # ========================================================

    if (
        row_count <= 3
        and
        column_count <= 3
    ):

        chart = (
            alt.Chart(
                chart_df
            )
            .mark_bar(
                cornerRadiusTopLeft=3,
                cornerRadiusTopRight=3
            )
            .encode(

                x=alt.X(
                    "Row Option:N",
                    title=None,

                    axis=alt.Axis(
                        labelLimit=250,
                        labelAngle=0
                    )
                ),

                xOffset=
                    "Column Option:N",

                y=alt.Y(
                    "Percentage:Q",
                    title=
                        "Percentage (%)"
                ),

                color=alt.Color(
                    "Column Option:N",
                    title=None,

                    scale=alt.Scale(
                        range=[
                            "#7FA6B8",
                            "#9CB9A8",
                            "#A99DB8",
                            "#B7AB8B"
                        ]
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
                height=270
            )
        )

        st.altair_chart(
            chart,
            use_container_width=True
        )

    # ========================================================
    # >3 x 3 → HORIZONTAL
    # ========================================================

    else:

        chart = (
            alt.Chart(
                chart_df
            )
            .mark_bar(
                cornerRadiusEnd=3
            )
            .encode(

                x=alt.X(
                    "Percentage:Q",
                    title=
                        "Percentage (%)"
                ),

                y=alt.Y(
                    "Row Option:N",
                    title=None,

                    axis=alt.Axis(
                        labelLimit=400,
                        labelPadding=8
                    )
                ),

                yOffset=
                    "Column Option:N",

                color=alt.Color(
                    "Column Option:N",
                    title=None,

                    scale=alt.Scale(
                        range=[
                            "#7FA6B8",
                            "#9CB9A8",
                            "#A99DB8",
                            "#B7AB8B",
                            "#8FAAB2",
                            "#A6B198"
                        ]
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
                height=max(
                    240,
                    row_count * 45
                )
            )
        )

        st.altair_chart(
            chart,
            use_container_width=True
        )


# ============================================================
# PREPARE DATAFRAME FOR EXCEL
# ============================================================

def prepare_excel_df(
    df
):

    export_df = (
        df.copy()
    )

    if isinstance(
        export_df.columns,
        pd.MultiIndex
    ):

        new_columns = []

        for column in (
            export_df.columns
        ):

            parts = []

            for part in column:

                if part is None:
                    continue

                try:

                    if pd.isna(part):
                        continue

                except Exception:
                    pass

                part_text = (
                    str(part)
                    .strip()
                )

                if not part_text:
                    continue

                if (
                    part_text.lower()
                    == "nan"
                ):
                    continue

                if (
                    part_text.lower()
                    .startswith(
                        "unnamed:"
                    )
                ):
                    continue

                parts.append(
                    part_text
                )

            if parts:

                new_columns.append(
                    " | ".join(
                        parts
                    )
                )

            else:

                new_columns.append(
                    "Unnamed"
                )

        seen = {}

        unique_columns = []

        for column in (
            new_columns
        ):

            if column not in seen:

                seen[
                    column
                ] = 0

                unique_columns.append(
                    column
                )

            else:

                seen[
                    column
                ] += 1

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
# HERO
# ============================================================

st.html(
    """
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
    """
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## ⚙️ Data Setup"
    )

    st.caption(
        "Upload your survey dataset to begin."
    )

    platform = (
        st.selectbox(
            "Survey Platform",
            [
                "SurveyMonkey",
                "Google Forms"
            ]
        )
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

    load_button = (
        st.button(
            "🚀 Load Data",
            type="primary",
            use_container_width=True
        )
    )

    st.divider()

    if (
        st.session_state[
            "data_loaded"
        ]
    ):

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

            st.session_state[
                "active_questions"
            ] = [
                item[
                    "question"
                ]
                for item
                in metadata
            ]

            st.session_state[
                "removed_questions"
            ] = []

            st.session_state[
                "global_filters"
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
                "duplicate_cleared"
            ] = False

            st.session_state[
                "crosstab_results"
            ] = []

            st.session_state[
                "variable_analysis_result"
            ] = {}

            st.session_state[
                "current_step"
            ] = 0

            st.session_state[
                "change_step_requested"
            ] = True

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
# VARIABLES
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
# NAVIGATION STATE SYNCHRONIZATION
# ============================================================

if st.session_state.get(
    "change_step_requested",
    False
):

    st.session_state[
        "workflow_navigation"
    ] = STEPS[
        st.session_state[
            "current_step"
        ]
    ]

    st.session_state[
        "change_step_requested"
    ] = False


# ============================================================
# NAVIGATION
# ============================================================

selected_step = (
    st.radio(
        "Workflow",
        STEPS,
        index=
            st.session_state[
                "current_step"
            ],
        horizontal=True,
        label_visibility=
            "collapsed",
        key=
            "workflow_navigation"
    )
)


st.session_state[
    "current_step"
] = (
    STEPS.index(
        selected_step
    )
)


# ============================================================
# OVERVIEW
# ============================================================

if selected_step == "🏠 Overview":

    st.header(
        "Data Overview"
    )

    total_questions = (
        len(
            metadata
        )
    )

    active_questions = (
        len(
            st.session_state[
                "active_questions"
            ]
        )
    )

    open_questions = sum(
        1
        for item
        in metadata
        if item[
            "type"
        ]
        == "Open"
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    metrics = [
        (
            col1,
            "Platform",
            st.session_state[
                "platform"
            ]
        ),
        (
            col2,
            "Respondents",
            f"{len(analysis_df):,}"
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

    for column, label, value in (
        metrics
    ):

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

    st.html(
            f"""
            <div class="info-box">

                <b>{active_questions}</b>
                active variables are currently included
                in the workflow.

            </div>
            """
        )

    st.subheader(
        "Question Overview"
    )

    overview_rows = []

    for item in metadata:

        overview_rows.append(
            {
                "Question":
                    item[
                        "question"
                    ],

                "Type":
                    item[
                        "type"
                    ],

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
                            item[
                                "type"
                            ]
                            == "Contact"

                            or

                            item[
                                "question"
                            ]
                            in st.session_state[
                                "active_questions"
                            ]
                        )

                        else "No"
                    )
            }
        )

    overview_df = (
        pd.DataFrame(
            overview_rows
        )
    )

    st.dataframe(
        overview_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "Raw Data Preview"
    )

    st.caption(
        "This preview preserves the original "
        "uploaded data structure."
    )

    st.dataframe(
        raw_df,
        use_container_width=True,
        height=420
    )

    continue_button(
        1
    )


# ============================================================
# DUPLICATE
# ============================================================

elif selected_step == "🔍 Duplicate":

    st.header(
        "🔍 Duplicate Detection"
    )

    st.html(
        """
        <div class="info-box">

            <b>
                Duplicate detection uses
                the phone/contact variable.
            </b>

            <br>

            Phone numbers are normalized
            before comparison.

        </div>
        """
    )

    contact_questions = [
        item[
            "question"
        ]
        for item
        in metadata
        if item[
            "type"
        ]
        == "Contact"
    ]

    if not contact_questions:

        st.info(
            "No phone/contact variable detected."
        )

    else:

        selected_question = (
            st.selectbox(
                "Select Contact Variable",
                [
                    "Select a question"
                ]
                + contact_questions
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
                    "Please select a contact variable first."
                )

            else:

                item = (
                    get_question_metadata(
                        metadata,
                        selected_question
                    )
                )

                duplicate_df = (
                    detect_contact_duplicates(
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

                st.session_state[
                    "duplicate_cleared"
                ] = (
                    duplicate_df.empty
                )

        if (
            st.session_state[
                "duplicate_cleared"
            ]
        ):

            st.success(
                "Duplicate data has been removed successfully. "
                "No duplicate contacts remain."
            )

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

            group_count = (
                duplicate_df[
                    "Duplicate Group"
                ]
                .nunique()
            )

            row_count = (
                len(
                    duplicate_df
                )
            )

            col1, col2 = (
                st.columns(2)
            )

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

            display_df = (
                duplicate_df[
                    [
                        "_original_index",
                        "Contact",
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
                        "Contact",
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

            contact_mapping = dict(
                zip(
                    duplicate_df[
                        "_original_index"
                    ],
                    duplicate_df[
                        "Contact"
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
                                f"{contact_mapping.get(index, '')}"
                            )
                )
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

                    st.session_state[
                        "analysis_df"
                    ] = (
                        st.session_state[
                            "analysis_df"
                        ]
                        .drop(
                            index=
                                selected_rows,
                            errors=
                                "ignore"
                        )
                    )

                    item = (
                        get_question_metadata(
                            metadata,
                            selected_question
                        )
                    )

                    remaining_duplicates = (
                        detect_contact_duplicates(
                            st.session_state[
                                "analysis_df"
                            ],
                            item
                        )
                    )

                    st.session_state[
                        "duplicate_df"
                    ] = (
                        remaining_duplicates
                    )

                    st.session_state[
                        "duplicate_cleared"
                    ] = (
                        remaining_duplicates.empty
                    )

                    st.session_state[
                        "crosstab_results"
                    ] = []

                    st.rerun()

    continue_button(
        2
    )


# ============================================================
# FILTERING
# ============================================================

elif selected_step == "🎯 Filtering":

    st.header(
        "🎯 Database Filtering"
    )

    st.caption(
        "Choose which respondents should be included "
        "in the analysis. You can apply up to 5 filters."
    )

    filter_questions = [
        item[
            "question"
        ]
        for item
        in metadata
        if item[
            "type"
        ]
        in [
            "SA",
            "MA"
        ]
    ]

    filter_config = []

    for index in range(5):

        st.subheader(
            f"Filter {index + 1}"
        )

        selected_question = (
            st.selectbox(
                "Variable",
                [
                    "No Filter"
                ]
                + filter_questions,

                key=
                    f"filter_question_{index}"
            )
        )

        if (
            selected_question
            != "No Filter"
        ):

            item = (
                get_question_metadata(
                    metadata,
                    selected_question
                )
            )

            selected_values = (
                st.multiselect(
                    "Included Values",
                    item[
                        "options"
                    ],
                    key=
                        f"filter_values_{index}"
                )
            )

            if selected_values:

                filter_config.append(
                    {
                        "question":
                            selected_question,

                        "values":
                            selected_values
                    }
                )

        st.divider()

    if st.button(
        "✅ Apply Filtering",
        type="primary",
        use_container_width=True
    ):

        st.session_state[
            "global_filters"
        ] = (
            filter_config
        )

        st.session_state[
            "crosstab_results"
        ] = []

        st.success(
            "Database filtering applied successfully."
        )

    filtered_preview = (
        apply_global_filters(
            st.session_state[
                "analysis_df"
            ],
            metadata,
            st.session_state[
                "global_filters"
            ]
        )
    )

    col1, col2 = (
        st.columns(2)
    )

    with col1:

        st.metric(
            "Before Filtering",
            len(
                st.session_state[
                    "analysis_df"
                ]
            )
        )

    with col2:

        st.metric(
            "After Filtering",
            len(
                filtered_preview
            )
        )

    if (
        st.session_state[
            "global_filters"
        ]
    ):

        st.subheader(
            "Applied Filters"
        )

        filter_summary = []

        for config in (
            st.session_state[
                "global_filters"
            ]
        ):

            filter_summary.append(
                {
                    "Variable":
                        config[
                            "question"
                        ],

                    "Included Values":
                        ", ".join(
                            config[
                                "values"
                            ]
                        )
                }
            )

        st.dataframe(
            pd.DataFrame(
                filter_summary
            ),
            use_container_width=True,
            hide_index=True
        )

    continue_button(
        3
    )


# ============================================================
# ROUTING
# ============================================================

elif selected_step == "🔀 Routing":

    st.header(
        "🔀 Routing Variable"
    )

    st.caption(
        "Configure which respondents should be included "
        "for each active variable."
    )

    routing_source_df = (
        apply_global_filters(
            st.session_state[
                "analysis_df"
            ],
            metadata,
            st.session_state[
                "global_filters"
            ]
        )
    )

    st.caption(
        f"Database after filtering: "
        f"{len(routing_source_df):,} respondent(s)."
    )

    if (
        st.session_state[
            "removed_questions"
        ]
    ):

        st.subheader(
            "Restore Variables"
        )

        restore_question = (
            st.selectbox(
                "Select a variable",
                [
                    "Select a variable"
                ]
                +
                st.session_state[
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

        if item[
            "type"
        ] == "Contact":

            continue

        st.html(
            f"""
            <div class="section-card">

                <b>{question}</b>

            </div>
            """
        )

        col1, col2 = (
            st.columns(
                [6, 1]
            )
        )

        with col1:

            st.html(
                    f"""
                    <span class="badge badge-{item['type'].lower()}">
                        {item['type']}
                    </span>
                    """
                )

        with col2:

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

        base_options = [
            "All Respondents"
        ] + [
            x[
                "question"
            ]

            for x
            in metadata

            if (
                x[
                    "question"
                ]
                != question

                and x[
                    "type"
                ]
                in [
                    "SA",
                    "MA"
                ]
            )
        ]

        selected_base = (
            st.selectbox(
                "Base Variable",
                base_options,
                key=
                    f"routing_base_{index}"
            )
        )

        if (
            selected_base
            == "All Respondents"
        ):

            routing_config[
                question
            ] = {
                "base_question":
                    "All Respondents",

                "values":
                    []
            }

        else:

            base_item = (
                get_question_metadata(
                    metadata,
                    selected_base
                )
            )

            if base_item is None:
                continue

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
    ] = (
        routing_config
    )

    if st.button(
        "✅ Apply Routing",
        type="primary",
        use_container_width=True
    ):

        st.session_state[
            "applied_routing_config"
        ] = (
            routing_config.copy()
        )

        st.session_state[
            "crosstab_results"
        ] = []

        st.success(
            "Routing configuration applied successfully."
        )

    continue_button(
        4
    )


# ============================================================
# CROSSTAB
# ============================================================

elif selected_step == "📊 Crosstab":

    st.header(
        "📊 Crosstab"
    )

    st.caption(
        "Create up to 10 crosstab configurations."
    )

    crosstab_variables = [
        item[
            "question"
        ]
        for item
        in metadata
        if (
            item[
                "type"
            ]
            in [
                "SA",
                "MA"
            ]
            and
            item[
                "question"
            ]
            in st.session_state[
                "active_questions"
            ]
        )
    ]

    crosstab_configs = []

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
                        + crosstab_variables,
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
                        + crosstab_variables,
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

            if (
                column_question
                != "Select Variable"
            ):

                column_item = (
                    get_question_metadata(
                        metadata,
                        column_question
                    )
                )

                if (
                    column_item
                    and
                    column_item[
                        "type"
                    ]
                    == "MA"
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

            if (
                row_question
                != "Select Variable"
                and
                column_question
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
                    row_item[
                        "type"
                    ]
                )

                column_type = (
                    column_item[
                        "type"
                    ]
                )

                if (
                    row_type == "SA"
                    and
                    column_type
                    in [
                        "SA",
                        "MA"
                    ]
                ):

                    crosstab_configs.append(
                        {
                            "name":
                                (
                                    crosstab_name.strip()
                                    or
                                    f"Crosstab {index + 1}"
                                ),

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

    if st.button(
        "🚀 Apply All Crosstabs",
        type="primary",
        use_container_width=True
    ):

        results = []

        analysis_base_df = (
            apply_global_filters(
                st.session_state[
                    "analysis_df"
                ],
                metadata,
                st.session_state[
                    "global_filters"
                ]
            )
        )

        for config in (
            crosstab_configs
        ):

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
                    analysis_base_df,
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
        ] = (
            results
        )

        st.success(
            f"{len(results)} crosstab(s) "
            f"applied successfully."
        )

    continue_button(
        5
    )


# ============================================================
# ANALYZE RESULT
# ============================================================

elif selected_step == "📈 Analyze Result":

    st.header(
        "📈 Analyze Result"
    )

    analysis_base_df = (
        apply_global_filters(
            st.session_state[
                "analysis_df"
            ],
            metadata,
            st.session_state[
                "global_filters"
            ]
        )
    )

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

        filtered_df = (
            get_filtered_df(
                analysis_base_df,
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
        ] = (
            result
        )

    st.session_state[
        "variable_analysis_result"
    ] = (
        all_results
    )

    st.subheader(
        "Analysis Summary"
    )

    total_cleaned = (
        len(
            analysis_base_df
        )
    )

    total_variables = (
        len(
            all_results
        )
    )

    total_open = sum(
        1
        for result
        in all_results.values()
        if result[
            "type"
        ]
        == "Open"
    )

    total_crosstabs = (
        len(
            st.session_state[
                "crosstab_results"
            ]
        )
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

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

    for column, label, value in (
        scorecards
    ):

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
    # VARIABLE ANALYSIS
    # ========================================================

    st.subheader(
        "Variable Analysis"
    )

    chart_questions = []

    for question, result in (
        all_results.items()
    ):

        item = (
            get_question_metadata(
                metadata,
                question
            )
        )

        if item is None:
            continue

        question_type = (
            str(
                item.get(
                    "type",
                    ""
                )
            )
            .strip()
            .lower()
        )

        result_type = (
            str(
                result.get(
                    "type",
                    ""
                )
            )
            .strip()
            .lower()
        )

        # ONLY SA / MA CAN BECOME CHART
        if question_type not in [
            "sa",
            "ma"
        ]:
            continue

        if result_type not in [
            "sa",
            "ma"
        ]:
            continue

        result_df = (
            result.get(
                "result",
                pd.DataFrame()
            )
        )

        if result_df.empty:
            continue

        required_columns = {
            "Option",
            "Absolute",
            "Percentage"
        }

        if not required_columns.issubset(
            result_df.columns
        ):
            continue

        chart_questions.append(
            question
        )

    for start in range(
        0,
        len(
            chart_questions
        ),
        2
    ):

        row_questions = (
            chart_questions[
                start:
                start + 2
            ]
        )

        chart_columns = (
            st.columns(
                len(
                    row_questions
                )
            )
        )

        for column, question in zip(
            chart_columns,
            row_questions
        ):

            result = (
                all_results[
                    question
                ]
            )

            result_df = (
                result[
                    "result"
                ]
            )

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

                render_variable_chart(
                    result_df
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
                item[
                    "result"
                ]
            )

            title = (
                item.get(
                    "name",
                    f"Crosstab {index + 1}"
                )
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
                result[
                    "percentage"
                ]
                .copy()
                .round(1)
            )

            if not percentage_df.empty:

                render_crosstab_chart(
                    percentage_df
                )

            with st.expander(
                "View Absolute Results"
            ):

                st.dataframe(
                    result[
                        "absolute"
                    ],
                    use_container_width=True,
                    hide_index=False
                )

            with st.expander(
                "View Percentage Results"
            ):

                st.dataframe(
                    result[
                        "percentage"
                    ]
                    .round(1),
                    use_container_width=True,
                    hide_index=False
                )

    # ========================================================
    # OPEN FEEDBACK
    # ========================================================

    st.divider()

    st.subheader(
        "💬 Open Feedback"
    )

    st.caption(
        "Open-ended suggestions and feedback "
        "from respondents."
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

        if (
            str(
                item.get(
                    "type",
                    ""
                )
            )
            .strip()
            .lower()
            != "open"
        ):
            continue

        if not item.get(
            "is_feedback",
            False
        ):
            continue

        filtered_df = (
            get_filtered_df(
                analysis_base_df,
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

    if not feedback_list:

        st.info(
            "No open-ended feedback available."
        )

    else:

        final_feedback_df = (
            pd.concat(
                feedback_list,
                ignore_index=True
            )
        )

        final_feedback_df = (
            final_feedback_df[
                final_feedback_df[
                    "Open Feedback"
                ]
                .notna()
            ]
            .copy()
        )

        final_feedback_df[
            "Open Feedback"
        ] = (
            final_feedback_df[
                "Open Feedback"
            ]
            .astype(str)
            .str.strip()
        )

        final_feedback_df = (
            final_feedback_df[
                final_feedback_df[
                    "Open Feedback"
                ]
                != ""
            ]
            .reset_index(
                drop=True
            )
        )

        st.caption(
            f"{len(final_feedback_df):,} "
            f"open feedback response(s)"
        )

        feedback_html = (
            '<div class="feedback-container">'
        )

        for index, row in (
            final_feedback_df
            .iterrows()
        ):

            question_text = (
                str(
                    row[
                        "Question"
                    ]
                )
                .strip()
            )

            feedback_text = (
                str(
                    row[
                        "Open Feedback"
                    ]
                )
                .strip()
            )

            feedback_html += f"""
            <div class="feedback-card">

                <div class="feedback-number">
                    Response {index + 1}
                </div>

                <div class="feedback-question">
                    {question_text}
                </div>

                <div class="feedback-text">
                    {feedback_text}
                </div>

            </div>
            """

        feedback_html += (
            "</div>"
        )

        st.html(
            feedback_html,
        )

    continue_button(
        6
    )


# ============================================================
# DOWNLOAD
# ============================================================

elif selected_step == "📥 Download":

    st.header(
        "📥 Download Result"
    )

    st.caption(
        "Export your cleaned dataset and analysis "
        "into one Excel workbook."
    )

    def generate_excel():

        output = (
            BytesIO()
        )

        export_analysis_df = (
            apply_global_filters(
                st.session_state[
                    "analysis_df"
                ],
                metadata,
                st.session_state[
                    "global_filters"
                ]
            )
        )

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            # =================================================
            # 1. RAW DATA
            # =================================================

            raw_export_df = (
                prepare_excel_df(
                    raw_df
                )
            )

            raw_export_df.to_excel(
                writer,
                sheet_name=
                    "1_Raw_Data",
                index=False
            )

            # =================================================
            # 2. VARIABLE ANALYSIS
            # =================================================

            variable_sheet = (
                "2_Variable_Analysis"
            )

            pd.DataFrame(
                {
                    "Question":
                        []
                }
            ).to_excel(
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

                filtered_df = (
                    get_filtered_df(
                        export_analysis_df,
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

                header_df = (
                    pd.DataFrame(
                        {
                            "Question":
                                [
                                    question
                                ],

                            "Type":
                                [
                                    result[
                                        "type"
                                    ]
                                ],

                            "Base N":
                                [
                                    result[
                                        "base_n"
                                    ]
                                ]
                        }
                    )
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
            # 3. CROSSTAB
            # =================================================

            crosstab_sheet = (
                "3_Crosstab"
            )

            pd.DataFrame(
                {
                    "Crosstab":
                        []
                }
            ).to_excel(
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

                title = (
                    item.get(
                        "name",
                        f"Crosstab {index + 1}"
                    )
                )

                pd.DataFrame(
                    {
                        "Crosstab":
                            [
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

                pd.DataFrame(
                    {
                        "Row Variable":
                            [
                                item[
                                    "row_question"
                                ]
                            ],

                        "Column Variable":
                            [
                                item[
                                    "column_question"
                                ]
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

                if item.get(
                    "column_option"
                ):

                    pd.DataFrame(
                        {
                            "MA Option":
                                [
                                    item[
                                        "column_option"
                                    ]
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

                result = (
                    item[
                        "result"
                    ]
                )

                pd.DataFrame(
                    {
                        "Base N":
                            [
                                result[
                                    "base_n"
                                ]
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

                if not absolute_df.empty:

                    pd.DataFrame(
                        {
                            "Result Type":
                                [
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

                percentage_df = (
                    result[
                        "percentage"
                    ]
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
                            "Result Type":
                                [
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
                        + 3
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

                item = (
                    get_question_metadata(
                        metadata,
                        question
                    )
                )

                if item is None:
                    continue

                if (
                    item[
                        "type"
                    ]
                    != "Open"
                    or
                    not item.get(
                        "is_feedback",
                        False
                    )
                ):

                    continue

                filtered_df = (
                    get_filtered_df(
                        export_analysis_df,
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

            open_feedback_df.to_excel(
                writer,
                sheet_name=
                    "4_Open_Feedback",
                index=False
            )

        output.seek(0)

        return output


    try:

        excel_file = (
            generate_excel()
        )

        st.success(
            "Your Excel report is ready."
        )

        st.download_button(
            "⬇️ Download Excel Result",

            data=
                excel_file,

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
