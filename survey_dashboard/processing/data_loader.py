import pandas as pd
import numpy as np
import re


# ============================================================
# BASIC HELPERS
# ============================================================

def is_blank(value):

    if pd.isna(value):
        return True

    text = str(value).strip()

    return text == ""


def clean_text(value):

    if pd.isna(value):
        return ""

    text = str(value).strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


def safe_column_name(value):

    text = clean_text(value)

    text = re.sub(
        r"\s+",
        "_",
        text
    )

    text = re.sub(
        r"[^A-Za-z0-9_]",
        "",
        text
    )

    if not text:

        text = "option"

    return text


def make_unique_name(
    base_name,
    existing_names
):

    if base_name not in existing_names:

        return base_name

    counter = 2

    while (
        f"{base_name}_{counter}"
        in existing_names
    ):

        counter += 1

    return f"{base_name}_{counter}"


# ============================================================
# PHONE / CONTACT QUESTION DETECTION
# ============================================================

def is_phone_question(question):

    text = clean_text(
        question
    ).lower()

    phone_keywords = [
        "nomor hp",
        "no hp",
        "no. hp",
        "no.h.p",
        "nomor handphone",
        "no handphone",
        "nomor telepon",
        "no telepon",
        "no. telepon",
        "nomor telephone",
        "telephone number",
        "phone number",
        "phone no",
        "phone",
        "mobile number",
        "mobile no",
        "mobile",
        "telephone",
        "telp",
        "telepon",
        "whatsapp",
        "whatsapp number",
        "wa number",
        "no wa",
        "nomor wa"
    ]

    return any(
        keyword in text
        for keyword in phone_keywords
    )


# ============================================================
# GOOGLE FORMS
# ============================================================

def detect_google_question_type(series):

    values = (
        series
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[
        values != ""
    ]

    if values.empty:

        return "SA"

    comma_ratio = (
        values
        .str.contains(
            ",",
            regex=False
        )
        .mean()
    )

    if comma_ratio >= 0.20:

        return "MA"

    unique_ratio = (
        values.nunique()
        / max(len(values), 1)
    )

    average_length = (
        values.str.len().mean()
    )

    if (
        unique_ratio >= 0.50
        and average_length >= 25
    ):

        return "Open"

    return "SA"


def parse_google_ma_options(series):

    options = []

    for value in series:

        if pd.isna(value):
            continue

        text = str(value).strip()

        if not text:
            continue

        parts = [
            x.strip()
            for x in text.split(",")
            if x.strip()
        ]

        options.extend(parts)

    return sorted(
        set(options)
    )


def load_google_forms(
    uploaded_file
):

    raw_df = pd.read_excel(
        uploaded_file,
        header=0,
        dtype=str
    )

    raw_df = raw_df.copy()

    respondent_count = len(raw_df)

    analysis_df = raw_df.copy()

    metadata = []

    used_internal_names = set()

    for column in raw_df.columns:

        question = clean_text(column)

        # ====================================================
        # PHONE QUESTIONS
        # ====================================================

        if is_phone_question(question):

            question_type = "Open"

        else:

            question_type = detect_google_question_type(
                raw_df[column]
            )

        # ====================================================
        # MA
        # ====================================================

        if question_type == "MA":

            options = parse_google_ma_options(
                raw_df[column]
            )

            internal_columns = []

            for option in options:

                base_name = safe_column_name(
                    f"{question}_{option}"
                )

                internal_name = make_unique_name(
                    base_name,
                    used_internal_names
                )

                used_internal_names.add(
                    internal_name
                )

                internal_columns.append(
                    internal_name
                )

                option_lower = (
                    clean_text(option)
                    .lower()
                )

                def parse_answer(
                    value,
                    target=option_lower
                ):

                    if pd.isna(value):

                        return 0

                    text = str(value).strip()

                    if not text:

                        return 0

                    answers = [
                        clean_text(x).lower()
                        for x in text.split(",")
                        if clean_text(x)
                    ]

                    return int(
                        target in answers
                    )

                analysis_df[internal_name] = (
                    raw_df[column]
                    .apply(parse_answer)
                )

            metadata.append(
                {
                    "question":
                        question,

                    "type":
                        "MA",

                    "options":
                        options,

                    "source_column":
                        column,

                    "source_columns":
                        [column],

                    "internal_columns":
                        internal_columns
                }
            )

        # ====================================================
        # SA / OPEN
        # ====================================================

        else:

            options = []

            if question_type == "SA":

                values = (
                    raw_df[column]
                    .dropna()
                    .astype(str)
                    .str.strip()
                )

                options = sorted(
                    [
                        x
                        for x in values.unique()
                        if x != ""
                    ]
                )

            metadata.append(
                {
                    "question":
                        question,

                    "type":
                        question_type,

                    "options":
                        options,

                    "source_column":
                        column,

                    "source_columns":
                        [column],

                    "internal_columns":
                        []
                }
            )

    return (
        raw_df,
        analysis_df,
        metadata,
        respondent_count
    )


# ============================================================
# SURVEYMONKEY
# ============================================================

def clean_surveymonkey_header(
    value
):

    if pd.isna(value):

        return ""

    text = str(value).strip()

    if text.lower().startswith(
        "unnamed"
    ):

        return ""

    return text


def load_surveymonkey(
    uploaded_file
):

    raw_df = pd.read_excel(
        uploaded_file,
        header=[0, 1],
        dtype=str
    )

    raw_df = raw_df.copy()

    physical_df = pd.read_excel(
        uploaded_file,
        header=None
    )

    respondent_count = max(
        len(physical_df) - 2,
        0
    )

    analysis_df = raw_df.copy()

    metadata = []

    used_internal_names = set()

    questions = []

    for column in raw_df.columns:

        question = clean_surveymonkey_header(
            column[0]
        )

        if (
            question
            and question not in questions
        ):

            questions.append(question)

    for question in questions:

        question_columns = [
            column
            for column in raw_df.columns
            if clean_surveymonkey_header(
                column[0]
            ) == question
        ]

        # ====================================================
        # PHONE QUESTIONS
        # ====================================================

        if is_phone_question(question):

            column = question_columns[0]

            metadata.append(
                {
                    "question":
                        question,

                    "type":
                        "Open",

                    "options":
                        [],

                    "source_column":
                        column,

                    "source_columns":
                        question_columns,

                    "internal_columns":
                        []
                }
            )

            continue

        # ====================================================
        # MULTIPLE COLUMNS = MA
        # ====================================================

        if len(question_columns) > 1:

            options = []

            internal_columns = []

            for column in question_columns:

                option = clean_surveymonkey_header(
                    column[1]
                )

                if not option:
                    continue

                options.append(option)

                base_name = safe_column_name(
                    f"{question}_{option}"
                )

                internal_name = make_unique_name(
                    base_name,
                    used_internal_names
                )

                used_internal_names.add(
                    internal_name
                )

                internal_columns.append(
                    internal_name
                )

                analysis_df[internal_name] = (
                    raw_df[column]
                    .apply(
                        lambda value:
                            1
                            if (
                                pd.notna(value)
                                and str(value).strip()
                                not in [
                                    "",
                                    "0",
                                    "No",
                                    "NO",
                                    "False",
                                    "FALSE"
                                ]
                            )
                            else 0
                    )
                )

            metadata.append(
                {
                    "question":
                        question,

                    "type":
                        "MA",

                    "options":
                        options,

                    "source_column":
                        None,

                    "source_columns":
                        question_columns,

                    "internal_columns":
                        internal_columns
                }
            )

        # ====================================================
        # ONE COLUMN = SA / OPEN
        # ====================================================

        else:

            column = question_columns[0]

            second_header = (
                clean_surveymonkey_header(
                    column[1]
                )
            )

            if second_header:

                question_type = "SA"

            else:

                question_type = "Open"

            options = []

            if question_type == "SA":

                values = (
                    raw_df[column]
                    .dropna()
                    .astype(str)
                    .str.strip()
                )

                options = sorted(
                    [
                        x
                        for x in values.unique()
                        if x != ""
                    ]
                )

            metadata.append(
                {
                    "question":
                        question,

                    "type":
                        question_type,

                    "options":
                        options,

                    "source_column":
                        column,

                    "source_columns":
                        [column],

                    "internal_columns":
                        []
                }
            )

    return (
        raw_df,
        analysis_df,
        metadata,
        respondent_count
    )


# ============================================================
# MAIN LOADER
# ============================================================

def load_survey_data(
    uploaded_file,
    platform
):

    if platform == "Google Forms":

        return load_google_forms(
            uploaded_file
        )

    if platform == "SurveyMonkey":

        return load_surveymonkey(
            uploaded_file
        )

    raise ValueError(
        "Unsupported platform."
    )
