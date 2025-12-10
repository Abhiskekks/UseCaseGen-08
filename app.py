# app.py - Updated for Combined Intent and Natural Conversation (Searching by Code08)

import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz
import random 
import re 

# --- Configuration ---
# 1. Specify the name of your CSV file
# NOTE: The CSV file MUST now have columns: Code08 and Use
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
    "I've checked my knowledge base, and here is the use case:",
    "I found a close match! Here are the details you requested:",
    "Certainly! You can find the information below:",
]
CSV_NOT_FOUND_SNIPPET = "I couldn't find a close match for that query in my knowledge base. Could you try rephrasing or check the exact code?"

# --- Core Functions ---

def load_data(file_path):
    """Loads the CSV file into a Pandas DataFrame."""
    try:
        df = pd.read_csv(file_path)
        # CHECK: Now expecting 'Code08' (for search key) and 'Use' (for answer)
        if not all(col in df.columns for col in ['Code08', 'Use']):
            st.error(f"Error: The file '{file_path}' must contain 'Code08' (for searching) and 'Use' (for the description) columns.")
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
    Searches the DataFrame's 'Code08' column for the best matching query 
    and returns the corresponding 'Use'.
    """
    best_score = 0
    best_answer_use = None
    best_answer_code08 = None # Storing the matched code for output
    
    # Iterate through each row's data
    for index, row in df.iterrows():
        # Search is now done against the 'Code08' column
        code_key_08 = str(row['Code08']) 
        code_use = str(row['Use']) 
        
        # Use token set ratio for fuzzy matching
        score = fuzz.token_set_ratio(query.lower(), code_key_08.lower())
        
        if score > best_score:
            best_score = score
            best_answer_use = code_use
            best_answer_code08 = code_key_08 # Store the matched code
                
    # If the best score is below the threshold, return the default "not found" message
    if best_score < MIN_MATCH_SCORE:
        return (False, None) # Return False flag and None for no good answer
        
    # Return the answer and a flag indicating it came from the CSV
    # FORMATTING CHANGE: Changed "Use Case" to "Use"
    formatted_answer = (
        f"**Matching 08th Code:** `{best_answer_code08}`\n\n"
        f"**Use:**\n{best_answer_use}"
    )
    return (True, formatted_answer)

def analyze_prompt_for_multiple_intents(prompt):
    """
    Analyzes the prompt to separate a greeting/small talk from the core query.
    Returns the detected greeting (or None) and the cleaned-up search query.
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
    st.set_page_config(page_title="General Chatbot", layout="centered")
    st.title(" UseCaseGen-08 ")
    st.markdown("Try saying **'Hi, what is the 08th code for ABC'** or a query related to your CSV data.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": "Hello! I can handle simple chat and search my knowledge base."})

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is your question?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get the assistant's response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                
                # --- NEW LOGIC: Analyze and Respond ---
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
                        # e.g., "Hello there! I've checked my knowledge base, and here is the use case: ..."
                        final_response += f" {connector}\n\n{csv_answer}"
                    else:
                        # e.g., "I've checked my knowledge base, and here is the use case: ..." (No greeting)
                        final_response += f"{connector}\n\n{csv_answer}"
                
                else:
                    # Handle "Not Found" case
                    
                    # If it was JUST a greeting (e.g., input was only "Hi"), add a helpful prompt
                    if not search_query.strip() or search_query == prompt.strip():
                        if greeting_response:
                            final_response += " I'm ready to search my knowledge base. What code or use case can I look up for you?"
                        else:
                            # If it wasn't a greeting and didn't match the CSV, use the general fallback
                            final_response = "I'm a specialized AI. I couldn't find an answer for that general topic. Try asking about a code or use case in my knowledge base!"
                    
                    # If it was a combined query that failed (e.g., "Hi, use case for ZZZZZZZZZ")
                    elif greeting_response:
                        final_response += f" {CSV_NOT_FOUND_SNIPPET}"
                    
                    # If it was just a failed search query (e.g., "use case for ZZZZZZZZZ")
                    else:
                        final_response = CSV_NOT_FOUND_SNIPPET


                st.markdown(final_response)
        
        # Add assistant message to chat history
        st.session_state.messages.append({"role": "assistant", "content": final_response})

    st.sidebar.subheader("Configuration")
    st.sidebar.info(f"Using **{CSV_FILE_NAME}** as the knowledge base. \n\nMinimum match score: **{MIN_MATCH_SCORE}%**")