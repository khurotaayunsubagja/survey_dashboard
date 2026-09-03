import pandas as pd
import re


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value):
    """
    Membersihkan teks dari spasi berlebih.
    """

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
    """
    Mengubah teks menjadi nama kolom internal yang aman.
    """

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
    """
    Mencegah nama kolom internal yang sama.
    """

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
# QUESTION TYPE HELPERS
# ============================================================

def is_phone_question(question):
    """
    Mendeteksi pertanyaan nomor HP / WhatsApp / telepon.

    Pertanyaan seperti ini akan diberi tipe 'Contact',
    bukan 'Open', supaya tidak ikut Open Feedback.
    """

    text = clean_text(
        question
    ).lower()

    phone_keywords = [
        "nomor hp",
        "no hp",
        "no. hp",
        "no.hp",
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


def is_open_question_hint(question):
    """
    Mendeteksi pertanyaan yang secara struktur
    kemungkinan besar merupakan pertanyaan terbuka.

    Fungsi ini sangat membantu untuk kolom seperti:
    - Saran
    - Masukan
    - Kritik
    - Feedback
    - Alasan
    - Jelaskan...
    - Mengapa...
    """

    text = clean_text(
        question
    ).lower()

    open_keywords = [
        "saran",
        "masukan",
        "kritik",
        "feedback",
        "komentar",
        "comment",
        "suggestion",
        "pendapat",
        "tanggapan",
        "keluhan",
        "ceritakan",
        "jelaskan",
        "sebutkan",
        "tuliskan",
        "mengapa",
        "kenapa",
        "apa alasan",
        "alasannya",
        "reason",
        "describe",
        "explain",
        "tell us",
        "open ended",
        "open-ended"
    ]

    return any(
        keyword in text
        for keyword in open_keywords
    )


def is_surveymonkey_open_header(header):
    """
    SurveyMonkey sering memberikan header kedua seperti:
    'Open-Ended Response'.

    Header tersebut harus dibaca sebagai Open,
    bukan SA.
    """

    text = clean_text(
        header
    ).lower()

    open_headers = [
        "open-ended response",
        "open ended response",
        "open-ended",
        "open ended",
        "comment",
        "comments",
        "other response",
        "other (please specify)",
        "please specify",
        "response text",
        "text response"
    ]

    return any(
        keyword in text
        for keyword in open_headers
    )


# ============================================================
# GOOGLE FORMS TYPE DETECTION
# ============================================================

def detect_google_question_type(
    series,
    question=""
):
    """
    Mendeteksi tipe pertanyaan Google Forms:
    SA, MA, atau Open.

    Nama pertanyaan diprioritaskan supaya pertanyaan
    seperti 'Saran' tidak salah dianggap SA.
    """

    # --------------------------------------------------------
    # Contact
    # --------------------------------------------------------

    if is_phone_question(question):
        return "Contact"

    # --------------------------------------------------------
    # Strong Open Question hint
    # --------------------------------------------------------

    if is_open_question_hint(question):
        return "Open"

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

    # --------------------------------------------------------
    # Basic statistics
    # --------------------------------------------------------

    total_values = len(values)

    unique_count = (
        values.nunique()
    )

    unique_ratio = (
        unique_count
        / max(total_values, 1)
    )

    average_length = (
        values.str.len().mean()
    )

    comma_ratio = (
        values
        .str.contains(
            ",",
            regex=False
        )
        .mean()
    )

    # --------------------------------------------------------
    # Open text heuristic
    # --------------------------------------------------------
    # Jawaban sangat bervariasi dan cukup panjang
    # biasanya merupakan pertanyaan terbuka.
    # --------------------------------------------------------

    if (
        unique_ratio >= 0.65
        and average_length >= 18
    ):
        return "Open"

    # --------------------------------------------------------
    # Multiple Answer heuristic
    # --------------------------------------------------------

    if comma_ratio >= 0.20:

        all_tokens = []

        for value in values:

            tokens = [
                clean_text(x).lower()
                for x in str(value).split(",")
                if clean_text(x)
            ]

            all_tokens.extend(tokens)

        unique_tokens = len(
            set(all_tokens)
        )

        # MA biasanya memiliki vocabulary jawaban terbatas.
        if unique_tokens <= max(
            30,
            unique_count * 3
        ):
            return "MA"

    return "SA"


def parse_google_ma_options(series):
    """
    Mengambil seluruh opsi MA dari Google Forms.
    """

    options = []

    for value in series:

        if pd.isna(value):
            continue

        text = str(value).strip()

        if not text:
            continue

        parts = [
            clean_text(x)
            for x in text.split(",")
            if clean_text(x)
        ]

        options.extend(parts)

    return sorted(
        set(options)
    )


# ============================================================
# GOOGLE FORMS LOADER
# ============================================================

def load_google_forms(
    uploaded_file
):
    """
    Membaca data Google Forms.
    """

    raw_df = pd.read_excel(
        uploaded_file,
        header=0,
        dtype=str
    )

    raw_df = raw_df.copy()

    analysis_df = raw_df.copy()

    respondent_count = len(
        raw_df
    )

    metadata = []

    used_internal_names = set()

    # ========================================================
    # LOOP QUESTIONS
    # ========================================================

    for column in raw_df.columns:

        question = clean_text(
            column
        )

        question_type = (
            detect_google_question_type(
                raw_df[column],
                question
            )
        )

        # ====================================================
        # CONTACT
        # ====================================================

        if question_type == "Contact":

            metadata.append(
                {
                    "question": question,
                    "type": "Contact",
                    "options": [],
                    "source_column": column,
                    "source_columns": [column],
                    "internal_columns": []
                }
            )

            continue

        # ====================================================
        # MULTIPLE ANSWER
        # ====================================================

        if question_type == "MA":

            options = (
                parse_google_ma_options(
                    raw_df[column]
                )
            )

            internal_columns = []

            for option in options:

                base_name = safe_column_name(
                    f"{question}_{option}"
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
                    clean_text(option)
                    .lower()
                )

                def parse_answer(
                    value,
                    target=target_option
                ):

                    if pd.isna(value):
                        return 0

                    text = str(
                        value
                    ).strip()

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

                analysis_df[
                    internal_name
                ] = (
                    raw_df[column]
                    .apply(parse_answer)
                )

            metadata.append(
                {
                    "question": question,
                    "type": "MA",
                    "options": options,
                    "source_column": column,
                    "source_columns": [column],
                    "internal_columns":
                        internal_columns
                }
            )

            continue

        # ====================================================
        # SINGLE ANSWER
        # ====================================================

        if question_type == "SA":

            values = (
                raw_df[column]
                .dropna()
                .astype(str)
                .str.strip()
            )

            options = sorted(
                [
                    value
                    for value
                    in values.unique()
                    if value != ""
                ]
            )

        else:

            options = []

        metadata.append(
            {
                "question": question,
                "type": question_type,
                "options": options,
                "source_column": column,
                "source_columns": [column],
                "internal_columns": []
            }
        )

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
    """
    Membersihkan header SurveyMonkey.
    """

    if pd.isna(value):
        return ""

    text = str(
        value
    ).strip()

    if text.lower().startswith(
        "unnamed"
    ):
        return ""

    return text


def detect_surveymonkey_single_type(
    question,
    second_header,
    series
):
    """
    Mendeteksi tipe pertanyaan SurveyMonkey
    yang hanya memiliki satu kolom.

    Ini memperbaiki masalah:
    Open-Ended Response sebelumnya dianggap SA.
    """

    # --------------------------------------------------------
    # Nomor HP
    # --------------------------------------------------------

    if is_phone_question(question):
        return "Contact"

    # --------------------------------------------------------
    # Nama pertanyaan jelas menunjukkan Open
    # --------------------------------------------------------

    if is_open_question_hint(question):
        return "Open"

    # --------------------------------------------------------
    # Header kedua SurveyMonkey menunjukkan Open
    # --------------------------------------------------------

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

    values = values[
        values != ""
    ]

    if values.empty:
        return "SA"

    unique_ratio = (
        values.nunique()
        / max(len(values), 1)
    )

    average_length = (
        values.str.len().mean()
    )

    # --------------------------------------------------------
    # Fallback Open Detection
    # --------------------------------------------------------

    if (
        unique_ratio >= 0.65
        and average_length >= 18
    ):
        return "Open"

    return "SA"


# ============================================================
# SURVEYMONKEY LOADER
# ============================================================

def load_surveymonkey(
    uploaded_file
):
    """
    Membaca data SurveyMonkey dengan 2 baris header.
    """

    raw_df = pd.read_excel(
        uploaded_file,
        header=[0, 1],
        dtype=str
    )

    raw_df = raw_df.copy()

    analysis_df = raw_df.copy()

    respondent_count = len(
        raw_df
    )

    metadata = []

    used_internal_names = set()

    # ========================================================
    # GET UNIQUE QUESTIONS
    # ========================================================

    questions = []

    for column in raw_df.columns:

        question = (
            clean_surveymonkey_header(
                column[0]
            )
        )

        if (
            question
            and question not in questions
        ):
            questions.append(
                question
            )

    # ========================================================
    # PROCESS QUESTION
    # ========================================================

    for question in questions:

        question_columns = [
            column
            for column in raw_df.columns
            if clean_surveymonkey_header(
                column[0]
            ) == question
        ]

        if not question_columns:
            continue

        # ====================================================
        # CONTACT
        # ====================================================

        if is_phone_question(question):

            column = (
                question_columns[0]
            )

            metadata.append(
                {
                    "question": question,
                    "type": "Contact",
                    "options": [],
                    "source_column": column,
                    "source_columns":
                        question_columns,
                    "internal_columns": []
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

                option = (
                    clean_surveymonkey_header(
                        column[1]
                    )
                )

                if not option:
                    continue

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

                analysis_df[
                    internal_name
                ] = (
                    raw_df[column]
                    .apply(
                        lambda value:
                            1
                            if (
                                pd.notna(value)
                                and clean_text(value)
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
                    "question": question,
                    "type": "MA",
                    "options": options,
                    "source_column": None,
                    "source_columns":
                        question_columns,
                    "internal_columns":
                        internal_columns
                }
            )

            continue

        # ====================================================
        # SINGLE COLUMN
        # ====================================================

        column = (
            question_columns[0]
        )

        second_header = (
            clean_surveymonkey_header(
                column[1]
            )
        )

        question_type = (
            detect_surveymonkey_single_type(
                question=question,
                second_header=second_header,
                series=raw_df[column]
            )
        )

        # ====================================================
        # SA OPTIONS
        # ====================================================

        if question_type == "SA":

            values = (
                raw_df[column]
                .dropna()
                .astype(str)
                .str.strip()
            )

            options = sorted(
                [
                    value
                    for value
                    in values.unique()
                    if value != ""
                ]
            )

        else:

            options = []

        metadata.append(
            {
                "question": question,
                "type": question_type,
                "options": options,
                "source_column": column,
                "source_columns": [column],
                "internal_columns": []
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
    """
    Main function untuk membaca dataset berdasarkan platform.
    """

    if platform == "Google Forms":

        return load_google_forms(
            uploaded_file
        )

    if platform == "SurveyMonkey":

        return load_surveymonkey(
            uploaded_file
        )

    raise ValueError(
        "Unsupported survey platform."
    )
