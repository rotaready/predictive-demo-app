import time

import chainlit as cl

class AssistantDirect():

    def __init__(self, assistant_id, client):

        self.assistant_id = assistant_id
        self.client = client

        # Create a thread

        self.thread = self.client.beta.threads.create()
        self.thread_id = self.thread.id

    async def persist_thread(self, user_prompt, **kwargs):    

        self.thread_id = kwargs.get('thread_id', self.thread_id)
        # Add a user question to the thread
        self.client.beta.threads.messages.create(
        thread_id=self.thread_id,
        role="user",
        content=user_prompt
        )

        # Run the thread
        run = self.client.beta.threads.runs.create(
        thread_id=self.thread_id,
        assistant_id=self.assistant_id
        )

        if kwargs.get('thread_id', None) is not None: # keep user updated if this is a persistent thread
            await cl.Message(content=f"In progress... \U0001F375").send()

        retrieval_count = 0
        # Looping until the run completes or fails
        while run.status in ['queued', 'in_progress', 'cancelling']:

            time.sleep(1)
            retrieval_count += 1

            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id,
                run_id=run.id
            )

            if retrieval_count%10 == 0: # display a message every 10th retrieval
                    await cl.Message(content="Computing... \U0001F3C3").send()

        if run.status == 'completed':
            messages = self.client.beta.threads.messages.list(
                thread_id=self.thread_id
            )
            # print(messages) # debug


            messages = self.client.beta.threads.messages.list(thread_id=self.thread_id)

            # go thru the messages (reasoning process) in reverse order (minus the user prompt)
            for thread_message in reversed(messages.data[:-1]):
                # Iterate over the 'content' attribute of the ThreadMessage, which is a list
                for content_item in thread_message.content:
                    # Assuming content_item is a MessageContentText object with a 'text' attribute
                    # and that 'text' has a 'value' attribute, print it
                    # print(content_item.text.value)
                    try: # text output
                        if kwargs.get('thread_id', None) is None: # only provide text response if first user interaction
                            await cl.Message(content=content_item.text.value).send() # content=messages.data[0].content[1].text.value
                    except: # image output
                        image_id = content_item.image_file.file_id
                        image_element = cl.Image(
                                            name=image_id,
                                            content=self.client.files.with_raw_response.content(image_id).content,
                                            display="inline",
                                            size="large"
                                        )
                        await cl.Message(
                            content='',
                            elements=[image_element]
                        ).send()

            # finally display the last text message only if this is a persistent thread
            # if kwargs.get('thread_id', None) is not None:
            #     await cl.Message(content=messages.data[0].content[0].text.value).send() 

        elif run.status == 'requires_action':
            # the assistant requires calling some functions
            # and submit the tool outputs back to the run
            pass
        else:
            print(run.status)
