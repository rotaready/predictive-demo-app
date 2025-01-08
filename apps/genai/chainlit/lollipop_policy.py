import os

from openai import AzureOpenAI

def main(prompt: str):

  '''function calls the OpenAI API to determine the type of question asked by the user\
    a) a greeting or small talk, 
    b) a sports or general knowledge, chat-gpt type question
    or 
    c) a question related to data, forecasting, models, training, inference, labour demand, clients, sites etc.'''

  


  # *check* OpenAI how to add examples to help provide better responses (few-shot training)
  lollipop_policy = [
      {
        "role": "system",
        "content": """"Determine whether a user's question is:

        a) a request to create a new AI agent or assistant, or clone (yourself)
        b) a greeting or small talk
        c) a question about your function or purpose
        d) a sports or general knowledge, chat-gpt type question like:

        - who was JFK ?
        - who is the likely to win the world cup ?

        e) a request to search or searching an existing agent
        or 
        f) a question related to forecasting, models, training, inference, labour demand, clients, sites, data e.g.

        - summarise the forecasts for me
        - what job errors are you seeing ?
        - what are the top 5 anomalies for client X

        For a) reply with 'create_agent' and if a specific client or realm name from this list:
        'guestline', 'shr', 'avvio', 'shr search', 'avvio search', 'dishoom', 'brownsofbrockley', 
        'maray', 'camino','brewdog','namco','signaturepubs', 'thehotelfolk','itison','warnerleisure',
        'roseacre','preto','pizzapilgrims','nq64','temper','spaceandthyme','bonnieandwild','housecafes',
        'mcmanuspubs','gusto' is mentioned, then add to the reply 'for client:' followed by the client name, 
        for b) reply with 'greeting', 
        for c) reply with 'my function',
        for d) reply with 'general knowledge',
        for e) reply with 'search',
        and for 
        f) just reply with 'data' only, NOT 'data.'."""
      },
      {
        "role": "user",
        "content": prompt
      },

    ]

  AZURE_OPENAI_ENDPOINT = "https://hospitalityopenai.openai.azure.com/"
  client = AzureOpenAI(
    api_key=os.getenv("ACC_AZURE_OPENAI_KEY"), 
    api_version="2024-02-01",
    azure_endpoint = AZURE_OPENAI_ENDPOINT
    )

  deployment_name='Rotaready' #This will correspond to the custom name you chose for your deployment when you deployed a model. Use a gpt-35-turbo-instruct deployment. 
      
  response = client.chat.completions.create(model=deployment_name, messages=lollipop_policy, temperature=0.01, max_tokens=50)

  return(response.choices[0].message.content)                                                                                   
