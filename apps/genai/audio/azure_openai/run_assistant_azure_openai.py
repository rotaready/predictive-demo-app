import os
import json
import requests
import time
from openai import AzureOpenAI

from IPython.display import Image, display

AZURE_OPENAI_ENDPOINT = "https://hospitalityopenai.openai.azure.com/"

class Assistant():
    
    def __init__(self):

      self.client = AzureOpenAI(
        azure_endpoint = AZURE_OPENAI_ENDPOINT,
        api_key= os.getenv("ACC_AZURE_OPENAI_KEY"),
        api_version="2024-02-15-preview"
      )

      self.assistant_id = os.getenv('ACC_AZURE_OPENAI_AST_CC_RS')

    def create_new_thread(self):

      # Create a thread
      self.thread = self.client.beta.threads.create()

    def delete_thread(self):

      response = client.beta.threads.delete(self.thread.id)
      print(response)


    def add_message_to_thread(self, input: str):

      # Add a user question to the thread
      self.messages = self.client.beta.threads.messages.create(
        thread_id=self.thread.id,
        role="user",
        content=input # Replace this with your prompt
      )


    def delete_messages_in_thread(self):

      # Create a thread
      deleted_message = client.beta.threads.messages.delete(
        message_id=self.messages.id,
        thread_id=self.thread.id,
      )
      print(deleted_message)

      

    def run_thread(self):

      # Run the thread
      run = self.client.beta.threads.runs.create(
        thread_id=self.thread.id,
        assistant_id=self.assistant_id,
        instructions="Please stick to the overarching instructions given when creating the assistant and consider the historical context of the conversation when responding."
      )

      retrieval_count = 0
      # Looping until the run completes or fails
      while run.status in ['queued', 'in_progress', 'cancelling']:
        time.sleep(1)
        retrieval_count += 1
        run = self.client.beta.threads.runs.retrieve(
          thread_id=self.thread.id,
          run_id=run.id
        )
        if retrieval_count%10 == 0: # display a message every 10th retrieval
                print(f"Generating output: {run.status }")

      if run.status == 'completed':
        # NB self.messages are the thought process from the Asstant - dont confuse with user messages
        # *check* may want to rename user messages variable as prompts above
        self.messages = self.client.beta.threads.messages.list(
          thread_id=self.thread.id
        )
        # print(self.messages) # debug

        if self.messages.data[0].content[0].type == "text":
            print(f"Assistant: {self.messages.data[0].content[0].text.value}") 
            return f"Assistant: {self.messages.data[0].content[0].text.value}"
            
        else: # assumed image, but also display the Assistant message
            print(f"Assistant: {self.messages.data[0].content[1].text.value}") # NB content[1] is the Assistant's text message suporting the image
            image_file_id = self.messages.data[0].content[0].image_file.file_id
            image_file = self.client.files.content(image_file_id)
            with open("ai_image_response.png", "wb") as f:
                    f.write(image_file.content)
            
            # display image
            display(Image(filename='ai_image_response.png', width=600))
            # image = Image.open('ai_image_response.png')
            # image.show()   
            print("Have a look at this and let me know if you have any questions.")   
            return "Have a look at this and let me know if you have any questions."

      elif run.status == 'requires_action':
        # the assistant requires calling some functions
        # and submit the tool outputs back to the run
        pass
      else:
        print(run.status)

  
# debug

# go = Assistant()

# go.create_new_thread()

# qu = "using the data uploaded, could you please plot revenue and net costs monthly"
# go.add_message_to_thread(qu)

# go.run_thread()
