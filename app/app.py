import os
import sys
import base64
from pathlib import Path

import requests
import folium
import streamlit as st
import joblib

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from streamlit_folium import st_folium


# ============================================================
# PATH SETUP
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# ============================================================
# LOCAL MODULES
# ============================================================

from database import (
    create_complaint,
    get_user_complaints,
    get_complaint,
    get_complaint_status_history,
    get_complaint_evidence
)

from auth import (
    register_user,
    authenticate_user
)

from extractor import (
    extract_with_local_rules
)

from department_router import (
    find_department
)

from evidence import (
    evidence_upload,
    save_evidence_files
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CivicBridge",
    page_icon="🏛️",
    layout="wide"
)


# ============================================================
# CUSTOM UI STYLING
# ============================================================

# ============================================================
# LOAD STYLES
# ============================================================

def load_stylesheet():
    style_path = BASE_DIR / "style.css"

    if not style_path.exists():
        st.error(
            "style.css was not found. "
            "Please keep style.css in the CivicBridge root folder."
        )
        return

    css = style_path.read_text(
        encoding="utf-8"
    )

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True
    )


load_stylesheet()



# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(
    BASE_DIR / ".env",
    override=True
)


# ============================================================
# LOAD ML MODEL
# ============================================================

@st.cache_resource
def load_models():

    model_path = (
        BASE_DIR
        / "models"
        / "civicbridge_transformer_lr.pkl"
    )

    classifier = joblib.load(
        model_path
    )

    transformer = SentenceTransformer(
        "paraphrase-multilingual-MiniLM-L12-v2"
    )

    return classifier, transformer


classifier, transformer = load_models()


# ============================================================
# ML CATEGORY PREDICTION
# ============================================================

def predict_category(complaint):

    embedding = transformer.encode(
        [complaint]
    )

    category = classifier.predict(
        embedding
    )[0]

    return str(category)


# ============================================================
# LOCATION GEOCODING
# ============================================================

@st.cache_data(show_spinner=False)
def geocode_location(location):

    if not location:
        return None

    url = (
        "https://nominatim.openstreetmap.org/search"
    )

    params = {
        "q": f"{location}, Maharashtra, India",
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 1
    }

    headers = {
        "User-Agent": "CivicBridge-FYP/1.0"
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        results = response.json()

        if not results:
            return None

        result = results[0]

        return {
            "latitude": float(
                result["lat"]
            ),
            "longitude": float(
                result["lon"]
            ),
            "display_name": result.get(
                "display_name",
                location
            ),
            "address": result.get(
                "address",
                {}
            )
        }

    except Exception:

        return None


# ============================================================
# LOCAL INFORMATION EXTRACTION
# ============================================================

def extract_complaint(complaint):

    extracted = extract_with_local_rules(
        complaint
    )

    return extracted


# ============================================================
# MAIN ANALYSIS PIPELINE
# ============================================================

def analyze_complaint(complaint):

    # --------------------------------------------------------
    # 1. EXTRACT COMPLAINT INFORMATION FIRST
    # --------------------------------------------------------

    extracted = extract_complaint(
        complaint
    )

    # --------------------------------------------------------
    # 2. ML CATEGORY PREDICTION
    # --------------------------------------------------------

    predicted_category = predict_category(
        complaint
    )

    # --------------------------------------------------------
    # 3. CATEGORY VALIDATION / CORRECTION
    # --------------------------------------------------------
    #
    # The ML model gives the initial category.
    # The extracted issue is then used to make sure
    # the final category does not contradict the
    # specific civic issue.
    #
    # This is especially important for Marathi and
    # Marathi-English complaints.
    # --------------------------------------------------------

    issue_type = str(
        extracted.get(
            "issue_type",
            ""
        )
    ).lower().strip()

    issue_category_map = {

        # Water
        "no water supply":
            "Water Supply",

        "water leakage":
            "Water Supply",

        "low water pressure":
            "Water Supply",

        "dirty or contaminated water":
            "Water Supply",

        # Drainage
        "drain blockage":
            "Drainage & Sewerage",

        "sewage overflow":
            "Drainage & Sewerage",

        "open or damaged manhole":
            "Drainage & Sewerage",

        # Waste
        "garbage collection failure":
            "Waste & Sanitation",

        "illegal waste dumping":
            "Waste & Sanitation",

        # Lighting
        "street light failure":
            "Street Lighting",

        # Roads
        "potholes":
            "Roads & Infrastructure",

        "damaged road":
            "Roads & Infrastructure",

        "footpath damage":
            "Roads & Infrastructure",

        # Flooding
        "waterlogging":
            "Roads & Infrastructure",

        # Electricity
        "power outage":
            "Electricity",

        "low voltage":
            "Electricity",

        "exposed electrical wire":
            "Electricity",

        # Health
        "mosquito breeding":
            "Public Health & Sanitation",

        "unhygienic conditions":
            "Public Health & Sanitation",

        # Toilets
        "public toilet issue":
            "Public Health & Sanitation",

        # Transport
        "bus service issue":
            "Public Transport",

        "damaged bus stop":
            "Public Transport",

        # Encroachment
        "encroachment":
            "Roads & Infrastructure",

        # Construction
        "illegal construction":
            "Building & Local Construction",

        # Traffic
        "traffic congestion":
            "Roads & Infrastructure",

        # Animals
        "stray animal issue":
            "Public Health & Sanitation",

        # Parks
        "public park issue":
            "Public Parks & Open Spaces"
    }

    # --------------------------------------------------------
    # USE ISSUE-SPECIFIC CATEGORY WHEN AVAILABLE
    # --------------------------------------------------------

    if issue_type in issue_category_map:

        category = issue_category_map[
            issue_type
        ]

    else:

        # Fall back to ML prediction
        category = predicted_category


    # --------------------------------------------------------
    # 4. DEPARTMENT ROUTING
    # --------------------------------------------------------

    routing = find_department(

        category=category,

        issue=extracted.get(
            "issue",
            ""
        ),

        location=extracted.get(
            "location",
            ""
        ),

        issue_type=extracted.get(
            "issue_type",
            ""
        )
    )


    # --------------------------------------------------------
    # 5. GEOCODING
    # --------------------------------------------------------

    location_data = None

    location = extracted.get(
        "location"
    )

    if location:

        location_data = geocode_location(
            location
        )


    # --------------------------------------------------------
    # 6. FINAL RESULT
    # --------------------------------------------------------

    return {

        # Original
        "original_complaint":
            complaint,

        # Category
        "category":
            category,

        "predicted_category":
            predicted_category,

        # Extraction
        "language":
            extracted.get(
                "language"
            ),

        "issue":
            extracted.get(
                "issue"
            ),

        "issue_type":
            extracted.get(
                "issue_type"
            ),

        "location":
            extracted.get(
                "location"
            ),

        "area":
            extracted.get(
                "area"
            ),

        "landmark":
            extracted.get(
                "landmark"
            ),

        "duration":
            extracted.get(
                "duration"
            ),

        "frequency":
            extracted.get(
                "frequency"
            ),

        "time_of_occurrence":
            extracted.get(
                "time_of_occurrence"
            ),

        "people_affected":
            extracted.get(
                "people_affected"
            ),

        "cause":
            extracted.get(
                "cause"
            ),

        "requested_action":
            extracted.get(
                "requested_action"
            ),

        "ongoing":
            extracted.get(
                "ongoing"
            ),

        "safety_risk":
            extracted.get(
                "safety_risk"
            ),

        "evidence_mentioned":
            extracted.get(
                "evidence_mentioned"
            ),

        "additional_details":
            extracted.get(
                "additional_details"
            ),

        # Routing
        "authority":
            routing.get(
                "authority"
            ),

        "department":
            routing.get(
                "department"
            ),

        "department_id":
            routing.get(
                "id"
            ),

        "routing_status":
            routing.get(
                "status"
            ),

        "routing_score":
            routing.get(
                "score"
            ),

        "routing_method":
            routing.get(
                "routing_method"
            ),

        "routing_extra_info":
            routing.get(
                "extra_info"
            ),

        # Map
        "location_data":
            location_data
    }

# ============================================================
# DISPLAY HELPER
# ============================================================

def display_value(value):

    if value is None:
        return "Not provided"

    if isinstance(value, bool):

        return (
            "Yes"
            if value
            else "No"
        )

    if str(value).strip() == "":
        return "Not provided"

    return value




def render_file_complaint():
    """
    Main citizen grievance submission workflow.
    Existing working ML, extraction, routing, map, evidence and
    MySQL logic is kept inside this page.
    """

    # ============================================================
    # HEADER
    # ============================================================

    st.markdown(
        '<div class="section-header">File a Grievance</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Describe your civic problem naturally in English, "
        "Marathi, or Marathi-English."
    )


    # ============================================================
    # SIGNED-IN CITIZEN
    # ============================================================

    current_user = st.session_state.get(
        "user"
    )

    if not current_user:
        st.warning(
            "Please sign in before filing a grievance."
        )
        return

    st.markdown(
        f"""
        <div class="cb-topbar">
            <div class="cb-user">
                Filing grievance as
                <strong>{current_user["name"]}</strong>
                &nbsp;•&nbsp;
                {current_user["email"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ============================================================
    # COMPLAINT INPUT
    # ============================================================

    st.markdown(
        '<div class="section-header">Describe Your Civic Problem</div>',
        unsafe_allow_html=True
    )

    complaint = st.text_area(

        "Complaint",

        placeholder=(
            "Example: There has been no water supply "
            "in New Panvel Sector-5 for three days. "
            "Many residents are affected."
        ),

        height=180,

        label_visibility="collapsed"
    )


    # ============================================================
    # ANALYSE BUTTON
    # ============================================================

    if st.button(
        "🔎 Analyse Complaint",
        use_container_width=True
    ):

        if not complaint.strip():

            st.warning(
                "Please enter a complaint."
            )

        else:

            with st.spinner(
                "Understanding and routing your complaint..."
            ):

                try:

                    result = analyze_complaint(
                        complaint.strip()
                    )

                    st.session_state[
                        "result"
                    ] = result

                    st.session_state[
                        "saved_complaint_id"
                    ] = None

                    st.session_state[
                        "saved_evidence"
                    ] = []

                    st.success(
                        "Complaint analysed successfully!"
                    )

                except Exception as e:

                    st.error(
                        "Something went wrong while "
                        "analysing the complaint."
                    )

                    st.exception(e)


    # ============================================================
    # DISPLAY RESULTS
    # ============================================================

    if "result" in st.session_state:

        result = st.session_state[
            "result"
        ]

        # ========================================================
        # ANALYSIS HEADER
        # ========================================================

        st.markdown(
            '<div class="section-header">Complaint Analysis</div>',
            unsafe_allow_html=True
        )


        # ========================================================
        # CATEGORY
        # ========================================================

        st.markdown(
            '<div class="sub-header">Complaint Category</div>',
            unsafe_allow_html=True
        )

        st.info(
            display_value(
                result.get(
                    "category"
                )
            )
        )


        # ========================================================
        # COMPLAINT DETAILS
        # ========================================================

        st.markdown(
            '<div class="section-header">Complaint Details</div>',
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.markdown(
                '<div class="field-label">Issue</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "issue"
                    )
                )
            )

        with col2:

            st.markdown(
                '<div class="field-label">Issue Type</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "issue_type"
                    )
                )
            )

        with col3:

            st.markdown(
                '<div class="field-label">Language</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "language"
                    )
                )
            )


        col4, col5, col6 = st.columns(3)

        with col4:

            st.markdown(
                '<div class="field-label">Duration</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "duration"
                    )
                )
            )

        with col5:

            st.markdown(
                '<div class="field-label">Frequency</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "frequency"
                    )
                )
            )

        with col6:

            st.markdown(
                '<div class="field-label">Time of Occurrence</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "time_of_occurrence"
                    )
                )
            )




        # ========================================================
        # LOCATION INTELLIGENCE
        # ========================================================

        st.markdown(
            '<div class="section-header">📍 Location Intelligence</div>',
            unsafe_allow_html=True
        )

        location_col1, location_col2 = st.columns(2)

        with location_col1:

            st.markdown(
                '<div class="field-label">Location</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "location"
                    )
                )
            )

            st.markdown(
                '<div class="field-label">Area</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "area"
                    )
                )
            )

        with location_col2:

            st.markdown(
                '<div class="field-label">Landmark</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "landmark"
                    )
                )
            )

            location_data = result.get(
                "location_data"
            )

            if location_data:

                st.markdown(
                    '<div class="field-label">Coordinates</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    f"{location_data['latitude']:.7f}, "
                    f"{location_data['longitude']:.7f}"
                )


        # ========================================================
        # MAP
        # ========================================================

        location_data = result.get(
            "location_data"
        )

        if location_data:

            latitude = location_data[
                "latitude"
            ]

            longitude = location_data[
                "longitude"
            ]

            map_object = folium.Map(

                location=[
                    latitude,
                    longitude
                ],

                zoom_start=15,

                control_scale=True
            )


            # ----------------------------------------------------
            # LARGE HIGHLIGHT CIRCLE
            # ----------------------------------------------------

            folium.Circle(

                location=[
                    latitude,
                    longitude
                ],

                radius=250,

                popup=folium.Popup(

                    f"""
                    <div style="
                        font-family: Arial;
                        font-size: 14px;
                    ">
                        <b>CivicBridge Complaint</b><br><br>

                        <b>Location:</b>
                        {result.get("location", "Unknown")}<br><br>

                        <b>Coordinates:</b><br>
                        {latitude:.6f},
                        {longitude:.6f}
                    </div>
                    """,

                    max_width=320
                ),

                tooltip="Complaint Location",

                fill=True,

                fill_opacity=0.20,

                weight=3

            ).add_to(
                map_object
            )


            # ----------------------------------------------------
            # EXACT LOCATION MARKER
            # ----------------------------------------------------

            folium.CircleMarker(

                location=[
                    latitude,
                    longitude
                ],

                radius=11,

                popup=folium.Popup(

                    f"""
                    <div style="
                        font-family: Arial;
                        font-size: 14px;
                    ">
                        <b>CivicBridge Complaint</b><br>
                        {result.get(
                            "location",
                            "Unknown location"
                        )}
                    </div>
                    """,

                    max_width=300
                ),

                tooltip="Complaint Location",

                fill=True,

                fill_opacity=1,

                weight=4

            ).add_to(
                map_object
            )


            # ----------------------------------------------------
            # MAP
            # ----------------------------------------------------

            st_folium(

                map_object,

                width=None,

                height=430,

                returned_objects=[]
            )


        elif result.get(
            "location"
        ):

            st.info(
                "Location identified, but it could not "
                "be geocoded on the map."
            )

        else:

            st.info(
                "No location was identified in the complaint."
            )


        # ========================================================
        # ADDITIONAL INFORMATION
        # ========================================================

        st.markdown(
            '<div class="section-header">Additional Information</div>',
            unsafe_allow_html=True
        )

        detail_col1, detail_col2 = st.columns(2)

        with detail_col1:

            st.markdown(
                '<div class="field-label">Possible Cause</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "cause"
                    )
                )
            )

            st.markdown(
                '<div class="field-label">Requested Action</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "requested_action"
                    )
                )
            )

        with detail_col2:

            st.markdown(
                '<div class="field-label">Ongoing Issue</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "ongoing"
                    )
                )
            )

            st.markdown(
                '<div class="field-label">Evidence Mentioned</div>',
                unsafe_allow_html=True
            )

            st.write(
                display_value(
                    result.get(
                        "evidence_mentioned"
                    )
                )
            )


        # ========================================================
        # ORIGINAL COMPLAINT
        # ========================================================

        with st.expander(
            "View Original Complaint"
        ):

            st.write(
                result.get(
                    "original_complaint",
                    ""
                )
            )


        # ========================================================
        # RESPONSIBLE DEPARTMENT
        # ========================================================

        st.markdown(
            '<div class="section-header">🏢 Responsible Department</div>',
            unsafe_allow_html=True
        )

        routing_status = result.get(
            "routing_status"
        )

        if routing_status == "Matched":

            route_col1, route_col2 = st.columns(2)

            with route_col1:

                st.markdown(
                    '<div class="field-label">Authority</div>',
                    unsafe_allow_html=True
                )

                st.success(
                    display_value(
                        result.get(
                            "authority"
                        )
                    )
                )

            with route_col2:

                st.markdown(
                    '<div class="field-label">Department</div>',
                    unsafe_allow_html=True
                )

                st.success(
                    display_value(
                        result.get(
                            "department"
                        )
                    )
                )


            st.markdown(
                '<div class="sub-header">Routing Information</div>',
                unsafe_allow_html=True
            )

            routing_col1, routing_col2 = st.columns(2)

            with routing_col1:

                st.markdown(
                    '<div class="field-label">Routing Method</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    display_value(
                        result.get(
                            "routing_method"
                        )
                    )
                )

            with routing_col2:

                st.markdown(
                    '<div class="field-label">Routing Score</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    display_value(
                        result.get(
                            "routing_score"
                        )
                    )
                )


            if result.get(
                "routing_extra_info"
            ):

                st.info(
                    result[
                        "routing_extra_info"
                    ]
                )

        else:

            st.warning(
                "No matching department was found "
                "for this complaint."
            )


        # ========================================================
        # SUPPORTING EVIDENCE
        # ========================================================

        uploaded_evidence = evidence_upload()


        # ========================================================
        # SAVE COMPLAINT
        # ========================================================

        st.markdown(
            '<div class="section-header">Submit Grievance</div>',
            unsafe_allow_html=True
        )

        st.write(
            "Review the information above and submit the grievance "
            "to CivicBridge."
        )

        save_col1, save_col2 = st.columns(
            [2, 1]
        )

        with save_col1:

            st.caption(
                "Your complaint, routing information, location "
                "and supporting evidence will be stored."
            )

        with save_col2:

            save_button = st.button(
                "Submit Grievance",
                use_container_width=True,
                key="submit_grievance_button"
            )

        if save_button:

            if st.session_state.get(
                "saved_complaint_id"
            ):

                st.info(
                    "This grievance has already been submitted."
                )

            else:

                try:

                    current_user = st.session_state[
                        "user"
                    ]

                    location_data = result.get(
                        "location_data"
                    )

                    latitude = None
                    longitude = None

                    if location_data:

                        latitude = location_data.get(
                            "latitude"
                        )

                        longitude = location_data.get(
                            "longitude"
                        )

                    complaint_id = create_complaint(

                        user_id=current_user[
                            "user_id"
                        ],

                        original_complaint=
                            result[
                                "original_complaint"
                            ],

                        language=
                            result.get(
                                "language"
                            )
                            or "Unknown",

                        category=
                            result.get(
                                "category"
                            )
                            or "Unknown",

                        issue=
                            result.get(
                                "issue"
                            ),

                        location=
                            result.get(
                                "location"
                            ),

                        duration=
                            result.get(
                                "duration"
                            ),

                        latitude=latitude,

                        longitude=longitude,

                        authority=
                            result.get(
                                "authority"
                            ),

                        department=
                            result.get(
                                "department"
                            )
                    )

                    saved_evidence = save_evidence_files(
                        complaint_id=complaint_id,
                        uploaded_files=uploaded_evidence,
                        base_dir=BASE_DIR
                    )

                    st.session_state[
                        "saved_complaint_id"
                    ] = complaint_id

                    st.session_state[
                        "saved_evidence"
                    ] = saved_evidence

                    st.success(
                        "Your grievance has been submitted successfully."
                    )

                    st.markdown(
                        f"### Acknowledgement No.: "
                        f"`CB-{int(complaint_id):05d}`"
                    )

                    st.info(
                        "Please keep your acknowledgement number "
                        "for future status tracking."
                    )

                except Exception as e:

                    st.error(
                        "The grievance could not be submitted."
                    )

                    st.exception(e)

        # ========================================================
        # SUBMISSION ACKNOWLEDGEMENT
        # ========================================================

        saved_id = st.session_state.get(
            "saved_complaint_id"
        )

        if saved_id:

            st.markdown(
                "---"
            )

            st.markdown(
                '<div class="section-header">Submission Acknowledgement</div>',
                unsafe_allow_html=True
            )

            st.success(
                "Your grievance has been submitted successfully."
            )

            ack_col1, ack_col2, ack_col3 = st.columns(3)

            with ack_col1:

                st.markdown(
                    '<div class="field-label">Acknowledgement No.</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    f"CB-{int(saved_id):05d}"
                )

            with ack_col2:

                st.markdown(
                    '<div class="field-label">Department</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    display_value(
                        result.get("department")
                    )
                )

            with ack_col3:

                st.markdown(
                    '<div class="field-label">Status</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    "Submitted"
                )

            saved_evidence = st.session_state.get(
                "saved_evidence",
                []
            )

            if saved_evidence:

                st.caption(
                    f"{len(saved_evidence)} supporting evidence "
                    f"file(s) attached to this grievance."
                )

            st.info(
                "Please keep your acknowledgement number "
                "for future status tracking."
            )




def render_track_complaint():
    st.markdown(
        '<div class="section-header">Track Complaint</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Enter your acknowledgement number and registered email "
        "to view the current status of your grievance."
    )

    tracking_id = st.text_input(
        "Acknowledgement Number",
        placeholder="Example: CB-00005",
        key="track_complaint_id"
    )

    track_button = st.button(
        "Track Complaint",
        use_container_width=True,
        key="track_button"
    )

    if track_button:

        if not tracking_id.strip():
            st.warning("Please enter your acknowledgement number.")
            return

        current_user = st.session_state.get("user")

        if not current_user:
            st.warning("Please sign in before tracking a grievance.")
            return

        clean_id = tracking_id.strip().upper()

        if clean_id.startswith("CB-"):
            clean_id = clean_id[3:]

        try:
            complaint_id = int(clean_id)
        except ValueError:
            st.error("Please enter a valid acknowledgement number, such as CB-00005.")
            return

        try:
            user = current_user

            complaint = get_complaint(
                complaint_id
            )

            if not complaint:
                st.warning(
                    "No complaint was found for this acknowledgement number."
                )
                return

            if int(complaint["user_id"]) != int(user["user_id"]):
                st.error(
                    "The acknowledgement number does not match the registered email."
                )
                return

            history = get_complaint_status_history(
                complaint_id
            )

            st.markdown(
                '<div class="sub-header">Complaint Details</div>',
                unsafe_allow_html=True
            )

            detail_col1, detail_col2, detail_col3 = st.columns(3)

            with detail_col1:
                st.markdown(
                    '<div class="field-label">Acknowledgement No.</div>',
                    unsafe_allow_html=True
                )
                st.write(
                    f"CB-{complaint_id:05d}"
                )

            with detail_col2:
                st.markdown(
                    '<div class="field-label">Category</div>',
                    unsafe_allow_html=True
                )
                st.write(
                    display_value(
                        complaint.get("category")
                    )
                )

            with detail_col3:
                st.markdown(
                    '<div class="field-label">Department</div>',
                    unsafe_allow_html=True
                )
                st.write(
                    display_value(
                        complaint.get("department")
                    )
                )

            st.markdown(
                '<div class="sub-header">Current Status</div>',
                unsafe_allow_html=True
            )

            current_status = complaint.get(
                "status",
                "Submitted"
            )

            st.success(
                str(current_status)
            )

            st.markdown(
                '<div class="sub-header">Status History</div>',
                unsafe_allow_html=True
            )

            if history:

                status_order = [
                    "Submitted",
                    "Routed",
                    "In Progress",
                    "Resolved",
                    "Closed"
                ]

                reached = {
                    str(row.get("status"))
                    for row in history
                }

                status_cols = st.columns(
                    len(status_order)
                )

                for index, status in enumerate(status_order):

                    with status_cols[index]:

                        if status in reached:
                            st.success(
                                f"✓ {status}"
                            )
                        elif (
                            status == current_status
                        ):
                            st.info(
                                status
                            )
                        else:
                            st.caption(
                                f"○ {status}"
                            )

                st.markdown(
                    ""
                )

                for row in history:
                    history_status = row.get(
                        "status"
                    )
                    remarks = row.get(
                        "remarks"
                    )
                    updated_at = row.get(
                        "updated_at"
                    )

                    line = (
                        f"**{history_status}**"
                    )

                    if updated_at:
                        line += (
                            f" — {updated_at}"
                        )

                    st.write(line)

                    if remarks:
                        st.caption(
                            remarks
                        )

            else:
                st.info(
                    "No status updates are available yet."
                )

        except Exception as e:

            st.error(
                "Unable to retrieve the complaint status."
            )
            st.exception(e)


def render_evidence_page():
    st.markdown(
        '<div class="section-header">Evidence</div>',
        unsafe_allow_html=True
    )

    st.write(
        "View supporting photographs and videos attached to a submitted grievance."
    )

    evidence_id_input = st.text_input(
        "Acknowledgement Number",
        placeholder="Example: CB-00005",
        key="evidence_complaint_id"
    )

    evidence_button = st.button(
        "View Evidence",
        use_container_width=True,
        key="view_evidence_button"
    )

    if evidence_button:

        if not evidence_id_input.strip():
            st.warning("Please enter your acknowledgement number.")
            return

        current_user = st.session_state.get("user")

        if not current_user:
            st.warning("Please sign in before viewing evidence.")
            return

        clean_id = evidence_id_input.strip().upper()

        if clean_id.startswith("CB-"):
            clean_id = clean_id[3:]

        try:
            complaint_id = int(clean_id)
        except ValueError:
            st.error("Please enter a valid acknowledgement number, such as CB-00005.")
            return

        try:
            user = current_user

            complaint = get_complaint(
                complaint_id
            )

            if not complaint:
                st.warning(
                    "No complaint was found for this acknowledgement number."
                )
                return

            if int(complaint["user_id"]) != int(user["user_id"]):
                st.error(
                    "The acknowledgement number does not match the registered email."
                )
                return

            evidence_records = get_complaint_evidence(
                complaint_id
            )

            st.markdown(
                '<div class="sub-header">Supporting Evidence</div>',
                unsafe_allow_html=True
            )

            if not evidence_records:
                st.info(
                    "No supporting evidence is attached to this complaint."
                )
                return

            st.success(
                f"{len(evidence_records)} evidence file(s) attached."
            )

            for record in evidence_records:

                file_name = record.get(
                    "file_name",
                    "Evidence"
                )

                file_type = str(
                    record.get(
                        "file_type",
                        ""
                    )
                ).lower()

                file_path = record.get(
                    "file_path"
                )

                st.markdown(
                    f"**{file_name}**"
                )

                if file_path:

                    full_path = (
                        BASE_DIR
                        / file_path
                    )

                    if full_path.exists():

                        if (
                            file_type.startswith("image/")
                            or full_path.suffix.lower()
                            in [".jpg", ".jpeg", ".png"]
                        ):
                            st.image(
                                str(full_path),
                                use_container_width=True
                            )

                        elif (
                            file_type.startswith("video/")
                            or full_path.suffix.lower()
                            in [".mp4", ".mov"]
                        ):
                            st.video(
                                str(full_path)
                            )

                        else:
                            st.caption(
                                f"Stored file: {file_path}"
                            )

                    else:
                        st.warning(
                            "The evidence record exists, but the stored file "
                            "could not be found on the server."
                        )

                st.divider()

        except Exception as e:

            st.error(
                "Unable to retrieve the supporting evidence."
            )
            st.exception(e)



def render_authentication():

    # ========================================================
    # FULL-PAGE BACKGROUND IMAGE
    # ========================================================

    background_path = (
        BASE_DIR
        / "images"
        / "CB Citizen.png"
    )

    if background_path.exists():

        image_bytes = base64.b64encode(
            background_path.read_bytes()
        ).decode("utf-8")

        background_css = f"""
        <style>
        .stApp {{
            background-image:
                linear-gradient(
                    rgba(244, 248, 253, 0.32),
                    rgba(244, 248, 253, 0.32)
                ),
                url("data:image/png;base64,{image_bytes}");

            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        [data-testid="stHeader"] {{
            background: transparent !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: transparent !important;
        }}

        [data-testid="stMain"] {{
            background: transparent !important;
        }}

        .block-container {{
            max-width: 1500px !important;
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }}
        </style>
        """

        st.markdown(
            background_css,
            unsafe_allow_html=True
        )

    else:
        st.error(
            "Background image not found. Please check "
            "CivicBridge/images/CB Citizen.png"
        )

    # ========================================================
    # LAYOUT: BACKGROUND VISIBLE ON LEFT, FORM ON RIGHT
    # ========================================================

    left, right = st.columns(
        [1.08, 0.92],
        gap="large"
    )

    # Leave the left side open so the illustration remains visible.
    with left:
        st.markdown(
            '<div class="cb-auth-spacer"></div>',
            unsafe_allow_html=True
        )

    # ========================================================
    # CITIZEN LOGIN PANEL
    # ========================================================

    with right:

        with st.container(border=True):

            st.markdown(
                """
                <div class="cb-login-brand">
                    <div class="cb-login-brand-name">
                        Civic<span>Bridge</span>
                    </div>
                    <div class="cb-login-tagline">
                        REPORT TODAY. CLEANER CITIES TOMORROW.
                    </div>
                    <div class="cb-login-accent"></div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                '<div class="cb-auth-card-title">'
                'Citizen Access</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                '<div class="cb-auth-card-subtitle">'
                'Sign in to file and track your grievances.'
                '</div>',
                unsafe_allow_html=True
            )

            login_tab, signup_tab = st.tabs(
                ["Sign In", "Create Account"]
            )

            # =================================================
            # SIGN IN
            # =================================================

            with login_tab:

                login_email = st.text_input(
                    "Email",
                    placeholder="Enter your email",
                    key="login_email"
                )

                login_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    key="login_password"
                )

                if st.button(
                    "Sign In",
                    use_container_width=True,
                    key="login_button"
                ):

                    if not login_email.strip():
                        st.warning("Please enter your email.")

                    elif not login_password:
                        st.warning("Please enter your password.")

                    else:
                        success, result = authenticate_user(
                            login_email,
                            login_password
                        )

                        if success:

                            st.session_state["user"] = result
                            st.session_state["authenticated"] = True
                            st.session_state[
                                "civicbridge_navigation"
                            ] = "Home"

                            st.rerun()

                        else:
                            st.error(result)

            # =================================================
            # CREATE ACCOUNT
            # =================================================

            with signup_tab:

                signup_name = st.text_input(
                    "Full Name",
                    placeholder="Enter your full name",
                    key="signup_name"
                )

                signup_email = st.text_input(
                    "Email",
                    placeholder="Enter your email address",
                    key="signup_email"
                )

                signup_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Minimum 8 characters",
                    key="signup_password"
                )

                signup_confirm = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Re-enter your password",
                    key="signup_confirm"
                )

                if st.button(
                    "Create Account",
                    use_container_width=True,
                    key="signup_button"
                ):

                    if signup_password != signup_confirm:
                        st.error("Passwords do not match.")

                    else:
                        success, result = register_user(
                            signup_name,
                            signup_email,
                            signup_password
                        )

                        if success:

                            st.session_state["user"] = result
                            st.session_state["authenticated"] = True
                            st.session_state[
                                "civicbridge_navigation"
                            ] = "Home"

                            st.rerun()

                        else:
                            st.error(result)

            st.markdown(
                """
                <div class="cb-secure-note">
                    <span class="cb-secure-dot"></span>
                    Secure citizen access
                </div>
                """,
                unsafe_allow_html=True
            )

            st.caption(
                "Your account links your grievances, evidence "
                "and status history to one citizen profile."
            )


def render_my_complaints():

    current_user = st.session_state.get(
        "user"
    )

    st.markdown(
        '<div class="section-header">My Grievances</div>',
        unsafe_allow_html=True
    )

    st.write(
        "View grievances submitted from your CivicBridge account."
    )

    try:

        complaints = get_user_complaints(
            current_user["user_id"]
        )

        if not complaints:

            st.info(
                "You have not submitted any grievances yet."
            )

            return

        st.success(
            f"{len(complaints)} grievance(s) found."
        )

        for complaint in complaints:

            complaint_id = int(
                complaint["complaint_id"]
            )

            with st.expander(
                f"CB-{complaint_id:05d}  •  "
                f"{complaint.get('category', 'Civic Issue')}  •  "
                f"{complaint.get('status', 'Submitted')}"
            ):

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown(
                        '<div class="field-label">Category</div>',
                        unsafe_allow_html=True
                    )
                    st.write(
                        complaint.get(
                            "category",
                            "Not provided"
                        )
                    )

                with col2:
                    st.markdown(
                        '<div class="field-label">Department</div>',
                        unsafe_allow_html=True
                    )
                    st.write(
                        complaint.get(
                            "department",
                            "Not provided"
                        )
                    )

                with col3:
                    st.markdown(
                        '<div class="field-label">Status</div>',
                        unsafe_allow_html=True
                    )
                    st.write(
                        complaint.get(
                            "status",
                            "Submitted"
                        )
                    )

                st.markdown(
                    '<div class="field-label">Complaint</div>',
                    unsafe_allow_html=True
                )

                st.write(
                    complaint.get(
                        "original_complaint",
                        ""
                    )
                )

                st.caption(
                    "Submitted: "
                    + str(
                        complaint.get(
                            "created_at",
                            ""
                        )
                    )
                )

    except Exception as e:

        st.error(
            "Unable to load your grievances."
        )

        st.exception(e)


def render_home():

    st.markdown(
        '<div class="section-header">Citizen Services</div>',
        unsafe_allow_html=True
    )

    st.write(
        "CivicBridge helps citizens prepare, submit and track "
        "civic grievances through one simple portal."
    )

    col1, col2, col3 = st.columns(3)

    cards = [
        (
            "File a Grievance",
            "Describe the issue naturally. CivicBridge structures "
            "the complaint and identifies the relevant department."
        ),
        (
            "Track a Grievance",
            "Use your acknowledgement number to view the latest "
            "status and status history."
        ),
        (
            "Supporting Evidence",
            "Keep photographs and short videos linked to the "
            "corresponding grievance."
        )
    ]

    for column, (title, text) in zip(
        [col1, col2, col3],
        cards
    ):

        with column:

            st.markdown(
                f"""
                <div class="cb-card">
                    <div class="cb-card-title">{title}</div>
                    <div class="cb-card-text">{text}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown(
        '<div class="sub-header">How it works</div>',
        unsafe_allow_html=True
    )

    workflow_cols = st.columns(5)

    workflow = [
        ("01", "Describe", "Enter the civic issue."),
        ("02", "Understand", "AI structures the complaint."),
        ("03", "Locate", "Identify the reported location."),
        ("04", "Route", "Identify the responsible department."),
        ("05", "Track", "Follow the grievance status.")
    ]

    for column, (number, title, description) in zip(
        workflow_cols,
        workflow
    ):

        with column:

            st.markdown(
                f"**{number}  {title}**"
            )

            st.caption(
                description
            )

    st.markdown(
        '<div class="sub-header">Account</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Signed in as "
        + st.session_state["user"]["name"]
        + " • "
        + st.session_state["user"]["email"]
    )



# ============================================================
# CIVICBRIDGE APPLICATION SHELL
# ============================================================

if not st.session_state.get(
    "authenticated"
):

    render_authentication()

else:

    current_user = st.session_state.get(
        "user"
    )

    nav_col1, nav_col2 = st.columns(
        [4, 1]
    )

    with nav_col1:

        st.markdown(
            '<div class="cb-brand">CivicBridge</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="cb-tagline">'
            'Citizen Grievance &amp; Routing Portal'
            '</div>',
            unsafe_allow_html=True
        )

    with nav_col2:

        st.caption(
            f"Signed in as {current_user['name']}"
        )

        if st.button(
            "Sign Out",
            use_container_width=True,
            key="logout_button"
        ):

            for key in [
                "user",
                "authenticated",
                "result",
                "saved_complaint_id",
                "saved_evidence"
            ]:

                st.session_state.pop(
                    key,
                    None
                )

            st.rerun()

    nav_options = [
        "Home",
        "File Complaint",
        "My Grievances",
        "Track Complaint",
        "Evidence"
    ]

    active_page = st.radio(
        "Navigation",
        nav_options,
        horizontal=True,
        label_visibility="collapsed",
        key="civicbridge_navigation"
    )

    if active_page == "Home":
        render_home()

    elif active_page == "File Complaint":
        render_file_complaint()

    elif active_page == "My Grievances":
        render_my_complaints()

    elif active_page == "Track Complaint":
        render_track_complaint()

    elif active_page == "Evidence":
        render_evidence_page()

    st.markdown(
        """
        <div class="cb-footer">
            CivicBridge • Citizen Grievance &amp; Routing Portal
            <br>
            AI-assisted grievance structuring, routing and tracking.
        </div>
        """,
        unsafe_allow_html=True
    )

