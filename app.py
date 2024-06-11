# Developer Note: Hey folks :) Especial thank to stlite, electron, and streamlit team. Thanks to developers and maintainers of following contents (my resources): https://github.com/whitphx/stlite/blob/main/packages/desktop/README.md   and  https://www.youtube.com/watch?v=3wZ7GRbr91g  and  https://www.electron.build/  
import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
import time
import pickle
import base64
import io
import zipfile

#-------- Configurable Paths --------#
script_path = os.path.abspath(sys.argv[0])
script_directory = os.path.dirname(script_path)
log_file_path = os.path.join(script_directory, "streamlit_logs.txt")

#-------- Column Names --------#
mrn_col_index = 0
date_col_index = 1
proc_col_index = 2
path_col_index = 3

#-------- Logging Function --------#
def append_log(log_message):
    current_time = datetime.now().strftime("%m-%d-%y %H:%M:%S")
    log_entry = f"-------\n{current_time} - {log_message}\n"
    try:
        with open(log_file_path, "a") as file:
            file.write(log_entry)
    except Exception as e:
        st.error(f"Failed to append log due to: {e}")

#-------- Data Entry Fields --------#
annotator_names = ['Soroush', 'Reviewer 1', 'Reviewer 2']

prior_history_fields = {
    "Precancerous polyps": ("True", "False", "N/A"),
    "Advanced polyps": ("True", "False", "N/A"),
    "Advanced polyp on 2nd most recent colonoscopy": ("True", "False", "N/A"),
    "Poor bowel preparation": ("True", "False", "N/A"),
    "Complications during colonoscopy": ("True", "False", "N/A"),
}

recent_colonoscopy_fields = {
    "Procedure Indication": (
        "other", "screening for colorectal cancer (baseline risk)", "screening for colorectal cancer (family history)",
        "surveillance of polyps", "positive FIT", "positive Cologuard", "positive FOBT", "positive CT colonography"
    ),
    "Withdrawal Time": "00m:01S",
    "Preparation Quality BPPS": (0, 9),
    "Preparation Quality Subjective": ("Poor", "Inadequate", "Fair", "Adequate", "Good", "Excellent", "N/A"),
    "Cecal Intubation": ("True", "False", "N/A"),
    "Number of Resected Specimens": (0, 20),
    "Other Polyps": (0, 20),
}

specimen_fields = {
    "Polyp Location": ("other", "cecum", "ascending colon", "transverse colon", "descending colon", "sigmoid colon", "rectum", "REMOVE DATA FOR THIS POLYP"),
    "Polyp Location Text": "",
    "Number of Polyps": (0, 20),
    "Size of largest polyp": (0, 200),
    "Polyp resection": ("Complete", "Partial"),
    "Polypectomy method": ("cold forceps", "jumbo forceps", "cold snare", "hot snare", "EMR", "ESD", "other"),
    "Polypectomy method Text": "",
    "Specimen Diagnosis": ("inflammatory", "hyperplastic", "tubular adenoma", "SSL", "tubulovillous adenoma", "villous adenoma", "other"),
    "Specimen Diagnosis Text": "",
}

empty_specimen = {
    key: (0 if isinstance(specimen_fields[key], tuple) and isinstance(specimen_fields[key][0], int) else None)
    for key in specimen_fields.keys()
}

specimen_fields_freetext4other_pair = {
    "Polyp Location Text": "Polyp Location",
    "Polypectomy method Text": "Polyp Location",
    "Specimen Diagnosis Text": "Specimen Diagnosis",
}
for key, item in specimen_fields_freetext4other_pair.items():
    if key not in specimen_fields or item not in specimen_fields:
        st.error(f"The object in specimen_fields_freetext4other_pair '{key}':'{item}' is not in the specimen_fields. Contact admin.")

batch_fields = {
    "Polyp location": ("other", "cecum", "ascending colon", "transverse colon", "descending colon", "sigmoid colon", "rectum"),
    "Polyp location text": "",
    "Number of polyps": (0, 20),
    "Polyp size (mm)": (0, 200),
    "Polyp resected": ("complete", "incomplete", "not attempted"),
    "Reason for not resecting": ("poor prep", "size of polyp", "benign polyp", "invasive disease", "other"),
    "Polyp resection method": ("cold forceps", "jumbo forceps", "cold snare", "hot snare", "EMR", "ESD", "other"),
    "Resection method text": "",
    "Biopsied": ("yes", "no"),
    "Polyp Histology": ("inflammatory", "hyperplastic", "tubular adenoma", "SSL", "tubulovillous adenoma", "villous adenoma", "other"),
    "Polyp Histology text": "",
}

empty_batch = {
    key: (0 if isinstance(batch_fields[key], tuple) and isinstance(batch_fields[key][0], int) else None)
    for key in batch_fields.keys()
}

batch_fields_freetext4other_pair = {
    "Polyp location text": "Polyp location",
    "Resection method text": "Polyp resection method",
    "Polyp Histology text": "Polyp Histology"
}
for key, item in batch_fields_freetext4other_pair.items():
    if key not in batch_fields or item not in batch_fields:
        append_log(f"The object in batch_fields_freetext4other_pair '{key}':'{item}' is not in the batch_fields. Contact admin.")
        st.error(f"The object in batch_fields_freetext4other_pair '{key}':'{item}' is not in the batch_fields. Contact admin.")

recommendation_options = [
    "Select an option", "next available", "3 months", "6 months", "1 year", "3 years", "3-5 years",
    "5 years", "5-10 years", "7-10 years", "10 years", "do not repeat", "other"
]

empty_mrn = {
    "User Notes": "",
    "Prior History": {key: (0 if isinstance(prior_history_fields[key], int) else None) for key in prior_history_fields.keys()},
    "Most recent colonoscopy": {
        **{key: (0 if isinstance(recent_colonoscopy_fields[key][0], int) else None) for key in recent_colonoscopy_fields.keys()},
        "Preparation Quality BPPS": 0,
        "Number of Resected Specimens": 0,
        "Other Polyps": 0
    },
    "Specimen data": {},
    "Batch data": {},
    "new_recommendation": {
        "Repeat Interval": None,
        "Repeat Interval text": None
    },
    "locked": False
}

#------------------------------------------------------------------------------------#
#--------------------------------- Load, Save, and Download Functions --------------#
def load_or_create_json_file():
    annotator_name = st.session_state['annotator']
    pickle_file_path = os.path.join(script_directory, f"{annotator_name}_annotations.pkl")
    
    if not os.path.exists(pickle_file_path):
        with open(pickle_file_path, 'wb') as file:
            pickle.dump({}, file)
        append_log("The empty pickle file was created")
        st.session_state['all_mrns_data'] = {}
    else:
        with open(pickle_file_path, 'rb') as file:
            st.session_state['all_mrns_data'] = pickle.load(file)

    st.session_state['pickle_file_loaded'] = True
    return st.session_state['all_mrns_data']

def load_mrn_data():
    mrn = st.session_state['mrn_4review']
    all_mrns_data = load_or_create_json_file()
    try:
        st.session_state['current_mrn'] = all_mrns_data.get(mrn, empty_mrn.copy())
        
        if mrn not in all_mrns_data:
            append_log(f"Starting new annotation for MRN {mrn}.")
    except Exception as e:
        append_log(f"Error in loading {mrn} annotation data: {e}")
        st.error(f"Error in loading {mrn} annotation data: {e}")
    st.session_state['previous_mrn'] = st.session_state['current_mrn'] 
    
    

def save_mrn_data():
        annotator_name = st.session_state['annotator']
        pickle_file_path = os.path.join(script_directory, f"{annotator_name}_annotations.pkl")
        
        all_mrn_data = st.session_state['all_mrns_data']
        mrn = st.session_state['mrn_4review']
        all_mrn_data[mrn] = st.session_state['current_mrn']
        
        with open(pickle_file_path, 'wb') as file:
            pickle.dump(all_mrn_data, file)
        append_log("The pickle file was saved")
        placeholder = st.empty()
        placeholder.success(f"{mrn} saved")
        time.sleep(1.2)
        placeholder.empty()
        
        st.session_state['save_button_disabled'] = True


def create_download_zip():
    script_path = os.path.abspath(sys.argv[0])
    script_directory = os.path.dirname(script_path)

    #File1: pickle file stored in .pkl
    annotator_name = st.session_state['annotator']
    pickle_file_path = os.path.join(script_directory, f"{annotator_name}_annotations.pkl")
    
    #File2: code for turning this into human readable .txt
    pickle_file_astxt_path = os.path.join(script_directory, f"{annotator_name}_annotations.txt")
    try: 
        with open(pickle_file_path, 'rb') as pkl_file:
            data = pickle.load(pkl_file)
        # Convert pickle data to a human-readable string (simple representation)
        readable_data = str(data)
        # Save the human-readable data to a text file
        with open(pickle_file_astxt_path, 'w') as txt_file:
            txt_file.write(readable_data)
    except Exception as e:
        append_log(f"Error in create_download_zip, turning the pkl to txt: {e}")
        # Create an empty .txt file with the error message
        with open(pickle_file_astxt_path, 'w') as txt_file:
            txt_file.write(f"Error in creating human-readable text file: {e}")
    
    #File 3: log file stored in .txt
    log_file_path = os.path.join("streamlit_logs.txt")
    
    # Create a zip file and add the CSV files
    annotator_name = st.session_state['annotator']
    zip_file_path = os.path.join(script_directory, f"ZipData_4{annotator_name}.zip")
    try:
        with zipfile.ZipFile(zip_file_path, 'w') as zf:
            zf.write(pickle_file_path, os.path.basename(pickle_file_path))
            zf.write(pickle_file_astxt_path, os.path.basename(pickle_file_astxt_path))
            zf.write(log_file_path, os.path.basename(log_file_path))
        append_log(f"Successfully created the zip file for download.")
    except Exception as e:
        placeholder_er = st.empty()
        placeholder_er.error(f"Error in create_download_zip, creating zip file: {e}")
        time.sleep(2)
        placeholder_er.empty()        
        append_log(f"Error in create_download_zip, creating zip file: {e}")
    st.session_state["disable_download_button"] = False    

def update_json_specimen_data():
    annotator_name = st.session_state['annotator']
    pickle_file_path = os.path.join(script_directory, f"{annotator_name}_annotations.pkl")
    all_mrn_data = st.session_state['all_mrns_data']
    mrn = st.session_state['mrn_4review']
    all_mrn_data[mrn]["Specimen data"] = st.session_state['current_mrn']["Specimen data"]
    
    with open(pickle_file_path, 'wb') as file:
        pickle.dump(all_mrn_data, file)
    append_log("The pickle file was saved")
    placeholder = st.empty()
    placeholder.success(f"{mrn} saved")
    time.sleep(1.2)
    placeholder.empty()
    
def update_removed_batch_data():
    annotator_name = st.session_state['annotator']
    pickle_file_path = os.path.join(script_directory, f"{annotator_name}_annotations.pkl")
    all_mrn_data = st.session_state['all_mrns_data']
    mrn = st.session_state['mrn_4review']
    all_mrn_data[mrn]["Batch data"] = st.session_state['current_mrn']["Batch data"]
    
    with open(pickle_file_path, 'wb') as file:
        pickle.dump(all_mrn_data, file)
    append_log("The pickle file was saved")
    placeholder = st.empty()
    placeholder.success(f"{mrn} saved")
    time.sleep(1.2)
    placeholder.empty()


def load_data_for_annotator():
    load_mrn_data()

#-----------------------------------------------------------------------------#
#--------------------------- Load CSV File -----------------------------------#
def read_df4review(excel_or_csv_file_path):
    try:
        if not os.path.exists(excel_or_csv_file_path):
            raise FileNotFoundError(f"No file found at the specified path: {excel_or_csv_file_path}")

        if excel_or_csv_file_path.endswith('.csv'):
            df = pd.read_csv(excel_or_csv_file_path)
        elif excel_or_csv_file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(excel_or_csv_file_path)
        else:
            raise ValueError("Unsupported file format. Please provide a .csv or .xlsx file.")

        date_column_name = df.columns[date_col_index]
        mrn_column_name = df.columns[mrn_col_index]

        df[date_column_name] = pd.to_datetime(df[date_column_name], errors='coerce').dt.strftime('%m-%d-%y')
        df[mrn_column_name] = pd.to_numeric(df[mrn_column_name], errors='coerce').apply(lambda x: f"{int(x):08}" if not pd.isna(x) else x)

        df = df.sort_values(by=[mrn_column_name, date_column_name], ascending=[True, False])

        append_log(f"File {os.path.basename(excel_or_csv_file_path)} read into DataFrame.")
        return df

    except FileNotFoundError as e:
        st.error(f"File not found error: {str(e)}")
    except ValueError as e:
        st.error(f"Value error: {str(e)}")
    except Exception as e:
        append_log(f"Failed to read the file due to: {e}")
        st.error(f"Failed to read the file due to: {e}")

def turn_one_or_multiple_cells_totext(filtered_df, column_index):
    try:
        return "\n".join(filtered_df.iloc[:, column_index].astype(str))
    except Exception as e:
        append_log(f"Error in preparing the notes for review: {e}")
        
#---------------------------------------------------------------------------------#
#--------------------------- Log file Functions -----------------------------------#
def append_success_message(message):
    if 'success_messages' not in st.session_state:
        st.session_state['success_messages'] = [message]
    else:
        if st.session_state['success_messages'][-1] != message:
            st.session_state['success_messages'].append(message)
            
def count_completed_items_4annotator():
    try:
        annotator_name = st.session_state['annotator']
        pickle_file_path = os.path.join(script_directory, f"{annotator_name}_annotations.pkl")
        with open(pickle_file_path, 'rb') as file:
            data = pickle.load(file)
        count = 0
        for key, value in data.items():
            if isinstance(value, dict) and value.get("locked") is True:
                count += 1
        return count
    except Exception as e:
        append_log(f"Error in counting the number of completed (locked) mrns in count_completed_items_4annotator: {e}")
        return 0

#------------------------------------------------------------------------------------#
#--------------------------------- Data Manipulation Functions ------ --------------#

def find_index_among_tuple(option, st_tuple):
    try:
        return st_tuple.index(option)
    except ValueError:
        return None
    
def minute_second_to_string(minutes, seconds):
    return f"{minutes}m:{seconds:02d}s"

def minute_second_from_string(time_str):
    parts = time_str.split('m:')
    minutes = int(parts[0])
    seconds = int(parts[1][:-1])
    return minutes, seconds

#------------------------------------------------------------------------------------#
#--------------------------------- Streamlet Aesthetics and Buttons ---------------------#
def disable_download_button():
    st.session_state["disable_download_button"] = True
def enable_save_button():
    st.session_state['save_button_disabled'] = False
    st.session_state["disable_download_button"] = True
    
def blue_line():
    st.markdown(
        """
        <hr style="border: none; height: 2px; background-color: blue;">
        """,
        unsafe_allow_html=True
    )
    
def load_custom_css():
    custom_css = """
    <style>
        select {
            font-size: 12px !important;  
        }
        .markdown-text-container {
        line-height: 1.1 !important;  
        }
        .stMarkdown p {
        line-height: 1.1 !important;
        }
        .stCheckbox, .stTextInput, .stSelectbox, .stDateInput {
            margin-top: 0px !important;
            margin-bottom: -10px !important;
            padding: 0px 0px !important;
        }
        .stMarkdown h2, .stMarkdown h3 {
            margin: 2px !important;
            padding: 2px !important;
            line-height: 1.1;
        }
        stMarkdown, .stMarkdown h1, .stMarkdown h4 {
            margin: 0px !important;
            padding: 0px !important;
            line-height: 1;
        }
        .block-container {
            margin-top: 10px !important;
            padding: 15px !important;
        }
        .st-cb, .css-1d391kg, .css-1kyxreq, .css-2trqyj, .css-k008qs, .css-1e5imcs, .css-1v3fvcr {
            margin: 0px !important;
            padding: 0px !important;
        }
        input, select, textarea {
            height: auto;
            font-size: 10px;
        }
        .stElement, .stTextInput > div, .stSelectbox > div, .stDateInput > div, .stCheckbox > div, .stContainer > div, .stColumns > div {
            margin-bottom: 0px !important;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)



#-------- Main Function --------#
def main():
    st.set_page_config(layout="wide", page_title="Colonoscopy Annotater", initial_sidebar_state="collapsed")
    load_custom_css()
    st.header("Colonoscopy QI Annotator 🔎")
    
    #<------------------------------------------------------------------------------------------------------------------------------------>        
    #<----------------------------------- Set stage: annotator, mrn, date ------------------------------------------------------------------------------->            
    with st.sidebar:
        textdataset_path = st.file_uploader("Upload csv file")
        if textdataset_path:
            st.session_state['df4review'] =pd.read_csv(textdataset_path)
            st.success("CSV file loaded, close the sidebar and proceed")
    try:    
        df4review = st.session_state['df4review']
        mrn_options = df4review.iloc[:, mrn_col_index].dropna().unique()
    except Exception as e:
        st.info("↖️Please upload the csv file using the left sidebar and then proceed.")
        raise ValueError("upload csv to proceed")
    
    if 'annotator' not in st.session_state:
        st.session_state['annotator'] = annotator_names[0]
    if 'mrn_4review' not in st.session_state:
        st.session_state['mrn_4review'] = mrn_options[0]
    if 'previous_mrn' not in st.session_state or st.session_state['mrn_4review'] != st.session_state['previous_mrn'] or not st.session_state['json_file_loaded']:
        load_mrn_data()
        st.session_state['previous_mrn'] = st.session_state['mrn_4review']
        st.session_state['json_file_loaded'] = True
    if 'save_button_disabled' not in st.session_state:
        st.session_state['save_button_disabled'] = False
    if "disable_download_button" not in st.session_state:
        st.session_state['disable_download_button'] = True
            
    col1, col2, col3 = st.columns([0.75, 1, 1])
    with col1:
        col1_1, col1_2, col1_3 = st.columns(3)
        with col1_1:
            annotator_name = st.selectbox("Annotator", options=annotator_names, index=0, key='annotator_name', on_change=load_mrn_data)
            if annotator_name != st.session_state.get('annotator'):
                st.session_state['annotator'] = annotator_name
                st.session_state['json_file_loaded'] = False

        col1_previous, col1_completed, col1_next = st.columns(3)
        if col1_previous.button('⬅'):
            current_index = list(mrn_options).index(st.session_state['mrn_4review'])
            if current_index > 0:
                st.session_state['mrn_4review'] = mrn_options[current_index - 1]
                load_mrn_data()
                st.session_state['previous_mrn'] = st.session_state['mrn_4review']
                st.session_state['json_file_loaded'] = True

        with col1_completed:
            completed_reviews_for_reviewer = count_completed_items_4annotator()
            st.markdown(f"""
                <div style='display: flex; justify-content: center; align-items: center; height: 5vh'>
                    <p style='font-size:12px;'>Completed(locked): {completed_reviews_for_reviewer}</p>
                </div>
                """, unsafe_allow_html=True)
            
        if col1_next.button('➡'):
            current_index = list(mrn_options).index(st.session_state['mrn_4review'])
            if current_index < len(mrn_options) - 1:
                st.session_state['mrn_4review'] = mrn_options[current_index + 1]
                load_mrn_data()
                st.session_state['previous_mrn'] = st.session_state['mrn_4review']
                st.session_state['json_file_loaded'] = True
    
        with col1_2:
            mrn_4review = st.selectbox('MRN', options=mrn_options, index=mrn_options.tolist().index(st.session_state['mrn_4review']), key='mrn_4review', on_change=load_mrn_data)
            
        with col1_3:
            date_options = df4review[df4review.iloc[:, mrn_col_index] == mrn_4review].iloc[:, date_col_index].unique()
            if date_options.size > 0:
                date_4review = st.selectbox('Date', date_options, index=0, key='date_4review', on_change=enable_save_button)
            else:
                st.error("No dates available for the selected MRN.")
                st.session_state.pop('date_4review', None)
        
    
        if 'mrn_4review' and 'date_4review' and 'current_mrn' in st.session_state:
            load_mrn_data()            
            with st.container():
                st.subheader('Data Entry')
                col1_a, col1_b, col1_c = st.columns([1.8, 1, 1.2])
#<------------------------------------------------------------------------------------------------------------------------------------>        
#<---------------------------------- Lock   ------------------------------------------------------------------------------->                     
            with col1_a:
                if "locked" not in st.session_state['current_mrn']:
                    st.session_state['current_mrn']["locked"]= False
                st.session_state['current_mrn']['locked'] = st.checkbox("Lock MRN & save", value=st.session_state['current_mrn']["locked"], key='finalize_lock', on_change=save_after_lock)

#<------------------------------------------------------------------------------------------------------------------------------------>        
#<---------------------------------- EVALUATION FORM -------------------------------------------------------------------------------> 

            user_notes = st.text_area("User Notes", value=st.session_state['current_mrn']['User Notes'], key="user_notes", 
                                    disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button) 
            st.session_state['current_mrn']['User Notes'] = user_notes

            with st.container(border=True):
                tab1, tab2, tab3, tab4 = st.tabs(["Prior History", "Most Recent", "Resected🗡️", "Unresected🥣"])

                with tab1:
                    st.markdown(f"Review the exams before {date_4review}:")
                    for label, options in prior_history_fields.items():
                        current_index = find_index_among_tuple(st.session_state['current_mrn']["Prior History"][label], options)
                        st.selectbox(label, options, key=label, index=current_index, disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button)
                        st.session_state['current_mrn']["Prior History"][label] = st.session_state[label]
                
                with tab2:
                    st.markdown(f"Review the most recent exam ({date_4review}):")
                    for label, options in recent_colonoscopy_fields.items():
                        if label == "Number of Resected Specimens":
                            resected_specimen_min, resected_specimen_max = recent_colonoscopy_fields[label]
                            st.session_state['current_mrn']["Most recent colonoscopy"][label] = st.number_input(
                                "Number of Resected Specimens 🗡️", 
                                min_value=resected_specimen_min, max_value=resected_specimen_max,
                                value=st.session_state['current_mrn']["Most recent colonoscopy"]["Number of Resected Specimens"],
                                key="Number of Resected Specimens",
                                disabled=st.session_state['current_mrn']['locked'],
                                on_change=enable_save_button
                            )     

                        elif label == "Other Polyps":
                            st.session_state['current_mrn']["Most recent colonoscopy"][label] = st.number_input(
                                "Other Polyps 🥣",
                                min_value=options[0], max_value=options[1],
                                value=len(st.session_state['current_mrn'].get("Batch data", {})),
                                key=f"{label}",
                                disabled=st.session_state['current_mrn']['locked'],
                                on_change=enable_save_button
                            )

                        elif label == "Preparation Quality BPPS":
                            st.session_state['current_mrn']["Most recent colonoscopy"][label] = st.number_input(
                                label,
                                min_value=options[0], max_value=options[1],
                                step=1,
                                value=st.session_state['current_mrn']["Most recent colonoscopy"].get(label, 0),
                                key={label},
                                disabled=st.session_state['current_mrn']['locked'],
                                on_change=enable_save_button
                            )
                            
                        elif label == "Withdrawal Time":
                            previous_time = st.session_state['current_mrn']["Most recent colonoscopy"].get(label, None)
                            if previous_time is None:
                                previous_time = options
                            previous_min, previous_sec = minute_second_from_string(previous_time)
                            
                            col1_withdrawaltime, col2_withdrawaltime, col3_withdrawaltime = st.columns([0.7, 1, 1])
                            col1_withdrawaltime.write("Withdrawal ⏱️")
                            minutes = col2_withdrawaltime.number_input(
                                "minutes⏱️",
                                min_value=0, max_value=59, step=1,
                                value=previous_min,
                                key="withdrawal_time_minutes",
                                disabled=st.session_state['current_mrn']['locked'],
                                on_change=enable_save_button
                            )
                            seconds = col3_withdrawaltime.number_input(
                                "seconds⏱️",
                                min_value=0, max_value=59, step=1,
                                value=previous_sec,
                                key="withdrawal_time_seconds",
                                disabled=st.session_state['current_mrn']['locked'],
                                on_change=enable_save_button
                            )
                            
                            st.session_state['current_mrn']["Most recent colonoscopy"][label] = minute_second_to_string(minutes, seconds)
                        
                        else:
                            current_index = find_index_among_tuple(st.session_state['current_mrn']["Most recent colonoscopy"].get(label, options[0]), options)
                            st.session_state['current_mrn']["Most recent colonoscopy"][label] = st.selectbox(
                                label,
                                options,
                                index=current_index,
                                key=label,
                                disabled=st.session_state['current_mrn']['locked'],
                                on_change=enable_save_button
                            )

                    recommended_index = find_index_among_tuple(st.session_state['current_mrn']["new_recommendation"]["Repeat Interval"], recommendation_options)
                    st.session_state['current_mrn']["new_recommendation"]["Repeat Interval"] = st.selectbox(
                        "Documented recommendation of repeated colonoscopy date:",
                        recommendation_options,
                        index=recommended_index,
                        key='doc_recommendation',
                        disabled=st.session_state['current_mrn']['locked'],
                        on_change=enable_save_button
                    )

                    if st.session_state['current_mrn']["new_recommendation"]["Repeat Interval"] == "other":
                        st.session_state['current_mrn']["new_recommendation"]["Repeat Interval text"] = st.text_input(
                            "Recommendation:",
                            key='doc_recommendation_text',
                            disabled=st.session_state['current_mrn']['locked'],
                            on_change=enable_save_button
                        )
                    
                with tab3:
                    st.markdown(f"Review the resected specimens for the most recent exam ({date_4review}):")
                    
                    selected_number_of_specimens = st.number_input("Number of resected specimen (most recent)", value=len(st.session_state['current_mrn'].get("Specimen data", {})), key='manipulate_resected', disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button) 
                    number_of_specimens_in_dic = len(st.session_state['current_mrn'].get("Specimen data", {}))
                    if selected_number_of_specimens < number_of_specimens_in_dic:
                        info_placeholder = st.empty()
                        button_placeholder = st.empty()
                        info_placeholder.info(f"There are currently {number_of_specimens_in_dic} objects in the saved data. You are viewing first {selected_number_of_specimens} object.")
                        number_to_remove = number_of_specimens_in_dic - selected_number_of_specimens
                        if button_placeholder.button(f"🔵Do you want to remove the last {number_to_remove} specimen object(s) ?"):
                            button_placeholder.empty()
                            removed_specimens_keys = []
                            while number_to_remove > 0:
                                removed_specimen_key, removed_specimen_data = st.session_state['current_mrn']["Specimen data"].popitem()
                                removed_specimens_keys.append(removed_specimen_key)
                                append_log(f"A specimen data was removed: {removed_specimen_key} -> {removed_specimen_data}")
                                number_to_remove -= 1
                            info_placeholder.info(f"{' & '.join(removed_specimens_keys)} removed")
                            update_json_specimen_data()
                            time.sleep(2)
                            info_placeholder.empty()

                    if selected_number_of_specimens > 0:
                        tabs_withintab3_labels = [f"Specimen {i + 1}" for i in range(selected_number_of_specimens)]
                        tabs_withintab3 = st.tabs(tabs_withintab3_labels)
                        
                        for i, tab_withintab3 in enumerate(tabs_withintab3):
                            with tab_withintab3:
                                specimen_label = f"Specimen {i + 1}"
                                st.subheader(specimen_label)
                                
                                if specimen_label not in st.session_state['current_mrn']["Specimen data"]:
                                    st.session_state['current_mrn']["Specimen data"][specimen_label] = empty_specimen.copy()
                                    
                                for label, options in specimen_fields.items():
                                    if label in specimen_fields_freetext4other_pair: 
                                        pair_of_freetext4other = specimen_fields_freetext4other_pair[label]
                                        if st.session_state['current_mrn']["Specimen data"][specimen_label][pair_of_freetext4other] == "other":
                                            current_value = st.session_state['current_mrn']["Specimen data"][specimen_label].get(label, "")
                                            st.session_state['current_mrn']["Specimen data"][specimen_label][label] = st.text_input(f"{label} (for {specimen_label}):", value=current_value, key=f"tuple_{specimen_label}_{label}", disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button)
                                    elif isinstance(options, str):
                                        current_value = st.session_state['current_mrn']["Specimen data"][specimen_label].get(label, "")
                                        st.session_state['current_mrn']["Specimen data"][specimen_label][label] = st.text_input(f"{label} (for {specimen_label}):", value=current_value, key=f"tuple_{specimen_label}_{label}", disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button)
                                    elif isinstance(options, tuple) and isinstance(options[0], str):
                                        current_value = st.session_state['current_mrn']["Specimen data"][specimen_label].get(label, options[0])
                                        current_index = find_index_among_tuple(current_value, options)
                                        st.session_state['current_mrn']["Specimen data"][specimen_label][label] = st.selectbox(f"{label} (for {specimen_label}):", options, index=current_index, key=f"tuple_{specimen_label}_{label}", disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button)
                                    elif isinstance(options, tuple) and isinstance(options[0], int):
                                        current_value = st.session_state['current_mrn']["Specimen data"][specimen_label].get(label, 0)
                                        st.session_state['current_mrn']["Specimen data"][specimen_label][label] = st.number_input(f"{label} (for {specimen_label}):", min_value=options[0], max_value=options[1], value=current_value, key=f"range_{specimen_label}_{label}", disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button)
                
                                
                with tab4:
                    st.markdown(f"Review the polyps from the most recent exam ({date_4review}) that were not sent for pathology:")
                    
                    selected_number_of_batch = st.number_input("Number of other polyps (unresected)", value=len(st.session_state['current_mrn'].get("Batch data", {})), key='manipulate_number_of_batch', disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button)
                    
                    number_of_batches_in_dic = len(st.session_state['current_mrn'].get("Batch data", {}))
                    if selected_number_of_batch < number_of_batches_in_dic:
                        batch_info_placeholder = st.empty()
                        batch_button_placeholder = st.empty()
                        batch_info_placeholder.info(f"There are currently {number_of_batches_in_dic} objects in the saved data. You are viewing first {selected_number_of_batch} object.")
                        batch_number_to_remove = number_of_batches_in_dic - selected_number_of_batch
                        if batch_button_placeholder.button(f"🔵Do you want to remove the last {batch_number_to_remove} batch object(s) ?"):
                            batch_button_placeholder.empty()
                            removed_batch_keys = []
                            while batch_number_to_remove != 0:
                                removed_batch_key, removed_batch_data = st.session_state['current_mrn']["Batch data"].popitem()
                                removed_batch_keys.append(removed_batch_key)
                                append_log(f"A batch data was removed: {removed_batch_key} -> {removed_batch_data}")
                                batch_number_to_remove -= 1
                            batch_info_placeholder.info(f"{' & '.join(removed_batch_keys)} removed")
                            update_removed_batch_data()
                            time.sleep(2)
                            batch_info_placeholder.empty()
                            
                    if selected_number_of_batch > 0:
                        tabs_withintab4_labels = [f"Batch {i + 1}" for i in range(selected_number_of_batch)]
                        tabs_withintab4 = st.tabs(tabs_withintab4_labels)
                        
                        for i, tab_withintab4 in enumerate(tabs_withintab4):
                            with tab_withintab4:
                                batch_label = f"Batch {i + 1}"
                                st.subheader(batch_label)

                                if batch_label not in st.session_state['current_mrn']["Batch data"]:
                                    st.session_state['current_mrn']["Batch data"][batch_label] = empty_batch.copy()

                                for label, options in batch_fields.items():
                                    if label in batch_fields_freetext4other_pair: 
                                        pair_of_freetext4other = batch_fields_freetext4other_pair[label]
                                        if st.session_state['current_mrn']["Batch data"][batch_label][pair_of_freetext4other] == "other":
                                            current_value = st.session_state['current_mrn']["Batch data"][batch_label].get(label, "")
                                            st.session_state['current_mrn']["Batch data"][batch_label][label] = st.text_input(f"{label} (for {batch_label}):", value=current_value, key=f"tuple_{batch_label}_{label}", disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button)
                                    elif isinstance(options, str):
                                        current_value = st.session_state['current_mrn']["Batch data"][batch_label].get(label, "")
                                        st.session_state['current_mrn']["Batch data"][batch_label][label] = st.text_input(f"{label} (for {batch_label}):", value=current_value, key=f"tuple_{batch_label}_{label}", disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button)
                                    elif isinstance(options, tuple) and isinstance(options[0], str):
                                        current_value = st.session_state['current_mrn']["Batch data"][batch_label].get(label, options[0])
                                        current_index = find_index_among_tuple(current_value, options)
                                        st.session_state['current_mrn']["Batch data"][batch_label][label] = st.selectbox(f"{label} (for {batch_label}):", options, index=current_index, key=f"tuple_{batch_label}_{label}", disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button)
                                    elif isinstance(options, tuple) and isinstance(options[0], int):
                                        current_value = st.session_state['current_mrn']["Batch data"][batch_label].get(label, 0)
                                        st.session_state['current_mrn']["Batch data"][batch_label][label] = st.number_input(f"{label} (for {batch_label}):", min_value=options[0], max_value=options[1], value=current_value, key=f"range_{batch_label}_{label}", disabled=st.session_state['current_mrn']['locked'], on_change=enable_save_button)

#<------------------------------------------------------------------------------------------------------------------------------------>        
#<---------------------------------- Save and Download   ------------------------------------------------------------------------------->                     
                
                with col1_b:
                    if st.button("Save", disabled=st.session_state['current_mrn'].get('locked', True) or st.session_state['save_button_disabled']):
                        save_mrn_data()
                        create_download_zip()
                with col1_c:
                    annotator_name = st.session_state['annotator']
                    zip_file_path = os.path.join(script_directory, f"ZipData_4{annotator_name}.zip")        
                    # Create a download button for the zip file
                    if os.path.exists(zip_file_path):
                        with open(zip_file_path, 'rb') as zip_file:
                            st.download_button(
                                label="Download",
                                data=zip_file,
                                file_name=os.path.basename(zip_file_path),
                                mime='application/zip',
                                on_click=disable_download_button,
                                disabled=st.session_state["disable_download_button"],
                                type='primary',
                            )
         
#<------------------------------------------------------------------------------------------------------------------------------------>        
#<---------------------------------- Printing Procedure/Pathology Notes  ------------------------------------------------------------------------------->                     
                
    with col2:
        if mrn_4review and date_4review:
            st.subheader('Procedure Note', anchor=False)
            with st.container(height=750):
                if 'df4review' in st.session_state and mrn_4review and date_4review:
                    current_df4review = df4review[(df4review.iloc[:, mrn_col_index] == mrn_4review) & (df4review.iloc[:, date_col_index] == date_4review)]
                    procedure_note_4review = turn_one_or_multiple_cells_totext(current_df4review, proc_col_index)
                    procedure_note = procedure_note_4review.replace('\n', '<br>')
                    st.markdown(
                        f"""
                        <style>
                        .small-font {{
                            font-size: 12px;
                        }}
                        </style>
                        <p class="small-font">{procedure_note}</p>
                        """, 
                        unsafe_allow_html=True
                    )
            
    with col3:
        if mrn_4review and date_4review:
            st.subheader('Pathology Note', anchor=False)
            with st.container(height=750):
                if 'df4review' in st.session_state and mrn_4review and date_4review:
                    pathology_notes_4review = turn_one_or_multiple_cells_totext(current_df4review, path_col_index)
                    pathology_note = pathology_notes_4review.replace('\n', '<br>')
                    st.markdown(
                        f"""
                        <style>
                        .small-font {{
                            font-size: 12px;
                        }}
                        </style>
                        <p class="small-font">{pathology_note}</p>
                        """, 
                        unsafe_allow_html=True
                    )
    with st.sidebar:
        blue_line()                 
        st.subheader("⬇️ Data for current_mrn ⬇️")                    
        st.write(st.session_state['current_mrn'])   
        
                        
def save_after_lock():
    previous = st.session_state['current_mrn'].get('locked')
    if previous is True:
        st.session_state['current_mrn']['locked'] =False
    elif previous is False:
        st.session_state['current_mrn']['locked'] =True
        
    if st.session_state['finalize_lock']:
        save_mrn_data()
        create_download_zip()
              
if __name__ == "__main__":
    main()
