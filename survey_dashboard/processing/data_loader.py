import pandas as pd
import re


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):

    if pd.isna(value):
        return ""

    text = (
        str(
            value
        )
        .strip()
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


def safe_column_name(value):

    text = (
        clean_text(
            value
        )
    )

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

    return (
        f"{base_name}_{counter}"
    )


# ============================================================
# CONTACT
# ============================================================

def is_phone_question(
    question
):

    text = (
        clean_text(
            question
        )
        .lower()
    )

    keywords = [
        "nomor hp",
        "no hp",
        "no. hp",
        "nomor handphone",
        "no handphone",
        "nomor telepon",
        "no telepon",
        "phone number",
        "mobile number",
        "nomor whatsapp",
        "whatsapp number",
        "no wa",
        "nomor wa"
    ]

    return any(
        keyword in text
        for keyword in keywords
    )


# ============================================================
# OPEN
# ============================================================

def is_name_question(
    question
):

    text = (
        clean_text(
            question
        )
        .lower()
    )

    keywords = [
        "nama anda",
        "nama lengkap",
        "nama responden",
        "nama kamu",
        "your name",
        "full name"
    ]

    return any(
        keyword in text
        for keyword in keywords
    )


def is_feedback_question(
    question
):

    text = (
        clean_text(
            question
        )
        .lower()
    )

    keywords = [
        "saran",
        "masukan",
        "kritik",
        "feedback",
        "komentar",
        "keluhan",
        "tanggapan",
        "perbaikan internal",
        "ceritakan pengalaman",
        "pengalaman anda",
        "pengalaman kamu",
        "pengalaman tersebut",
        "secara rinci",
        "secara detail",
        "suggestion",
        "comment",
        "complaint",
        "describe your experience",
        "tell us your experience"
    ]

    return any(
        keyword in text
        for keyword in keywords
    )


def is_open_question_hint(
    question
):

    text = (
        clean_text(
            question
        )
        .lower()
    )

    keywords = [
        "ceritakan",
        "jelaskan",
        "uraikan",
        "deskripsikan",
        "tuliskan",
        "secara rinci",
        "secara detail",
        "please explain",
        "please describe",
        "tell us",
        "describe your",
        "in detail"
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
        for keyword in keywords
    )


# ============================================================
# LAINNYA
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


def is_other_option(
    value
):

    text = (
        clean_text(
            value
        )
        .lower()
    )

    for prefix in (
        OTHER_PREFIXES
    ):

        if text == prefix:
            return True

        if text.startswith(
            prefix + ":"
        ):
            return True

        if text.startswith(
            prefix + "-"
        ):
            return True

        if text.startswith(
            prefix + " -"
        ):
            return True

    return False


def normalize_ma_option(
    option
):

    text = (
        clean_text(
            option
        )
    )

    if is_other_option(
        text
    ):

        return "Lainnya"

    return text


def extract_other_detail(
    value
):

    if pd.isna(value):
        return ""

    text = (
        clean_text(
            value
        )
    )

    lower = (
        text.lower()
    )

    for prefix in (
        OTHER_PREFIXES
    ):

        if lower == prefix:
            return ""

        patterns = [
            prefix + ":",
            prefix + "-",
            prefix + " -"
        ]

        for pattern in patterns:

            if lower.startswith(
                pattern
            ):

                return (
                    text[
                        len(
                            pattern
                        ):
                    ]
                    .strip()
                )

    return ""


# ============================================================
# GOOGLE FORMS TYPE
# ============================================================

def detect_google_question_type(
    series,
    question=""
):

    if is_phone_question(
        question
    ):
        return "Contact"

    if is_open_question_hint(
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

    unique_ratio = (
        values.nunique()
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

    if (
        unique_ratio >= 0.90
        and
        average_length >= 60
    ):

        return "Open"

    rows_with_multiple = 0

    split_options = []

    for value in values:

        parts = [
            normalize_ma_option(
                part
            )
            for part
            in str(
                value
            ).split(",")
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

    if (
        rows_with_multiple > 0
        and
        split_options
    ):

        multi_ratio = (
            rows_with_multiple
            / total_rows
        )

        split_series = (
            pd.Series(
                split_options
            )
        )

        repeated_ratio = (
            1
            -
            (
                split_series.nunique()
                / len(
                    split_series
                )
            )
        )

        average_option_length = (
            split_series
            .str.len()
            .mean()
        )

        if (
            multi_ratio >= 0.10
            and
            repeated_ratio >= 0.30
            and
            average_option_length <= 80
        ):

            return "MA"

    return "SA"


def parse_google_ma_options(
    series
):

    options = []

    seen = set()

    for value in series:

        if pd.isna(value):
            continue

        parts = [
            normalize_ma_option(
                part
            )
            for part
            in str(
                value
            ).split(",")
            if clean_text(
                part
            )
        ]

        for option in parts:

            key = (
                option.lower()
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
# GOOGLE FORMS LOAD
# ============================================================

def load_google_forms(
    uploaded_file,
    sheet_name
):

    raw_df = (
        pd.read_excel(
            uploaded_file,
            sheet_name=
                sheet_name,
            header=0,
            dtype=str
        )
    )

    analysis_df = (
        raw_df.copy()
    )

    metadata = []

    used_names = set()

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

                internal_name = (
                    make_unique_name(
                        safe_column_name(
                            f"{question}_{option}"
                        ),
                        used_names
                    )
                )

                used_names.add(
                    internal_name
                )

                internal_columns.append(
                    internal_name
                )

                target = (
                    option.lower()
                )

                def parse_answer(
                    value,
                    target_option=target
                ):

                    if pd.isna(value):
                        return 0

                    answers = [
                        normalize_ma_option(
                            part
                        )
                        .lower()
                        for part
                        in str(
                            value
                        ).split(",")
                        if clean_text(
                            part
                        )
                    ]

                    return int(
                        target_option
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

                if option == "Lainnya":

                    other_detail_column = (
                        make_unique_name(
                            safe_column_name(
                                f"{question}_Lainnya_Detail"
                            ),
                            used_names
                        )
                    )

                    used_names.add(
                        other_detail_column
                    )

                    def extract_google_other(
                        value
                    ):

                        if pd.isna(value):
                            return ""

                        details = []

                        for part in str(
                            value
                        ).split(","):

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

        elif question_type == "SA":

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

            options = (
                list(
                    dict.fromkeys(
                        values.tolist()
                    )
                )
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

        elif question_type == "Open":

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

        elif question_type == "Contact":

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

    return (
        raw_df,
        analysis_df,
        metadata,
        len(
            raw_df
        )
    )


# ============================================================
# SURVEYMONKEY HELPERS
# ============================================================

def clean_surveymonkey_header(
    value
):

    if pd.isna(value):
        return ""

    text = (
        str(
            value
        )
        .strip()
    )

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

    text = (
        clean_text(
            value
        )
        .lower()
    )

    open_headers = [
        "open-ended response",
        "open ended response",
        "open-response",
        "open response",
        "text response",
        "response text"
    ]

    return any(
        header in text
        for header
        in open_headers
    )


# ============================================================
# SURVEYMONKEY LOAD
# ============================================================

def load_surveymonkey(
    uploaded_file,
    sheet_name
):

    raw_df = (
        pd.read_excel(
            uploaded_file,
            sheet_name=
                sheet_name,
            header=[
                0,
                1
            ],
            dtype=str
        )
    )

    analysis_df = (
        raw_df.copy()
    )

    metadata = []

    used_names = set()

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

        # ====================================================
        # CONTACT
        # ====================================================

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

        # ====================================================
        # OPEN-ENDED RESPONSE PRIORITY
        # ====================================================

        open_columns = [
            column
            for column
            in question_columns
            if is_surveymonkey_open_header(
                column[
                    1
                ]
            )
        ]

        if open_columns:

            open_column = (
                open_columns[
                    0
                ]
            )

            metadata.append(
                {
                    "question":
                        question,
                    "type":
                        "Open",
                    "options":
                        [],
                    "source_column":
                        open_column,
                    "source_columns":
                        open_columns,
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

        # ====================================================
        # SINGLE COLUMN = SA / OPEN FALLBACK
        # ====================================================

        if len(
            question_columns
        ) == 1:

            column = (
                question_columns[
                    0
                ]
            )

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

            if (
                is_name_question(
                    question
                )
                or
                is_feedback_question(
                    question
                )
            ):

                question_type = (
                    "Open"
                )

            elif (
                not values.empty
                and
                values.nunique()
                / len(
                    values
                )
                >= 0.90
                and
                values
                .str.len()
                .mean()
                >= 60
            ):

                question_type = (
                    "Open"
                )

            else:

                question_type = (
                    "SA"
                )

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

            else:

                options = (
                    list(
                        dict.fromkeys(
                            values.tolist()
                        )
                    )
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

        # ====================================================
        # MULTIPLE COLUMNS = MA
        # ====================================================

        normalized_options = []

        option_columns = {}

        other_sources = []

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

            if option == "Lainnya":

                other_sources.append(
                    column
                )

            if (
                option
                not in option_columns
            ):

                normalized_options.append(
                    option
                )

                option_columns[
                    option
                ] = []

            option_columns[
                option
            ].append(
                column
            )

        internal_columns = []

        other_detail_column = None

        for option in (
            normalized_options
        ):

            internal_name = (
                make_unique_name(
                    safe_column_name(
                        f"{question}_{option}"
                    ),
                    used_names
                )
            )

            used_names.add(
                internal_name
            )

            internal_columns.append(
                internal_name
            )

            masks = []

            for source_column in (
                option_columns[
                    option
                ]
            ):

                mask = (
                    raw_df[
                        source_column
                    ]
                    .apply(
                        lambda value:
                        int(
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
                    )
                )

                masks.append(
                    mask
                )

            analysis_df[
                internal_name
            ] = (
                pd.concat(
                    masks,
                    axis=1
                )
                .max(
                    axis=1
                )
                .astype(
                    int
                )
            )

        if (
            "Lainnya"
            in normalized_options
            and
            other_sources
        ):

            other_detail_column = (
                make_unique_name(
                    safe_column_name(
                        f"{question}_Lainnya_Detail"
                    ),
                    used_names
                )
            )

            used_names.add(
                other_detail_column
            )

            def collect_other(
                row
            ):

                details = []

                for column in (
                    other_sources
                ):

                    value = (
                        row[
                            column
                        ]
                    )

                    if pd.isna(value):
                        continue

                    text = (
                        clean_text(
                            value
                        )
                    )

                    if not text:
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

                    elif (
                        text.lower()
                        not in [
                            "1",
                            "yes",
                            "true"
                        ]
                        and
                        not is_other_option(
                            text
                        )
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
                    collect_other,
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
                    normalized_options,
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

    return (
        raw_df,
        analysis_df,
        metadata,
        len(
            raw_df
        )
    )


# ============================================================
# MAIN LOADER
# ============================================================

def load_survey_data(
    uploaded_file,
    platform,
    sheet_name
):

    if platform == "Google Forms":

        return load_google_forms(
            uploaded_file,
            sheet_name
        )

    if platform == "SurveyMonkey":

        return load_surveymonkey(
            uploaded_file,
            sheet_name
        )

    raise ValueError(
        "Unsupported platform."
    )
