import pandas as pd
import re


# ============================================================
# METADATA
# ============================================================

def get_question_metadata(
    metadata,
    question
):

    for item in metadata:

        if (
            item[
                "question"
            ]
            == question
        ):

            return item

    return None


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(
    value
):

    if pd.isna(value):
        return ""

    text = (
        str(value)
        .strip()
        .lower()
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ============================================================
# GLOBAL FILTER
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
            or
            not selected_values
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

        if (
            item[
                "type"
            ]
            == "SA"
        ):

            column = (
                item[
                    "source_column"
                ]
            )

            if column not in filtered_df.columns:
                continue

            values = (
                filtered_df[
                    column
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            filtered_df = (
                filtered_df[
                    values.isin(
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

        elif (
            item[
                "type"
            ]
            == "MA"
        ):

            options = (
                item.get(
                    "options",
                    []
                )
            )

            internal_columns = (
                item.get(
                    "internal_columns",
                    []
                )
            )

            selected_columns = []

            for value in selected_values:

                if value not in options:
                    continue

                option_index = (
                    options.index(
                        value
                    )
                )

                if (
                    option_index
                    >=
                    len(
                        internal_columns
                    )
                ):
                    continue

                column = (
                    internal_columns[
                        option_index
                    ]
                )

                if column in filtered_df.columns:

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
                .sum(
                    axis=1
                )
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

    filtered_df = (
        df.copy()
    )

    if not routing_config:
        return filtered_df

    config = (
        routing_config.get(
            question
        )
    )

    if not config:
        return filtered_df

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
        or
        base_question
        == "All Respondents"
        or
        not selected_values
    ):

        return filtered_df

    base_item = (
        get_question_metadata(
            metadata,
            base_question
        )
    )

    if base_item is None:
        return filtered_df


    # ========================================================
    # SA BASE
    # ========================================================

    if (
        base_item[
            "type"
        ]
        == "SA"
    ):

        column = (
            base_item[
                "source_column"
            ]
        )

        if column not in filtered_df.columns:
            return filtered_df

        values = (
            filtered_df[
                column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        return (
            filtered_df[
                values.isin(
                    [
                        str(value)
                        for value
                        in selected_values
                    ]
                )
            ]
            .copy()
        )


    # ========================================================
    # MA BASE
    # ========================================================

    if (
        base_item[
            "type"
        ]
        == "MA"
    ):

        options = (
            base_item.get(
                "options",
                []
            )
        )

        internal_columns = (
            base_item.get(
                "internal_columns",
                []
            )
        )

        selected_columns = []

        for value in selected_values:

            if value not in options:
                continue

            index = (
                options.index(
                    value
                )
            )

            if (
                index
                >=
                len(
                    internal_columns
                )
            ):
                continue

            column = (
                internal_columns[
                    index
                ]
            )

            if column in filtered_df.columns:

                selected_columns.append(
                    column
                )

        if not selected_columns:
            return filtered_df

        mask = (
            filtered_df[
                selected_columns
            ]
            .apply(
                pd.to_numeric,
                errors="coerce"
            )
            .fillna(0)
            .sum(
                axis=1
            )
            > 0
        )

        return (
            filtered_df[
                mask
            ]
            .copy()
        )

    return filtered_df


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
            df[
                column
            ]
            .dropna()
            .astype(str)
            .str.strip()
        )

        series = (
            series[
                series != ""
            ]
        )

        base_n = (
            len(series)
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

        result[
            "Percentage"
        ] = (
            result[
                "Absolute"
            ]
            / base_n
            * 100

            if base_n > 0

            else 0
        )

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
            metadata_item.get(
                "options",
                []
            )
        )

        internal_columns = (
            metadata_item.get(
                "internal_columns",
                []
            )
        )

        valid_columns = [
            column
            for column
            in internal_columns
            if column in df.columns
        ]

        if valid_columns:

            respondent_mask = (
                df[
                    valid_columns
                ]
                .apply(
                    pd.to_numeric,
                    errors="coerce"
                )
                .fillna(0)
                .sum(
                    axis=1
                )
                > 0
            )

            base_n = int(
                respondent_mask.sum()
            )

        else:

            base_n = 0

        rows = []

        for index, option in enumerate(
            options
        ):

            if (
                index
                >=
                len(
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
                    df[
                        column
                    ],
                    errors="coerce"
                )
                .fillna(0)
            )

            absolute = int(
                (
                    values > 0
                )
                .sum()
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
            df[
                column
            ]
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
                len(series),

            "result":
                pd.DataFrame(
                    {
                        "Open Feedback":
                            series.values
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

def calculate_crosstab(
    df,
    row_metadata,
    column_metadata
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

    if row_type != "SA":

        raise ValueError(
            "Row Variable must be SA."
        )

    if column_type not in [
        "SA",
        "MA"
    ]:

        raise ValueError(
            "Column Variable must be SA or MA."
        )

    row_column = (
        row_metadata[
            "source_column"
        ]
    )

    row_series = (
        df[
            row_column
        ]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    valid_row = (
        row_series != ""
    )

    working_df = (
        df[
            valid_row
        ]
        .copy()
    )

    row_series = (
        row_series[
            valid_row
        ]
    )


    # ========================================================
    # SA × SA
    # ========================================================

    if column_type == "SA":

        column = (
            column_metadata[
                "source_column"
            ]
        )

        column_series = (
            working_df[
                column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        valid = (
            column_series != ""
        )

        row_valid = (
            row_series[
                valid.values
            ]
        )

        column_valid = (
            column_series[
                valid
            ]
        )

        absolute = (
            pd.crosstab(
                row_valid,
                column_valid
            )
        )

        row_base = (
            absolute.sum(
                axis=1
            )
        )

        percentage = (
            absolute
            .div(
                row_base.replace(
                    0,
                    pd.NA
                ),
                axis=0
            )
            .fillna(0)
            * 100
        )

        base_n = (
            len(row_valid)
        )


    # ========================================================
    # SA × MA
    # ========================================================

    else:

        options = (
            column_metadata.get(
                "options",
                []
            )
        )

        internal_columns = (
            column_metadata.get(
                "internal_columns",
                []
            )
        )

        row_options = (
            row_series
            .drop_duplicates()
            .tolist()
        )

        absolute = (
            pd.DataFrame(
                0,
                index=row_options,
                columns=options,
                dtype=int
            )
        )

        row_base = (
            row_series
            .value_counts()
            .reindex(
                row_options
            )
            .fillna(0)
        )

        for option_index, option in enumerate(
            options
        ):

            if (
                option_index
                >=
                len(
                    internal_columns
                )
            ):
                continue

            ma_column = (
                internal_columns[
                    option_index
                ]
            )

            if ma_column not in working_df.columns:
                continue

            values = (
                pd.to_numeric(
                    working_df[
                        ma_column
                    ],
                    errors="coerce"
                )
                .fillna(0)
            )

            for row_option in row_options:

                mask = (
                    row_series
                    ==
                    row_option
                )

                absolute.loc[
                    row_option,
                    option
                ] = int(
                    (
                        values[
                            mask.values
                        ]
                        > 0
                    )
                    .sum()
                )

        percentage = (
            absolute
            .div(
                row_base.replace(
                    0,
                    pd.NA
                ),
                axis=0
            )
            .fillna(0)
            * 100
        )

        base_n = (
            len(
                working_df
            )
        )

    absolute.index.name = (
        row_metadata[
            "question"
        ]
    )

    percentage.index.name = (
        row_metadata[
            "question"
        ]
    )

    return {
        "absolute":
            absolute,

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
        metadata_item.get(
            "type"
        )
        != "Open"
    ):

        return pd.DataFrame(
            columns=[
                "Question",
                "Open Feedback"
            ]
        )

    if not metadata_item.get(
        "is_feedback",
        False
    ):

        return pd.DataFrame(
            columns=[
                "Question",
                "Open Feedback"
            ]
        )

    column = (
        metadata_item.get(
            "source_column"
        )
    )

    if (
        column is None
        or
        column not in df.columns
    ):

        return pd.DataFrame(
            columns=[
                "Question",
                "Open Feedback"
            ]
        )

    series = (
        df[
            column
        ]
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
                series.values
        }
    )


# ============================================================
# MA OTHER DETAILS
# ============================================================

def collect_ma_other_details(
    df,
    metadata_item
):

    if (
        metadata_item.get(
            "type"
        )
        != "MA"
    ):

        return pd.DataFrame(
            columns=[
                "Other Response"
            ]
        )

    column = (
        metadata_item.get(
            "other_detail_column"
        )
    )

    if (
        not column
        or
        column not in df.columns
    ):

        return pd.DataFrame(
            columns=[
                "Other Response"
            ]
        )

    series = (
        df[
            column
        ]
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
            "Other Response":
                series.values
        }
    )


# ============================================================
# CONTACT NORMALIZATION
# ============================================================

def normalize_contact(
    value
):

    if pd.isna(value):
        return ""

    text = re.sub(
        r"\D",
        "",
        str(value)
    )

    if (
        text.startswith(
            "62"
        )
    ):

        text = (
            "0"
            +
            text[2:]
        )

    return text


# ============================================================
# GENERIC DUPLICATE DETECTION
# ============================================================

def detect_duplicates(
    df,
    metadata_item
):

    if metadata_item is None:

        return pd.DataFrame()

    question_type = (
        metadata_item.get(
            "type"
        )
    )

    question = (
        metadata_item.get(
            "question",
            ""
        )
    )

    working = (
        pd.DataFrame(
            index=df.index
        )
    )

    working[
        "_original_index"
    ] = df.index


    # ========================================================
    # CONTACT
    # ========================================================

    if question_type == "Contact":

        column = (
            metadata_item.get(
                "source_column"
            )
        )

        if (
            column is None
            or
            column not in df.columns
        ):

            return pd.DataFrame()

        working[
            "Value"
        ] = (
            df[
                column
            ]
        )

        working[
            "_duplicate_key"
        ] = (
            working[
                "Value"
            ]
            .apply(
                normalize_contact
            )
        )


    # ========================================================
    # SA / OPEN
    # ========================================================

    elif question_type in [
        "SA",
        "Open"
    ]:

        column = (
            metadata_item.get(
                "source_column"
            )
        )

        if (
            column is None
            or
            column not in df.columns
        ):

            return pd.DataFrame()

        working[
            "Value"
        ] = (
            df[
                column
            ]
        )

        working[
            "_duplicate_key"
        ] = (
            working[
                "Value"
            ]
            .apply(
                normalize_text
            )
        )


    # ========================================================
    # MA
    # ========================================================

    elif question_type == "MA":

        options = (
            metadata_item.get(
                "options",
                []
            )
        )

        internal_columns = (
            metadata_item.get(
                "internal_columns",
                []
            )
        )

        valid_pairs = [
            (
                option,
                column
            )
            for option, column
            in zip(
                options,
                internal_columns
            )
            if column in df.columns
        ]

        if not valid_pairs:

            return pd.DataFrame()

        display_values = []
        duplicate_keys = []

        for row_index in df.index:

            selected_options = []
            pattern = []

            for option, column in valid_pairs:

                value = (
                    pd.to_numeric(
                        pd.Series(
                            [
                                df.at[
                                    row_index,
                                    column
                                ]
                            ]
                        ),
                        errors="coerce"
                    )
                    .fillna(0)
                    .iloc[0]
                )

                selected = (
                    1
                    if value > 0
                    else 0
                )

                pattern.append(
                    str(selected)
                )

                if selected:

                    selected_options.append(
                        option
                    )

            if not selected_options:

                display_values.append(
                    ""
                )

                duplicate_keys.append(
                    ""
                )

            else:

                display_values.append(
                    ", ".join(
                        selected_options
                    )
                )

                duplicate_keys.append(
                    "|".join(
                        pattern
                    )
                )

        working[
            "Value"
        ] = display_values

        working[
            "_duplicate_key"
        ] = duplicate_keys


    else:

        return pd.DataFrame()


    # ========================================================
    # REMOVE BLANK
    # ========================================================

    working[
        "_duplicate_key"
    ] = (
        working[
            "_duplicate_key"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    working = (
        working[
            working[
                "_duplicate_key"
            ]
            != ""
        ]
        .copy()
    )

    if working.empty:

        return pd.DataFrame()


    # ========================================================
    # DUPLICATE COUNTS
    # ========================================================

    counts = (
        working[
            "_duplicate_key"
        ]
        .value_counts()
    )

    duplicate_values = (
        counts[
            counts > 1
        ]
        .index
        .tolist()
    )

    if not duplicate_values:

        return pd.DataFrame()

    duplicate_df = (
        working[
            working[
                "_duplicate_key"
            ]
            .isin(
                duplicate_values
            )
        ]
        .copy()
    )


    # ========================================================
    # DUPLICATE GROUP
    # ========================================================

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
            "_duplicate_key"
        ]
        .map(
            group_mapping
        )
    )

    duplicate_df[
        "Duplicate Count"
    ] = (
        duplicate_df[
            "_duplicate_key"
        ]
        .map(
            counts
        )
    )

    duplicate_df[
        "Question"
    ] = question

    return (
        duplicate_df[
            [
                "_original_index",
                "Question",
                "Value",
                "Duplicate Group",
                "Duplicate Count"
            ]
        ]
        .sort_values(
            [
                "Duplicate Group",
                "_original_index"
            ]
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def detect_contact_duplicates(
    df,
    metadata_item
):

    return detect_duplicates(
        df,
        metadata_item
    )
