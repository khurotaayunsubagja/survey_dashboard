import pandas as pd
import re


# ============================================================
# HELPER
# ============================================================

def clean_text(value):

    if pd.isna(value):
        return ""

    value = str(value).strip()

    return value


def clean_column_name(value):

    value = clean_text(value)

    value = re.sub(r"\s+", " ", value)

    return value


# ============================================================
# SURVEYMONKEY LOADER
# ============================================================

def load_surveymonkey(uploaded_file):

    # --------------------------------------------------------
    # RAW DATA
    # --------------------------------------------------------

    raw_df = pd.read_excel(
        uploaded_file,
        header=[0, 1]
    )

    # Jangan ubah raw_df
    # Karena raw_df digunakan untuk Data Overview
    # dan sheet Raw Data.


    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    metadata = []

    # Ambil logical question
    # berdasarkan header level pertama

    top_headers = raw_df.columns.get_level_values(0)

    unique_questions = []

    for q in top_headers:

        q = clean_column_name(q)

        if q and q not in unique_questions:
            unique_questions.append(q)


    # --------------------------------------------------------
    # CONTOH DETEKSI QUESTION
    # --------------------------------------------------------

    for question in unique_questions:

        columns = []

        for col in raw_df.columns:

            q = clean_column_name(col[0])
            option = clean_column_name(col[1])

            if q == question:

                columns.append({
                    "raw_column": col,
                    "option": option
                })


        # ----------------------------------------------------
        # SEMENTARA:
        # > 1 kolom = MA
        # 1 kolom = SA / Open
        # ----------------------------------------------------

        if len(columns) > 1:

            q_type = "MA"

            options = [
                x["option"]
                for x in columns
            ]

        else:

            q_type = "SA"

            options = [
                x["option"]
                for x in columns
            ]


        metadata.append({

            "question": question,

            "type": q_type,

            "options": options,

            "raw_columns": [
                x["raw_column"]
                for x in columns
            ]

        })


    # --------------------------------------------------------
    # ANALYSIS DATA
    # --------------------------------------------------------

    analysis_df = pd.DataFrame()

    respondent_df = raw_df.copy()

    # Buang 2 baris header
    # karena header SurveyMonkey sudah menjadi column header

    # Contoh transformasi MA
    for item in metadata:

        question = item["question"]

        if item["type"] == "MA":

            for col_info in item["raw_columns"]:

                option = clean_column_name(
                    col_info[1]
                )

                new_col = (
                    f"{question}__{option}"
                )

                analysis_df[new_col] = (
                    respondent_df[col_info]
                    .notna()
                    .astype(int)
                )

        else:

            col = item["raw_columns"][0]

            analysis_df[question] = (
                respondent_df[col]
            )


    return raw_df, analysis_df, metadata


# ============================================================
# GOOGLE FORMS LOADER
# ============================================================

def load_google_forms(uploaded_file):

    raw_df = pd.read_excel(
        uploaded_file
    )

    metadata = []

    analysis_df = raw_df.copy()


    # --------------------------------------------------------
    # DETEKSI QUESTION
    # --------------------------------------------------------

    for col in raw_df.columns:

        question = clean_column_name(col)

        if question.lower() in [
            "timestamp",
            "time stamp"
        ]:

            continue


        series = raw_df[col].fillna("").astype(str)


        # ----------------------------------------------------
        # CONTOH DETEKSI MA
        # ----------------------------------------------------

        comma_count = (
            series.str.count(",")
        )

        avg_comma = comma_count.mean()


        if avg_comma > 0.2:

            q_type = "MA"

            # Ambil semua opsi
            options = set()

            for value in series:

                if value.strip():

                    parts = value.split(",")

                    for part in parts:

                        options.add(
                            part.strip()
                        )

            options = sorted(options)


            # Buat binary column
            for option in options:

                clean_option = re.sub(
                    r"[^A-Za-z0-9]+",
                    "_",
                    option
                ).strip("_")


                new_col = (
                    f"{question}__{clean_option}"
                )


                analysis_df[new_col] = (
                    series
                    .str.split(",")
                    .apply(
                        lambda x:
                        int(
                            option in
                            [
                                i.strip()
                                for i in x
                            ]
                        )
                    )
                )

        else:

            q_type = "SA"

            options = (
                series[
                    series != ""
                ]
                .unique()
                .tolist()
            )


        metadata.append({

            "question": question,

            "type": q_type,

            "options": options,

            "raw_columns": [
                col
            ]

        })


    return raw_df, analysis_df, metadata


# ============================================================
# MAIN LOADER
# ============================================================

def load_survey_data(
    uploaded_file,
    platform
):

    if platform == "SurveyMonkey":

        return load_surveymonkey(
            uploaded_file
        )

    elif platform == "Google Forms":

        return load_google_forms(
            uploaded_file
        )

    else:

        raise ValueError(
            "Platform tidak dikenali."
        )