# app.py - FINAL AND CORRECTED CODE: Contextual Handling for Ambiguous "Show All" and NameError fix

import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz
import random
import re

# --- Configuration ---
# 1. Specify the name of your EXCEL file 
CSV_FILE_NAME = 'knowledge_base_file.xlsx' 
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
AMBIGUOUS_MATCH_SNIPPET = (
    "I found multiple possible matches that score {score}%. "
    "Please try searching for one of the specific 08 Codes below for the full details:"
)
AMBIGUOUS_SHOW_ALL_SNIPPET = (
    "Displaying details for all the highly-matched 08 Codes below:"
)
CSV_NOT_FOUND_SNIPPET = "I couldn't find a close match for that 08 Code or query in my knowledge base. Could you try rephrasing or check the exact code or setting name?"

# --- REQUIRED COLUMNS ---
REQUIRED_COLUMNS = [
    'Access Code',
    'Setting item name',
    'Sub Code',
    'Meaning of sub code'
]

# --- Helper Patterns ---
# Regex pattern to detect a "Show All" command
SHOW_ALL_PATTERN = r'\b(show all|all options|give all|all of them)\b'
# Regex pattern to extract codes from the Ambiguous Search Result block
CODE_EXTRACTION_PATTERN = r'\* `([A-Z0-9-]+)`'


# --- Core Functions ---

def load_data(file_path):
    """Loads the Excel file into a Pandas DataFrame."""
    try:
        df = pd.read_excel(file_path)
        
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
        st.info("Ensure the file structure is correct and necessary libraries (pandas, openpyxl) and tabulate are installed.")
        return None

def format_single_code_details(access_code, matched_df):
    """Formats the detailed output for a single, known Access Code."""
    
    # Get the common header values
    setting_item_name = str(matched_df.iloc[0]['Setting item name'])

    # --- A. Format the Header Block ---
    header_block = (
        f"**08 Code:**\t`{access_code}`\n\n"
        f"**Setting Item Name:**\t{setting_item_name}\n\n"
    )

    # --- B. Prepare the Sub-Table Data ---
    sub_table_df = matched_df[[
        'Sub Code', 
        'Meaning of sub code', 
    ]].copy()
    
    sub_table_df.columns = ['Sub Code', 'Meaning'] 
    
    # Convert the sub-table DataFrame to a Markdown table string (Requires 'tabulate')
    table_markdown = sub_table_df.to_markdown(index=False)

    # --- C. Combine all parts ---
    formatted_answer = (
        f"### Details for Code: `{access_code}`\n\n"
        f"{header_block}"
        f"Available options:\n\n"
        f"{table_markdown}\n\n" # Added extra newline for separation
        f"---" # Separator for multiple codes
    )
    return formatted_answer

def format_ambiguous_output(matched_codes, score):
    """Formats the output when multiple high-scoring codes are found (asking for clarification)."""
    
    # Remove duplicates and format into a Markdown list
    code_list = "\n".join([f"* `{code}`" for code in sorted(list(set(matched_codes)))])
    
    # Get the introductory snippet and insert the score
    snippet = AMBIGUOUS_MATCH_SNIPPET.format(score=score)
    
    formatted_answer = (
        f"### Ambiguous Search Result\n\n"
        f"{snippet}\n\n"
        f"{code_list}"
    )
    return (True, formatted_answer)


def find_best_answer(query, df):
    """
    Searches the DataFrame against 'Access Code' and 'Setting item name'.
    Lists all codes that achieve the best score, regardless of whether that score is 100%.
    """
    best_score = 0
    score_to_codes = {} 
    
    # 1. FIND THE BEST MATCHING SCORE AND IDENTIFY ALL CODES THAT ACHIEVE IT
    for access_code in df['Access Code'].unique():
        
        setting_name = df[df['Access Code'] == access_code]['Setting item name'].iloc[0]
        
        # Search 1: Fuzzy score against the Access Code
        score_code = fuzz.token_set_ratio(query.lower(), str(access_code).lower())
        
        # Search 2: Fuzzy score against the Setting Item Name
        score_name = fuzz.token_set_ratio(query.lower(), str(setting_name).lower())
        
        # Take the maximum score from the two searches
        current_max_score = max(score_code, score_name)

        if current_max_score > best_score:
            best_score = current_max_score
            score_to_codes = {best_score: [access_code]}
        elif current_max_score == best_score and current_max_score >= MIN_MATCH_SCORE:
            score_to_codes.setdefault(best_score, []).append(access_code)
            
    # 2. CHECK THRESHOLD
    if best_score < MIN_MATCH_SCORE or not score_to_codes:
        return (False, None) # No good match found

    # Get the list of codes that achieved the best score
    best_score_codes = list(set(score_to_codes[best_score]))
    
    # 3. AMBIGUITY CHECK: If multiple unique codes share the best score, ask for clarification.
    if len(best_score_codes) > 1:
        return format_ambiguous_output(best_score_codes, best_score)
        
    # 4. HANDLE SINGLE BEST MATCH
    best_match_code = best_score_codes[0]
        
    # 5. RETRIEVE ALL ROWS AND FORMAT DETAILS FOR THE SINGLE CODE
    matched_df = df[df['Access Code'] == best_match_code].copy()
        
    if matched_df.empty:
        return (False, None)

    formatted_answer = format_single_code_details(best_match_code, matched_df)
    
    return (True, formatted_answer)


# The analyze_prompt_for_multiple_intents function remains unchanged.
def analyze_prompt_for_multiple_intents(prompt):
    """Analyzes the prompt to separate a greeting/small talk from the core query."""
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


# --- Streamlit App Interface (Contains new logic for "Show All" and fix for NameError) ---

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
                
                # Initialize variables to avoid NameError
                csv_answer = ""
                csv_match_found = False

                if greeting_response:
                    final_response += greeting_response
                
                # --- CONTEXTUAL LOGIC ---
                is_show_all_command = re.search(SHOW_ALL_PATTERN, search_query.lower())
                
                # Check if the previous message was an Ambiguous Search Result
                if st.session_state.messages and len(st.session_state.messages) >= 2:
                    last_assistant_message = st.session_state.messages[-2]['content']

                    if is_show_all_command and "### Ambiguous Search Result" in last_assistant_message:
                        
                        matched_codes = re.findall(CODE_EXTRACTION_PATTERN, last_assistant_message)
                        
                        if matched_codes:
                            # 1. Start response
                            final_response += f" {AMBIGUOUS_SHOW_ALL_SNIPPET}\n\n"
                            
                            # 2. Process and combine details for all extracted codes
                            combined_details = ""
                            for code in matched_codes:
                                matched_df = data_df[data_df['Access Code'] == code].copy()
                                if not matched_df.empty:
                                    combined_details += format_single_code_details(code, matched_df)
                            
                            final_response += combined_details
                            csv_match_found = True
                            # Use a specific flag value for csv_answer to indicate handling was done
                            csv_answer = "SHOW_ALL_HANDLED" 
                        else:
                            final_response = "I couldn't identify the codes from the previous context. Please try searching for a single code name."
                            csv_match_found = False
                    
                    else: # Not a "Show All" command or no previous ambiguous result
                        csv_match_found, csv_answer = find_best_answer(search_query, data_df)
                
                else: # Fresh chat or only one previous message
                    csv_match_found, csv_answer = find_best_answer(search_query, data_df)
                # --- END CONTEXTUAL LOGIC ---
                
                # --- FORMATTING OUTPUT ---
                if csv_match_found:
                    # Check if the result came from the standard find_best_answer call
                    if csv_answer != "SHOW_ALL_HANDLED":
                        
                        if "### Ambiguous Search Result" in csv_answer:
                            connector = "I need a little more clarity."
                            final_response += f" {connector}\n\n{csv_answer}"
                        
                        elif "### Details for Code:" in csv_answer:
                            # This is a single, non-ambiguous match result
                            connector = random.choice(CSV_MATCH_SNIPPETS)
                            if final_response:
                                final_response += f" {connector}\n\n{csv_answer}"
                            else:
                                final_response += f"{connector}\n\n{csv_answer}"
                    # If csv_answer == "SHOW_ALL_HANDLED", final_response is already complete.

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
