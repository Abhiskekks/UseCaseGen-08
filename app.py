# app.py - Updated for Dual-Field Search (Access Code OR Setting Item Name)
# NOW USING EXCEL (.xlsx or .xls) FILE INPUT and REMOVING BEST MATCH SCORE DISPLAY

import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz
import random
import re

# --- Configuration ---
# 1. Specify the name of your EXCEL file (Make sure your file is now an Excel file, e.g., knowledge_base.xlsx)
CSV_FILE_NAME = 'knowledge_base.xlsx' # Changed expected file extension for clarity/best practice
# 2. Set the minimum score for a "good" match (0 to 100)
MIN_MATCH_SCORE = 75

# --- Conversational Responses ---
GREETINGS = ["hi", "hello", "hey", "good morning", "good afternoon"]
GREETING_RESPONSES = [
    "Hello there!",
    "Hi!",
    "Hey! Good to chat.",
]
CSV_MATCH_SNIPPETS = [
    "I've checked my knowledge base, and here are the details for that 08 Code:",
    "I found a close match! Here is the information you requested:",
    "Certainly! You can find the full mapping details below:",
]
CSV_NOT_FOUND_SNIPPET = "I couldn't find a close match for that 08 Code or query in my knowledge base. Could you try rephrasing or check the exact code or setting name?"

# --- REQUIRED COLUMNS ---
REQUIRED_COLUMNS = [
    'Access Code',
    'Setting item name',
    'Sub Code',
    'Meaning of sub code',
    'Description of values'
]

# --- Core Functions ---

def load_data(file_path):
    """Loads the Excel file into a Pandas DataFrame."""
    try:
        # --- MAJOR CHANGE HERE: Using pd.read_excel() ---
        # Assuming the data is in the first sheet (sheet_name=0 is default)
        df = pd.read_excel(file_path)
        # ------------------------------------------------
        
        # CHECK: Ensure all new required columns are present
        if not all(col in df.columns for col in REQUIRED_COLUMNS):
            missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            st.error(f"Error: The file '{file_path}' is missing required columns: {', '.join(missing_cols)}. Please check the column headers.")
            return None
        return df
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please ensure it is an Excel file (.xlsx or .xls) and correctly named.")
        return None
    except Exception as e:
        st.error(f"An error occurred while loading the Excel file: {e}")
        st.info("Make sure you have the 'openpyxl' or 'xlrd' library installed if you encounter an error here. You may need to add it to requirements.txt.")
        return None

def find_best_answer(query, df):
    """
    Searches the DataFrame against both 'Access Code' and 'Setting item name'.
    If a match is found, it retrieves ALL entries for the best-matched Access Code.
    """
    best_score = 0
    best_match_code = None
    
    # 1. FIND THE BEST MATCHING ACCESS CODE by searching two columns
    for access_code in df['Access Code'].unique():
        
        # Get the associated setting name (assuming one setting name per unique Access Code)
        setting_name = df[df['Access Code'] == access_code]['Setting item name'].iloc[0]
        
        # Search 1: Fuzzy score against the Access Code
        score_code = fuzz.token_set_ratio(query.lower(), str(access_code).lower())
        
        # Search 2: Fuzzy score against the Setting Item Name
        score_name = fuzz.token_set_ratio(query.lower(), str(setting_name).lower())
        
        # Take the maximum score from the two searches
        current_max_score = max(score_code, score_name)

        if current_max_score > best_score:
            best_score = current_max_score
            best_match_code = access_code
            
    # 2. CHECK THRESHOLD
    if best_score < MIN_MATCH_SCORE or best_match_code is None:
        return (False, None)

    # 3. RETRIEVE ALL ROWS FOR THE BEST MATCHED CODE
    matched_df = df[df['Access Code'] == best_match_code].copy()
        
    if matched_df.empty:
        return (False, None)
        
    # Get the common header values
    access_code = str(matched_df.iloc[0]['Access Code'])
    setting_item_name = str(matched_df.iloc[0]['Setting item name'])

    # 4. FORMAT THE OUTPUT

    # --- A. Format the Header Block ---
    # The format requested: 08 Code: PR-401, Setting Item Name: Print Quality Mode
    header_block = (
        f"**08 Code:**\t`{access_code}`\n\n"
        f"**Setting Item Name:**\t{setting_item_name}\n\n"
    )

    # --- B. Prepare the Sub-Table Data ---
    sub_table_df = matched_df[[
        'Sub Code', 
        'Meaning of sub code', 
        'Description of values'
    ]].copy()
    
    sub_table_df.columns = ['Sub Code', 'Meaning', 'Description']
    
    # Convert the sub-table DataFrame to a Markdown table string
    table_markdown = sub_table_df.to_markdown(index=False)

    # --- C. Combine all parts ---
    formatted_answer = (
        f"### 08 Code Details\n\n"
        f"{header_block}"
        f"Here is the detailed breakdown of the available options:\n\n"
        f"{table_markdown}"
    )

    return (True, formatted_answer)

# The analyze_prompt_for_multiple_intents function remains unchanged.
def analyze_prompt_for_multiple_intents(prompt):
    """
    Analyzes the prompt to separate a greeting/small talk from the core query.
    """
    q_lower = prompt.lower().strip()
    detected_greeting = None

    for greeting in GREETINGS:
        if re.match(r'\b' + re.escape(greeting) + r'\b', q_lower) or q_lower.startswith(greeting):
            detected_greeting = random.choice(GREETING_RESPONSES)

            match_end = q_lower.find(greeting) + len(greeting)
            search_query = q_lower[match_end:].strip()
            search_query = re.sub(r'^[\s,.:;]+', '', search_query) 

            if not search_query:
                return detected_greeting, prompt 

            return detected_greeting, search_query

    return None, prompt


# --- Streamlit App Interface (Remains mostly the same) ---

# Load the data once at the start
data_df = load_data(CSV_FILE_NAME)

if data_df is not None:
    st.set_page_config(page_title="UseCaseGen-08", layout="centered")
    st.title(" 🚀 UseCaseGen-08 ")
    st.markdown("Try searching by **08 Code** (e.g., 'PR-401') OR **Setting Item Name** (e.g., 'Print Quality Mode').")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": "Hello! I can search my knowledge base for specific 08 Code mappings by code or setting name."})

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Enter the 08 code or a query..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching and Mapping..."):
                
                greeting_response, search_query = analyze_prompt_for_multiple_intents(prompt)

                final_response = ""

                if greeting_response:
                    final_response += greeting_response

                csv_match_found, csv_answer = find_best_answer(search_query, data_df)

                if csv_match_found:
                    connector = random.choice(CSV_MATCH_SNIPPETS)
                    if final_response:
                        final_response += f" {connector}\n\n{csv_answer}"
                    else:
                        final_response += f"{connector}\n\n{csv_answer}"

                else:
                    if not search_query.strip() or search_query == prompt.strip():
                        if greeting_response:
                            final_response += " I'm ready to search my knowledge base. What 08 code or setting name can I look up for you?"
                        else:
                            final_response = "I'm a specialized tool. I couldn't find an answer for that general topic. Try asking about a specific 08 Code or Setting Name!"

                    elif greeting_response:
                        final_response += f" {CSV_NOT_FOUND_SNIPPET}"

                    else:
                        final_response = CSV_NOT_FOUND_SNIPPET

                st.markdown(final_response)

        st.session_state.messages.append({"role": "assistant", "content": final_response})

    st.sidebar.subheader("Configuration")
    st.sidebar.info(f"Using **{CSV_FILE_NAME}** as the knowledge base. \n\nMinimum match score: **{MIN_MATCH_SCORE}%**")
