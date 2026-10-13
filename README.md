# CivicBridge — Bilingual Civic Complaint Classification and Routing System

CivicBridge is a civic technology project designed to streamline the handling of public complaints by classifying reported issues, extracting relevant location information, and routing complaints to the appropriate departments.

The system focuses on supporting multilingual complaint descriptions, including English, Marathi, and Marathi-English code-mixed text, to make civic issue reporting more accessible.

## Problem Statement

Civic complaints concerning sanitation, water supply, public infrastructure, and other essential services can be difficult to categorize and direct to the appropriate authority. Language variations and incomplete location information can further complicate the process.

CivicBridge explores the use of machine learning, text processing, and geocoding to support structured complaint classification and department routing.

## Objectives

- Classify civic complaints into relevant categories using machine learning.
- Support English, Marathi, and Marathi-English complaint descriptions.
- Extract useful location information from complaint text.
- Convert extracted locations into geographic coordinates where possible.
- Route complaints to relevant departments using department information and keywords.
- Provide complaint acknowledgement numbers and status tracking.
- Support administrative review and complaint management.

## Key Features

### 1. Citizen Portal
- Citizen registration and login.
- Complaint submission with descriptive text.
- Evidence uploads where supported.
- Complaint acknowledgement and tracking.

### 2. Multilingual Complaint Classification
- Processes supported complaint text in English and Marathi, including code-mixed input.
- Uses a trained machine learning pipeline for complaint categorization.
- Applies text processing and multilingual text representations.

### 3. Location Extraction and Geocoding
- Extracts location-related information from complaint descriptions.
- Uses geocoding to associate recognized locations with geographic coordinates where possible.
- Supports map-based location visualization where implemented.

### 4. Department Routing
- Uses complaint categories and department-related keywords to identify an appropriate department.
- Supports structured department configuration and routing workflows.

### 5. Complaint Tracking
- Generates acknowledgement identifiers.
- Maintains complaint records and status history where implemented.
- Supports status updates and administrative processing.

### 6. Administrative Workflow
- Provides an administrative interface for reviewing complaints.
- Supports complaint management and department-level workflow where implemented.

## Machine Learning Methodology

The project uses a machine learning pipeline built around multilingual text processing and supervised classification.

The implementation includes:

1. **Text preprocessing:** Normalization and preparation of complaint descriptions.
2. **Text representation:** Multilingual sentence embeddings using `paraphrase-multilingual-MiniLM-L12-v2`.
3. **Classification:** A trained Logistic Regression classifier for predicting complaint categories.
4. **Location processing:** Extraction of location information and geocoding.
5. **Department routing:** Matching classified complaints with department configuration and relevant keywords.

Model performance depends on the training data and evaluation methodology. Reported accuracy should be interpreted in the context of the dataset used.

## Technology Stack

- Python
- Scikit-learn
- Sentence Transformers
- Pandas
- Flask or Streamlit, depending on the implemented interface
- MySQL
- OpenStreetMap Nominatim for geocoding
- HTML, CSS, and JavaScript where used

## Dataset

The project uses complaint data and department configuration for model development and complaint routing.

Synthetic complaint records may be used for development and evaluation. Dataset composition and performance depend on the data available to the implementation.

Do not publish personal information, private complaint records, or confidential evidence.

## Societal Impact

CivicBridge aims to improve the organization of civic complaints by supporting multilingual reporting, structured classification, location identification, and department routing.

The project explores how machine learning and geospatial tools can assist civic administration while retaining the need for appropriate human review and operational oversight.

## Limitations

- Classification quality depends on the representativeness and quality of training data.
- Location extraction and geocoding may fail when descriptions are ambiguous or incomplete.
- Department routing depends on the available department configuration and keyword coverage.
- Real-world deployment requires security testing, privacy safeguards, and validation with appropriate authorities.

## Future Scope

- Expand and validate multilingual complaint datasets.
- Improve location extraction for regional and code-mixed language descriptions.
- Evaluate model performance on independently collected, representative data.
- Improve accessibility and usability for citizens.
- Strengthen security, scalability, and integration with authorized civic systems.

## Author

**Gargi Ashish Surve**
