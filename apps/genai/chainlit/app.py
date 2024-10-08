import os
from io import BytesIO
from pathlib import Path

import json

import base64
import boto3

from typing import List

from openai import AsyncAssistantEventHandler, AsyncAzureOpenAI, AzureOpenAI
from openai import AsyncOpenAI # still needed for speech to text as whisper model unsupported in uk_south *check*

from literalai.helper import utc_now

from chainlit.cli import run_chainlit
import chainlit as cl
from chainlit.config import config
from chainlit.element import Element

import lollipop_policy as lp
import create_assistant as cr_agent

    


import random

AZURE_OPENAI_ENDPOINT = "https://hospitalityopenai.openai.azure.com/"

async_openai_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT, 
        api_key=os.getenv("ACC_AZURE_OPENAI_KEY"),
        api_version="2024-05-01-preview"
)

sync_openai_client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=os.getenv("ACC_AZURE_OPENAI_KEY"),
        api_version="2024-05-01-preview"
)


# whisper model speech to text unsupported in Europe, so using my credits again bah *check*
whisper_client = AsyncOpenAI(api_key=os.environ.get("CE_OPENAI_API_KEY"))

class EventHandler(AsyncAssistantEventHandler):

    def __init__(self, assistant_name: str) -> None:
        super().__init__()
        self.current_message: cl.Message = None
        self.current_step: cl.Step = None
        self.current_tool_call = None
        self.assistant_name = assistant_name

    async def on_text_created(self, text) -> None:
        self.current_message = await cl.Message(author=self.assistant_name, content="").send()

    async def on_text_delta(self, delta, snapshot):
        await self.current_message.stream_token(delta.value)

    async def on_text_done(self, text):
        await self.current_message.update()

    async def on_tool_call_created(self, tool_call):
        self.current_tool_call = tool_call.id
        self.current_step = cl.Step(name=tool_call.type, type="tool")
        self.current_step.language = "python"
        self.current_step.created_at = utc_now()
        await self.current_step.send()

    async def on_tool_call_delta(self, delta, snapshot): 
        if snapshot.id != self.current_tool_call:
            self.current_tool_call = snapshot.id
            self.current_step = cl.Step(name=delta.type, type="tool")
            self.current_step.language = "python"
            self.current_step.start = utc_now()
            await self.current_step.send()  
                 
        if delta.type == "code_interpreter":
            if delta.code_interpreter.outputs:
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        error_step = cl.Step(
                            name=delta.type,
                            type="tool"
                        )
                        error_step.is_error = True
                        error_step.output = output.logs
                        error_step.language = "markdown"
                        error_step.start = self.current_step.start
                        error_step.end = utc_now()
                        await error_step.send()
            else:
                if delta.code_interpreter.input:
                    await self.current_step.stream_token(delta.code_interpreter.input)


    async def on_tool_call_done(self, tool_call):
        self.current_step.end = utc_now()
        await self.current_step.update()

    async def on_image_file_done(self, image_file):
        image_id = image_file.file_id
        response = await async_openai_client.files.with_raw_response.content(image_id)
        image_element = cl.Image(
            name=image_id,
            content=response.content,
            display="inline",
            size="large"
        )
        if not self.current_message.elements:
            self.current_message.elements = []
        self.current_message.elements.append(image_element)
        await self.current_message.update()


@cl.step(type="tool")
async def speech_to_text(audio_file):
    response = await whisper_client.audio.transcriptions.create(
        model="whisper-1", file=audio_file
    )

    return response.text


async def upload_files(files: List[Element]):
    file_ids = []
    for file in files:
        uploaded_file = await async_openai_client.files.create(
            file=Path(file.path), purpose="assistants"
        )
        file_ids.append(uploaded_file.id)
    return file_ids


async def process_files(files: List[Element]):
    # Upload files if any and get file_ids
    file_ids = []
    if len(files) > 0:
        file_ids = await upload_files(files)

    return [
        {
            "file_id": file_id,
            "tools": [{"type": "code_interpreter"}],
        }
        for file_id in file_ids
    ]


@cl.on_chat_start
async def start_chat():

    # initial (orchestrator) assistant setup
    cl.user_session.set("assistant_id", os.getenv("ACC_AZURE_OAI_AST_ORCHESTRATOR"))

    # Create a Thread
    thread = await async_openai_client.beta.threads.create()
    # Store thread ID in user session for later use
    cl.user_session.set("thread_id", thread.id)
    # await cl.Avatar(name=assistant.name, path="./public/logo.png").send()
    # await cl.Message(content=f"Hello, I'm {assistant.name}!", disable_feedback=True).send()
    await cl.Message(content=f"Hello, fire away!").send()
    

@cl.on_message
async def main(message: cl.Message):

    # data_context_qu = ['forecasting', 'models', 'training', 'inference', 'labour demand', 'clients', 'sites', 'data', 'revenue', 'cost', 'rota', 'plot', 'chart', 'graph', 'calculate']
    
    check_lollipop = lp.main(cl.chat_context.to_openai()[-1]['content']) # determnine if about creating an agent, a data related question or something else

    client_context = ['client', 'realm']
    client_list = ['dishoom', 'brownsofbrockley' , 'maray', 'camino','brewdog','namco','signaturepubs',
        'thehotelfolk','itison','warnerleisure','roseacre','preto','pizzapilgrims','nq64',
        'temper','spaceandthyme','bonnieandwild','housecafes','mcmanuspubs','gusto']
    
    # *check* logic below
    if 'create_agent' in check_lollipop: # assumed agent related question

        if any(word in check_lollipop for word in client_context):
            await cl.Message(content=f"Bear with me while we create an agent...").send()
            CURRENT_ASSISTANT_ID, text_answer = await cr_agent.main(next(s for s in client_list if s in check_lollipop.lower())) # create a new agent for client in list mentioned in user question
            await cl.Message(content=text_answer).send()
            cl.user_session.set("changed_assistant", True)
            cl.user_session.set("assistant_id", CURRENT_ASSISTANT_ID)
            assistant = sync_openai_client.beta.assistants.retrieve(CURRENT_ASSISTANT_ID)
            # Create a new thread (as looks like a thread cannot be shared across multiple assistants)
            
            thread = await async_openai_client.beta.threads.create(tool_resources={
                                                                        "code_interpreter": {"file_ids": assistant.tool_resources.code_interpreter.file_ids}},
                                                                       )
            # Store thread ID in user session for later use
            cl.user_session.set("thread_id", thread.id)
        else:
            text_answer = "please could you clarify the client or realm name for the new agent"

    # only do data routine below (to retrieve an existing assistant) if user is still on orchestator
    if check_lollipop == 'data' and cl.user_session.get("assistant_id") == os.getenv("ACC_AZURE_OAI_AST_ORCHESTRATOR"): # assumed data related question *check* that non-image or data qus are answered earlier in the process as this part isnt invoked
    # if not elements and any(word in user_input for word in data_context_qu): # assumed data related question *check* that non-image or data qus are answered earlier in the process as this part isnt invoked
        
        # first check if a specific client was mentioned, check it against the existing agent names
        # and switch the agent id to that assistant/agent
        # *check* inefficient probably - refactor
        if any(word in cl.chat_context.to_openai()[-1]['content'] for word in client_list):
            client_mention = next(s for s in client_list if s in cl.chat_context.to_openai()[-1]['content'].lower())
        # loop back thru assistants from last one created
        for assistant_counter in range(len(sync_openai_client.beta.assistants.list().data)):
            # next assistant
            next_assistant = sync_openai_client.beta.assistants.list().data[assistant_counter].name
            # if client appears in next assistant name, switch to that assistant
            if next_assistant is not None and client_mention in next_assistant.lower():
                cl.user_session.set("changed_assistant", True)
                cl.user_session.set("assistant_id", sync_openai_client.beta.assistants.list().data[assistant_counter].id)
                assistant = sync_openai_client.beta.assistants.retrieve(cl.user_session.get("assistant_id"))
                await cl.Message(content=f'switched to {client_mention} agent: {cl.user_session.get("assistant_id")}').send()
                # Create a new thread (as looks like a thread cannot be shared across multiple assistants)
                thread = await async_openai_client.beta.threads.create(tool_resources={
                                                                        "code_interpreter": {"file_ids": assistant.tool_resources.code_interpreter.file_ids}},
                                                                       )
                # Store thread ID in user session for later use
                cl.user_session.set("thread_id", thread.id)
                break
        if not cl.user_session.get("changed_assistant"): # client mentioned in client_list not found in existing agents, so ask the user if you would like to create a new one
            await cl.Message(content=f"The client's AI assistant doesnt exist yet, would you like me to create one ?").send()

    # else: # al other qus (non-data or data question on new/existing agent)

    # only one assistant change allowed for now *check*
    # changed assistant could be a newly created one or an existing one that has been retrieved
    # if cl.user_session.get("changed_assistant"):

    #     # config.ui.name = assistant.name

    #     # Create a new thread if a new assistant
    #     thread = await async_openai_client.beta.threads.create()
    #     # Store thread ID in user session for later use
    #     cl.user_session.set("thread_id", thread.id)
    #     cl.user_session.set("changed_assistant", False) # set back to False, as we are supporting one change in assistant for now

    # msg = cl.Message(author="You", content=user_input, elements=elements)
    # await main(message=msg)

    # provide a default answer for text2speech
    # placeholder_responses = ["could you take a look at the above and let me know what you think",
    #                          "does this answer your question ?",
    #                          "check out above and let me know what you think",
    #                          "let me know if this helps",
    #                          "the response above hopefully provides some direction and guidance, but feel free to ask more questions",
    #                          "is this what you were looking for ?"]
    # text_answer = random.choice(placeholder_responses) 

    

    # attachments = await process_files(message.elements)

    thread_id = cl.user_session.get("thread_id")

    # Add a Message to the Thread
    
    # i = 1
    # # get the last user message *check* this will ignore any assistant updates in middle of conversation
    # while cl.chat_context.to_openai()[-i]['role'] != 'user':
    #     i+=1
    await async_openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=cl.chat_context.to_openai()[-1]['content'],
        # attachments=attachments,
    )
    
    assistant = sync_openai_client.beta.assistants.retrieve(cl.user_session.get("assistant_id"))
    assistant_name = assistant.name # *check* refactor

    # Create and Stream a Run
    async with async_openai_client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=cl.user_session.get("assistant_id"),
        event_handler=EventHandler(assistant_name=assistant_name),
        instructions="Please stick to the overarching instructions given when the assistant was created and consider the historical context of the conversation when responding. \
        If the assistant was created with uploaded files, please review their contents before answering and use them as your knowledge base.",
        tools=[{"type":"code_interpreter"}]
    ) as stream:
        await stream.until_done()

    


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    


@cl.step(type="tool")
async def generate_text_answer(transcription, images):
    if images:
        # Only process the first 3 images
        images = images[:3]

        images_content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image.mime};base64,{encode_image(image.path)}"
                },
            }
            for image in images
        ]

        model = "Rotaready"
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": transcription}, *images_content],
            }
        ]
    else:
        model = 'RotareadyGPT35' # "gpt-3.5-turbo"
        messages = [{"role": "user", "content": transcription}]

    response = await async_openai_client.chat.completions.create(
        messages=messages, model=model, temperature=0.3
    )
    

    return response.choices[0].message.content


@cl.step(type="tool")
async def text_to_speech(text: str, mime_type: str):

    polly_client = boto3.Session(
                aws_access_key_id=os.environ['AWS_ACCESS_KEY'],                     
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name='eu-west-1').client('polly')

    response = polly_client.synthesize_speech(VoiceId='Aria',
                OutputFormat='mp3', 
                Text = text,
                Engine = 'neural')

    file = open('speech.mp3', 'wb')
    file.write(response['AudioStream'].read())
    file.close()

    os.system("open speech.mp3 &")


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.AudioChunk):
    if chunk.isStart:
        buffer = BytesIO()
        # This is required for whisper to recognize the file type
        buffer.name = f"input_audio.{chunk.mimeType.split('/')[1]}"
        # Initialize the session for a new audio stream
        cl.user_session.set("audio_buffer", buffer)
        cl.user_session.set("audio_mime_type", chunk.mimeType)

    # Write the chunks to a buffer and transcribe the whole audio at the end
    cl.user_session.get("audio_buffer").write(chunk.data)


@cl.on_audio_end
async def on_audio_end(elements: list[Element]):
    # Get the audio buffer from the session
    audio_buffer: BytesIO = cl.user_session.get("audio_buffer")
    audio_buffer.seek(0)  # Move the file pointer to the beginning
    audio_file = audio_buffer.read()
    audio_mime_type: str = cl.user_session.get("audio_mime_type")

    input_audio_el = cl.Audio(
        mime=audio_mime_type, content=audio_file, name=audio_buffer.name
    )
    await cl.Message(
        author="You",
        type="user_message",
        content="",
        elements=[input_audio_el, *elements],
    ).send()

    whisper_input = (audio_buffer.name, audio_file, audio_mime_type)
    transcription = await speech_to_text(whisper_input)


    data_context_qu = ['forecasting', 'models', 'training', 'inference', 'labour demand', 'clients', 'sites', 'data', 'revenue', 'cost', 'rota', 'plot', 'chart', 'graph', 'calculate']

    if not elements and any(word in transcription for word in data_context_qu): # assumed data related question *check* that non-image or data qus are answered earlier in the process as this part isnt invoked
        
        msg = cl.Message(author="You", content=transcription, elements=elements)
        await main(message=transcription)

        # provide a default answer for text2speech
        placeholder_responses = ["could you take a look at the above and let me know what you think",
                                 "does this answer your question ?"
                                 "check out above and let me know what you think",
                                 "let me know if this helps",
                                 "the response above hopefully provides some direction and guidance, but feel free to ask more questions",
                                 "is this what you were looking for ?"]
        text_answer = random.choice(placeholder_responses) 


    else: # image-related question

        images = [file for file in elements if "image" in file.mime]

        text_answer = await generate_text_answer(transcription, images)
        # await generate_text_answer(transcription, images)

    await text_to_speech(text_answer, audio_mime_type)



if __name__ == "__main__":
    run_chainlit(__file__) # opens a web broswer with the chainlit chat UI and calls @cl.on_chat_start
