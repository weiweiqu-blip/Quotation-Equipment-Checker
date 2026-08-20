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
st.write(
    "Upload a quotation and automatically identify equipment items."
)


# =========================================================
# Equipment keywords
# =========================================================

equipment_keywords = [
    # General equipment
    "equipment",
    "instrument",
    "machine",
    "system",
    "setup",
    "apparatus",
    "unit",

    # Laboratory instruments
    "microscope",
    "centrifuge",
    "spectrometer",
    "spectrophotometer",
    "raman",
    "raman spectro",
    "potentiostat",
    "electrolyser",
    "electrolyzer",
    "chromatograph",
    "microgc",
    "hplc",
    "gc-ms",
    "mass spectrometer",
    "analyzer",
    "analyser",
    "detector",
    "monitor",

    # Printing / manufacturing
    "3d printer",
    "printer",
    "assembly line",
    "fabrication system",

    # Reactors / process equipment
    "reactor",
    "parallel reactor",
    "electrolyser",
    "electrolyzer",
    "dehydration setup",
    "process system",
    "processing unit",

    # Cooling / heating
    "chiller",
    "mini chiller",
    "mini chiler",
    "water chiller",
    "recirculating chiller",
    "cooling system",
    "cooling unit",
    "heater",
    "heating system",
    "heating circulator",
    "water bath",
    "dry bath",

    # Common laboratory equipment
    "oven",
    "vacuum oven",
    "incubator",
    "freezer",
    "refrigerator",
    "shaker",
    "autoclave",
    "fume hood",
    "biosafety cabinet",
    "balance",
    "analytical balance",
    "vacuum pump",
    "pump",
    "laser",
    "probe station",
    "environmental chamber",
    "glove box",
    "glovebox",

    # Radiation equipment
    "radiation monitor",
    "radiation detector",
    "contamination monitor",
    "radiation contamination monitor",

    # Other
    "scanner",
    "printer",
    "fabrication",
    "production system"
]


# =========================================================
# Non-equipment keywords
# =========================================================

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
    "repair",
    "replacement part",
    "spare part"
]


# =========================================================
# Strong equipment phrases
# =========================================================

strong_equipment_phrases = [
    "3d printer",
    "portable potentiostat",
    "radiation contamination monitor",
    "radiation monitor",
    "contamination monitor",
    "benchtop-plant",
    "assembly line",
    "parallel reactor",
    "formic acid dehydration setup",
    "mini chiller",
    "mini chiler",
    "raman spectro",
    "microgc",
    "electrolyser",
    "electrolyzer"
]


# =========================================================
# Extract PDF
# =========================================================

def read_pdf(uploaded_file):

    pdf_bytes = uploaded_file.read()

    pdf = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pages = []

    for page_number, page in enumerate(pdf, start=1):

        pages.append({
            "page": page_number,
            "text": page.get_text()
        })

    return pages


# =========================================================
# Detect quotation terms
# =========================================================

def is_terms_section(text):

    text_lower = text.lower()

    terms_keywords = [
        "terms & condition",
        "terms and condition",
        "terms & conditions",
        "terms and conditions",
        "delivery time",
        "incoterms",
        "payment terms",
        "customs duty",
        "force majeure",
        "cancellation"
    ]

    matches = sum(
        keyword in text_lower
        for keyword in terms_keywords
    )

    return matches >= 2


# =========================================================
# Extract quotation items
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

            # Item number
            item_match = re.match(
                r"^(\d+)\s*$",
                line
            )

            if item_match:

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

            # Ignore quotation headers
            if line.lower() in [
                "pricing",
                "sr. no.",
                "description",
                "qty",
                "quantity",
                "unit",
                "price",
                "unit price",
                "total",
                "total amount",
                "sar"
            ]:
                continue

            if line.lower().startswith("total amt"):
                continue

            if line.lower().startswith("note:"):
                continue

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

    description = re.sub(
        r"\s+",
        " ",
        description
    )

    return description.strip()


# =========================================================
# Classify item
# =========================================================

def classify_item(description):

    text = description.lower()

    # ---------------------------------------------
    # Strong equipment phrase
    # ---------------------------------------------

    strong_matches = []

    for phrase in strong_equipment_phrases:

        if phrase in text:
            strong_matches.append(phrase)

    if strong_matches:

        return (
            "Equipment",
            99,
            "Strong equipment match: "
            + ", ".join(strong_matches)
        )


    # ---------------------------------------------
    # Normal equipment keywords
    # ---------------------------------------------

    equipment_matches = []

    for keyword in equipment_keywords:

        if keyword in text:
            equipment_matches.append(keyword)


    # ---------------------------------------------
    # Non-equipment keywords
    # ---------------------------------------------

    non_equipment_matches = []

    for keyword in non_equipment_keywords:

        if keyword in text:
            non_equipment_matches.append(keyword)


    # ---------------------------------------------
    # Equipment
    # ---------------------------------------------

    if equipment_matches and not non_equipment_matches:

        confidence = min(
            90 + len(equipment_matches) * 3,
            98
        )

        return (
            "Equipment",
            confidence,
            "Equipment indicators: "
            + ", ".join(equipment_matches)
        )


    # ---------------------------------------------
    # Non-equipment
    # ---------------------------------------------

    if non_equipment_matches and not equipment_matches:

        confidence = min(
            90 + len(non_equipment_matches) * 3,
            98
        )

        return (
            "Not Equipment",
            confidence,
            "Non-equipment indicators: "
            + ", ".join(non_equipment_matches)
        )


    # ---------------------------------------------
    # Both
    # ---------------------------------------------

    if equipment_matches and non_equipment_matches:

        return (
            "Review",
            65,
            "Both equipment and non-equipment indicators were found."
        )


    # ---------------------------------------------
    # Unknown
    # ---------------------------------------------

    return (
        "Review",
        50,
        "Not enough information for automatic classification."
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

    pages = read_pdf(
        uploaded_file
    )


    # =====================================================
    # Preview PDF text
    # =====================================================

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


    # =====================================================
    # Check
    # =====================================================

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
