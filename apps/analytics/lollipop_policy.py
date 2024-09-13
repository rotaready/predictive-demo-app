import os

import urllib.request, json

# from openai import OpenAI
from openai import AzureOpenAI

def main(prompt: str):

  '''function calls the OpenAI API to determine the type of question asked by the user\
    a) a greeting or small talk, 
    b) a sports or general knowledge, chat-gpt type question
    or 
    c) a question related to data, forecasting, models, training, inference, labour demand, clients, sites etc.'''

  # openai_client = OpenAI(api_key=os.getenv('CE_OPENAI_API_KEY'))

  # examples:
  # prompt = "hello"
  # prompt = "whats going on with this data"
  # prompt = "how many forecast runs were there yesterday"
  # prompt = "Yo!"
  # prompt = "hey hows it going"


  # *check* OpenAI how to add examples to help provide better responses (few-shot training)
  lollipop_policy = [
      {
        "role": "system",
        "content": """"Determine whether a user's question is:
        a) a greeting or small talk 
        b) a sports or general knowledge, chat-gpt type question like:

        - who was JFK ?
        - who is the likely to win the world cup ?

        or 
        c) a question related to forecasting, models, training, inference, labour demand, clients, sites, data e.g.

        - summarise the forecasts for me
        - what job errors are you seeing ?
        - what are the top 5 anomalies for client X

        If a) or b) reply with an appropriate conversational response and please don't state the classification of the question itself). 
        If c) just reply with 'data' only, NOT 'data.'"""
      },
      {
        "role": "user",
        "content": prompt
      },

      # {
      #   "role": "user",
      #   "content": "Hello! How are you today?"
      # },
      # {
      #   "role": "assistant",
      #   "content": "convo"
      # },
      # {
      #   "role": "user",
      #   "content": "How many failed forecast runs were there yesterday ?"
      # },
      # {
      #   "role": "assistant",
      #   "content": "data"
      # },
    ]

  # below replaced with Access Azure OpenAI Completions API (Contoso)
  # response = openai_client.chat.completions.create(
  #   model="gpt-3.5-turbo",
  #   messages=lollipop_policy,                                                                                                                                            
  #   temperature=0.5,
  #   max_tokens=64,
  #   top_p=1
  # )


  AZURE_OPENAI_ENDPOINT = "https://hospitalityopenai.openai.azure.com/"
  client = AzureOpenAI(
    api_key=os.getenv("ACC_AZURE_OPENAI_KEY"), 
    api_version="2024-02-01",
    azure_endpoint = AZURE_OPENAI_ENDPOINT
    )

  # NB deployment model correspods to correspond to the custom name you chose for your deployment when you deployed a model. This value can be found under Resource Management > Model Deployments in the Azure portal or alternatively under Management > Deployments in Azure OpenAI Studio.
  # see https://learn.microsoft.com/en-gb/azure/ai-services/openai/quickstart?pivots=programming-language-python&tabs=command-line%2Cpython-new
  deployment_name='RotareadyGPT35' #This will correspond to the custom name you chose for your deployment when you deployed a model. Use a gpt-35-turbo-instruct deployment. 
      
  # Send a completion call to generate an answer
  # NB MUST USE client.chat.completions.create NOT client.completions.create
  response = client.chat.completions.create(model=deployment_name, messages=lollipop_policy, max_tokens=50)

  return(response.choices[0].message.content)
  


  
  # print(response.choices[0].message.content)                                                                                        
