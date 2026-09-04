import pandas as pd
import re


# ============================================================
# GENERAL HELPERS
# ============================================================

def get_question_metadata(
    metadata,
    question
):

    for item in metadata:

        if item["question"] == question:

            return item

    return None


def normalize_text(value):

    if pd.isna(value):
        return ""

    text = str(value)

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# GLOBAL FILTERING
# ============================================================

def apply_global_filters(
    df,
    metadata,
    filter_config
):

    filtered_df = (
        df.copy()
    )

    if not filter_config:

        return filtered_df

    for config in filter_config:

        question = (
            config.get(
                "question"
            )
        )

        selected_values = (
            config.get(
                "values",
                []
            )
        )

        if (
            not question
            or not selected_values
        ):

            continue

        item = (
            get_question_metadata(
                metadata,
                question
            )
        )

        if item is None:

            continue

        # ====================================================
        # SA
        # ====================================================

        if item["type"] == "SA":

            column = (
                item[
                    "source_column"
                ]
            )

            if column not in filtered_df.columns:

                continue

            series = (
                filtered_df[
                    column
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            filtered_df = (
                filtered_df[
                    series.isin(
                        [
                            str(value)
                            for value
                            in selected_values
                        ]
                    )
                ]
                .copy()
            )

        # ====================================================
        # MA
        # ====================================================

        elif item["type"] == "MA":

            options = (
                item[
                    "options"
                ]
            )

            internal_columns = (
                item[
                    "internal_columns"
                ]
            )

            selected_columns = []

            for value in (
                selected_values
            ):

                if value not in options:
                    continue

                option_index = (
                    options.index(
                        value
                    )
                )

                if (
                    option_index
                    >= len(
                        internal_columns
                    )
                ):

                    continue

                column = (
                    internal_columns[
                        option_index
                    ]
                )

                if (
                    column
                    in filtered_df.columns
                ):

                    selected_columns.append(
                        column
                    )

            if not selected_columns:

                continue

            mask = (
                filtered_df[
                    selected_columns
                ]
                .apply(
                    pd.to_numeric,
                    errors="coerce"
                )
                .fillna(0)
                .sum(axis=1)
                > 0
            )

            filtered_df = (
                filtered_df[
                    mask
                ]
                .copy()
            )

    return filtered_df


# ============================================================
# ROUTING
# ============================================================

def get_filtered_df(
    df,
    question,
    metadata,
    routing_config
):

    if not routing_config:
        return df.copy()

    if question not in routing_config:
        return df.copy()

    config = (
        routing_config[
            question
        ]
    )

    if not config:
        return df.copy()

    base_question = (
        config.get(
            "base_question"
        )
    )

    selected_values = (
        config.get(
            "values",
            []
        )
    )

    if (
        not base_question
        or base_question
        == "All Respondents"
    ):

        return df.copy()

    if not selected_values:

        return df.copy()

    base_metadata = (
        get_question_metadata(
            metadata,
            base_question
        )
    )

    if base_metadata is None:

        return df.copy()

    # ========================================================
    # SA
    # ========================================================

    if (
        base_metadata[
            "type"
        ]
        == "SA"
    ):

        column = (
            base_metadata[
                "source_column"
            ]
        )

        if column not in df.columns:

            return df.copy()

        series = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        return (
            df[
                series.isin(
                    [
                        str(x)
                        for x
                        in selected_values
                    ]
                )
            ]
            .copy()
        )

    # ========================================================
    # MA
    # ========================================================

    if (
        base_metadata[
            "type"
        ]
        == "MA"
    ):

        options = (
            base_metadata[
                "options"
            ]
        )

        internal_columns = (
            base_metadata[
                "internal_columns"
            ]
        )

        selected_columns = []

        for value in (
            selected_values
        ):

            if value not in options:
                continue

            index = (
                options.index(
                    value
                )
            )

            if (
                index
                < len(
                    internal_columns
                )
            ):

                column = (
                    internal_columns[
                        index
                    ]
                )

                if column in df.columns:

                    selected_columns.append(
                        column
                    )

        if not selected_columns:

            return df.copy()

        mask = (
            df[
                selected_columns
            ]
            .fillna(0)
            .apply(
                pd.to_numeric,
                errors="coerce"
            )
            .fillna(0)
            .sum(axis=1)
            > 0
        )

        return (
            df[
                mask
            ]
            .copy()
        )

    return df.copy()


# ============================================================
# VARIABLE ANALYSIS
# ============================================================

def calculate_variable_analysis(
    df,
    metadata_item
):

    question = (
        metadata_item[
            "question"
        ]
    )

    question_type = (
        metadata_item[
            "type"
        ]
    )

    # ========================================================
    # CONTACT
    # ========================================================

    if question_type == "Contact":

        return {
            "question":
                question,

            "type":
                "Contact",

            "base_n":
                0,

            "result":
                pd.DataFrame()
        }

    # ========================================================
    # SA
    # ========================================================

    if question_type == "SA":

        column = (
            metadata_item[
                "source_column"
            ]
        )

        if column not in df.columns:

            return {
                "question":
                    question,

                "type":
                    "SA",

                "base_n":
                    0,

                "result":
                    pd.DataFrame()
            }

        series = (
            df[column]
            .dropna()
            .astype(str)
            .str.strip()
        )

        series = (
            series[
                series != ""
            ]
        )

        base_n = len(
            series
        )

        result = (
            series
            .value_counts()
            .rename_axis(
                "Option"
            )
            .reset_index(
                name="Absolute"
            )
        )

        if base_n > 0:

            result[
                "Percentage"
            ] = (
                result[
                    "Absolute"
                ]
                / base_n
                * 100
            )

        else:

            result[
                "Percentage"
            ] = 0

        return {
            "question":
                question,

            "type":
                "SA",

            "base_n":
                base_n,

            "result":
                result
        }

    # ========================================================
    # MA
    # ========================================================

    if question_type == "MA":

        options = (
            metadata_item[
                "options"
            ]
        )

        internal_columns = (
            metadata_item[
                "internal_columns"
            ]
        )

        base_n = len(
            df
        )

        rows = []

        for index, option in (
            enumerate(
                options
            )
        ):

            if (
                index
                >= len(
                    internal_columns
                )
            ):

                continue

            column = (
                internal_columns[
                    index
                ]
            )

            if column not in df.columns:
                continue

            values = (
                pd.to_numeric(
                    df[column],
                    errors="coerce"
                )
                .fillna(0)
            )

            absolute = int(
                values.sum()
            )

            percentage = (
                absolute
                / base_n
                * 100

                if base_n > 0

                else 0
            )

            rows.append(
                {
                    "Option":
                        option,

                    "Absolute":
                        absolute,

                    "Percentage":
                        percentage
                }
            )

        return {
            "question":
                question,

            "type":
                "MA",

            "base_n":
                base_n,

            "result":
                pd.DataFrame(
                    rows
                )
        }

    # ========================================================
    # OPEN
    # ========================================================

    if question_type == "Open":

        column = (
            metadata_item[
                "source_column"
            ]
        )

        if column not in df.columns:

            return {
                "question":
                    question,

                "type":
                    "Open",

                "base_n":
                    0,

                "result":
                    pd.DataFrame()
            }

        series = (
            df[column]
            .dropna()
            .astype(str)
            .str.strip()
        )

        series = (
            series[
                series != ""
            ]
        )

        return {
            "question":
                question,

            "type":
                "Open",

            "base_n":
                len(
                    series
                ),

            "result":
                pd.DataFrame(
                    {
                        "Open Feedback":
                            series
                    }
                )
        }

    return {
        "question":
            question,

        "type":
            question_type,

        "base_n":
            0,

        "result":
            pd.DataFrame()
    }


# ============================================================
# CROSSTAB
# ============================================================

def find_ma_option_column(
    metadata_item,
    option
):

    options = (
        metadata_item[
            "options"
        ]
    )

    internal_columns = (
        metadata_item[
            "internal_columns"
        ]
    )

    if option not in options:

        return None

    index = (
        options.index(
            option
        )
    )

    if (
        index
        >= len(
            internal_columns
        )
    ):

        return None

    return (
        internal_columns[
            index
        ]
    )


def calculate_crosstab(
    df,
    row_metadata,
    column_metadata,
    column_option=None
):

    row_type = (
        row_metadata[
            "type"
        ]
    )

    column_type = (
        column_metadata[
            "type"
        ]
    )

    if (
        row_type == "MA"
        and column_type == "MA"
    ):

        raise ValueError(
            "MA × MA analysis cannot be performed."
        )

    if (
        row_type == "MA"
        and column_type == "SA"
    ):

        raise ValueError(
            "MA × SA is not supported. "
            "Please use SA as Row Variable "
            "and MA as Column Variable."
        )

    if (
        row_type in [
            "Open",
            "Contact"
        ]
        or column_type in [
            "Open",
            "Contact"
        ]
    ):

        raise ValueError(
            "Open-ended or Contact questions "
            "cannot be used in a crosstab."
        )

    row_column = (
        row_metadata[
            "source_column"
        ]
    )

    if row_column not in df.columns:

        return {
            "absolute":
                pd.DataFrame(),

            "percentage":
                pd.DataFrame(),

            "base_n":
                0
        }

    row_series = (
        df[row_column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # ========================================================
    # SA × SA
    # ========================================================

    if column_type == "SA":

        column_column = (
            column_metadata[
                "source_column"
            ]
        )

        if column_column not in df.columns:

            return {
                "absolute":
                    pd.DataFrame(),

                "percentage":
                    pd.DataFrame(),

                "base_n":
                    0
            }

        column_series = (
            df[
                column_column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        mask = (
            (row_series != "")
            &
            (column_series != "")
        )

        row_series = (
            row_series[
                mask
            ]
        )

        column_series = (
            column_series[
                mask
            ]
        )

        result = (
            pd.crosstab(
                row_series,
                column_series
            )
        )

    # ========================================================
    # SA × MA
    # ========================================================

    elif column_type == "MA":

        if not column_option:

            raise ValueError(
                "Please select an MA option."
            )

        ma_column = (
            find_ma_option_column(
                column_metadata,
                column_option
            )
        )

        if ma_column is None:

            return {
                "absolute":
                    pd.DataFrame(),

                "percentage":
                    pd.DataFrame(),

                "base_n":
                    0
            }

        ma_series = (
            pd.to_numeric(
                df[
                    ma_column
                ],
                errors="coerce"
            )
            .fillna(0)
        )

        mask = (
            row_series
            != ""
        )

        row_series = (
            row_series[
                mask
            ]
        )

        ma_series = (
            ma_series[
                mask
            ]
        )

        result = (
            pd.crosstab(
                row_series,
                ma_series
            )
        )

        if 1 in result.columns:

            result = (
                result[
                    [1]
                ]
            )

            result.columns = [
                column_option
            ]

        else:

            result = (
                pd.DataFrame(
                    0,
                    index=
                        result.index,
                    columns=[
                        column_option
                    ]
                )
            )

    else:

        raise ValueError(
            "Unsupported crosstab combination."
        )

    base_n = len(
        row_series
    )

    if base_n > 0:

        percentage = (
            result
            / base_n
            * 100
        )

    else:

        percentage = (
            result.copy()
        )

    return {
        "absolute":
            result,

        "percentage":
            percentage,

        "base_n":
            base_n
    }


# ============================================================
# OPEN FEEDBACK
# ============================================================

def collect_open_feedback(
    df,
    metadata_item
):

    if (
        metadata_item[
            "type"
        ]
        != "Open"
        or not metadata_item.get(
            "is_feedback",
            False
        )
    ):

        return pd.DataFrame(
            columns=[
                "Question",
                "Open Feedback"
            ]
        )

    column = (
        metadata_item[
            "source_column"
        ]
    )

    if column not in df.columns:

        return pd.DataFrame(
            columns=[
                "Question",
                "Open Feedback"
            ]
        )

    series = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    series = (
        series[
            series != ""
        ]
    )

    return pd.DataFrame(
        {
            "Question":
                metadata_item[
                    "question"
                ],

            "Open Feedback":
                series
        }
    )


# ============================================================
# OPEN DUPLICATE DETECTION
# ============================================================

def detect_open_duplicates(
    df,
    metadata_item
):

    if (
        metadata_item[
            "type"
        ]
        != "Open"
    ):

        return pd.DataFrame()

    column = (
        metadata_item[
            "source_column"
        ]
    )

    if column not in df.columns:

        return pd.DataFrame()

    working = pd.DataFrame(
        {
            "_original_index":
                df.index,

            "Response":
                df[column]
        }
    )

    working[
        "_normalized_answer"
    ] = (
        working[
            "Response"
        ]
        .apply(
            normalize_text
        )
    )

    working = (
        working[
            working[
                "_normalized_answer"
            ]
            != ""
        ]
        .copy()
    )

    if working.empty:

        return pd.DataFrame()

    counts = (
        working[
            "_normalized_answer"
        ]
        .value_counts()
    )

    duplicate_values = (
        counts[
            counts > 1
        ]
        .index
    )

    if len(
        duplicate_values
    ) == 0:

        return pd.DataFrame()

    duplicate_df = (
        working[
            working[
                "_normalized_answer"
            ]
            .isin(
                duplicate_values
            )
        ]
        .copy()
    )

    group_mapping = {
        value:
            index + 1

        for index, value
        in enumerate(
            duplicate_values
        )
    }

    duplicate_df[
        "Duplicate Group"
    ] = (
        duplicate_df[
            "_normalized_answer"
        ]
        .map(
            group_mapping
        )
    )

    duplicate_df[
        "Duplicate Count"
    ] = (
        duplicate_df[
            "_normalized_answer"
        ]
        .map(
            counts
        )
    )

    return duplicate_df


# ============================================================
# CONTACT DUPLICATE DETECTION
# ============================================================

def normalize_contact(value):

    if pd.isna(value):
        return ""

    text = str(
        value
    ).strip()

    text = re.sub(
        r"\D",
        "",
        text
    )

    if text.startswith(
        "62"
    ):

        text = (
            "0"
            + text[2:]
        )

    return text


def detect_contact_duplicates(
    df,
    metadata_item
):

    if (
        metadata_item[
            "type"
        ]
        != "Contact"
    ):

        return pd.DataFrame()

    column = (
        metadata_item[
            "source_column"
        ]
    )

    if column not in df.columns:

        return pd.DataFrame()

    working = pd.DataFrame(
        {
            "_original_index":
                df.index,

            "Contact":
                df[column]
        }
    )

    working[
        "_normalized_contact"
    ] = (
        working[
            "Contact"
        ]
        .apply(
            normalize_contact
        )
    )

    working = (
        working[
            working[
                "_normalized_contact"
            ]
            != ""
        ]
        .copy()
    )

    if working.empty:

        return pd.DataFrame()

    counts = (
        working[
            "_normalized_contact"
        ]
        .value_counts()
    )

    duplicate_values = (
        counts[
            counts > 1
        ]
        .index
    )

    if len(
        duplicate_values
    ) == 0:

        return pd.DataFrame()

    duplicate_df = (
        working[
            working[
                "_normalized_contact"
            ]
            .isin(
                duplicate_values
            )
        ]
        .copy()
    )

    group_mapping = {
        value:
            index + 1

        for index, value
        in enumerate(
            duplicate_values
        )
    }

    duplicate_df[
        "Duplicate Group"
    ] = (
        duplicate_df[
            "_normalized_contact"
        ]
        .map(
            group_mapping
        )
    )

    duplicate_df[
        "Duplicate Count"
    ] = (
        duplicate_df[
            "_normalized_contact"
        ]
        .map(
            counts
        )
    )

    return duplicate_df
