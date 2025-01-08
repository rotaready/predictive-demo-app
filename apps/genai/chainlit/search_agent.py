import time

import chainlit as cl

class SearchAgent():

    def __init__(self, assistant_id, client):

        self.assistant_id = assistant_id
        self.client = client

        # Create a thread

        self.thread = self.client.beta.threads.create()
        self.thread_id = self.thread.id

    async def persist_thread(self, user_prompt, **kwargs):    

        # Create a thread
        thread = self.client.beta.threads.create()

        # Add a user question to the thread
        message = self.client.beta.threads.messages.create(
        thread_id=self.thread_id,
        role="user",
        content=user_prompt
        )

        # Run the thread
        run = self.client.beta.threads.runs.create(
        thread_id=self.thread_id,
        assistant_id=self.assistant_id
        )


        # Looping until the run completes or fails
        while run.status in ['queued', 'in_progress', 'cancelling']:
            time.sleep(1)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=run.id
            )

        if run.status == 'completed':
            messages = self.client.beta.threads.messages.list(
                thread_id=self.thread.id
            )
            print(messages)

            # go thru the messages (reasoning process) in reverse order (minus the user prompt)
            for thread_message in reversed(messages.data[:-1]):
                # Iterate over the 'content' attribute of the ThreadMessage, which is a list
                for content_item in thread_message.content:
                    await cl.Message(content=content_item.text.value).send() # content=messages.data[0].content[1].text.value

        elif run.status == 'requires_action':
            # the assistant requires calling some functions
            # and submit the tool outputs back to the run
            pass
        else:
            print(run.status)

