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
st.write("Automatically extract and classify quotation line items.")


# =========================================================
# KEYWORDS
# =========================================================

equipment_keywords = [
    "equipment",
    "instrument",
    "machine",
    "system",
    "setup",
    "apparatus",

     "nxds",
    "nxds6ic",
    "vacuum pump",
    "vacuum",

    "3d printer",
    "printer",
    "generator",
    "hydrogen generator",

    "microscope",
    "centrifuge",
    "spectrometer",
    "spectrophotometer",
    "raman",
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

    "reactor",
    "parallel reactor",

    "chiller",
    "chiler",
    "mini chiller",
    "mini chiler",
    "water chiller",
    "recirculating chiller",
    "cooling system",
    "cooling unit",

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

    "pump",
    "vacuum pump",

    "laser",
    "probe station",

    "environmental chamber",

    "radiation monitor",
    "radiation detector",
    "contamination monitor",

    "assembly line",
    "fabrication system"
]


accessory_keywords = [
    "cable",
    "power cable",
    "pwr cable",
    "silencer",
    "adapter",
    "adaptor",
    "connector",
    "hose",
    "bracket",
    "mounting kit",
    "stand",
    "holder",
    "accessory",
    "spare part",
    "replacement part"
]


consumable_keywords = [
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
    "tube",
    "tubes",
    "bottle",
    "gloves",
    "filter",
    "membrane"
]


service_keywords = [
    "service",
    "installation service",
    "maintenance service",
    "training",
    "repair",
    "calibration service"
]


stop_keywords = [
    "remarks:",
    "remarks",
    "incoterm:",
    "incoterms:",
    "payment term:",
    "payment terms:",
    "bank info:",
    "bank information:",
    "bank charge",
    "terms & conditions",
    "terms and conditions",
    "terms & condition",
    "terms and condition",
    "delivery time:",
    "warranty:",
    "validity:",
    "force majeure:",
    "cancellation:",
    "customs duty:",
    "value added tax:",
    "vat:",
    "please raise the order",
    "best regards",
    "kind regards"
]


# =========================================================
# PDF READING
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
# STOP CHECK
# =========================================================

def is_stop_line(line):

    text = line.lower().strip()

    for keyword in stop_keywords:

        if text.startswith(keyword):
            return True

    return False


# =========================================================
# HEADER CHECK
# =========================================================

def is_header(line):

    text = line.lower().strip()

    headers = [
        "description",
        "qty",
        "quantity",
        "unit",
        "unit price",
        "price",
        "total",
        "total price",
        "total amount",
        "unit price (usd)",
        "total price (usd)",
        "unit price sar",
        "total amount sar",
        "pn",
        "part no.",
        "part number",
        "sr. no.",
        "sr no."
    ]

    return text in headers


# =========================================================
# PART NUMBER CHECK
# =========================================================

def looks_like_part_number(line):

    text = line.strip()

    patterns = [

        r"^[A-Z]\d{6,}$",

        r"^[A-Z]{2,}\d{3,}$",

        r"^[A-Z0-9]+-[A-Z0-9-]+$",

        r"^[A-Z0-9]{5,}$"
    ]

    return any(
        re.match(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


# =========================================================
# ITEM NUMBER CHECK
# =========================================================

def looks_like_item_number(line):

    return bool(
        re.match(
            r"^\d{1,3}$",
            line.strip()
        )
    )


# =========================================================
# PRICE CHECK
# =========================================================

def looks_like_price(line):

    text = line.strip()

    return bool(
        re.match(
            r"^[\d,]+(?:\.\d{1,2})?$",
            text
        )
    )


# =========================================================
# EXTRACT ITEMS
# =========================================================

def extract_items(pages):

    items = []

    for page in pages:

        lines = [
            line.strip()
            for line in page["text"].splitlines()
            if line.strip()
        ]

        current_item = None
        current_description = []

        inside_quotation = False

        for line in lines:

            lower = line.lower().strip()


            # ---------------------------------------------
            # Detect quotation table
            # ---------------------------------------------

            if (
                lower == "description"
                or lower == "pn"
                or "unit price" in lower
                or "total price" in lower
            ):

                inside_quotation = True

                continue


            # ---------------------------------------------
            # Stop after quotation table
            # ---------------------------------------------

            if inside_quotation and is_stop_line(line):

                if current_item is not None:

                    description = " ".join(
                        current_description
                    ).strip()

                    if description:

                        items.append({
                            "Item": current_item,
                            "Description": description,
                            "Page": page["page"]
                        })

                current_item = None
                current_description = []

                inside_quotation = False

                continue


            if not inside_quotation:
                continue


            # ---------------------------------------------
            # Skip headers
            # ---------------------------------------------

            if is_header(line):
                continue


            # ---------------------------------------------
            # New Part Number
            # ---------------------------------------------

            if looks_like_part_number(line):

                if current_item is not None:

                    description = " ".join(
                        current_description
                    ).strip()

                    if description:

                        items.append({
                            "Item": current_item,
                            "Description": description,
                            "Page": page["page"]
                        })

                current_item = line
                current_description = []

                continue


            # ---------------------------------------------
            # Numeric item number
            # ---------------------------------------------

            if looks_like_item_number(line):

                # If we already have an item, a number
                # is probably Qty, not a new item.
                if current_item is not None:

                    continue

                current_item = line
                current_description = []

                continue


            # ---------------------------------------------
            # Ignore prices
            # ---------------------------------------------

            if looks_like_price(line):

                continue


            # ---------------------------------------------
            # Ignore obvious table totals
            # ---------------------------------------------

            if lower.startswith("fca "):
                continue

            if lower.startswith("total"):
                continue


            # ---------------------------------------------
            # Add to description
            # ---------------------------------------------

            if current_item is not None:

                current_description.append(line)


        # ---------------------------------------------
        # Save final item
        # ---------------------------------------------

        if current_item is not None:

            description = " ".join(
                current_description
            ).strip()

            if description:

                items.append({
                    "Item": current_item,
                    "Description": description,
                    "Page": page["page"]
                })


    return items


# =========================================================
# CLEAN DESCRIPTION
# =========================================================

def clean_description(description):

    description = re.sub(
        r"\s+",
        " ",
        description
    )

    return description.strip()


# =========================================================
# CLASSIFICATION
# =========================================================

def classify_item(description):

    text = description.lower()


    # Service
    service_matches = [
        x for x in service_keywords
        if x in text
    ]

    if service_matches:

        return (
            "Service",
            98,
            "Service indicator: "
            + ", ".join(service_matches)
        )


    # Accessory
    accessory_matches = [
        x for x in accessory_keywords
        if x in text
    ]

    if accessory_matches:

        return (
            "Accessory",
            98,
            "Accessory indicator: "
            + ", ".join(accessory_matches)
        )


    # Consumable
    consumable_matches = [
        x for x in consumable_keywords
        if x in text
    ]

    if consumable_matches:

        return (
            "Consumable",
            97,
            "Consumable indicator: "
            + ", ".join(consumable_matches)
        )


    # Equipment
    equipment_matches = [
        x for x in equipment_keywords
        if x in text
    ]

    if equipment_matches:

        confidence = min(
            90 + len(equipment_matches) * 3,
            99
        )

        return (
            "Equipment",
            confidence,
            "Equipment indicator: "
            + ", ".join(equipment_matches)
        )


    # Unknown
    return (
        "Review",
        50,
        "No clear classification keyword found."
    )


# =========================================================
# MAIN APP
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
    # Preview extracted text
    # =====================================================

    with st.expander(
        "📄 View extracted quotation text"
    ):

        for page in pages:

            st.write(
                f"--- Page {page['page']} ---"
            )

            st.text(
                page["text"][:10000]
            )


    # =====================================================
    # CHECK
    # =====================================================

    if st.button(
        "🔍 Check Quotation",
        type="primary"
    ):

        items = extract_items(
            pages
        )


        if not items:

            st.error(
                "No quotation items could be identified."
            )

            st.info(
                "Please open 'View extracted quotation text' "
                "and check the quotation table structure."
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
            # RESULTS
            # =================================================

            st.subheader(
                "📋 All Quotation Items"
            )

            st.dataframe(
                result_df,
                use_container_width=True,
                hide_index=True
            )


            # =================================================
            # SUMMARY
            # =================================================

            total_items = len(
                result_df
            )

            equipment_count = len(
                result_df[
                    result_df["Category"]
                    == "Equipment"
                ]
            )

            accessory_count = len(
                result_df[
                    result_df["Category"]
                    == "Accessory"
                ]
            )

            consumable_count = len(
                result_df[
                    result_df["Category"]
                    == "Consumable"
                ]
            )

            service_count = len(
                result_df[
                    result_df["Category"]
                    == "Service"
                ]
            )

            review_count = len(
                result_df[
                    result_df["Category"]
                    == "Review"
                ]
            )


            st.subheader(
                "📊 Summary"
            )


            col1, col2, col3, col4, col5, col6 = st.columns(6)


            with col1:
                st.metric(
                    "Total",
                    total_items
                )


            with col2:
                st.metric(
                    "Equipment",
                    equipment_count
                )


            with col3:
                st.metric(
                    "Accessory",
                    accessory_count
                )


            with col4:
                st.metric(
                    "Consumable",
                    consumable_count
                )


            with col5:
                st.metric(
                    "Service",
                    service_count
                )


            with col6:
                st.metric(
                    "Review",
                    review_count
                )


            # =================================================
            # EXCEL
            # =================================================

            output = io.BytesIO()


            with pd.ExcelWriter(
                output,
                engine="openpyxl"
            ) as writer:

                result_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Quotation Check"
                )


            st.download_button(

                label="📥 Download Excel Result",

                data=output.getvalue(),

                file_name=
                    "quotation_equipment_check.xlsx",

                mime=
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
