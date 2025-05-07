import streamlit as st
import camelot
import pytesseract
from pdf2image import convert_from_bytes
import json
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import pandas as pd
import numpy as np

st.title("📄 PDF Table Extractor to JSON (OCR + Camelot)")

uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
password = st.text_input("Enter PDF password", type="password")



def extract_tables_with_camelot(file_path):
    try:
        tables = camelot.read_pdf(file_path, pages='all', flavor='stream')  # 'stream' for complex tables
        extracted_tables = []
        #for table in tables:
        #    extracted_tables.append(table.df.to_dict(orient="records"))
        extracted_tables.append(tables[0].df.to_dict(orient="records"))
        # st.dataframe(tables[0].df)
        itable = tables[2].df

        # ✅ Now create a new DataFrame from result
        cloned_df = pd.DataFrame(add_group_col(itable))
        #cloned_df = pd.DataFrame(itable)
        #extracted_tables[0]=cloned_df
        st.dataframe(cloned_df)
        #st.dataframe(itable)
        #st.data_editor(itable, num_rows="dynamic")
        return extracted_tables
    except Exception as e:
        st.error(f"Error extracting tables: {e}")
        return []

def add_group_col(table, group_size=3):
    group_col = []
    i = 0
    group_num = 1

    while i < len(table):
        value = table.iloc[i, 2]
        if isinstance(value, str) and value.startswith(("UPI", "MMT","BIL")):
            # Assign group_num to the next group_size rows
            end = min(i + group_size, len(table))
            group_col.extend([group_num] * (end - i))
            i += group_size
        else:
            group_col.append(group_num)
            i += 1
        group_num += 1

    # Fill remaining rows with NaN if shorter than length
    while len(group_col) < len(table):
        group_col.append(np.nan)

    table[6] = group_col
    # Now group by column 6 and merge each column using string join
    merged = table.groupby(6).agg(lambda col: ' '.join(col.astype(str))).reset_index()
    table = merged

    # create transaction table
    

    return table




def sanitize_table(itable):
    # How many rows you want to merge in one group
    group_size = 3
    cloned_df = pd.DataFrame(columns= itable.columns)

    #particular = get_merge_array(itable)
    particular = [''.join("3" if itable[2][i].startswith(("UPI","MMT")) else "1") for i in range(0, len(itable), 1)]
    
    # Split into groups and join text
    result = {}
    for col in itable.columns:
        #merged = []
        #for i in range(0, len(itable), group_size):
            #if(itable[2][i].startswith(("UPI","MMT"))):
                #part = itable[col][i:i+group_size]
                #print(part)
                #joined = ''.join(part)
                #merged.append(joined)
            #else: 
                #merged.append(itable[col][i])

        #merged = [''.join(itable[col][i:i+group_size]) for i in range(0, len(itable), group_size)]
        merged = [''.join(itable[col][i:i+group_size]) for i in range(0, len(itable), group_size)]
        result[col] = merged
    return result




def extract_text_with_ocr(file_bytes):
    images = convert_from_bytes(file_bytes)
    extracted_text = ""
    for img in images:
        text = pytesseract.image_to_string(img)
        extracted_text += text + "\n"
    return extracted_text



def decrypt_pdf(input_pdf_bytes, password):
    try:
        # Load the encrypted PDF
        reader = PdfReader(input_pdf_bytes)
        
        if reader.is_encrypted:
            reader.decrypt(password)
        
        # Create a new PDF without encryption
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        # Save to bytes
        from io import BytesIO
        output_pdf = BytesIO()
        writer.write(output_pdf)
        output_pdf.seek(0)
        return output_pdf
    except Exception as e:
        raise Exception(f"Failed to decrypt PDF: {e}")


if uploaded_file is not None and password is not None:
    try:
        decrypted_pdf = decrypt_pdf(uploaded_file, password)
        st.success("PDF decrypted successfully!")
            
            # Now you can pass `decrypted_pdf` to camelot or OCR functions
            # For example:
            # extract_tables_with_camelot(decrypted_pdf)
    except Exception as e:
        st.error(str(e))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(decrypted_pdf.read())
        tmp_file_path = tmp_file.name

    st.subheader("🔎 Table Extraction using Camelot")
    tables = extract_tables_with_camelot(tmp_file_path)

    if tables:
        st.success(f"Extracted {len(tables)} tables!")
        #for idx, table in enumerate(tables):
            #st.json({f"Table {idx + 1}": table})
    else:
        st.warning("No tables found with Camelot. Trying OCR...")
        extracted_text = extract_text_with_ocr(uploaded_file.getvalue())
        st.subheader("🧠 OCR Extracted Text")
        st.text_area("Extracted Text", extracted_text, height=400)
