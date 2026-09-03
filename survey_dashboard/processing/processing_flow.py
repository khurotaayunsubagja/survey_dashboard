import pandas as pd
import re


# ============================================================
# GENERAL HELPERS
# ============================================================

def get_question_metadata(
    metadata,
    question
):
    """
    Mengambil metadata berdasarkan nama pertanyaan.
    """

    for item in metadata:

        if item["question"] == question:
            return item

    return None


def normalize_text(value):
    """
    Normalisasi teks untuk duplicate detection.
    """

    if pd.isna(value):
        return ""

    text = str(value).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# ROUTING
# ============================================================

def get_filtered_df(
    df,
    question,
    metadata,
    routing_config
):
    """
    Filter responden berdasarkan routing yang sudah diterapkan.
    """

    if not routing_config:
        return df.copy()

    config = routing_config.get(
        question
    )

    if not config:
        return df.copy()

    base_question = config.get(
        "base_question"
    )

    selected_values = config.get(
        "values",
        []
    )

    if (
        not base_question
        or base_question == "All Respondents"
        or not selected_values
    ):
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
    # SA ROUTING
    # ========================================================

    if base_metadata["type"] == "SA":

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

        selected_values = [
            str(value)
            for value
            in selected_values
        ]

        mask = (
            series.isin(
                selected_values
            )
        )

        return df[
            mask
        ].copy()

    # ========================================================
    # MA ROUTING
    # ========================================================

    if base_metadata["type"] == "MA":

        options = (
            base_metadata["options"]
        )

        internal_columns = (
            base_metadata[
                "internal_columns"
            ]
        )

        selected_columns = []

        for value in selected_values:

            if value not in options:
                continue

            option_index = (
                options.index(value)
            )

            if option_index >= len(
                internal_columns
            ):
                continue

            column = (
                internal_columns[
                    option_index
                ]
            )

            if column in df.columns:

                selected_columns.append(
                    column
                )

        if not selected_columns:
            return df.copy()

        numeric_df = (
            df[selected_columns]
            .apply(
                pd.to_numeric,
                errors="coerce"
            )
            .fillna(0)
        )

        mask = (
            numeric_df
            .sum(axis=1)
            > 0
        )

        return df[
            mask
        ].copy()

    return df.copy()


# ============================================================
# VARIABLE ANALYSIS
# ============================================================

def calculate_variable_analysis(
    df,
    metadata_item
):
    """
    Menghasilkan frequency analysis berdasarkan tipe pertanyaan.
    """

    question = (
        metadata_item["question"]
    )

    question_type = (
        metadata_item["type"]
    )

    # ========================================================
    # CONTACT
    # ========================================================
    # Contact tidak dianalisis.
    # ========================================================

    if question_type == "Contact":

        return {
            "question": question,
            "type": "Contact",
            "base_n": 0,
            "result": pd.DataFrame()
        }

    # ========================================================
    # SINGLE ANSWER
    # ========================================================

    if question_type == "SA":

        column = (
            metadata_item[
                "source_column"
            ]
        )

        if column not in df.columns:

            return {
                "question": question,
                "type": "SA",
                "base_n": 0,
                "result":
                    pd.DataFrame()
            }

        series = (
            df[column]
            .dropna()
            .astype(str)
            .str.strip()
        )

        series = series[
            series != ""
        ]

        base_n = len(
            series
        )

        result = (
            series
            .value_counts()
            .rename_axis("Option")
            .reset_index(
                name="Absolute"
            )
        )

        if base_n > 0:

            result[
                "Percentage"
            ] = (
                result["Absolute"]
                / base_n
                * 100
            )

        else:

            result[
                "Percentage"
            ] = 0

        return {
            "question": question,
            "type": "SA",
            "base_n": base_n,
            "result": result
        }

    # ========================================================
    # MULTIPLE ANSWER
    # ========================================================

    if question_type == "MA":

        options = (
            metadata_item["options"]
        )

        internal_columns = (
            metadata_item[
                "internal_columns"
            ]
        )

        # ----------------------------------------------------
        # Base MA:
        # hanya responden yang memiliki minimal 1 jawaban
        # pada pertanyaan MA.
        # ----------------------------------------------------

        available_columns = [
            column
            for column
            in internal_columns
            if column in df.columns
        ]

        if available_columns:

            ma_values = (
                df[available_columns]
                .apply(
                    pd.to_numeric,
                    errors="coerce"
                )
                .fillna(0)
            )

            answered_mask = (
                ma_values
                .sum(axis=1)
                > 0
            )

            base_n = int(
                answered_mask.sum()
            )

        else:

            base_n = 0

        rows = []

        for index, option in enumerate(
            options
        ):

            if index >= len(
                internal_columns
            ):
                continue

            column = (
                internal_columns[index]
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

            if base_n > 0:

                percentage = (
                    absolute
                    / base_n
                    * 100
                )

            else:

                percentage = 0

            rows.append(
                {
                    "Option": option,
                    "Absolute": absolute,
                    "Percentage":
                        percentage
                }
            )

        result = pd.DataFrame(
            rows
        )

        return {
            "question": question,
            "type": "MA",
            "base_n": base_n,
            "result": result
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
                "question": question,
                "type": "Open",
                "base_n": 0,
                "result":
                    pd.DataFrame()
            }

        series = (
            df[column]
            .dropna()
            .astype(str)
            .str.strip()
        )

        series = series[
            series != ""
        ]

        result = pd.DataFrame(
            {
                "Open Feedback":
                    series
            }
        )

        return {
            "question": question,
            "type": "Open",
            "base_n": len(series),
            "result": result
        }

    # ========================================================
    # FALLBACK
    # ========================================================

    return {
        "question": question,
        "type": question_type,
        "base_n": 0,
        "result": pd.DataFrame()
    }


# ============================================================
# CROSSTAB HELPERS
# ============================================================

def find_ma_option_column(
    metadata_item,
    option
):
    """
    Mencari kolom internal berdasarkan opsi MA.
    """

    options = (
        metadata_item["options"]
    )

    internal_columns = (
        metadata_item[
            "internal_columns"
        ]
    )

    if option not in options:
        return None

    option_index = (
        options.index(option)
    )

    if option_index >= len(
        internal_columns
    ):
        return None

    return (
        internal_columns[
            option_index
        ]
    )


# ============================================================
# CROSSTAB
# ============================================================

def calculate_crosstab(
    df,
    row_metadata,
    column_metadata,
    column_option=None
):
    """
    Crosstab yang didukung:

    SA x SA
    SA x MA

    Tidak mendukung:
    MA x SA
    MA x MA
    Open
    Contact
    """

    row_type = (
        row_metadata["type"]
    )

    column_type = (
        column_metadata["type"]
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    if (
        row_type in ["Open", "Contact"]
        or column_type in [
            "Open",
            "Contact"
        ]
    ):

        raise ValueError(
            "Open-ended dan Contact variable "
            "tidak dapat digunakan dalam crosstab."
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

    if row_type != "SA":

        raise ValueError(
            "Row Variable must be SA."
        )

    # ========================================================
    # ROW DATA
    # ========================================================

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
            "base_n": 0
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
                "base_n": 0
            }

        column_series = (
            df[column_column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        valid_mask = (
            (row_series != "")
            &
            (column_series != "")
        )

        clean_row = (
            row_series[
                valid_mask
            ]
        )

        clean_column = (
            column_series[
                valid_mask
            ]
        )

        result = pd.crosstab(
            clean_row,
            clean_column
        )

        base_n = len(
            clean_row
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

        if (
            ma_column is None
            or ma_column
            not in df.columns
        ):

            return {
                "absolute":
                    pd.DataFrame(),
                "percentage":
                    pd.DataFrame(),
                "base_n": 0
            }

        ma_series = (
            pd.to_numeric(
                df[ma_column],
                errors="coerce"
            )
            .fillna(0)
        )

        valid_mask = (
            row_series != ""
        )

        clean_row = (
            row_series[
                valid_mask
            ]
        )

        clean_ma = (
            ma_series[
                valid_mask
            ]
        )

        result = pd.crosstab(
            clean_row,
            clean_ma
        )

        if 1 in result.columns:

            result = (
                result[[1]]
            )

            result.columns = [
                column_option
            ]

        else:

            result = pd.DataFrame(
                0,
                index=result.index,
                columns=[
                    column_option
                ]
            )

        base_n = len(
            clean_row
        )

    else:

        raise ValueError(
            "Unsupported crosstab combination."
        )

    # ========================================================
    # PERCENTAGE
    # ========================================================

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
        "absolute": result,
        "percentage": percentage,
        "base_n": base_n
    }


# ============================================================
# OPEN FEEDBACK
# ============================================================

def collect_open_feedback(
    df,
    metadata_item
):
    """
    Mengambil hanya pertanyaan Open.

    Contact seperti nomor HP otomatis tidak masuk.
    """

    if metadata_item["type"] != "Open":

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

    series = series[
        series != ""
    ]

    if series.empty:

        return pd.DataFrame(
            columns=[
                "Question",
                "Open Feedback"
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
# DUPLICATE DETECTION
# ============================================================

def detect_open_duplicates(
    df,
    metadata_item
):
    """
    Duplicate detection hanya untuk Open Question.
    Contact tidak diperiksa.
    """

    if metadata_item["type"] != "Open":
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
        working["Response"]
        .apply(normalize_text)
    )

    # --------------------------------------------------------
    # Remove blanks
    # --------------------------------------------------------

    working = (
        working[
            working[
                "_normalized_answer"
            ] != ""
        ]
        .copy()
    )

    if working.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # Count identical answers
    # --------------------------------------------------------

    counts = (
        working[
            "_normalized_answer"
        ]
        .value_counts()
    )

    duplicate_values = (
        counts[
            counts > 1
        ].index
    )

    if len(
        duplicate_values
    ) == 0:

        return pd.DataFrame()

    duplicate_df = (
        working[
            working[
                "_normalized_answer"
            ].isin(
                duplicate_values
            )
        ]
        .copy()
    )

    # --------------------------------------------------------
    # Duplicate group
    # --------------------------------------------------------

    group_mapping = {
        value: index + 1
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
        .map(counts)
    )

    return duplicate_df
