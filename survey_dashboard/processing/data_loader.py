import pandas as pd
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
# PHONE / CONTACT DETECTION
# ============================================================

def is_phone_question(question):

    text = clean_text(
        question
    ).lower()

    phone_keywords = [
        "nomor hp",
        "no hp",
        "no. hp",
        "no.hp",
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
        "mobile number",
        "mobile no",
        "nomor whatsapp",
        "whatsapp number",
        "wa number",
        "no wa",
        "nomor wa",
        "no. wa"
    ]

    return any(
        keyword in text
        for keyword in phone_keywords
    )


# ============================================================
# OPEN QUESTION DETECTION
# ============================================================

def is_name_question(question):

    text = clean_text(
        question
    ).lower()

    name_keywords = [
        "nama anda",
        "nama lengkap",
        "nama responden",
        "nama kamu",
        "siapa nama",
        "your name",
        "full name",
        "respondent name"
    ]

    return any(
        keyword in text
        for keyword in name_keywords
    )


def is_feedback_question(question):

    text = clean_text(
        question
    ).lower()

    feedback_keywords = [
        "saran",
        "masukan",
        "kritik",
        "feedback",
        "komentar",
        "keluhan",
        "tanggapan",
        "suggestion",
        "comment",
        "complaint"
    ]

    return any(
        keyword in text
        for keyword in feedback_keywords
    )


def is_open_question_hint(question):

    text = clean_text(
        question
    ).lower()

    open_keywords = [
        "ceritakan",
        "jelaskan secara",
        "tuliskan",
        "please explain",
        "please describe",
        "tell us",
        "describe your",
        "open ended",
        "open-ended"
    ]

    if is_name_question(
        question
    ):
        return True

    if is_feedback_question(
        question
    ):
        return True

    return any(
        keyword in text
        for keyword in open_keywords
    )


# ============================================================
# OTHER / LAINNYA
# ============================================================

OTHER_PREFIXES = [
    "lainnya",
    "lain-lain",
    "lain lain",
    "other",
    "others",
    "other response",
    "other (please specify)",
    "other please specify"
]


def is_other_option(value):

    text = (
        clean_text(
            value
        )
        .lower()
    )

    if not text:

        return False

    for prefix in OTHER_PREFIXES:

        if text == prefix:

            return True

        if text.startswith(
            prefix + ":"
        ):

            return True

        if text.startswith(
            prefix + " -"
        ):

            return True

        if text.startswith(
            prefix + "-"
        ):

            return True

    return False


def normalize_ma_option(option):

    text = clean_text(
        option
    )

    if is_other_option(
        text
    ):

        return "Lainnya"

    return text


def normalize_google_ma_option(option):

    return normalize_ma_option(
        option
    )


def extract_other_detail(value):

    if pd.isna(value):

        return ""

    text = clean_text(
        value
    )

    text_lower = (
        text.lower()
    )

    for prefix in OTHER_PREFIXES:

        if text_lower == prefix:

            return ""

        patterns = [
            prefix + ":",
            prefix + " -",
            prefix + "-"
        ]

        for pattern in patterns:

            if text_lower.startswith(
                pattern
            ):

                return (
                    text[
                        len(pattern):
                    ]
                    .strip()
                )

    return ""


# ============================================================
# GOOGLE FORMS QUESTION TYPE
# ============================================================

def detect_google_question_type(
    series,
    question=""
):

    if is_phone_question(
        question
    ):
        return "Contact"

    if is_name_question(
        question
    ):
        return "Open"

    if is_feedback_question(
        question
    ):
        return "Open"

    values = (
        series
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = (
        values[
            values != ""
        ]
    )

    if values.empty:
        return "SA"

    total_rows = (
        len(
            values
        )
    )

    unique_count = (
        values.nunique()
    )

    unique_ratio = (
        unique_count
        / max(
            total_rows,
            1
        )
    )

    average_length = (
        values
        .str.len()
        .mean()
    )

    rows_with_multiple = 0

    split_options = []

    for value in values:

        parts = [
            normalize_google_ma_option(
                part
            )

            for part
            in str(value).split(",")

            if clean_text(
                part
            )
        ]

        if len(parts) >= 2:

            rows_with_multiple += 1

        split_options.extend(
            [
                part.lower()
                for part
                in parts
            ]
        )

    multi_row_ratio = (
        rows_with_multiple
        / max(
            total_rows,
            1
        )
    )

    if (
        rows_with_multiple > 0
        and
        split_options
    ):

        split_series = (
            pd.Series(
                split_options
            )
        )

        total_split = (
            len(
                split_series
            )
        )

        unique_split = (
            split_series.nunique()
        )

        repeated_ratio = (
            1
            -
            (
                unique_split
                / max(
                    total_split,
                    1
                )
            )
        )

        average_option_length = (
            split_series
            .str.len()
            .mean()
        )

        if (
            multi_row_ratio >= 0.10
            and
            repeated_ratio >= 0.30
            and
            average_option_length <= 80
        ):

            return "MA"

    if (
        unique_ratio >= 0.90
        and
        average_length >= 60
    ):

        return "Open"

    return "SA"


# ============================================================
# GOOGLE FORMS MA OPTIONS
# ============================================================

def parse_google_ma_options(series):

    options = []

    seen = set()

    for value in series:

        if pd.isna(value):
            continue

        text = str(
            value
        ).strip()

        if not text:
            continue

        parts = [
            normalize_ma_option(
                part
            )

            for part
            in text.split(",")

            if clean_text(
                part
            )
        ]

        for option in parts:

            key = (
                option
                .lower()
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            options.append(
                option
            )

    return options


# ============================================================
# LOAD GOOGLE FORMS
# ============================================================

def load_google_forms(
    uploaded_file
):

    raw_df = pd.read_excel(
        uploaded_file,
        header=0,
        dtype=str
    )

    raw_df = (
        raw_df.copy()
    )

    analysis_df = (
        raw_df.copy()
    )

    respondent_count = (
        len(
            raw_df
        )
    )

    metadata = []

    used_internal_names = set()

    for column in (
        raw_df.columns
    ):

        question = (
            clean_text(
                column
            )
        )

        question_type = (
            detect_google_question_type(
                raw_df[
                    column
                ],
                question
            )
        )

        if question_type == "MA":

            options = (
                parse_google_ma_options(
                    raw_df[
                        column
                    ]
                )
            )

            internal_columns = []

            other_detail_column = None

            for option in options:

                base_name = (
                    safe_column_name(
                        f"{question}_{option}"
                    )
                )

                internal_name = (
                    make_unique_name(
                        base_name,
                        used_internal_names
                    )
                )

                used_internal_names.add(
                    internal_name
                )

                internal_columns.append(
                    internal_name
                )

                target_option = (
                    normalize_ma_option(
                        option
                    )
                    .lower()
                )

                def parse_answer(
                    value,
                    target=target_option
                ):

                    if pd.isna(
                        value
                    ):
                        return 0

                    text = str(
                        value
                    ).strip()

                    if not text:
                        return 0

                    answers = [
                        normalize_ma_option(
                            part
                        )
                        .lower()

                        for part
                        in text.split(",")

                        if clean_text(
                            part
                        )
                    ]

                    return int(
                        target
                        in answers
                    )

                analysis_df[
                    internal_name
                ] = (
                    raw_df[
                        column
                    ]
                    .apply(
                        parse_answer
                    )
                )

                if (
                    option
                    == "Lainnya"
                ):

                    other_detail_column = (
                        make_unique_name(
                            safe_column_name(
                                f"{question}_Lainnya_Detail"
                            ),
                            used_internal_names
                        )
                    )

                    used_internal_names.add(
                        other_detail_column
                    )

                    def extract_google_other(
                        value
                    ):

                        if pd.isna(
                            value
                        ):

                            return ""

                        details = []

                        for part in str(
                            value
                        ).split(","):

                            part = (
                                clean_text(
                                    part
                                )
                            )

                            if not part:
                                continue

                            detail = (
                                extract_other_detail(
                                    part
                                )
                            )

                            if detail:

                                details.append(
                                    detail
                                )

                        return " | ".join(
                            details
                        )

                    analysis_df[
                        other_detail_column
                    ] = (
                        raw_df[
                            column
                        ]
                        .apply(
                            extract_google_other
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
                        column,

                    "source_columns":
                        [
                            column
                        ],

                    "internal_columns":
                        internal_columns,

                    "other_detail_column":
                        other_detail_column,

                    "is_feedback":
                        False
                }
            )

            continue

        if question_type == "SA":

            options = []

            seen = set()

            values = (
                raw_df[
                    column
                ]
                .dropna()
                .astype(str)
                .str.strip()
            )

            values = (
                values[
                    values != ""
                ]
            )

            for value in values:

                key = (
                    value.lower()
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                options.append(
                    value
                )

            metadata.append(
                {
                    "question":
                        question,

                    "type":
                        "SA",

                    "options":
                        options,

                    "source_column":
                        column,

                    "source_columns":
                        [
                            column
                        ],

                    "internal_columns":
                        [],

                    "other_detail_column":
                        None,

                    "is_feedback":
                        False
                }
            )

            continue

        if question_type == "Open":

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
                        [
                            column
                        ],

                    "internal_columns":
                        [],

                    "other_detail_column":
                        None,

                    "is_feedback":
                        is_feedback_question(
                            question
                        )
                }
            )

            continue

        if question_type == "Contact":

            metadata.append(
                {
                    "question":
                        question,

                    "type":
                        "Contact",

                    "options":
                        [],

                    "source_column":
                        column,

                    "source_columns":
                        [
                            column
                        ],

                    "internal_columns":
                        [],

                    "other_detail_column":
                        None,

                    "is_feedback":
                        False
                }
            )

            continue

    return (
        raw_df,
        analysis_df,
        metadata,
        respondent_count
    )


# ============================================================
# SURVEYMONKEY HELPERS
# ============================================================

def clean_surveymonkey_header(
    value
):

    if pd.isna(value):
        return ""

    text = str(
        value
    ).strip()

    if (
        text.lower()
        .startswith(
            "unnamed"
        )
    ):
        return ""

    return text


def is_surveymonkey_open_header(
    value
):

    text = clean_text(
        value
    ).lower()

    open_headers = [
        "open-ended response",
        "open ended response",
        "open-ended",
        "open ended",
        "text response",
        "response text",
        "comment",
        "comments",
        "other response",
        "other (please specify)",
        "please specify"
    ]

    return any(
        keyword in text
        for keyword in open_headers
    )


def detect_surveymonkey_single_type(
    question,
    second_header,
    series
):

    if is_phone_question(
        question
    ):
        return "Contact"

    if is_name_question(
        question
    ):
        return "Open"

    if is_feedback_question(
        question
    ):
        return "Open"

    if is_surveymonkey_open_header(
        second_header
    ):
        return "Open"

    values = (
        series
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = (
        values[
            values != ""
        ]
    )

    if values.empty:

        if not second_header:
            return "Open"

        return "SA"

    unique_ratio = (
        values.nunique()
        / max(
            len(
                values
            ),
            1
        )
    )

    average_length = (
        values
        .str.len()
        .mean()
    )

    if (
        unique_ratio >= 0.90
        and
        average_length >= 60
    ):
        return "Open"

    return "SA"


# ============================================================
# LOAD SURVEYMONKEY
# ============================================================

def load_surveymonkey(
    uploaded_file
):

    raw_df = pd.read_excel(
        uploaded_file,
        header=[
            0,
            1
        ],
        dtype=str
    )

    raw_df = (
        raw_df.copy()
    )

    analysis_df = (
        raw_df.copy()
    )

    respondent_count = (
        len(
            raw_df
        )
    )

    metadata = []

    used_internal_names = set()

    questions = []

    for column in (
        raw_df.columns
    ):

        question = (
            clean_surveymonkey_header(
                column[
                    0
                ]
            )
        )

        if (
            question
            and
            question not in questions
        ):

            questions.append(
                question
            )

    for question in questions:

        question_columns = [
            column

            for column
            in raw_df.columns

            if (
                clean_surveymonkey_header(
                    column[
                        0
                    ]
                )
                == question
            )
        ]

        if not question_columns:
            continue

        if is_phone_question(
            question
        ):

            column = (
                question_columns[
                    0
                ]
            )

            metadata.append(
                {
                    "question":
                        question,

                    "type":
                        "Contact",

                    "options":
                        [],

                    "source_column":
                        column,

                    "source_columns":
                        question_columns,

                    "internal_columns":
                        [],

                    "other_detail_column":
                        None,

                    "is_feedback":
                        False
                }
            )

            continue

        if len(
            question_columns
        ) > 1:

            normalized_options = []

            option_source_columns = {}

            other_detail_sources = []

            for column in (
                question_columns
            ):

                raw_option = (
                    clean_surveymonkey_header(
                        column[
                            1
                        ]
                    )
                )

                if not raw_option:
                    continue

                option = (
                    normalize_ma_option(
                        raw_option
                    )
                )

                if (
                    option
                    == "Lainnya"
                ):

                    other_detail_sources.append(
                        column
                    )

                if option not in option_source_columns:

                    normalized_options.append(
                        option
                    )

                    option_source_columns[
                        option
                    ] = []

                option_source_columns[
                    option
                ].append(
                    column
                )

            options = []

            internal_columns = []

            other_detail_column = None

            for option in normalized_options:

                source_columns = (
                    option_source_columns[
                        option
                    ]
                )

                options.append(
                    option
                )

                base_name = (
                    safe_column_name(
                        f"{question}_{option}"
                    )
                )

                internal_name = (
                    make_unique_name(
                        base_name,
                        used_internal_names
                    )
                )

                used_internal_names.add(
                    internal_name
                )

                internal_columns.append(
                    internal_name
                )

                masks = []

                for source_column in (
                    source_columns
                ):

                    source_series = (
                        raw_df[
                            source_column
                        ]
                    )

                    mask = (
                        source_series
                        .apply(
                            lambda value:
                                (
                                    1

                                    if (
                                        pd.notna(
                                            value
                                        )
                                        and
                                        str(
                                            value
                                        )
                                        .strip()
                                        .lower()
                                        not in [
                                            "",
                                            "0",
                                            "no",
                                            "false",
                                            "nan"
                                        ]
                                    )

                                    else 0
                                )
                        )
                    )

                    masks.append(
                        mask
                    )

                if masks:

                    combined = (
                        pd.concat(
                            masks,
                            axis=1
                        )
                        .max(
                            axis=1
                        )
                    )

                else:

                    combined = (
                        pd.Series(
                            0,
                            index=
                                raw_df.index
                        )
                    )

                analysis_df[
                    internal_name
                ] = combined.astype(
                    int
                )

            if (
                "Lainnya"
                in options
                and
                other_detail_sources
            ):

                other_detail_column = (
                    make_unique_name(
                        safe_column_name(
                            f"{question}_Lainnya_Detail"
                        ),
                        used_internal_names
                    )
                )

                used_internal_names.add(
                    other_detail_column
                )

                def collect_surveymonkey_other(
                    row
                ):

                    details = []

                    for source_column in (
                        other_detail_sources
                    ):

                        value = (
                            row[
                                source_column
                            ]
                        )

                        if pd.isna(
                            value
                        ):
                            continue

                        text = (
                            clean_text(
                                value
                            )
                        )

                        if not text:
                            continue

                        if text.lower() in [
                            "1",
                            "yes",
                            "true"
                        ]:
                            continue

                        detail = (
                            extract_other_detail(
                                text
                            )
                        )

                        if detail:

                            details.append(
                                detail
                            )

                        elif not is_other_option(
                            text
                        ):

                            details.append(
                                text
                            )

                    return " | ".join(
                        dict.fromkeys(
                            details
                        )
                    )

                analysis_df[
                    other_detail_column
                ] = (
                    raw_df
                    .apply(
                        collect_surveymonkey_other,
                        axis=1
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
                        internal_columns,

                    "other_detail_column":
                        other_detail_column,

                    "is_feedback":
                        False
                }
            )

            continue

        column = (
            question_columns[
                0
            ]
        )

        second_header = (
            clean_surveymonkey_header(
                column[
                    1
                ]
            )
        )

        question_type = (
            detect_surveymonkey_single_type(
                question,
                second_header,
                raw_df[
                    column
                ]
            )
        )

        if question_type == "SA":

            options = []

            seen = set()

            values = (
                raw_df[
                    column
                ]
                .dropna()
                .astype(str)
                .str.strip()
            )

            values = (
                values[
                    values != ""
                ]
            )

            for value in values:

                key = (
                    value.lower()
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                options.append(
                    value
                )

            metadata.append(
                {
                    "question":
                        question,

                    "type":
                        "SA",

                    "options":
                        options,

                    "source_column":
                        column,

                    "source_columns":
                        [
                            column
                        ],

                    "internal_columns":
                        [],

                    "other_detail_column":
                        None,

                    "is_feedback":
                        False
                }
            )

            continue

        if question_type == "Open":

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
                        [
                            column
                        ],

                    "internal_columns":
                        [],

                    "other_detail_column":
                        None,

                    "is_feedback":
                        is_feedback_question(
                            question
                        )
                }
            )

            continue

        if question_type == "Contact":

            metadata.append(
                {
                    "question":
                        question,

                    "type":
                        "Contact",

                    "options":
                        [],

                    "source_column":
                        column,

                    "source_columns":
                        [
                            column
                        ],

                    "internal_columns":
                        [],

                    "other_detail_column":
                        None,

                    "is_feedback":
                        False
                }
            )

            continue

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
