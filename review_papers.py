import os
import shutil
from typing import Dict
import requests
import pandas as pd
import re
import evadb
from bs4 import BeautifulSoup
from time import sleep
import wget
import urllib
import warnings
import os
from time import perf_counter

from gpt4all import GPT4All
from unidecode import unidecode
from find_and_download import find_basis_paper

def receive_user_input():

    find_basis_paper()

    user_input = {}
    print()

    paper_name = input("Enter the file name of the paper you want to review: ")
    user_input['name'] = paper_name
    # user_input['name'] = "user_paper0.pdf"
    
    review_pages = input("Which pages do you want to review? (1 2 3): ")
    review_pages = list(map(int,review_pages.split()))
    user_input['review_pages'] = review_pages

    review_para = input("Which paragraphs do you want to review? (1 2 3 or press enter if all paras or multiple pages): ")
    review_para = list(map(int,review_para.split()))
    user_input['review_para'] = review_para

    review_actor = input("Choose role of reviewer (advocate, critque or neutral): ")
    user_input['review_actor'] = review_actor
        # user_input['review_actor'] = "neutral"
        
    return user_input


def review_single(args):
    # create table to load pdfs
    cursor.query("DROP TABLE IF EXISTS MyPDFs").df()
    cursor.query(f"LOAD PDF '{os.path.join('papers',args['name'])}' INTO MyPDFs").df()

    print(cursor.query("SELECT * FROM MyPDFs").df())

    assert len(user_input['review_pages']) >0, "Enter at least one page number"

    page_query = ""
    for page_num in user_input['review_pages']:
        if (page_query != ""):
            page_query += " OR "
        page_query += f"page = {page_num}"


    para_query = ""
    for para_num in user_input['review_para']:
        if (para_query != ""):
            para_query += " OR "
        para_query += f"paragraph = {para_num}"

    # create udf for text summarization
    cursor.query("""
    CREATE FUNCTION IF NOT EXISTS TextSummarizer
    TYPE HuggingFace
    TASK 'summarization'
    MODEL 'facebook/bart-large-cnn'
    """).df()

    # print(cursor.query("""
    # SELECT *
    # FROM MyPDFs
    # WHERE data @> ['Abstract']
    # """).df())

    if (para_query!=""):
        data = cursor.query(f"""
        SELECT SEGMENT(data)
        FROM MyPDFs
        WHERE {page_query} AND {para_query}
        """).df()
    else:
        
        data = cursor.query(f"""
        SELECT *
        FROM MyPDFs
        WHERE {page_query}
        """).df()

    concat_query = ' '.join(data['mypdfs.data'].tolist())

    cursor.query("DROP TABLE IF EXISTS UserQueryData").df()
    cursor.query(f"""
    CREATE TABLE UserQueryData
    (id INTEGER,
    data TEXT(4096));
    """).df()

    cursor.query(f"""
    INSERT INTO UserQueryData (id, data) VALUES
    (1, '{concat_query}');
    """).df()

    if(user_input['review_actor'] == "neutral"):
        # use fb model since faster for summarizing
        summary_fb = cursor.query(f"""
        SELECT TextSummarizer(data)
        FROM UserQueryData
        """).df()
        
        print("Summary produced by fb model:")
        print(' '.join(summary_fb['textsummarizer.summary_text'].tolist()))
    else:
        llm = GPT4All("ggml-model-gpt4all-falcon-q4_0.bin")
        question = f"Review in detail as {user_input['review_actor']}"

        # LLM
        query = f"""{concat_query}
        
        {question}"""

        full_response = llm.generate(query)

        print("Summary produced by local llm:")
        print(full_response)


def cleanup():
    """Removes any temporary file / directory created by EvaDB."""
    if os.path.exists("evadb_data"):
        shutil.rmtree("evadb_data")

if __name__=="__main__":
    
    warnings.filterwarnings("ignore")

    # receive input from user
    user_input = receive_user_input()

    try:
        # establish evadb api cursor
        cursor = evadb.connect().cursor()
        review_single(user_input)

    except Exception as e:
        cleanup()
        print("❗️ Session ended with an error.")
        print(e)
        print("===========================================")