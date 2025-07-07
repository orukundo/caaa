# -*- coding: utf-8 -*-
"""
Created on Wed Oct 23 20:55:24 2024

@author: Olivier.Rukundo
"""

"""
Created on Fri Oct 18 10:18:41 2024

@author: Olivier.Rukundo
"""


import tkinter as tk
from tkinter import scrolledtext
import openai
import yaml
import requests
import urllib.parse
import re
from tkinter import messagebox

# Load the OpenAI and ClaimBuster API keys from YAML files
with open("config.yaml") as f:
    openai.api_key = yaml.safe_load(f)['token']

with open("config1.yaml") as f:
    claimbuster_api_key = yaml.safe_load(f)['token']

# Function to check if the question is grammatically correct and coherent
def check_question_clarity(question):
    check_prompt = f"Is the following question grammatically correct and clear?\n\n{question}\n\nPlease reply with 'Yes' if it is, or 'No' if it is not."
    chat_response = openai.ChatCompletion.create(
        model="gpt-4o",
        max_tokens=10,
        messages=[{"role": "user", "content": check_prompt}]
    )
    return chat_response["choices"][0]["message"]["content"].strip().lower() == 'yes'

# Function to ask a question to ChatGPT and get the revised question for confirmation 
def rephrase_question_if_needed(question):
    is_question_clear = check_question_clarity(question)

    if is_question_clear:
        return question 

    # If not clear, rephrase the question
    rephrase_prompt = f"Please rephrase the following question for clarity and logical consistency:\n\n{question}"
    chat_response = openai.ChatCompletion.create(
        model="gpt-4o",
        max_tokens=2048,
        messages=[{"role": "user", "content": rephrase_prompt}]
    )
    return chat_response["choices"][0]["message"]["content"]

# Function to ask ChatGPT for an answer
def ask_chatgpt(question):
    chat_response = openai.ChatCompletion.create(
        model="gpt-4o",
        max_tokens=2048,
        messages=[{"role": "user", "content": question}]
    )
    return chat_response["choices"][0]["message"]["content"]


# Function to fact-check a claim using ClaimBuster
def fact_check_claim(claim):
    api_endpoint = f"https://idir.uta.edu/claimbuster/api/v2/score/text/{urllib.parse.quote(claim)}"
    response = requests.get(url=api_endpoint, headers={"x-api-key": claimbuster_api_key})

    if response.status_code == 200:
        return response.json()
    return {"error": f"Error: {response.status_code}, {response.text}"}

# Function to split text into sentences based on periods
def split_into_sentences(text):
    sentences = re.findall(r'[^.]+(?=\.)', text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]

# Function to analyze the question, display the ChatGPT answer, fact-check, and show the result
def ask_and_fact_check():
    question = question_textbox.get("1.0", tk.END).strip()
    
    if not question:
        status_label.config(text="Please enter a question.", fg="red")
        return
    
    # Rephrase and confirm the question
    revised_question = rephrase_question_if_needed(question)
    
    # Show the revised question to the user for confirmation
    if not messagebox.askyesno("Confirm Question", f"This is how ChatGPT understands your question:\n\n{revised_question}\n\nIs this correct?"):
        status_label.config(text="Please revise your question.", fg="red")
        return
    
    # Update the question textbox with the revised question after confirmation
    question_textbox.config(state=tk.NORMAL)  
    question_textbox.delete("1.0", tk.END)    
    question_textbox.insert(tk.END, revised_question)  
    question_textbox.update_idletasks()  

    
    # If confirmed, proceed to ask ChatGPT
    answer = ask_chatgpt(revised_question)
    chatgpt_answer_box.config(state=tk.NORMAL)
    chatgpt_answer_box.delete("1.0", tk.END)
    chatgpt_answer_box.insert(tk.END, answer)
    chatgpt_answer_box.config(state=tk.DISABLED)
    
    # Split the answer into sentences and visualize
    sentences = split_into_sentences(answer)
    
    total_score = 0
    sentence_count = len(sentences)

    # Fact-check each sentence using ClaimBuster
    for sentence in sentences:
        fact_check_result = fact_check_claim(sentence)
        
        if 'error' in fact_check_result:
            status_label.config(text=fact_check_result['error'], fg="red")
            return
        else:
            total_score += fact_check_result["results"][0]['score']
    
    # Calculate average score and display results
    if sentence_count > 0:
        average_score = float(total_score / sentence_count)
        status_label.config(text=f"ClaimBuster Score: {average_score:.3f}", fg="black")
        
        # Display analysis in green or red based on the score
        print(f"Average Score: {average_score}")
        if average_score < 0.50:
            analysis_label.config(text="NO VERIFICATION REQUIRED", bg="green", fg="white")
        else:
            analysis_label.config(text="VERIFICATION REQUIRED", bg="red", fg="white")
            
            # If verification required, recheck the answer and recalculate score
            rechecked_answer = ask_chatgpt(f"Please recheck the following answer for accuracy:\n\n{answer}")
            
            # Remove the first (redundant) sentence if there is more than one sentence
            display_sentences = sentences[1:] if len(sentences) > 1 else sentences

            chatgpt_answer_box.config(state=tk.NORMAL)
            chatgpt_answer_box.delete("1.0", tk.END)
            chatgpt_answer_box.insert(tk.END, ". ".join(display_sentences) + ".")
            chatgpt_answer_box.config(state=tk.DISABLED)

            # Recalculate ClaimBuster score for rechecked answer
            sentences = split_into_sentences(rechecked_answer)
            
            # Remove the first redundant sentence if there is more than one sentence
            sentences = sentences[1:] if len(sentences) > 1 else sentences
    
            total_score = sum(fact_check_claim(sentence)["results"][0]['score'] for sentence in sentences)
            average_score = total_score / len(sentences)
            
            status_label.config(text=f"ClaimBuster Score: {average_score:.3f}", fg="black")
            print(f"Average Score: {average_score}")  
            if average_score < 0.50:
                analysis_label.config(text="NO VERIFICATION REQUIRED", bg="green", fg="white")
            else:
                analysis_label.config(text="VERIFICATION REQUIRED", bg="red", fg="white")
    else:
        status_label.config(text="No sentences were found in the text for analysis.", fg="red")

# Set up the tkinter window
window = tk.Tk()
window.title("ChatGPT Answers Analysis App")
window.geometry("600x500")

# Input section
tk.Label(window, text="Enter your question:").pack(pady=5)
question_textbox = tk.Text(window, height=4, width=60)
question_textbox.pack()

# Ask question button
ask_button = tk.Button(window, text="Ask Question", command=ask_and_fact_check)
ask_button.pack(pady=10)

# ChatGPT response section
tk.Label(window, text="ChatGPT Answer:").pack()
chatgpt_answer_box = scrolledtext.ScrolledText(window, height=10, width=60, state=tk.DISABLED)
chatgpt_answer_box.pack()

# Status label
status_label = tk.Label(window, text="", fg="black")
status_label.pack(pady=10)

# Analysis label
analysis_label = tk.Label(window, text="", width=40)
analysis_label.pack(pady=10)

# Start the tkinter loop
window.mainloop()
