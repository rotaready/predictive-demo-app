# References:
# 
# https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/file-search?tabs=python
# https://learn.microsoft.com/en-us/azure/ai-services/openai/assistants-reference?tabs=python
# https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/assistant
# https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/code-interpreter?tabs=python
# 

import os

import chainlit as cl

import mysql.connector
from sql_scripts import costcontrol as cc
from sql_scripts import rota_shift as ro

import pandas as pd

from openai import AzureOpenAI



async def main(REALM: str):
    
  # PART I first create data file as Assistant's Knwoledge Base
  await cl.Message(content=f"STEP 1 connecting to RDS...").send()

  conn = mysql.connector.connect(
    host=os.environ['UAT_RDS_CLONE_HOST'],
    user=os.environ['UAT_RDS_CLONE_USER'],
    password=os.environ['UAT_RDS_CLONE_PASSWORD'],
    database=f"rr_{REALM}"
  )

  await cl.Message(content=f"STEP 2 running cost control query...").send()
  df_cc = pd.read_sql_query(cc.SQL_SCRIPT, con=conn) # params= (REALM,), dropped for now as more reliable to connect to client DB than rr_core

  await cl.Message(content=f"STEP 3 running rota shift query...").send()
  df_ro = pd.read_sql_query(ro.SQL_SCRIPT, con=conn) # params= (REALM,), dropped for now as more reliable to connect to client DB than rr_core

  # export for pickup when creating Assistant
  df_cc.to_csv(f'cost_control_{REALM}.csv', index = False)
  df_ro.to_csv(f'rota_shift_{REALM}.csv', index = False)
  # df.to_csv(f'cost_control_{REALM}.txt', index = False)
  # df.to_json(f'cost_control_{REALM}.json', orient='split')

  # PART II setup AzureOpenAI client

  AZURE_OPENAI_ENDPOINT = "https://hospitalityopenai.openai.azure.com/"

  client = AzureOpenAI(
    azure_endpoint = AZURE_OPENAI_ENDPOINT,
    api_key= os.getenv("ACC_AZURE_OPENAI_KEY"),
    api_version="2024-05-01-preview"
  )

  
  # PART III enable file search
  await cl.Message(content=f"STEP 4 Creating Azure OpenAI Assistant...").send()

  assistant = client.beta.assistants.create(
    name = f"{REALM}_agent",   
    model="Rotaready", # model deployment name.
    instructions="You are a multi-modal AI with access to revenue / cost and labour (clock in/out) data as shown in the contents of the attached files. \
                  Please review the contents of these files before answering and use these as your knowledge base to best respond to user queries. \
                  Format your responses in markdown, and if the user has requested or implied they want a chart or visual in their request, please make use of the coolest, latest python visualisation libraries.",
    tools=[{"type":"code_interpreter"}], # file_search
    temperature=0.01,
    top_p=0.3 
  )

  # PART IV upload files to vector store for file search
  # *check* create Azure vector store (embeddings) for Assistant
  # then connect the code interpreter to the vector storage as opposed to the raw file
  # see e.g. https://farzzy.hashnode.dev/azure-ai-search-integrating-vectorization-and-openai-embeddings-for-csv-files

  # await cl.Message(content=f"STEP 3 Creating vector store and uploading knowledge base...").send()
  # # Create a vector store
  # vector_store = client.beta.vector_stores.create(name=f"rr_{REALM}")
  
  await cl.Message(content=f"STEP 5 Attaching knowledge base...").send()

  cc_file = client.files.create(
    file=open(f"cost_control_{REALM}.csv", "rb"),
    purpose="assistants"
  )

  ro_file = client.files.create(
    file=open(f"rota_shift_{REALM}.csv", "rb"),
    purpose="assistants"
  )

  # Use the upload and poll SDK helper to upload the files, add them to the vector store,
  # and poll the status of the file batch for completion.
  # file_batch = client.beta.vector_stores.file_batches.create(
  #   vector_store_id=vector_store.id, file_ids=[kb_file.id],
  # )

  # print the status and the file counts of the batch to see the result of this operation.
  # print(file_batch.status)
  # print(file_batch.file_counts)

  # update the assistant to use the new vector store
  assistant = client.beta.assistants.update(
  assistant_id=assistant.id,
  # tool_resources={"file_search": {"vector_store_ids": [vector_store.id]},
  #                 "code_interpreter": {"file_ids": [kb_file.id]}}
  tool_resources={"code_interpreter": {"file_ids": [cc_file.id, ro_file.id]}}
)

  

  return assistant.id, f'successfully created agent: {assistant.id} for realm: {REALM}'
