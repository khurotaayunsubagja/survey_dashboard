import pandas as pd
import re


# ============================================================
# METADATA
# ============================================================

def get_question_metadata(
    metadata,
    question
):

    if not metadata:
        return None

    for item in metadata:

        if (
            item.get(
                "question"
            )
            ==
            question
        ):

            return item

    return None


# ============================================================
# BASIC NORMALIZATION
# ============================================================

def normalize_text(value):

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


def normalize_contact(value):

    if pd.isna(value):
        return ""

    text = re.sub(
        r"\D",
        "",
        str(value)
    )

    if not text:
        return ""

    if text.startswith(
        "62"
    ):

        text = (
            "0"
            +
            text[2:]
        )

    return text


def numeric_binary_series(
    series
):

    return (
        pd.to_numeric(
            series,
            errors="coerce"
        )
        .fillna(0)
        .gt(0)
        .astype(int)
    )


# ============================================================
# SA FILTER HELPER
# ============================================================

def filter_sa_values(
    df,
    metadata_item,
    selected_values
):

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

        return df.copy()


    comparison_values = {
        normalize_text(
            value
        )
        for value
        in selected_values
    }


    series = (
        df[
            column
        ]
        .apply(
            normalize_text
        )
    )


    return (
        df[
            series.isin(
                comparison_values
            )
        ]
        .copy()
    )


# ============================================================
# MA FILTER HELPER
# ============================================================

def filter_ma_values(
    df,
    metadata_item,
    selected_values
):

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


    option_lookup = {
        normalize_text(
            option
        ):
            index

        for index, option
        in enumerate(
            options
        )
    }


    selected_columns = []


    for selected_value in (
        selected_values
    ):

        selected_key = (
            normalize_text(
                selected_value
            )
        )


        if (
            selected_key
            not in
            option_lookup
        ):

            continue


        option_index = (
            option_lookup[
                selected_key
            ]
        )


        if (
            option_index
            >=
            len(
                internal_columns
            )
        ):

            continue


        internal_column = (
            internal_columns[
                option_index
            ]
        )


        if (
            internal_column
            in
            df.columns
        ):

            selected_columns.append(
                internal_column
            )


    if not selected_columns:

        return df.copy()


    mask = (
        df[
            selected_columns
        ]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .fillna(0)
        .gt(0)
        .any(
            axis=1
        )
    )


    return (
        df[
            mask
        ]
        .copy()
    )


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


    for config in (
        filter_config
    ):

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


        question_type = (
            item.get(
                "type"
            )
        )


        if question_type == "SA":

            filtered_df = (
                filter_sa_values(
                    filtered_df,
                    item,
                    selected_values
                )
            )


        elif question_type == "MA":

            filtered_df = (
                filter_ma_values(
                    filtered_df,
                    item,
                    selected_values
                )
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
        ==
        "All Respondents"
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


    if (
        base_item.get(
            "type"
        )
        ==
        "SA"
    ):

        return filter_sa_values(
            filtered_df,
            base_item,
            selected_values
        )


    if (
        base_item.get(
            "type"
        )
        ==
        "MA"
    ):

        return filter_ma_values(
            filtered_df,
            base_item,
            selected_values
        )


    return filtered_df


# ============================================================
# VARIABLE ANALYSIS
# ============================================================

def calculate_variable_analysis(
    df,
    metadata_item
):

    if metadata_item is None:

        return {
            "question": "",
            "type": "",
            "base_n": 0,
            "result":
                pd.DataFrame()
        }


    question = (
        metadata_item.get(
            "question",
            ""
        )
    )

    question_type = (
        metadata_item.get(
            "type",
            ""
        )
    )


    # ========================================================
    # SA
    # ========================================================

    if question_type == "SA":

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

            return {
                "question":
                    question,
                "type":
                    "SA",
                "base_n":
                    0,
                "result":
                    pd.DataFrame(
                        columns=[
                            "Option",
                            "Absolute",
                            "Percentage"
                        ]
                    )
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
            len(
                series
            )
        )


        # Keep metadata option order first
        metadata_options = (
            metadata_item.get(
                "options",
                []
            )
        )


        actual_counts = (
            series
            .value_counts()
        )


        rows = []


        processed_keys = set()


        for option in (
            metadata_options
        ):

            option_text = (
                str(
                    option
                )
                .strip()
            )

            option_key = (
                normalize_text(
                    option_text
                )
            )


            matching_values = [
                value

                for value
                in actual_counts.index

                if (
                    normalize_text(
                        value
                    )
                    ==
                    option_key
                )
            ]


            absolute = sum(
                int(
                    actual_counts[
                        value
                    ]
                )

                for value
                in matching_values
            )


            percentage = (
                absolute
                /
                base_n
                *
                100

                if base_n > 0

                else 0
            )


            rows.append(
                {
                    "Option":
                        option_text,

                    "Absolute":
                        absolute,

                    "Percentage":
                        percentage
                }
            )


            processed_keys.add(
                option_key
            )


        # Add values not available in metadata
        for value, count in (
            actual_counts.items()
        ):

            value_key = (
                normalize_text(
                    value
                )
            )


            if (
                value_key
                in
                processed_keys
            ):

                continue


            percentage = (
                int(count)
                /
                base_n
                *
                100

                if base_n > 0

                else 0
            )


            rows.append(
                {
                    "Option":
                        str(
                            value
                        ),

                    "Absolute":
                        int(
                            count
                        ),

                    "Percentage":
                        percentage
                }
            )


        return {
            "question":
                question,

            "type":
                "SA",

            "base_n":
                base_n,

            "result":
                pd.DataFrame(
                    rows,
                    columns=[
                        "Option",
                        "Absolute",
                        "Percentage"
                    ]
                )
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
                .gt(0)
                .any(
                    axis=1
                )
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

                absolute = 0

            else:

                values = (
                    numeric_binary_series(
                        df[
                            column
                        ]
                    )
                )

                absolute = int(
                    values.sum()
                )


            percentage = (
                absolute
                /
                base_n
                *
                100

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
                    rows,
                    columns=[
                        "Option",
                        "Absolute",
                        "Percentage"
                    ]
                )
        }


    # ========================================================
    # OPEN
    # ========================================================

    if question_type == "Open":

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

            return {
                "question":
                    question,
                "type":
                    "Open",
                "base_n":
                    0,
                "result":
                    pd.DataFrame(
                        columns=[
                            "Open Feedback"
                        ]
                    )
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
                len(
                    series
                ),

            "result":
                pd.DataFrame(
                    {
                        "Open Feedback":
                            series.values
                    }
                )
        }


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

            base_n = 0

        else:

            series = (
                df[
                    column
                ]
                .dropna()
                .astype(str)
                .str.strip()
            )

            base_n = int(
                (
                    series != ""
                )
                .sum()
            )


        return {
            "question":
                question,

            "type":
                "Contact",

            "base_n":
                base_n,

            "result":
                pd.DataFrame()
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

    if (
        row_metadata is None
        or
        column_metadata is None
    ):

        raise ValueError(
            "Invalid crosstab metadata."
        )


    row_type = (
        row_metadata.get(
            "type"
        )
    )

    column_type = (
        column_metadata.get(
            "type"
        )
    )


    if row_type != "SA":

        raise ValueError(
            "Row Variable harus bertipe SA."
        )


    if (
        column_type
        not in [
            "SA",
            "MA"
        ]
    ):

        raise ValueError(
            "Column Variable harus bertipe SA atau MA."
        )


    row_column = (
        row_metadata.get(
            "source_column"
        )
    )


    if (
        row_column is None
        or
        row_column not in df.columns
    ):

        return {
            "absolute":
                pd.DataFrame(),

            "percentage":
                pd.DataFrame(),

            "base_n":
                0
        }


    row_series = (
        df[
            row_column
        ]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    valid_row_mask = (
        row_series
        != ""
    )


    working_df = (
        df.loc[
            valid_row_mask
        ]
        .copy()
    )


    working_row_series = (
        row_series.loc[
            valid_row_mask
        ]
    )


    # ========================================================
    # SA × SA
    # ========================================================

    if column_type == "SA":

        column = (
            column_metadata.get(
                "source_column"
            )
        )


        if (
            column is None
            or
            column not in
            working_df.columns
        ):

            return {
                "absolute":
                    pd.DataFrame(),

                "percentage":
                    pd.DataFrame(),

                "base_n":
                    0
            }


        column_series = (
            working_df[
                column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )


        valid_column_mask = (
            column_series
            != ""
        )


        row_valid = (
            working_row_series.loc[
                valid_column_mask
            ]
        )

        column_valid = (
            column_series.loc[
                valid_column_mask
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
            *
            100
        )


        base_n = (
            len(
                row_valid
            )
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
            working_row_series
            .drop_duplicates()
            .tolist()
        )


        absolute = (
            pd.DataFrame(
                0,
                index=
                    row_options,
                columns=
                    options,
                dtype=int
            )
        )


        row_base = (
            working_row_series
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


            if (
                ma_column
                not in
                working_df.columns
            ):

                continue


            values = (
                numeric_binary_series(
                    working_df[
                        ma_column
                    ]
                )
            )


            for row_option in (
                row_options
            ):

                mask = (
                    working_row_series
                    ==
                    row_option
                )


                absolute.loc[
                    row_option,
                    option
                ] = int(
                    values.loc[
                        mask
                    ].sum()
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
            *
            100
        )


        base_n = (
            len(
                working_df
            )
        )


    absolute.index.name = (
        row_metadata.get(
            "question"
        )
    )


    percentage.index.name = (
        row_metadata.get(
            "question"
        )
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

    if metadata_item is None:

        return pd.DataFrame(
            columns=[
                "Question",
                "Open Feedback"
            ]
        )


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
                [
                    metadata_item.get(
                        "question",
                        ""
                    )
                ]
                *
                len(
                    series
                ),

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

    if metadata_item is None:

        return pd.DataFrame(
            columns=[
                "Other Response"
            ]
        )


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
# GENERIC DUPLICATE DETECTION
# ============================================================

def detect_duplicates(
    df,
    metadata_item
):

    if (
        metadata_item is None
        or
        df is None
        or
        df.empty
    ):

        return pd.DataFrame(
            columns=[
                "_original_index",
                "Question",
                "Value",
                "Duplicate Group",
                "Duplicate Count"
            ]
        )


    question = (
        metadata_item.get(
            "question",
            ""
        )
    )

    question_type = (
        metadata_item.get(
            "type",
            ""
        )
    )


    working = (
        pd.DataFrame(
            index=
                df.index
        )
    )


    working[
        "_original_index"
    ] = (
        df.index
    )


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

            return pd.DataFrame(
                columns=[
                    "_original_index",
                    "Question",
                    "Value",
                    "Duplicate Group",
                    "Duplicate Count"
                ]
            )


        working[
            "Value"
        ] = (
            df[
                column
            ]
            .fillna("")
            .astype(str)
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

    elif (
        question_type
        in [
            "SA",
            "Open"
        ]
    ):

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
                    "_original_index",
                    "Question",
                    "Value",
                    "Duplicate Group",
                    "Duplicate Count"
                ]
            )


        working[
            "Value"
        ] = (
            df[
                column
            ]
            .fillna("")
            .astype(str)
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

            return pd.DataFrame(
                columns=[
                    "_original_index",
                    "Question",
                    "Value",
                    "Duplicate Group",
                    "Duplicate Count"
                ]
            )


        display_values = []
        duplicate_keys = []


        for row_index in (
            df.index
        ):

            selected_options = []
            pattern = []


            for option, column in (
                valid_pairs
            ):

                raw_value = (
                    df.at[
                        row_index,
                        column
                    ]
                )


                try:

                    numeric_value = (
                        float(
                            raw_value
                        )
                    )

                    selected = (
                        1
                        if numeric_value > 0
                        else 0
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    text_value = (
                        normalize_text(
                            raw_value
                        )
                    )

                    selected = (
                        0
                        if (
                            not text_value
                            or
                            text_value
                            in [
                                "0",
                                "no",
                                "false",
                                "nan"
                            ]
                        )
                        else 1
                    )


                pattern.append(
                    str(
                        selected
                    )
                )


                if selected == 1:

                    selected_options.append(
                        str(
                            option
                        )
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
        ] = (
            display_values
        )


        working[
            "_duplicate_key"
        ] = (
            duplicate_keys
        )


    else:

        return pd.DataFrame(
            columns=[
                "_original_index",
                "Question",
                "Value",
                "Duplicate Group",
                "Duplicate Count"
            ]
        )


    # ========================================================
    # REMOVE EMPTY VALUE
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

        return pd.DataFrame(
            columns=[
                "_original_index",
                "Question",
                "Value",
                "Duplicate Group",
                "Duplicate Count"
            ]
        )


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

        return pd.DataFrame(
            columns=[
                "_original_index",
                "Question",
                "Value",
                "Duplicate Group",
                "Duplicate Count"
            ]
        )


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
    # GROUP NUMBER
    # ========================================================

    group_mapping = {
        duplicate_key:
            index + 1

        for index, duplicate_key
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
        .astype(int)
    )


    duplicate_df[
        "Question"
    ] = (
        question
    )


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
