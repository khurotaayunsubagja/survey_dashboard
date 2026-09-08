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
    detect_duplicates
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
# CHART COLORS
# ============================================================

CHART_COLORS = [
    "#2F80ED",
    "#56CCF2",
    "#27AE60",
    "#F2C94C",
    "#F2994A",
    "#EB5757",
    "#9B51E0",
    "#6FCF97",
    "#BB6BD9",
    "#828282"
]


# ============================================================
# CSS
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
            1px solid rgba(128,128,128,0.22);
    }

    .metric-label {
        font-size: 13px;
        opacity: 0.65;
        font-weight: 600;
        margin-bottom: 7px;
    }

    .metric-value {
        font-size: 26px;
        font-weight: 800;
        overflow-wrap: anywhere;
    }

    .section-card {
        background-color:
            var(--secondary-background-color);
        padding: 18px;
        border-radius: 16px;
        border:
            1px solid rgba(128,128,128,0.22);
        margin-bottom: 12px;
    }

    .analysis-card {
        background-color:
            var(--secondary-background-color);
        padding: 14px 18px;
        border-radius: 16px;
        border:
            1px solid rgba(128,128,128,0.22);
        margin-bottom: 12px;
    }

    .analysis-question {
        font-size: 16px;
        font-weight: 750;
        line-height: 1.45;
    }

    .analysis-small {
        font-size: 12px;
        opacity: 0.65;
        margin-top: 5px;
    }

    .feedback-container {
        height: 520px;
        overflow-y: auto;
        padding: 14px;
        border:
            1px solid rgba(128,128,128,0.22);
        border-radius: 16px;
    }

    .feedback-card {
        background-color:
            var(--background-color);
        border:
            1px solid rgba(128,128,128,0.18);
        border-radius: 12px;
        padding: 15px 17px;
        margin-bottom: 12px;
    }

    .feedback-number {
        font-size: 12px;
        font-weight: 700;
        opacity: 0.55;
    }

    .feedback-question {
        font-size: 13px;
        font-weight: 700;
        opacity: 0.75;
        font-style: italic;
        margin: 5px 0 8px 0;
    }

    .feedback-text {
        font-size: 15px;
        line-height: 1.65;
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
# HELPERS
# ============================================================

def make_widget_key(
    prefix,
    value
):

    digest = (
        hashlib.md5(
            str(value).encode("utf-8")
        )
        .hexdigest()[:10]
    )

    return f"{prefix}_{digest}"


def get_sheet_names(
    file_bytes
):

    if not file_bytes:
        return []

    excel_file = pd.ExcelFile(
        BytesIO(file_bytes)
    )

    return excel_file.sheet_names


def percentage_to_text(
    value
):

    try:

        if pd.isna(value):
            return ""

        return f"{float(value):.1f}%"

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

    return vlc.vegalite_to_png(
        export_chart.to_dict(),
        scale=2
    )


def continue_button(
    next_step_index
):

    st.divider()

    if st.button(
        "Continue to Next Step →",
        use_container_width=True,
        key=f"continue_{next_step_index}"
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

    chart_df["Absolute"] = (
        pd.to_numeric(
            chart_df["Absolute"],
            errors="coerce"
        )
        .fillna(0)
    )

    chart_df["Percentage"] = (
        pd.to_numeric(
            chart_df["Percentage"],
            errors="coerce"
        )
        .fillna(0)
    )

    if len(chart_df) == 2:

        chart = (
            alt.Chart(chart_df)
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
                        range=CHART_COLORS
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

    else:

        chart = (
            alt.Chart(chart_df)
            .mark_bar(
                cornerRadiusEnd=4
            )
            .encode(

                x=alt.X(
                    "Percentage:Q",
                    title="Percentage (%)"
                ),

                y=alt.Y(
                    "Option:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(
                        labelLimit=350
                    )
                ),

                color=alt.value(
                    CHART_COLORS[0]
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

    png = chart_to_png(
        chart,
        question
    )

    if png is not None:

        st.download_button(
            "💾 Save Chart",
            data=png,
            file_name=f"{chart_key}.png",
            mime="image/png",
            key=f"download_{chart_key}",
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
            alt.Chart(chart_df)
            .mark_bar()
            .encode(

                x=alt.X(
                    "Percentage:Q",
                    title="Percentage (%)",
                    stack="zero"
                ),

                y=alt.Y(
                    "Row Option:N",
                    title=None
                ),

                color=alt.Color(
                    "Column Option:N",
                    title=None,
                    scale=alt.Scale(
                        range=CHART_COLORS
                    )
                ),

                tooltip=[
                    "Row Option:N",
                    "Column Option:N",
                    alt.Tooltip(
                        "Percentage:Q",
                        format=".1f"
                    )
                ]
            )
            .properties(
                height=max(
                    250,
                    percentage_df.shape[0] * 48
                )
            )
        )

    else:

        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(

                x=alt.X(
                    "Percentage:Q",
                    title="Percentage (%)"
                ),

                y=alt.Y(
                    "Row Option:N",
                    title=None
                ),

                yOffset=
                    "Column Option:N",

                color=alt.Color(
                    "Column Option:N",
                    title=None,
                    scale=alt.Scale(
                        range=CHART_COLORS
                    )
                ),

                tooltip=[
                    "Row Option:N",
                    "Column Option:N",
                    alt.Tooltip(
                        "Percentage:Q",
                        format=".1f"
                    )
                ]
            )
            .properties(
                height=max(
                    250,
                    percentage_df.shape[0] * 48
                )
            )
        )

    st.altair_chart(
        chart,
        use_container_width=True
    )

    png = chart_to_png(
        chart,
        title
    )

    if png is not None:

        st.download_button(
            "💾 Save Crosstab Chart",
            data=png,
            file_name=f"{chart_key}.png",
            mime="image/png",
            key=f"download_{chart_key}",
            use_container_width=True
        )


# ============================================================
# MULTI COMPARISON DATA
# ============================================================

def build_multi_comparison_df(
    datasets
):

    option_mapping = {}
    option_order = []

    for dataset in datasets:

        result_df = (
            dataset[
                "result"
            ][
                "result"
            ]
        )

        for _, row in result_df.iterrows():

            option = str(
                row["Option"]
            ).strip()

            option_key = (
                option.lower()
            )

            if option_key not in option_mapping:

                option_mapping[
                    option_key
                ] = option

                option_order.append(
                    option_key
                )

    rows = []

    for dataset_index, dataset in enumerate(
        datasets
    ):

        result_df = (
            dataset[
                "result"
            ][
                "result"
            ]
            .copy()
        )

        result_df[
            "Option Key"
        ] = (
            result_df[
                "Option"
            ]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        result_lookup = (
            result_df
            .set_index(
                "Option Key"
            )
        )

        for option_index, option_key in enumerate(
            option_order
        ):

            option_name = (
                option_mapping[
                    option_key
                ]
            )

            absolute = 0
            percentage = 0

            if option_key in result_lookup.index:

                result_row = (
                    result_lookup.loc[
                        option_key
                    ]
                )

                if isinstance(
                    result_row,
                    pd.DataFrame
                ):

                    result_row = (
                        result_row.iloc[0]
                    )

                absolute = float(
                    result_row[
                        "Absolute"
                    ]
                )

                percentage = float(
                    result_row[
                        "Percentage"
                    ]
                )

            rows.append(
                {
                    "Dataset":
                        dataset[
                            "label"
                        ],

                    "Dataset Order":
                        dataset_index,

                    "Option":
                        option_name,

                    "Option Order":
                        option_index,

                    "Absolute":
                        absolute,

                    "Percentage":
                        percentage,

                    "Base N":
                        dataset[
                            "result"
                        ][
                            "base_n"
                        ]
                }
            )

    return pd.DataFrame(
        rows
    )


# ============================================================
# MULTI VERTICAL STACKED CHART
# ============================================================

def render_multi_comparison_chart(
    chart_df,
    metric,
    title,
    chart_key
):

    if chart_df.empty:
        return

    chart_df = (
        chart_df.copy()
    )

    if metric == "Percentage":

        chart_df[
            "Value"
        ] = (
            pd.to_numeric(
                chart_df[
                    "Percentage"
                ],
                errors="coerce"
            )
            .fillna(0)
        )

        chart_df[
            "Data Label"
        ] = (
            chart_df[
                "Value"
            ]
            .apply(
                lambda x:
                    f"{x:.1f}%"
            )
        )

        axis_title = (
            "Percentage (%)"
        )

        tooltip_format = (
            ".1f"
        )

    else:

        chart_df[
            "Value"
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
            "Data Label"
        ] = (
            chart_df[
                "Value"
            ]
            .apply(
                lambda x:
                    f"{x:,.0f}"
            )
        )

        axis_title = (
            "Absolute"
        )

        tooltip_format = (
            ",.0f"
        )

    dataset_order = (
        chart_df[
            [
                "Dataset",
                "Dataset Order"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            "Dataset Order"
        )[
            "Dataset"
        ]
        .tolist()
    )

    option_order = (
        chart_df[
            [
                "Option",
                "Option Order"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            "Option Order"
        )[
            "Option"
        ]
        .tolist()
    )

    bars = (
        alt.Chart(chart_df)
        .mark_bar(
            size=90
        )
        .encode(

            x=alt.X(
                "Dataset:N",
                title=None,
                sort=dataset_order,
                axis=alt.Axis(
                    labelAngle=0,
                    labelFontSize=13,
                    labelFontWeight="bold",
                    labelLimit=200
                )
            ),

            y=alt.Y(
                "Value:Q",
                title=axis_title,
                stack="zero"
            ),

            color=alt.Color(
                "Option:N",
                title=None,
                sort=option_order,
                scale=alt.Scale(
                    range=CHART_COLORS
                ),
                legend=alt.Legend(
                    orient="right",
                    labelLimit=450
                )
            ),

            order=alt.Order(
                "Option Order:Q",
                sort="ascending"
            ),

            tooltip=[
                alt.Tooltip(
                    "Dataset:N",
                    title="Dataset"
                ),
                alt.Tooltip(
                    "Option:N",
                    title="Category"
                ),
                alt.Tooltip(
                    "Value:Q",
                    title=metric,
                    format=
                        tooltip_format
                ),
                alt.Tooltip(
                    "Base N:Q",
                    title="Base N",
                    format=",.0f"
                )
            ]
        )
    )

    labels = (
        alt.Chart(chart_df)
        .mark_text(
            color="white",
            fontSize=11,
            fontWeight="bold",
            baseline="middle"
        )
        .encode(

            x=alt.X(
                "Dataset:N",
                sort=dataset_order
            ),

            y=alt.Y(
                "Value:Q",
                stack="center"
            ),

            detail=
                "Option:N",

            order=alt.Order(
                "Option Order:Q",
                sort="ascending"
            ),

            text=alt.Text(
                "Data Label:N"
            )
        )
    )

    chart = (
        bars
        +
        labels
    ).properties(
        height=500
    )

    st.altair_chart(
        chart,
        use_container_width=True
    )

    png = chart_to_png(
        chart,
        title
    )

    if png is not None:

        st.download_button(
            "💾 Save Comparison Chart",
            data=png,
            file_name=
                f"{chart_key}.png",
            mime="image/png",
            key=
                f"download_{chart_key}",
            use_container_width=True
        )


# ============================================================
# EXCEL HELPER
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
# HERO
# ============================================================

st.html(
    """
    <div class="hero">

        <div class="hero-title">
            📊 Survey Insight Dashboard
        </div>

        <div class="hero-subtitle">
            Survey processing, routing,
            crosstab, comparison and feedback analysis.
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
                f"Failed to read sheets: {error}"
            )

    load_button = (
        st.button(
            "🚀 Load Data",
            type="primary",
            use_container_width=True
        )
    )

    if (
        st.session_state[
            "data_loaded"
        ]
    ):

        st.divider()

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
            "Please upload an Excel file."
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
                f"Failed to load data: {error}"
            )


# ============================================================
# REQUIRE DATA
# ============================================================

if not st.session_state[
    "data_loaded"
]:

    st.info(
        "Upload file, pilih sheet, "
        "kemudian klik Load Data."
    )

    st.stop()


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
        label_visibility="collapsed",
        key="workflow_navigation"
    )
)

st.session_state[
    "current_step"
] = STEPS.index(
    selected_step
)


# ============================================================
# OVERVIEW
# ============================================================

if selected_step == "🏠 Overview":

    st.header(
        "Data Overview"
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    overview_metrics = [
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
            len(
                st.session_state[
                    "analysis_df"
                ]
            )
        ),
        (
            col4,
            "Questions",
            len(metadata)
        )
    ]

    for column, label, value in overview_metrics:

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

    rows = []

    for item in metadata:

        rows.append(
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
                                "question"
                            ]
                            in
                            st.session_state[
                                "active_questions"
                            ]
                        )

                        else "No"
                    )
            }
        )

    st.dataframe(
        pd.DataFrame(
            rows
        ),
        use_container_width=True,
        hide_index=True
    )

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

    st.caption(
        "Duplicate detection dapat menggunakan "
        "seluruh variable pada dataset."
    )

    duplicate_questions = [
        item[
            "question"
        ]
        for item
        in metadata
    ]

    selected_question = (
        st.selectbox(
            "Select Variable",
            [
                "Select a variable"
            ]
            +
            duplicate_questions,
            key=
                "duplicate_selected_question"
        )
    )

    if (
        selected_question
        != "Select a variable"
    ):

        selected_metadata = (
            get_question_metadata(
                metadata,
                selected_question
            )
        )

        st.caption(
            f"Variable Type: "
            f"{selected_metadata['type']}"
        )

    if st.button(
        "🔎 Detect Duplicates",
        type="primary",
        use_container_width=True
    ):

        if (
            selected_question
            ==
            "Select a variable"
        ):

            st.warning(
                "Please select a variable."
            )

        else:

            item = (
                get_question_metadata(
                    metadata,
                    selected_question
                )
            )

            duplicate_df = (
                detect_duplicates(
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
        and
        st.session_state[
            "duplicate_question"
        ]
    ):

        st.success(
            "No duplicate values detected."
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
            duplicate_df.copy()
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
                    "Value",
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

        value_mapping = dict(
            zip(
                duplicate_df[
                    "_original_index"
                ],
                duplicate_df[
                    "Value"
                ]
            )
        )

        rows_to_delete = (
            st.multiselect(
                "Rows to Delete",
                options=
                    available_indices,
                format_func=
                    lambda index:
                    (
                        f"Row {index + 1} — "
                        f"{value_mapping.get(index, '')}"
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

            if not rows_to_delete:

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
                            rows_to_delete,
                        errors="ignore"
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
                    detect_duplicates(
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

        selected_question = (
            st.selectbox(
                f"Filter {index + 1}",
                [
                    "No Filter"
                ]
                +
                filter_questions,
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

    if st.button(
        "✅ Apply Filtering",
        type="primary",
        use_container_width=True
    ):

        st.session_state[
            "global_filters"
        ] = filter_config

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
                ]
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
                <br>
                <small>{item["type"]}</small>
            </div>
            """
        )

        if st.button(
            "✕ Remove",
            key=make_widget_key(
                "remove",
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

        base_options = (
            [
                "All Respondents"
            ]
            +
            [
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
        )

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

        selected_values = []

        if (
            selected_base
            != "All Respondents"
        ):

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
            in
            st.session_state[
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
            in
            st.session_state[
                "active_questions"
            ]
        )
    ]

    configs = []

    for index in range(10):

        with st.expander(
            f"Crosstab {index + 1}",
            expanded=(
                index == 0
            )
        ):

            name = (
                st.text_input(
                    "Name",
                    value=
                        f"Crosstab {index + 1}",
                    key=
                        f"ct_name_{index}"
                )
            )

            row_q = (
                st.selectbox(
                    "Row Variable",
                    [
                        "Select Variable"
                    ]
                    +
                    row_variables,
                    key=
                        f"ct_row_{index}"
                )
            )

            col_q = (
                st.selectbox(
                    "Column Variable",
                    [
                        "Select Variable"
                    ]
                    +
                    column_variables,
                    key=
                        f"ct_col_{index}"
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
                        f"ct_chart_{index}"
                )
            )

            if (
                row_q
                != "Select Variable"
                and
                col_q
                != "Select Variable"
            ):

                configs.append(
                    {
                        "name":
                            name,

                        "row_question":
                            row_q,

                        "column_question":
                            col_q,

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

        base_df = (
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

        for config in configs:

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
                    base_df,
                    config[
                        "row_question"
                    ],
                    metadata,
                    st.session_state[
                        "applied_routing_config"
                    ]
                )
            )

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

        st.session_state[
            "crosstab_results"
        ] = results

        st.success(
            "Crosstab created."
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


    # ========================================================
    # VARIABLE ANALYSIS
    # ========================================================

    st.subheader(
        "Variable Analysis"
    )

    all_results = {}

    filtered_data = {}

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

        filtered_data[
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

    chart_questions = [
        question
        for question, result
        in all_results.items()
        if (
            result[
                "type"
            ]
            in [
                "SA",
                "MA"
            ]
            and
            not result[
                "result"
            ].empty
        )
    ]

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
                            • {result["type"]}
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
                        "variable",
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
                    in
                    item.get(
                        "options",
                        []
                    )
                ):

                    other_df = (
                        collect_ma_other_details(
                            filtered_data[
                                question
                            ],
                            item
                        )
                    )

                    if not other_df.empty:

                        with st.expander(
                            "🔎 Lihat isi Lainnya"
                        ):

                            st.dataframe(
                                other_df,
                                use_container_width=True,
                                hide_index=True
                            )


    # ========================================================
    # CROSSTAB RESULT
    # ========================================================

    st.divider()

    st.subheader(
        "Crosstab Analysis"
    )

    if not st.session_state[
        "crosstab_results"
    ]:

        st.info(
            "No crosstab results."
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

            st.markdown(
                f"### {item['name']}"
            )

            render_crosstab_chart(
                result[
                    "percentage"
                ],
                item[
                    "chart_type"
                ],
                item[
                    "name"
                ],
                f"crosstab_{index}"
            )


    # ========================================================
    # MULTI DATASET COMPARISON
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Comparison Analysis"
    )

    st.caption(
        "Maksimal 4 dataset: "
        "1 data utama + maksimal 3 pembanding."
    )

    current_label = (
        st.text_input(
            "Nama Data Utama",
            value=
                st.session_state[
                    "selected_sheet"
                ],
            key=
                "comparison_current_label"
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
            in
            st.session_state[
                "active_questions"
            ]
        )
    ]

    if current_variables:

        current_question = (
            st.selectbox(
                "Variable Data Utama",
                current_variables,
                key=
                    "comparison_current_question"
            )
        )

        current_item = (
            get_question_metadata(
                metadata,
                current_question
            )
        )

        current_type = (
            current_item[
                "type"
            ]
        )

        comparison_source = (
            st.radio(
                "Sumber Data Pembanding",
                [
                    "Other Sheets in Current File",
                    "Upload Other Files"
                ],
                key=
                    "comparison_source_multi"
            )
        )

        comparison_configs = []


        # ====================================================
        # OTHER SHEETS
        # ====================================================

        if (
            comparison_source
            ==
            "Other Sheets in Current File"
        ):

            all_sheets = (
                get_sheet_names(
                    st.session_state[
                        "source_file_bytes"
                    ]
                )
            )

            available_sheets = [
                sheet
                for sheet
                in all_sheets
                if (
                    sheet
                    !=
                    st.session_state[
                        "selected_sheet"
                    ]
                )
            ]

            selected_sheets = (
                st.multiselect(
                    "Pilih Sheet Pembanding",
                    available_sheets,
                    max_selections=3,
                    key=
                        "comparison_sheet_multi"
                )
            )

            for index, sheet in enumerate(
                selected_sheets
            ):

                st.markdown(
                    f"#### Pembanding {index + 1}"
                )

                label = (
                    st.text_input(
                        f"Nama Data Pembanding {index + 1}",
                        value=sheet,
                        key=
                            f"comparison_sheet_label_{index}"
                    )
                )

                try:

                    (
                        comparison_raw,
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
                        sheet
                    )

                    available_variables = [
                        item[
                            "question"
                        ]
                        for item
                        in comparison_metadata
                        if item[
                            "type"
                        ]
                        ==
                        current_type
                    ]

                    if available_variables:

                        default_index = 0

                        if (
                            current_question
                            in
                            available_variables
                        ):

                            default_index = (
                                available_variables.index(
                                    current_question
                                )
                            )

                        comparison_question = (
                            st.selectbox(
                                f"Variable Pembanding {index + 1}",
                                available_variables,
                                index=
                                    default_index,
                                key=
                                    f"comparison_sheet_var_{index}"
                            )
                        )

                        comparison_configs.append(
                            {
                                "label":
                                    label,

                                "df":
                                    comparison_df,

                                "metadata":
                                    comparison_metadata,

                                "question":
                                    comparison_question
                            }
                        )

                except Exception as error:

                    st.error(
                        f"Failed loading {sheet}: {error}"
                    )


        # ====================================================
        # MULTIPLE FILES
        # ====================================================

        else:

            comparison_files = (
                st.file_uploader(
                    "Upload File Pembanding",
                    type=[
                        "xlsx",
                        "xls"
                    ],
                    accept_multiple_files=True,
                    key=
                        "comparison_files_multi"
                )
            )

            if (
                len(
                    comparison_files
                )
                > 3
            ):

                st.warning(
                    "Maksimal 3 file pembanding."
                )

                comparison_files = (
                    comparison_files[:3]
                )

            for index, comparison_file in enumerate(
                comparison_files
            ):

                st.markdown(
                    f"#### Pembanding {index + 1}"
                )

                comparison_platform = (
                    st.selectbox(
                        f"Platform Pembanding {index + 1}",
                        [
                            "SurveyMonkey",
                            "Google Forms"
                        ],
                        index=(
                            0
                            if
                            st.session_state[
                                "platform"
                            ]
                            ==
                            "SurveyMonkey"
                            else 1
                        ),
                        key=
                            f"comparison_platform_{index}"
                    )
                )

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
                            f"Sheet Pembanding {index + 1}",
                            comparison_sheets,
                            key=
                                f"comparison_file_sheet_{index}"
                        )
                    )

                    comparison_label = (
                        st.text_input(
                            f"Nama Data Pembanding {index + 1}",
                            value=
                                comparison_sheet,
                            key=
                                f"comparison_file_label_{index}"
                        )
                    )

                    (
                        comparison_raw,
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

                    available_variables = [
                        item[
                            "question"
                        ]
                        for item
                        in comparison_metadata
                        if item[
                            "type"
                        ]
                        ==
                        current_type
                    ]

                    if available_variables:

                        default_index = 0

                        if (
                            current_question
                            in
                            available_variables
                        ):

                            default_index = (
                                available_variables.index(
                                    current_question
                                )
                            )

                        comparison_question = (
                            st.selectbox(
                                f"Variable Pembanding {index + 1}",
                                available_variables,
                                index=
                                    default_index,
                                key=
                                    f"comparison_file_var_{index}"
                            )
                        )

                        comparison_configs.append(
                            {
                                "label":
                                    comparison_label,

                                "df":
                                    comparison_df,

                                "metadata":
                                    comparison_metadata,

                                "question":
                                    comparison_question
                            }
                        )

                except Exception as error:

                    st.error(
                        f"Failed loading "
                        f"{comparison_file.name}: "
                        f"{error}"
                    )

        comparison_metric = (
            st.selectbox(
                "Metric",
                [
                    "Percentage",
                    "Absolute"
                ],
                key=
                    "comparison_metric_multi"
            )
        )

        if st.button(
            "🚀 Generate Comparison",
            type="primary",
            use_container_width=True
        ):

            if not comparison_configs:

                st.warning(
                    "Tambahkan minimal satu "
                    "data pembanding."
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

                datasets = [
                    {
                        "label":
                            current_label,

                        "question":
                            current_question,

                        "result":
                            current_result,

                        "type":
                            current_type
                    }
                ]

                for config in comparison_configs:

                    comparison_item = (
                        get_question_metadata(
                            config[
                                "metadata"
                            ],
                            config[
                                "question"
                            ]
                        )
                    )

                    comparison_result = (
                        calculate_variable_analysis(
                            config[
                                "df"
                            ],
                            comparison_item
                        )
                    )

                    datasets.append(
                        {
                            "label":
                                config[
                                    "label"
                                ],

                            "question":
                                config[
                                    "question"
                                ],

                            "result":
                                comparison_result,

                            "type":
                                comparison_item[
                                    "type"
                                ]
                        }
                    )

                comparison_table = (
                    build_multi_comparison_df(
                        datasets
                    )
                )

                st.session_state[
                    "comparison_result"
                ] = {
                    "datasets":
                        datasets,

                    "table":
                        comparison_table,

                    "metric":
                        comparison_metric,

                    "question":
                        current_question,

                    "type":
                        current_type
                }

        saved_comparison = (
            st.session_state[
                "comparison_result"
            ]
        )

        if saved_comparison:

            st.divider()

            dataset_names = (
                " vs ".join(
                    dataset[
                        "label"
                    ]
                    for dataset
                    in saved_comparison[
                        "datasets"
                    ]
                )
            )

            comparison_title = (
                f"{saved_comparison['question']} "
                f"— {dataset_names}"
            )

            base_text = (
                " • ".join(
                    (
                        f"{dataset['label']} "
                        f"N={dataset['result']['base_n']}"
                    )
                    for dataset
                    in saved_comparison[
                        "datasets"
                    ]
                )
            )

            st.html(
                f"""
                <div class="analysis-card">
                    <div class="analysis-question">
                        {comparison_title}
                    </div>
                    <div class="analysis-small">
                        {base_text}
                    </div>
                </div>
                """
            )

            render_multi_comparison_chart(
                saved_comparison[
                    "table"
                ],
                saved_comparison[
                    "metric"
                ],
                comparison_title,
                "multi_comparison_chart"
            )

            with st.expander(
                "View Comparison Table"
            ):

                display_comparison = (
                    saved_comparison[
                        "table"
                    ][
                        [
                            "Dataset",
                            "Option",
                            "Absolute",
                            "Percentage",
                            "Base N"
                        ]
                    ]
                    .copy()
                )

                display_comparison[
                    "Percentage"
                ] = (
                    display_comparison[
                        "Percentage"
                    ]
                    .round(1)
                )

                st.dataframe(
                    display_comparison,
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

        if (
            item[
                "type"
            ]
            != "Open"
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
            "No open feedback available."
        )

    else:

        final_feedback = (
            pd.concat(
                feedback_list,
                ignore_index=True
            )
        )

        html = (
            '<div class="feedback-container">'
        )

        for index, row in (
            final_feedback.iterrows()
        ):

            html += f"""
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

        html += "</div>"

        st.html(
            html
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

        output = BytesIO()

        export_df = (
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

            prepare_excel_df(
                raw_df
            ).to_excel(
                writer,
                sheet_name="1_Raw_Data",
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
                        export_df,
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

                result_df = (
                    result[
                        "result"
                    ]
                    .copy()
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
                ).to_excel(
                    writer,
                    sheet_name=
                        "2_Variable_Analysis",
                    startrow=
                        row_position,
                    index=False
                )

                row_position += 2

                result_df.to_excel(
                    writer,
                    sheet_name=
                        "2_Variable_Analysis",
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
                    ][
                        [
                            "Dataset",
                            "Option",
                            "Absolute",
                            "Percentage",
                            "Base N"
                        ]
                    ]
                    .copy()
                )

                comparison_export[
                    "Percentage"
                ] = (
                    comparison_export[
                        "Percentage"
                    ]
                    .apply(
                        percentage_to_text
                    )
                )

                comparison_export.to_excel(
                    writer,
                    sheet_name=
                        "3_Comparison",
                    index=False
                )

        output.seek(0)

        return output

    excel_output = (
        generate_excel()
    )

    st.download_button(
        "⬇️ Download Excel Result",
        data=
            excel_output,
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
