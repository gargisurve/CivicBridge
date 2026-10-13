from pathlib import Path
import re
import uuid

import streamlit as st

from database import add_evidence


ALLOWED_TYPES = ["jpg", "jpeg", "png", "mp4", "mov"]
MAX_FILES = 5
MAX_FILE_SIZE_MB = 10


def _safe_filename(filename):
    name = Path(filename).name
    stem = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        Path(name).stem
    ).strip("._")

    stem = stem or "evidence"
    suffix = Path(name).suffix.lower()

    return f"{stem}{suffix}"


def evidence_upload():
    """
    Compact supporting-evidence section.
    The uploader is kept collapsed by default so the
    complaint form remains short and government-portal-like.
    """

    with st.expander(
        "Supporting Evidence (Optional)",
        expanded=False
    ):

        st.caption(
            "Attach photographs or short videos that support "
            "your complaint. Evidence will be linked to "
            "the complaint after submission."
        )

        uploaded_files = st.file_uploader(
            "Upload supporting evidence",
            type=ALLOWED_TYPES,
            accept_multiple_files=True,
            key="civicbridge_evidence"
        )

        if not uploaded_files:
            return []

        if len(uploaded_files) > MAX_FILES:
            st.warning(
                f"Please upload a maximum of {MAX_FILES} files."
            )
            return []

        valid_files = []

        for file in uploaded_files:

            size_mb = file.size / (1024 * 1024)

            if size_mb > MAX_FILE_SIZE_MB:
                st.warning(
                    f"{file.name} exceeds the "
                    f"{MAX_FILE_SIZE_MB} MB limit and "
                    "will not be uploaded."
                )
                continue

            valid_files.append(file)

        if valid_files:
            st.caption(
                f"{len(valid_files)} supporting file(s) selected."
            )

        return valid_files


def save_evidence_files(
    complaint_id,
    uploaded_files,
    base_dir
):
    """
    Saves evidence files to disk and registers them in MySQL.
    """

    if not complaint_id or not uploaded_files:
        return []

    evidence_dir = (
        Path(base_dir)
        / "uploads"
        / "evidence"
    )

    evidence_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    saved_records = []

    for uploaded_file in uploaded_files:

        original_name = Path(
            uploaded_file.name
        ).name

        safe_name = _safe_filename(
            original_name
        )

        unique_name = (
            f"{uuid.uuid4().hex[:12]}_"
            f"{safe_name}"
        )

        destination = (
            evidence_dir
            / unique_name
        )

        uploaded_file.seek(0)

        with open(
            destination,
            "wb"
        ) as output_file:

            output_file.write(
                uploaded_file.getbuffer()
            )

        file_type = (
            uploaded_file.type
            or destination.suffix.lower().lstrip(".")
        )

        relative_path = str(
            destination.relative_to(
                base_dir
            )
        ).replace("\\", "/")

        evidence_id = add_evidence(
            complaint_id=complaint_id,
            file_name=original_name,
            file_type=file_type,
            file_path=relative_path
        )

        saved_records.append(
            {
                "evidence_id": evidence_id,
                "file_name": original_name,
                "file_type": file_type,
                "file_path": relative_path
            }
        )

    return saved_records
