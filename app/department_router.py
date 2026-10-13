import pandas as pd
import os
import re


# ============================================================
# LOAD DEPARTMENT DATA
# ============================================================

DEPARTMENT_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "departments.csv"
)

departments = pd.read_csv(
    DEPARTMENT_FILE
)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if text is None:
        return ""

    text = str(text).lower().strip()

    text = re.sub(
        r"[^a-z0-9\s\-&]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# FIND DEPARTMENT ROW
# ============================================================

def get_department_by_name(department_name):

    target = normalize_text(
        department_name
    )

    for _, row in departments.iterrows():

        current = normalize_text(
            row["department"]
        )

        if current == target:
            return row

    return None


# ============================================================
# SPECIFIC ISSUE ROUTING
# ============================================================

SPECIFIC_ISSUE_ROUTES = {

    # Water
    "no water supply":
        "Water Supply",

    "water leakage":
        "Water Supply",

    # Drainage
    "drain blockage":
        "Drainage & Sewerage",

    "sewage overflow":
        "Drainage & Sewerage",

    # Waste
    "garbage accumulation":
        "Solid Waste Management & Sanitation",

    "garbage collection failure":
        "Solid Waste Management & Sanitation",

    # Street lighting
    "street light failure":
        "Street Lighting",

    # Electricity
    "power outage":
        "Electricity Distribution",

    # Transport
    "bus service issue":
        "Public Transport",

    # Flooding
    "waterlogging":
        "Flooding & Stormwater",

    "flooding":
        "Flooding & Stormwater",

    # Public health
    "public health issue":
        "Public Health",

    # Toilets
    "public toilet issue":
        "Public Toilets & Sanitation",

    # Encroachment
    "encroachment":
        "Encroachment & Obstructions",

    # Construction
    "illegal construction":
        "Building & Local Construction",

    # Traffic
    "traffic congestion":
        "Traffic & Road Safety",

    # Animal
    "animal control":
        "Animal Control",

    # Roads
    "potholes":
        "Roads & Infrastructure",

    "damaged road":
        "Roads & Infrastructure",
}


# ============================================================
# KEYWORD MATCH
# ============================================================

def keyword_matches(
    keyword,
    search_text
):

    keyword = normalize_text(
        keyword
    )

    if not keyword:
        return False

    pattern = (
        r"\b"
        + re.escape(keyword)
        + r"\b"
    )

    return bool(
        re.search(
            pattern,
            search_text
        )
    )


# ============================================================
# FIND DEPARTMENT
# ============================================================

def find_department(
    category,
    issue="",
    location="",
    issue_type=""
):

    category = normalize_text(
        category
    )

    issue = normalize_text(
        issue
    )

    location = normalize_text(
        location
    )

    issue_type = normalize_text(
        issue_type
    )

    search_text = " ".join(
        part
        for part in [
            category,
            issue,
            issue_type,
            location
        ]
        if part
    )

    # ========================================================
    # STEP 1 — SPECIFIC ISSUE ROUTING
    # ========================================================

    specific_department = (
        SPECIFIC_ISSUE_ROUTES.get(
            issue_type
        )
    )

    if specific_department:

        row = get_department_by_name(
            specific_department
        )

        if row is not None:

            return {

                "status":
                    "Matched",

                "id":
                    row["id"],

                "authority":
                    row["authority"],

                "department":
                    row["department"],

                "extra_info":
                    row["extra_info"],

                "score":
                    100,

                "routing_method":
                    "Specific issue rule"
            }

    # ========================================================
    # STEP 2 — KEYWORD MATCHING
    # ========================================================

    best_match = None
    best_score = 0

    for _, row in departments.iterrows():

        keywords = str(
            row["keywords"]
        ).split(",")

        score = 0

        for keyword in keywords:

            keyword = normalize_text(
                keyword
            )

            if not keyword:
                continue

            if keyword_matches(
                keyword,
                search_text
            ):

                word_count = len(
                    keyword.split()
                )

                # More specific phrases get more weight
                if word_count >= 3:

                    score += 6

                elif word_count == 2:

                    score += 4

                else:

                    score += 2

        # ====================================================
        # CATEGORY BONUS
        # ====================================================

        category_department_map = {

            "water supply":
                "Water Supply",

            "drainage & sewerage":
                "Drainage & Sewerage",

            "waste & sanitation":
                "Solid Waste Management & Sanitation",

            "street lighting":
                "Street Lighting",

            "roads & infrastructure":
                "Roads & Infrastructure",

            "public health & sanitation":
                "Public Health",

            "electricity":
                "Electricity Distribution",

            "public transport":
                "Public Transport",
        }

        expected_department = (
            category_department_map.get(
                category
            )
        )

        current_department = normalize_text(
            row["department"]
        )

        if (
            expected_department
            and
            current_department
            ==
            normalize_text(
                expected_department
            )
        ):

            score += 10

        # ====================================================
        # PRIORITY AS TIE BREAKER
        # ====================================================

        priority = int(
            row.get(
                "priority",
                0
            )
        )

        if score > best_score:

            best_score = score
            best_match = row

        elif score == best_score:

            if best_match is not None:

                old_priority = int(
                    best_match.get(
                        "priority",
                        0
                    )
                )

                if priority > old_priority:

                    best_match = row

    # ========================================================
    # NO MATCH
    # ========================================================

    if (
        best_match is None
        or
        best_score == 0
    ):

        return {

            "status":
                "No matching department",

            "id":
                None,

            "authority":
                None,

            "department":
                None,

            "extra_info":
                None,

            "score":
                0,

            "routing_method":
                "No match"
        }

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        "status":
            "Matched",

        "id":
            best_match["id"],

        "authority":
            best_match["authority"],

        "department":
            best_match["department"],

        "extra_info":
            best_match["extra_info"],

        "score":
            best_score,

        "routing_method":
            "Keyword + category matching"
    }