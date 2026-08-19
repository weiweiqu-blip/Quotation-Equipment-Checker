import streamlit as st
import pandas as pd
import fitz
import io
import re

st.set_page_config(
    page_title="Quotation Equipment Checker",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Quotation Equipment Checker")
st.write("Upload a quotation PDF and identify whether the quoted item is equipment.")


# =========================================================
# Keywords
# =========================================================

equipment_keywords = [
    "equipment",
    "instrument",
    "machine",
    "system",
    "analyzer",
    "monitor",
    "microscope",
    "centrifuge",
    "spectrometer",
    "spectrophotometer",
    "chromatograph",
    "hplc",
    "gc-ms",
    "mass spectrometer",
    "pcr machine",
    "thermal cycler",
    "oven",
    "vacuum oven",
    "incubator",
    "freezer",
    "refrigerator",
    "shaker",
    "autoclave",
    "pump",
    "vacuum pump",
    "water bath",
    "dry bath",
    "fume hood",
    "biosafety cabinet",
    "balance",
    "analytical balance",
    "laser",
    "detector",
    "radiation monitor",
    "contamination monitor",
    "radiation detector",
    "printer",
    "scanner"
]

non_equipment_keywords = [
    "chemical",
    "reagent",
    "solvent",
    "acid",
    "buffer",
    "powder",
    "solution",
    "consumable",
    "pipette tip",
    "pipette tips",
    "tips",
    "tube",
    "tubes",
    "bottle",
    "gloves",
    "filter",
    "membrane",
    "service",
    "installation service",
    "maintenance service",
    "training",
    "repair"
]


# =========================================================
# Extract PDF text
# =========================================================

def read_pdf(uploaded_file):

    pdf_bytes = uploaded_file.read()

    pdf = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pages = []

    for page_number, page in enumerate(pdf, start=1):

        page_text = page.get_text()

        pages.append({
            "page": page_number,
            "text": page_text
        })

    return pages


# =========================================================
# Remove quotation terms
# =========================================================

def is_terms_section(text):

    terms_keywords = [
        "terms & condition",
        "terms and condition",
        "terms & conditions",
        "terms and conditions",
        "delivery time",
        "incoterms",
        "payment terms",
        "validity",
        "customs duty",
        "value added tax",
        "vat",
        "force majeure",
        "cancellation"
    ]

    lower_text = text.lower()

    matches = 0

    for keyword in terms_keywords:

        if keyword in lower_text:
            matches += 1

    return matches >= 2


# =========================================================
# Find item descriptions
# =========================================================

def extract_items(pages):

    items = []

    for page in pages:

        text = page["text"]

        if is_terms_section(text):
            continue

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        current_item = None
        current_description = []

        for line in lines:

            # Detect item number
            item_match = re.match(
                r"^(\d+)\s*$",
                line
            )

            if item_match:

                # Save previous item
                if current_item is not None:

                    description = " ".join(
                        current_description
                    )

                    if description:

                        items.append({
                            "Item": current_item,
                            "Description": description,
                            "Page": page["page"]
                        })

                current_item = item_match.group(1)
                current_description = []

                continue

            # Skip obvious headers
            if line.lower() in [
                "pricing",
                "sr. no.",
                "description",
                "qty",
                "unit",
                "price",
                "total amount",
                "sar"
            ]:
                continue

            # Skip total
            if line.lower().startswith("total amt"):
                continue

            # Skip notes
            if line.lower().startswith("note:"):
                continue

            # Add useful description text
            if current_item is not None:

                current_description.append(line)

        # Save final item
        if current_item is not None:

            description = " ".join(
                current_description
            )

            if description:

                items.append({
                    "Item": current_item,
                    "Description": description,
                    "Page": page["page"]
                })

    return items


# =========================================================
# Clean description
# =========================================================

def clean_description(description):

    # Remove repeated spaces
    description = re.sub(
        r"\s+",
        " ",
        description
    )

    # Remove pricing information
    description = re.sub(
        r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b",
        "",
        description
    )

    return description.strip()


# =========================================================
# Classification
# =========================================================

def classify_item(description):

    text = description.lower()

    equipment_matches = []
    non_equipment_matches = []

    for keyword in equipment_keywords:

        if keyword in text:

            equipment_matches.append(
                keyword
            )

    for keyword in non_equipment_keywords:

        if keyword in text:

            non_equipment_matches.append(
                keyword
            )

    # Strong equipment evidence
    if equipment_matches and not non_equipment_matches:

        confidence = min(
            95 + len(equipment_matches) * 2,
            99
        )

        reason = (
            "The description contains equipment-related terms: "
            + ", ".join(equipment_matches)
        )

        return (
            "Equipment",
            confidence,
            reason
        )

    # Strong non-equipment evidence
    if non_equipment_matches and not equipment_matches:

        confidence = min(
            95 + len(non_equipment_matches) * 2,
            99
        )

        reason = (
            "The description contains non-equipment terms: "
            + ", ".join(non_equipment_matches)
        )

        return (
            "Not Equipment",
            confidence,
            reason
        )

    # Both types detected
    if equipment_matches and non_equipment_matches:

        return (
            "Review",
            60,
            "Both equipment and non-equipment terms were detected."
        )

    # Nothing detected
    return (
        "Review",
        50,
        "The description does not contain enough information for automatic classification."
    )


# =========================================================
# Upload
# =========================================================

uploaded_file = st.file_uploader(
    "Upload quotation PDF",
    type=["pdf"]
)


if uploaded_file:

    st.success(
        f"Uploaded: {uploaded_file.name}"
    )

    # Read PDF
    pages = read_pdf(
        uploaded_file
    )

    # Preview extracted text
    with st.expander(
        "📄 View extracted quotation text"
    ):

        for page in pages:

            st.write(
                f"--- Page {page['page']} ---"
            )

            st.text(
                page["text"][:5000]
            )


    if st.button(
        "🔍 Check Quotation",
        type="primary"
    ):

        items = extract_items(
            pages
        )

        if not items:

            st.warning(
                "No quotation items could be identified."
            )

        else:

            results = []

            for item in items:

                description = clean_description(
                    item["Description"]
                )

                category, confidence, reason = classify_item(
                    description
                )

                results.append({

                    "Item":
                        item["Item"],

                    "Description":
                        description,

                    "Category":
                        category,

                    "Confidence":
                        f"{confidence}%",

                    "Reason":
                        reason,

                    "Page":
                        item["Page"]
                })


            result_df = pd.DataFrame(
                results
            )


            # =================================================
            # Results
            # =================================================

            st.subheader(
                "Checking Result"
            )

            st.dataframe(
                result_df,
                use_container_width=True,
                hide_index=True
            )


            # =================================================
            # Summary
            # =================================================

            equipment_count = len(
                result_df[
                    result_df["Category"]
                    == "Equipment"
                ]
            )

            not_equipment_count = len(
                result_df[
                    result_df["Category"]
                    == "Not Equipment"
                ]
            )

            review_count = len(
                result_df[
                    result_df["Category"]
                    == "Review"
                ]
            )


            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Equipment",
                    equipment_count
                )

            with col2:

                st.metric(
                    "Not Equipment",
                    not_equipment_count
                )

            with col3:

                st.metric(
                    "Review",
                    review_count
                )


            # =================================================
            # Download Excel
            # =================================================

            output = io.BytesIO()

            with pd.ExcelWriter(
                output,
                engine="openpyxl"
            ) as writer:

                result_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Equipment Check"
                )


            st.download_button(

                label="📥 Download Excel Result",

                data=output.getvalue(),

                file_name=
                    "quotation_equipment_check.xlsx",

                mime=
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )