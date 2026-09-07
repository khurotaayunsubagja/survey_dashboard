import streamlit as st
import pandas as pd
import altair as alt
import hashlib

from io import BytesIO

try:
    import vl_convert as vlc
except ImportError:
    vlc = None

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
    collect_ma_other_details,
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
        line-height: 1.45;
        min-height: 46px;
    }

    .analysis-small {
        font-size: 12px;
        color: var(--text-color);
        opacity: 0.65;
    }

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
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 700;
        min-height: 42px;
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
    "selected_sheet": None,

    "source_file_bytes": None,
    "source_file_name": None,

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

    "comparison_result": None,

    "current_step": 0,
    "change_step_requested": False
}


for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# GENERAL HELPERS
# ============================================================

def make_widget_key(
    prefix,
    value
):

    digest = (
        hashlib.md5(
            str(value)
            .encode(
                "utf-8"
            )
        )
        .hexdigest()[:10]
    )

    return (
        f"{prefix}_{digest}"
    )


def get_sheet_names(
    file_bytes
):

    if not file_bytes:
        return []

    excel_file = pd.ExcelFile(
        BytesIO(
            file_bytes
        )
    )

    return excel_file.sheet_names


def percentage_to_text(
    value
):

    try:

        if pd.isna(value):
            return ""

        return (
            f"{float(value):.1f}%"
        )

    except (
        TypeError,
        ValueError
    ):

        return value


def chart_to_png(
    chart,
    title
):

    if vlc is None:
        return None

    export_chart = (
        chart
        .properties(
            title=alt.TitleParams(
                text=title,
                fontSize=18,
                fontWeight="bold",
                anchor="start",
                offset=18
            )
        )
    )

    spec = (
        export_chart
        .to_dict()
    )

    return (
        vlc.vegalite_to_png(
            spec,
            scale=2
        )
    )


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
        ] = next_step_index

        st.session_state[
            "change_step_requested"
        ] = True

        st.rerun()


# ============================================================
# VARIABLE CHART
# ============================================================

def render_variable_chart(
    result_df,
    question,
    chart_key
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

    if len(chart_df) == 2:

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
                    title=None
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

    else:

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
                height=max(
                    200,
                    len(chart_df) * 36
                )
            )
        )

    st.altair_chart(
        chart,
        use_container_width=True
    )

    png_data = (
        chart_to_png(
            chart,
            question
        )
    )

    if png_data is not None:

        st.download_button(
            "💾 Save Chart",
            data=
                png_data,
            file_name=
                f"{chart_key}.png",
            mime=
                "image/png",
            key=
                f"download_{chart_key}",
            use_container_width=True
        )


# ============================================================
# CROSSTAB CHART
# ============================================================

def render_crosstab_chart(
    percentage_df,
    chart_type,
    title,
    chart_key
):

    if percentage_df.empty:
        return

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

    if chart_type == "Stacked Bar":

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
                        "Percentage (%)",
                    stack="zero"
                ),

                y=alt.Y(
                    "Row Option:N",
                    title=None,
                    axis=alt.Axis(
                        labelLimit=400,
                        labelPadding=8
                    )
                ),

                color=alt.Color(
                    "Column Option:N",
                    title=None
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
                    250,
                    percentage_df.shape[0]
                    * 48
                )
            )
        )

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
                    title=None
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
                    250,
                    percentage_df.shape[0]
                    * 48
                )
            )
        )

    st.altair_chart(
        chart,
        use_container_width=True
    )

    png_data = (
        chart_to_png(
            chart,
            title
        )
    )

    if png_data is not None:

        st.download_button(
            "💾 Save Crosstab Chart",
            data=
                png_data,
            file_name=
                f"{chart_key}.png",
            mime=
                "image/png",
            key=
                f"download_{chart_key}",
            use_container_width=True
        )


# ============================================================
# COMPARISON HELPERS
# ============================================================

def build_comparison_df(
    current_result,
    comparison_result,
    current_label,
    comparison_label
):

    current_df = (
        current_result[
            "result"
        ]
        .copy()
    )

    comparison_df = (
        comparison_result[
            "result"
        ]
        .copy()
    )

    current_df = (
        current_df[
            [
                "Option",
                "Absolute",
                "Percentage"
            ]
        ]
    )

    comparison_df = (
        comparison_df[
            [
                "Option",
                "Absolute",
                "Percentage"
            ]
        ]
    )

    current_df[
        "Option Key"
    ] = (
        current_df[
            "Option"
        ]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    comparison_df[
        "Option Key"
    ] = (
        comparison_df[
            "Option"
        ]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    display_mapping = {}

    for _, row in current_df.iterrows():

        display_mapping[
            row[
                "Option Key"
            ]
        ] = row[
            "Option"
        ]

    for _, row in comparison_df.iterrows():

        if (
            row[
                "Option Key"
            ]
            not in display_mapping
        ):

            display_mapping[
                row[
                    "Option Key"
                ]
            ] = row[
                "Option"
            ]

    current_lookup = (
        current_df
        .set_index(
            "Option Key"
        )
    )

    comparison_lookup = (
        comparison_df
        .set_index(
            "Option Key"
        )
    )

    rows = []

    for option_key, option_name in (
        display_mapping.items()
    ):

        current_absolute = 0
        current_percentage = 0

        comparison_absolute = 0
        comparison_percentage = 0

        if option_key in current_lookup.index:

            current_row = (
                current_lookup.loc[
                    option_key
                ]
            )

            current_absolute = (
                float(
                    current_row[
                        "Absolute"
                    ]
                )
            )

            current_percentage = (
                float(
                    current_row[
                        "Percentage"
                    ]
                )
            )

        if (
            option_key
            in comparison_lookup.index
        ):

            comparison_row = (
                comparison_lookup.loc[
                    option_key
                ]
            )

            comparison_absolute = (
                float(
                    comparison_row[
                        "Absolute"
                    ]
                )
            )

            comparison_percentage = (
                float(
                    comparison_row[
                        "Percentage"
                    ]
                )
            )

        rows.append(
            {
                "Option":
                    option_name,

                f"{current_label} Absolute":
                    current_absolute,

                f"{comparison_label} Absolute":
                    comparison_absolute,

                f"{current_label} Percentage":
                    current_percentage,

                f"{comparison_label} Percentage":
                    comparison_percentage
            }
        )

    return pd.DataFrame(
        rows
    )


def render_comparison_chart(
    comparison_df,
    current_label,
    comparison_label,
    metric,
    chart_type,
    title,
    chart_key
):

    if comparison_df.empty:
        return

    if metric == "Percentage":

        current_column = (
            f"{current_label} Percentage"
        )

        comparison_column = (
            f"{comparison_label} Percentage"
        )

        axis_title = (
            "Percentage (%)"
        )

    else:

        current_column = (
            f"{current_label} Absolute"
        )

        comparison_column = (
            f"{comparison_label} Absolute"
        )

        axis_title = (
            "Absolute"
        )

    long_df = (
        comparison_df[
            [
                "Option",
                current_column,
                comparison_column
            ]
        ]
        .melt(
            id_vars=[
                "Option"
            ],
            var_name=
                "Dataset",
            value_name=
                "Value"
        )
    )

    long_df[
        "Dataset"
    ] = (
        long_df[
            "Dataset"
        ]
        .str.replace(
            " Percentage",
            "",
            regex=False
        )
        .str.replace(
            " Absolute",
            "",
            regex=False
        )
    )

    if chart_type == "Stacked Bar":

        chart = (
            alt.Chart(
                long_df
            )
            .mark_bar(
                cornerRadiusEnd=3
            )
            .encode(

                x=alt.X(
                    "Value:Q",
                    title=
                        axis_title,
                    stack="zero"
                ),

                y=alt.Y(
                    "Option:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(
                        labelLimit=400,
                        labelPadding=8
                    )
                ),

                color=alt.Color(
                    "Dataset:N",
                    title=None
                ),

                tooltip=[
                    alt.Tooltip(
                        "Option:N",
                        title="Option"
                    ),
                    alt.Tooltip(
                        "Dataset:N",
                        title="Dataset"
                    ),
                    alt.Tooltip(
                        "Value:Q",
                        title=
                            metric,
                        format=
                            ".1f"
                        if metric
                        == "Percentage"
                        else ",.0f"
                    )
                ]
            )
            .properties(
                height=max(
                    260,
                    len(
                        comparison_df
                    ) * 42
                )
            )
        )

    else:

        chart = (
            alt.Chart(
                long_df
            )
            .mark_bar(
                cornerRadiusEnd=3
            )
            .encode(

                x=alt.X(
                    "Value:Q",
                    title=
                        axis_title
                ),

                y=alt.Y(
                    "Option:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(
                        labelLimit=400,
                        labelPadding=8
                    )
                ),

                yOffset=
                    "Dataset:N",

                color=alt.Color(
                    "Dataset:N",
                    title=None
                ),

                tooltip=[
                    alt.Tooltip(
                        "Option:N",
                        title="Option"
                    ),
                    alt.Tooltip(
                        "Dataset:N",
                        title="Dataset"
                    ),
                    alt.Tooltip(
                        "Value:Q",
                        title=
                            metric,
                        format=
                            ".1f"
                        if metric
                        == "Percentage"
                        else ",.0f"
                    )
                ]
            )
            .properties(
                height=max(
                    260,
                    len(
                        comparison_df
                    ) * 42
                )
            )
        )

    st.altair_chart(
        chart,
        use_container_width=True
    )

    png_data = (
        chart_to_png(
            chart,
            title
        )
    )

    if png_data is not None:

        st.download_button(
            "💾 Save Comparison Chart",
            data=
                png_data,
            file_name=
                f"{chart_key}.png",
            mime=
                "image/png",
            key=
                f"download_{chart_key}",
            use_container_width=True
        )


# ============================================================
# PREPARE EXCEL
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

                text = (
                    str(part)
                    .strip()
                )

                if not text:
                    continue

                if text.lower() == "nan":
                    continue

                if (
                    text.lower()
                    .startswith(
                        "unnamed:"
                    )
                ):
                    continue

                parts.append(
                    text
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
            compare datasets, and generate reports.
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

    selected_sheet = None

    if uploaded_file is not None:

        try:

            uploaded_bytes = (
                uploaded_file
                .getvalue()
            )

            sheet_names = (
                get_sheet_names(
                    uploaded_bytes
                )
            )

            selected_sheet = (
                st.selectbox(
                    "Select Sheet",
                    sheet_names
                )
            )

        except Exception as error:

            st.error(
                f"Failed to read sheets: "
                f"{error}"
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
            f"Sheet: "
            f"{st.session_state['selected_sheet']}"
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

    elif selected_sheet is None:

        st.warning(
            "Please select a sheet."
        )

    else:

        try:

            source_bytes = (
                uploaded_file
                .getvalue()
            )

            (
                raw_df,
                analysis_df,
                metadata,
                respondent_count

            ) = load_survey_data(
                BytesIO(
                    source_bytes
                ),
                platform,
                selected_sheet
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
                "selected_sheet"
            ] = selected_sheet

            st.session_state[
                "source_file_bytes"
            ] = source_bytes

            st.session_state[
                "source_file_name"
            ] = uploaded_file.name

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
                "comparison_result"
            ] = None

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
        "Upload an Excel file, "
        "select a sheet, then click Load Data."
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
# NAVIGATION
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

    col1, col2, col3, col4, col5 = (
        st.columns(5)
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
            "Sheet",
            st.session_state[
                "selected_sheet"
            ]
        ),
        (
            col3,
            "Respondents",
            f"{len(analysis_df):,}"
        ),
        (
            col4,
            "Questions",
            f"{total_questions}"
        ),
        (
            col5,
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

    st.dataframe(
        pd.DataFrame(
            overview_rows
        ),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "Raw Data Preview"
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
                + contact_questions,
                key=
                    "duplicate_contact_question"
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
                    "Please select a contact variable."
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
                "No duplicate contacts remain."
            )

        duplicate_df = (
            st.session_state[
                "duplicate_df"
            ]
        )

        if (
            duplicate_df is not None
            and
            not duplicate_df.empty
        ):

            st.subheader(
                "Duplicate Responses"
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
                hide_index=True
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
                    "Rows to Delete",
                    options=
                        available_indices,
                    format_func=
                        lambda index:
                        (
                            f"Row {index + 1} — "
                            f"{contact_mapping.get(index, '')}"
                        ),
                    key=
                        "duplicate_rows_to_delete"
                )
            )

            if st.button(
                "🗑️ Execute Delete",
                type="primary",
                use_container_width=True
            ):

                if not selected_rows:

                    st.warning(
                        "Select at least one row."
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
                            st.session_state[
                                "duplicate_question"
                            ]
                        )
                    )

                    remaining = (
                        detect_contact_duplicates(
                            st.session_state[
                                "analysis_df"
                            ],
                            item
                        )
                    )

                    st.session_state[
                        "duplicate_df"
                    ] = remaining

                    st.session_state[
                        "duplicate_cleared"
                    ] = (
                        remaining.empty
                    )

                    st.session_state[
                        "crosstab_results"
                    ] = []

                    st.session_state[
                        "comparison_result"
                    ] = None

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
        ] = filter_config

        st.session_state[
            "crosstab_results"
        ] = []

        st.session_state[
            "comparison_result"
        ] = None

        st.success(
            "Filtering applied."
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

    if (
        st.session_state[
            "removed_questions"
        ]
    ):

        restore_question = (
            st.selectbox(
                "Restore Variable",
                [
                    "Select a variable"
                ]
                +
                st.session_state[
                    "removed_questions"
                ],
                key=
                    "restore_variable"
            )
        )

        if st.button(
            "↩️ Restore Variable"
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

    for question in list(
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
                key=make_widget_key(
                    "remove_question",
                    question
                )
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
            item2[
                "question"
            ]
            for item2
            in metadata
            if (
                item2[
                    "question"
                ]
                != question
                and
                item2[
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
                key=make_widget_key(
                    "routing_base",
                    question
                )
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

            selected_values = (
                st.multiselect(
                    "Routing Values",
                    base_item[
                        "options"
                    ],
                    key=make_widget_key(
                        "routing_values",
                        question
                    )
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

    if st.button(
        "✅ Apply Routing",
        type="primary",
        use_container_width=True
    ):

        st.session_state[
            "applied_routing_config"
        ] = {
            key: {
                "base_question":
                    value.get(
                        "base_question"
                    ),

                "values":
                    list(
                        value.get(
                            "values",
                            []
                        )
                    )
            }
            for key, value
            in routing_config.items()
        }

        st.session_state[
            "crosstab_results"
        ] = []

        st.session_state[
            "comparison_result"
        ] = None

        st.success(
            "Routing applied."
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
        "Supported combinations: "
        "SA × SA and SA × MA."
    )

    row_variables = [
        item[
            "question"
        ]
        for item
        in metadata
        if (
            item[
                "type"
            ]
            == "SA"
            and
            item[
                "question"
            ]
            in st.session_state[
                "active_questions"
            ]
        )
    ]

    column_variables = [
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

            name = (
                st.text_input(
                    "Crosstab Name",
                    value=
                        f"Crosstab {index + 1}",
                    key=
                        f"ct_name_{index}"
                )
            )

            col1, col2 = (
                st.columns(2)
            )

            with col1:

                row_question = (
                    st.selectbox(
                        "Row Variable",
                        [
                            "Select Variable"
                        ]
                        + row_variables,
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
                        + column_variables,
                        key=
                            f"ct_column_{index}"
                    )
                )

            chart_type = (
                st.selectbox(
                    "Chart Type",
                    [
                        "Grouped Bar",
                        "Stacked Bar"
                    ],
                    key=
                        f"ct_chart_type_{index}"
                )
            )

            if (
                row_question
                != "Select Variable"
                and
                column_question
                != "Select Variable"
            ):

                crosstab_configs.append(
                    {
                        "name":
                            (
                                name.strip()
                                or
                                f"Crosstab {index + 1}"
                            ),

                        "row_question":
                            row_question,

                        "column_question":
                            column_question,

                        "chart_type":
                            chart_type
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
                        column_item
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

    filtered_data_by_question = {}

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

        filtered_data_by_question[
            question
        ] = filtered_df

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
    # VARIABLE ANALYSIS
    # ========================================================

    st.subheader(
        "Variable Analysis"
    )

    chart_questions = []

    for question, result in (
        all_results.items()
    ):

        if (
            result[
                "type"
            ]
            not in [
                "SA",
                "MA"
            ]
        ):
            continue

        result_df = (
            result.get(
                "result",
                pd.DataFrame()
            )
        )

        if result_df.empty:
            continue

        chart_questions.append(
            question
        )

    for start in range(
        0,
        len(chart_questions),
        2
    ):

        row_questions = (
            chart_questions[
                start:
                start + 2
            ]
        )

        columns = (
            st.columns(
                len(
                    row_questions
                )
            )
        )

        for column, question in zip(
            columns,
            row_questions
        ):

            result = (
                all_results[
                    question
                ]
            )

            item = (
                get_question_metadata(
                    metadata,
                    question
                )
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
                    result[
                        "result"
                    ],
                    question,
                    make_widget_key(
                        "variable_chart",
                        question
                    )
                )

                if (
                    result[
                        "type"
                    ]
                    == "MA"
                    and
                    "Lainnya"
                    in item.get(
                        "options",
                        []
                    )
                ):

                    other_df = (
                        collect_ma_other_details(
                            filtered_data_by_question[
                                question
                            ],
                            item
                        )
                    )

                    if not other_df.empty:

                        with st.expander(
                            f"🔎 Lihat isi Lainnya "
                            f"({len(other_df):,})"
                        ):

                            st.dataframe(
                                other_df,
                                use_container_width=True,
                                hide_index=True
                            )

    # ========================================================
    # CROSSTAB ANALYSIS
    # ========================================================

    st.divider()

    st.subheader(
        "Crosstab Analysis"
    )

    if not st.session_state[
        "crosstab_results"
    ]:

        st.info(
            "No crosstab results available."
        )

    else:

        for index, item in enumerate(
            st.session_state[
                "crosstab_results"
            ]
        ):

            result = (
                item[
                    "result"
                ]
            )

            title = (
                item[
                    "name"
                ]
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

            render_crosstab_chart(
                result[
                    "percentage"
                ],
                item.get(
                    "chart_type",
                    "Grouped Bar"
                ),
                title,
                f"crosstab_{index + 1}"
            )

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
                    ]
                    .round(1),
                    use_container_width=True
                )

    # ========================================================
    # COMPARISON ANALYSIS
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Comparison Analysis"
    )

    st.caption(
        "Compare the currently loaded sheet "
        "with another sheet or another survey file."
    )

    current_label = (
        st.text_input(
            "Current Dataset Label",
            value=
                st.session_state[
                    "selected_sheet"
                ],
            key=
                "comparison_current_label"
        )
    )

    comparison_source = (
        st.radio(
            "Comparison Source",
            [
                "Another Sheet from Current File",
                "Upload Another File"
            ],
            key=
                "comparison_source"
        )
    )

    comparison_df = None
    comparison_metadata = None
    comparison_sheet = None
    comparison_label_default = (
        "Comparison"
    )

    if (
        comparison_source
        == "Another Sheet from Current File"
    ):

        all_sheets = (
            get_sheet_names(
                st.session_state[
                    "source_file_bytes"
                ]
            )
        )

        comparison_sheets = [
            sheet
            for sheet
            in all_sheets
            if sheet
            != st.session_state[
                "selected_sheet"
            ]
        ]

        if not comparison_sheets:

            st.info(
                "No other sheet is available "
                "in the current file."
            )

        else:

            comparison_sheet = (
                st.selectbox(
                    "Comparison Sheet",
                    comparison_sheets,
                    key=
                        "comparison_sheet"
                )
            )

            comparison_label_default = (
                comparison_sheet
            )

            try:

                (
                    comparison_raw_df,
                    comparison_df,
                    comparison_metadata,
                    comparison_n

                ) = load_survey_data(
                    BytesIO(
                        st.session_state[
                            "source_file_bytes"
                        ]
                    ),
                    st.session_state[
                        "platform"
                    ],
                    comparison_sheet
                )

            except Exception as error:

                st.error(
                    f"Failed to load comparison sheet: "
                    f"{error}"
                )

    else:

        comparison_platform = (
            st.selectbox(
                "Comparison Survey Platform",
                [
                    "SurveyMonkey",
                    "Google Forms"
                ],
                index=(
                    0
                    if st.session_state[
                        "platform"
                    ]
                    == "SurveyMonkey"
                    else 1
                ),
                key=
                    "comparison_platform"
            )
        )

        comparison_file = (
            st.file_uploader(
                "Upload Comparison File",
                type=[
                    "xlsx",
                    "xls"
                ],
                key=
                    "comparison_file"
            )
        )

        if comparison_file is not None:

            try:

                comparison_bytes = (
                    comparison_file
                    .getvalue()
                )

                comparison_sheets = (
                    get_sheet_names(
                        comparison_bytes
                    )
                )

                comparison_sheet = (
                    st.selectbox(
                        "Comparison Sheet",
                        comparison_sheets,
                        key=
                            "comparison_uploaded_sheet"
                    )
                )

                comparison_label_default = (
                    comparison_sheet
                )

                (
                    comparison_raw_df,
                    comparison_df,
                    comparison_metadata,
                    comparison_n

                ) = load_survey_data(
                    BytesIO(
                        comparison_bytes
                    ),
                    comparison_platform,
                    comparison_sheet
                )

            except Exception as error:

                st.error(
                    f"Failed to load comparison file: "
                    f"{error}"
                )

    comparison_label = (
        st.text_input(
            "Comparison Dataset Label",
            value=
                comparison_label_default,
            key=
                "comparison_label"
        )
    )

    current_variables = [
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

    if (
        comparison_df is not None
        and
        comparison_metadata is not None
    ):

        comparison_variables = [
            item[
                "question"
            ]
            for item
            in comparison_metadata
            if item[
                "type"
            ]
            in [
                "SA",
                "MA"
            ]
        ]

        col1, col2 = (
            st.columns(2)
        )

        with col1:

            current_question = (
                st.selectbox(
                    "Current Variable",
                    current_variables,
                    key=
                        "comparison_current_question"
                )
            )

        with col2:

            default_index = 0

            if (
                current_question
                in comparison_variables
            ):

                default_index = (
                    comparison_variables.index(
                        current_question
                    )
                )

            comparison_question = (
                st.selectbox(
                    "Comparison Variable",
                    comparison_variables,
                    index=
                        default_index,
                    key=
                        "comparison_question"
                )
            )

        col3, col4 = (
            st.columns(2)
        )

        with col3:

            comparison_metric = (
                st.selectbox(
                    "Metric",
                    [
                        "Percentage",
                        "Absolute"
                    ],
                    key=
                        "comparison_metric"
                )
            )

        with col4:

            comparison_chart_type = (
                st.selectbox(
                    "Chart Type",
                    [
                        "Grouped Bar",
                        "Stacked Bar"
                    ],
                    key=
                        "comparison_chart_type"
                )
            )

        if st.button(
            "🚀 Generate Comparison",
            type="primary",
            use_container_width=True
        ):

            current_item = (
                get_question_metadata(
                    metadata,
                    current_question
                )
            )

            comparison_item = (
                get_question_metadata(
                    comparison_metadata,
                    comparison_question
                )
            )

            if (
                current_item[
                    "type"
                ]
                != comparison_item[
                    "type"
                ]
            ):

                st.error(
                    "Comparison variable types must match. "
                    "Use SA vs SA or MA vs MA."
                )

            else:

                current_filtered_df = (
                    get_filtered_df(
                        analysis_base_df,
                        current_question,
                        metadata,
                        st.session_state[
                            "applied_routing_config"
                        ]
                    )
                )

                current_result = (
                    calculate_variable_analysis(
                        current_filtered_df,
                        current_item
                    )
                )

                comparison_variable_result = (
                    calculate_variable_analysis(
                        comparison_df,
                        comparison_item
                    )
                )

                comparison_table = (
                    build_comparison_df(
                        current_result,
                        comparison_variable_result,
                        current_label,
                        comparison_label
                    )
                )

                current_other_df = (
                    collect_ma_other_details(
                        current_filtered_df,
                        current_item
                    )
                    if current_item[
                        "type"
                    ]
                    == "MA"
                    else pd.DataFrame()
                )

                comparison_other_df = (
                    collect_ma_other_details(
                        comparison_df,
                        comparison_item
                    )
                    if comparison_item[
                        "type"
                    ]
                    == "MA"
                    else pd.DataFrame()
                )

                st.session_state[
                    "comparison_result"
                ] = {
                    "table":
                        comparison_table,

                    "current_label":
                        current_label,

                    "comparison_label":
                        comparison_label,

                    "current_question":
                        current_question,

                    "comparison_question":
                        comparison_question,

                    "metric":
                        comparison_metric,

                    "chart_type":
                        comparison_chart_type,

                    "current_base_n":
                        current_result[
                            "base_n"
                        ],

                    "comparison_base_n":
                        comparison_variable_result[
                            "base_n"
                        ],

                    "current_other_df":
                        current_other_df,

                    "comparison_other_df":
                        comparison_other_df
                }

    saved_comparison = (
        st.session_state[
            "comparison_result"
        ]
    )

    if saved_comparison:

        st.divider()

        comparison_title = (
            f"{saved_comparison['current_question']} — "
            f"{saved_comparison['current_label']} "
            f"vs "
            f"{saved_comparison['comparison_label']}"
        )

        st.html(
            f"""
            <div class="analysis-card">

                <div class="analysis-question">
                    {comparison_title}
                </div>

                <div class="analysis-small">
                    {saved_comparison["current_label"]}
                    Base N:
                    {saved_comparison["current_base_n"]}
                    &nbsp; • &nbsp;
                    {saved_comparison["comparison_label"]}
                    Base N:
                    {saved_comparison["comparison_base_n"]}
                </div>

            </div>
            """
        )

        render_comparison_chart(
            saved_comparison[
                "table"
            ],
            saved_comparison[
                "current_label"
            ],
            saved_comparison[
                "comparison_label"
            ],
            saved_comparison[
                "metric"
            ],
            saved_comparison[
                "chart_type"
            ],
            comparison_title,
            "comparison_chart"
        )

        with st.expander(
            "View Comparison Table"
        ):

            display_comparison = (
                saved_comparison[
                    "table"
                ]
                .copy()
            )

            percentage_columns = [
                column
                for column
                in display_comparison.columns
                if "Percentage"
                in column
            ]

            for column in (
                percentage_columns
            ):

                display_comparison[
                    column
                ] = (
                    display_comparison[
                        column
                    ]
                    .round(1)
                )

            st.dataframe(
                display_comparison,
                use_container_width=True,
                hide_index=True
            )

        if (
            not saved_comparison[
                "current_other_df"
            ].empty
        ):

            with st.expander(
                f"🔎 "
                f"{saved_comparison['current_label']} "
                f"— Lainnya"
            ):

                st.dataframe(
                    saved_comparison[
                        "current_other_df"
                    ],
                    use_container_width=True,
                    hide_index=True
                )

        if (
            not saved_comparison[
                "comparison_other_df"
            ].empty
        ):

            with st.expander(
                f"🔎 "
                f"{saved_comparison['comparison_label']} "
                f"— Lainnya"
            ):

                st.dataframe(
                    saved_comparison[
                        "comparison_other_df"
                    ],
                    use_container_width=True,
                    hide_index=True
                )

    # ========================================================
    # OPEN FEEDBACK
    # ========================================================

    st.divider()

    st.subheader(
        "💬 Open Feedback"
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

        if item[
            "type"
        ] != "Open":
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

        feedback_html = (
            '<div class="feedback-container">'
        )

        for index, row in (
            final_feedback_df.iterrows()
        ):

            feedback_html += f"""
            <div class="feedback-card">

                <div class="feedback-number">
                    Response {index + 1}
                </div>

                <div class="feedback-question">
                    {row["Question"]}
                </div>

                <div class="feedback-text">
                    {row["Open Feedback"]}
                </div>

            </div>
            """

        feedback_html += (
            "</div>"
        )

        st.html(
            feedback_html
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
            # RAW DATA
            # =================================================

            prepare_excel_df(
                raw_df
            ).to_excel(
                writer,
                sheet_name=
                    "1_Raw_Data",
                index=False
            )

            # =================================================
            # VARIABLE ANALYSIS
            # =================================================

            variable_sheet = (
                "2_Variable_Analysis"
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

                result_df = (
                    prepare_excel_df(
                        result[
                            "result"
                        ]
                    )
                )

                if (
                    "Percentage"
                    in result_df.columns
                ):

                    result_df[
                        "Percentage"
                    ] = (
                        result_df[
                            "Percentage"
                        ]
                        .apply(
                            percentage_to_text
                        )
                    )

                if not result_df.empty:

                    result_df.to_excel(
                        writer,
                        sheet_name=
                            variable_sheet,
                        startrow=
                            row_position,
                        index=False
                    )

                    row_position += (
                        len(
                            result_df
                        )
                        + 3
                    )

            # =================================================
            # CROSSTAB
            # =================================================

            crosstab_sheet = (
                "3_Crosstab"
            )

            row_position = 0

            for index, item in enumerate(
                st.session_state[
                    "crosstab_results"
                ]
            ):

                result = (
                    item[
                        "result"
                    ]
                )

                pd.DataFrame(
                    {
                        "Crosstab":
                            [
                                item[
                                    "name"
                                ]
                            ],
                        "Row":
                            [
                                item[
                                    "row_question"
                                ]
                            ],
                        "Column":
                            [
                                item[
                                    "column_question"
                                ]
                            ],
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
                    prepare_excel_df(
                        result[
                            "absolute"
                        ]
                        .reset_index()
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

                percentage_df = (
                    result[
                        "percentage"
                    ]
                    .reset_index()
                )

                for column in (
                    percentage_df.columns[
                        1:
                    ]
                ):

                    percentage_df[
                        column
                    ] = (
                        percentage_df[
                            column
                        ]
                        .apply(
                            percentage_to_text
                        )
                    )

                prepare_excel_df(
                    percentage_df
                ).to_excel(
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
            # OPEN FEEDBACK
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

            # =================================================
            # OTHER RESPONSES
            # =================================================

            other_results = []

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

                if item[
                    "type"
                ] != "MA":
                    continue

                other_df = (
                    collect_ma_other_details(
                        export_analysis_df,
                        item
                    )
                )

                if other_df.empty:
                    continue

                other_df = (
                    other_df.copy()
                )

                other_df.insert(
                    0,
                    "Question",
                    question
                )

                other_results.append(
                    other_df
                )

            if other_results:

                other_export_df = (
                    pd.concat(
                        other_results,
                        ignore_index=True
                    )
                )

            else:

                other_export_df = (
                    pd.DataFrame(
                        columns=[
                            "Question",
                            "Other Response"
                        ]
                    )
                )

            other_export_df.to_excel(
                writer,
                sheet_name=
                    "5_Other_Responses",
                index=False
            )

            # =================================================
            # COMPARISON
            # =================================================

            if (
                st.session_state[
                    "comparison_result"
                ]
            ):

                comparison_export = (
                    st.session_state[
                        "comparison_result"
                    ][
                        "table"
                    ]
                    .copy()
                )

                for column in (
                    comparison_export.columns
                ):

                    if (
                        "Percentage"
                        in column
                    ):

                        comparison_export[
                            column
                        ] = (
                            comparison_export[
                                column
                            ]
                            .apply(
                                percentage_to_text
                            )
                        )

                comparison_export.to_excel(
                    writer,
                    sheet_name=
                        "6_Comparison",
                    index=False
                )

        output.seek(0)

        return output


    try:

        excel_file = (
            generate_excel()
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
            f"Failed to generate report: "
            f"{error}"
        )
