# app.py - Updated for Access Code Mapping (Searching by Access Code) - NOW WITH TABLE OUTPUT (ERROR FIX APPLIED)

import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz
import random
import re

# --- Configuration ---
# 1. Specify the name of your CSV file
CSV_FILE_NAME = 'knowledge_base.csv'
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
    "I've checked my knowledge base, and here are the details for that Access Code:",
    "I found a close match! Here is the information you requested:",
    "Certainly! You can find the full mapping details below:",
]
CSV_NOT_FOUND_SNIPPET = "I couldn't find a close match for that Access Code or query in my knowledge base. Could you try rephrasing or check the exact code?"

# --- NEW REQUIRED COLUMNS ---
REQUIRED_COLUMNS = [
    'Access Code',
    'Setting item name',
    'Sub Code',
    'Meaning of sub code',
    'Description of values'
]

# --- Core Functions ---

def load_data(file_path):
    """Loads the CSV file into a Pandas DataFrame."""
    try:
        df = pd.read_csv(file_path)
        # CHECK: Ensure all new required columns are present
        if not all(col in df.columns for col in REQUIRED_COLUMNS):
            missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            st.error(f"Error: The file '{file_path}' is missing required columns: {', '.join(missing_cols)}. Please check the column headers.")
            return None
        return df
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please create it and restart.")
        return None
    except Exception as e:
        st.error(f"An error occurred while loading the CSV: {e}")
        return None

def find_best_answer(query, df):
    """
    Searches the DataFrame's 'Access Code' column for the best matching query
    and returns the corresponding mapped values in a table format.
    """
    best_score = 0
    best_match_data = {}

    # Iterate through each row's data
    for index, row in df.iterrows():
        # Search is now done against the 'Access Code' column
        access_code_key = str(row['Access Code'])

        # Use token set ratio for fuzzy matching
        score = fuzz.token_set_ratio(query.lower(), access_code_key.lower())

        if score > best_score:
            best_score = score
            # Store the data for the best match found so far
            best_match_data = {
                'Access Code': access_code_key,
                'Setting item name': str(row['Setting item name']),
                'Sub Code': str(row['Sub Code']),
                'Meaning of sub code': str(row['Meaning of sub code']),
                'Description of values': str(row['Description of values']),
            }

    # If the best score is below the threshold, return the default "not found" message
    if best_score < MIN_MATCH_SCORE:
        return (False, None) # Return False flag and None for no good answer

    # --- UPDATED FORMATTING SECTION: Use Markdown Table ---
    # The keys in the table are the labels, and the values are the data.
    formatted_answer = (
        f"### Access Code Mapping Details\n\n"
        f"| Item | Value |\n"
        f"| :--- | :--- |\n"
        f"| **Access Code** | `{best_match_data['Access Code']}` |\n"
        f"| **Setting Item Name** | {best_match_data['Setting item name']} |\n"
        f"| **Sub Code** | `{best_match_data['Sub Code']}` |\n"
        f"| **Meaning of Sub Code** | {best_match_data['Meaning of sub code']} |\n"
        f"| **Description of Values** | {best_match_data['Description of values']} |\n"
    )
    # --------------------------------------------------------

    return (True, formatted_answer)

def analyze_prompt_for_multiple_intents(prompt):
    """
    Analyzes the prompt to separate a greeting/small talk from the core query.
    (This function remains the same as it handles general conversational flow)
    """
    q_lower = prompt.lower().strip()
    detected_greeting = None

    # Check for Greetings at the start
    for greeting in GREETINGS:
        if re.match(r'\b' + re.escape(greeting) + r'\b', q_lower) or q_lower.startswith(greeting):
            detected_greeting = random.choice(GREETING_RESPONSES)

            # Find the end of the greeting + separator
            match_end = q_lower.find(greeting) + len(greeting)
            search_query = q_lower[match_end:].strip()
            search_query = re.sub(r'^[\s,.:;]+', '', search_query) # Remove leading separators

            # If the search query is empty after removing the greeting, use the original prompt
            if not search_query:
                return detected_greeting, prompt # Let the prompt be searched too, but keep the greeting

            return detected_greeting, search_query

    # If no greeting was found, the search query is the original prompt
    return None, prompt


# --- Streamlit App Interface ---

# Load the data once at the start
data_df = load_data(CSV_FILE_NAME)

if data_df is not None:
    st.set_page_config(page_title="UseCaseGen-08", layout="centered")
    st.title(" 🚀 UseCaseGen-08 ")
    st.markdown("Try saying **'Hi, I need the details for access code XXX'** or a query related to your Access Codes.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": "Hello! I can search my knowledge base for specific Access Code mappings."})

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Enter the Access Code or a query..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get the assistant's response
        with st.chat_message("assistant"):
            with st.spinner("Searching and Mapping..."):

                # --- Core Logic: Analyze and Respond ---
                greeting_response, search_query = analyze_prompt_for_multiple_intents(prompt)

                final_response = ""

                # 1. Start the response with the greeting if one was detected
                if greeting_response:
                    final_response += greeting_response

                # 2. Perform the search using the cleaned query
                csv_match_found, csv_answer = find_best_answer(search_query, data_df)

                if csv_match_found:
                    connector = random.choice(CSV_MATCH_SNIPPETS)

                    if final_response:
                        # Combine greeting and table
                        final_response += f" {connector}\n\n{csv_answer}"
                    else:
                        # Table only
                        final_response += f"{connector}\n\n{csv_answer}"

                else:
                    # Handle "Not Found" case
                    
                    # If it was JUST a greeting (e.g., input was only "Hi"), add a helpful prompt
                    if not search_query.strip() or search_query == prompt.strip():
                        if greeting_response:
                            # Line 188 (approximately): Added the text to the same line as the +=
                            final_response += " I'm ready to search my knowledge base. What Access Code can I look up for you?"
                        else:
                            final_response = "I'm a specialized tool. I couldn't find an answer for that general topic. Try asking about a specific Access Code!"

                    elif greeting_response:
                        final_response += f" {CSV_NOT_FOUND_SNIPPET}"

                    else:
                        final_response = CSV_NOT_FOUND_SNIPPET

                st.markdown(final_response)

        # Add assistant message to chat history
        st.session_state.messages.append({"role": "assistant", "content": final_response})

    st.sidebar.subheader("Configuration")
    st.sidebar.info(f"Using **{CSV_FILE_NAME}** as the knowledge base. \n\nMinimum match score: **{MIN_MATCH_SCORE}%**")
