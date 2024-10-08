# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os, sys
import pandas as pd
import numpy as np
import json

from datetime import timedelta

from flask import render_template, request, session
from flask_migrate import Migrate
from   flask_minify  import Minify
from   sys import exit

import subprocess

from localStoragePy import localStoragePy

from apps.config import config_dict
from apps import create_app, db

from chainlit.cli import run_chainlit

from apps.analytics import quicksight_embed as qe
from apps.analytics import bedrock_rag as rag
from apps.analytics import bedrock_rag_enhanced as re
from apps.analytics import bedrock_rag_LangChain as lc
from apps.analytics import openai_nlp2sql as oai

from apps.analytics.recommendations import notifications as nof
from apps.analytics.recommendations import absences as ab

from slack import WebClient


# now cd into sales inference module so we can run main.py for the new sales forecast
# *check* if better way of doing this - running a python function from a modules from another repo
import sys
sys.path.insert(0, '/Users/barry.walsh/rotaready/rr_repos/ML-modelTraining/training/docker/SalesPredictions/inference')
# OR ? 
# %cd "/Users/barry.walsh/rotaready/rr_repos/ML-LabourDemandForecasting/inference/docker/LabourDemandForecasting"
import main as nsf_inf

client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
kb_id = os.getenv("BEDROCK_KB")

# WARNING: Don't run with debug turned on in production!
DEBUG = (os.getenv('DEBUG', 'False') == 'True')

# The configuration
get_config_mode = 'Debug' if DEBUG else 'Production'

try:

    # Load the configuration using the default values
    app_config = config_dict[get_config_mode.capitalize()]

except KeyError:
    exit('Error: Invalid <config_mode>. Expected values [Debug, Production] ')

app = create_app(app_config)
# app = flask.Flask("__main__")

# secret key is needed for session
app.secret_key = b'\x19\x86\x1b\x19\xfe?z\x11\x9e\xc1.\x87\xe7\x00\xd7\xf8'

# local storage
localStorage = localStoragePy('salesfc', 'text')

Migrate(app, db)

env = 'local' # *update {env} param later to config.ENV

if not DEBUG:
    Minify(app=app, html=True, js=False, cssless=False)
    
if DEBUG:
    app.logger.info('DEBUG            = ' + str(DEBUG) )
    app.logger.info('Page Compression = ' + 'FALSE' if DEBUG else 'TRUE' )
    app.logger.info('DBMS             = ' + app_config.SQLALCHEMY_DATABASE_URI)

# index route, shows index.html view
@app.route('/')
def index():

    return render_template('index.html')
    

@app.route("/start_salesfc", methods=['GET'])
def start_salesfc(): #realm, site, future_preds, start_date):

    # NB request.args for GET, request.form for POST requests

    salesfc_job = { "env": request.args["env"], 
                    "realmId": request.args["realm"], 
                    "entityId": request.args["site"],     
                    "docker": 0,
                    "inf_start": request.args["start_date"],
                    "inf_end": (pd.to_datetime(request.args["start_date"], format="%Y-%m-%d") + timedelta(days=int(request.args["future_preds"]))).strftime('%Y-%m-%d'),
                    "settings": {"normalisation": False} # not needed for xgboost as underlying decision trees dont need scaled features, and target scaling aslo not required *check*
                }

    # *check* need to inject vals captured above to main.py (in same way as SQS job)
    batch = nsf_inf.main(job_override = salesfc_job, notifications = True)

    session["output"]=f"{str(batch['display_msg'])}" # NB session variable must be a string to render in html
    print("session[output] Output: ", session["output"]) 
    session["realm-site"]=salesfc_job["realmId"] + " - " + salesfc_job["entityId"]
    
    if isinstance(batch['display_msg'], pd.DataFrame): # i.e. a prediction dataframe (rather than an error msg) has been returned

        # *check* refactor below - may be too complicated
        forecast_df =  batch['display_msg']
        forecast_df['Actuals'] = batch['actuals'] # add actuals to df for comparison

        #session["fcast_sales"]=int(df.to_dict('list')['sales'][0]) # example forecasted revenue for 1st day of forecast for coststream 1
        session["fcast_sales"] = f'Total sales forecasted: ${round(forecast_df['Prediction'].sum())}'

        session["fcast_dates"] = [d for d in np.unique(forecast_df['Date'].dt.strftime('%d-%b')).tolist()]
        # OLD
        # session["fcast_dates"]= [x.strftime('%d-%b') for x in df.loc[df['stream_id'] == max(df['stream_id'])].to_dict('list')['time']] # example forecasted revenue list of vals for chart or use dummy example [-3, 15, 15, 35, 65, 40, 80, 25, 15, 85, 25, 75] 
        

        for i in forecast_df['stream_id'].unique():

            # *check* for now stream_id 1 only
            forecast_sales = forecast_df.loc[forecast_df['stream_id'] == i] [['Date', 'Prediction']]
            #filtered_actuals = forecast_df.loc[forecast_df['stream_id'] == i] [['Actuals']] # .loc[actuals['entity_stream'] == salesfc_job["entityId"] + '-' + i] [['sales']]

            session[f"fcast_vals_raw_{i}"]= [int(x) for x in forecast_sales.to_dict('list')['Prediction']] # example forecasted revenue list of vals for chart or use dummy example [-3, 15, 15, 35, 65, 40, 80, 25, 15, 85, 25, 75] 

        # finally filter actual sales only for the forecast time period and put values in a list for html/.js redendering
        # filtered_actuals = filtered_actuals[(filtered_actuals.index>=df.time.iloc[0]) & (filtered_actuals.index<=df.time.iloc[-1])]  
        session["actuals"]= forecast_df.groupby(by='Date').agg({'Actuals': 'sum'})['Actuals'].astype(int).tolist() # *check* - update [int(x) for x in filtered_actuals.to_dict('list')['sales']] 

    else:
        
        session["fcast_sales"] = f"{str(batch['display_msg'])}" # just display while run failed

    # finally get notifications (possibly move this to a seprate flask route)
    notifications = nof.getRecommendations()

    # *check* refactor, we shouldnt have to split out the dictionary here, should be possible in html/.js
    session["notification_1"]= list(notifications.values())[0]
    session["notification_2"]= list(notifications.values())[1]
    session["notification_3"]= list(notifications.values())[2]
    session["notification_4"]= list(notifications.values())[3]
    session["notification_5"]= list(notifications.values())[4]

    return render_template('pages/sample-page.html' ) 


@app.route("/start_streaming", methods=['GET'])
def start_streaming(): 

    print("streaming route started")
    # str_ex.main() # just stream
    subprocess.run(["python", "apps/streaming/cost-control-streaming.py"]) # *check* run in background

    return render_template('pages/streaming.html')


@app.route("/analytics", methods=['GET'])
def analytics(): 

    session["qs_url"]=qe.getDashboardURL()

    print("session[qs_url]: ", session["qs_url"])

    return render_template('pages/typography.html')


@app.route("/absence_analysis", methods=['GET'])
def absence_analysis(): 

    # get absences
    absences = ab.absences_analyis()

    # *check* refactor, we shouldnt have to split out the dictionary here, should be possible in html/.js
    for i in range(len(absences)):
        session[f'{[elem for elem in absences.keys()][i]}'] = [elem for elem in absences.values()][i].split()[0]
        session[f'{[elem for elem in absences.keys()][i]}_result'] = [elem for elem in absences.values()][i].split()[1]
    return render_template('pages/index.html')


@app.route("/refresh_job_status", methods=['GET'])
def refresh_job_status(): 

    # str_ex.main() # just stream
    import subprocess
    subprocess.run(["python", "apps/analytics/genai_rds_export.py"]) # *check* run in background

    return render_template('pages/typography.html')


@app.route("/gen_ai", methods=['GET'])
def gen_ai(): 

    # example questions:
    #target_qu = "What are the key anomalies we are seeing in the model training process ?"
    #target_qu = "What are the main errors we are seeing in the inference process ?"
    #"What are the key anomalies we are seeing in the model training process ?"
    # "can you tell me approximately how many training jobs failed within the last month with the train_size=None error and what percentage this is of all the training jobs in that period ?""

    target_qu = request.args["target_qu"]

    # custom responses from LLM (Anthropic) to the question posed in the last cell
    response = rag.retrieveAndGenerate(
        target_qu, kb_id
    )

    session["genai_resp"]= response["output"]["text"]

    print("session[genai]: ", session["genai_resp"])

    return render_template('pages/typography.html')

# chatbot UI invocation of bedrock - just call the RAG function
@app.route("/ask", methods=['GET', 'POST'])
def ask(): 

    # example questions:
    #target_qu = "What are the key anomalies we are seeing in the model training process ?"
    #target_qu = "What are the main errors we are seeing in the inference process ?"
    #"What are the key anomalies we are seeing in the model training process ?"
    # "can you tell me approximately how many training jobs failed within the last month with the train_size=None error and what percentage this is of all the training jobs in that period ?""

    # target_qu = request.args["target_qu"]
    target_qu = eval(request.data)['prompt']


    # basic model - custom responses from LLM (Anthropic) to the question posed in the last cell
    rag_result = rag.retrieveAndGenerate(
        target_qu, kb_id
    )

    print(rag_result["output"]["text"]) # debug

    # enhanced model - passes chunked vectors from KB to LLM for context-specific, sophisticted answer
    # rag_e_result = re.rag_enhanced(
    #     target_qu, kb_id
    # )

    # LangChain - recommended API for LLMs *check* but its not doing a good job and doesnt seem very context-specific
    # lc_result = lc.LangChain(
    #     target_qu, kb_id
    # )



    # session["genai_resp"]= response["output"]["text"]

    # print("session[genai]: ", session["genai_resp"])

    genai_response = {"success": True, "message": rag_result["output"]["text"]} # {"success": True, "message": lc_result}

    return genai_response


# chatbot UI invocation of OpenAI NL to SQL
@app.route("/askopenai", methods=['GET', 'POST'])
def askopenai(): 

    # BELOW QUESTIONS THAT SHOULD BE ANSWERABLE
    # *check* below needs to understand fail or failed
    
    # query = "Hello, how are you ?"
    # query = "How many inference jobs fail on 14th Jun 2024 ?"
    # query = "How many inference jobs failed this morning"
    # query = "What is the main anomaly in the data"
    # query = "What was the main anomaly in inference jobs today"
    # query = "What has been the main forecast error recently"

    # query = "What % of jobs succeeded versus failed in the last 7 days"
    # query = "What has been the trend in failed v. successful runs"

    # target_qu = request.args["target_qu"]
    target_qu = eval(request.data)['openaiprompt']

    # basic model - custom responses from LLM (Anthropic) to the question posed in the last cell
    openai_result = oai.main(target_qu)
    print(openai_result) # debug

    try:
        openai_final = openai_result.to_string(index=False)
    except:
        openai_final = openai_result


    genai_response = {"success": True, "message": openai_final} 

    return genai_response


# genai chatbot route, shows genai-chatbot.html view
@app.route('/genai-chatbot')
def genai_chatbot():
    return render_template('pages/genai-chatbot.html')

# data for charts
@app.route('/chart_salesfc', methods=["GET"])
def chart_salesfc():    
    return str(session["fcast_sales"]['sales'])
    # return render_template('index.html', output = f"{session["fcast_sales"]['sales']}")


if __name__ == "__main__":
    # Start the Flask web server    
    app.run(debug=True, port=5002)
