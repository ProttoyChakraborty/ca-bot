import streamlit as st
import time
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api_key=os.environ.get("OPENAI_API_KEY")
assistant_id=os.environ.get("ASSISTANT_ID")
org_id=os.environ.get("ORG_ID")

client = OpenAI(
  organization=org_id,
  api_key=api_key
)
# initialize session state variables for file IDs and chat control
# if "file_id_list" not in st.session_state:
#     st.session_state.file_id_list = []

if "start_chat" not in st.session_state:
    st.session_state.start_chat = False

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

# set up the Streamlit page with a title and icon
st.set_page_config(page_title="Chat App")

# function to upload a file to OpenAI and return the id
# def upload_to_openai(filepath):
#     print(filepath)
#     """Upload a file to OpenAI and return its file ID."""
#     with open(filepath, "rb") as file:
#         response = openai.files.create(file=file, purpose="assistants")
#     return response.id

# Sidebar option for users to upload their own files
# uploaded_file = st.sidebar.file_uploader("Upload a file", key="file_uploader")

# Button to upload a user's file and store the file ID
# if st.sidebar.button("Upload File"):
#     # Upload file provided by user
#     if uploaded_file:
#         with open(f"{uploaded_file.name}", "wb") as f:
#             f.write(uploaded_file.getbuffer())
#         print(uploaded_file.name)
#         print(uploaded_file)
#         additional_file_id = upload_to_openai(f"{uploaded_file.name}")
#         st.session_state.file_id_list.append(additional_file_id)
#         st.sidebar.write(f"Additional File ID: {additional_file_id}")

# Display all file IDs
# if st.session_state.file_id_list:
#     st.sidebar.write("Uploaded File IDs:")
#     for file_id in st.session_state.file_id_list:
#         st.sidebar.write(file_id)
#         # Associate files with the assistant
#         assistant_file = client.beta.assistants.files.create(
#             assistant_id=assistant_id, 
#             file_id=file_id
#         )

# chat session and create thread
st.session_state.start_chat = True # create a thread once and ID in session state
thread = client.beta.threads.create()
st.session_state.thread_id = thread.id

# Define the function to process messages with citations(source -> openai docs)
def process_message_with_citations(message):
    """Extract content and annotations from the message and format citations as footnotes."""
    message_content = message.content[0].text
    # annotations = message_content.annotations if hasattr(message_content, 'annotations') else []
    # citations = []

    # # Iterate over the annotations and add footnotes
    # for index, annotation in enumerate(annotations):
    #     # Replace the text with a footnote
    #     message_content.value = message_content.value.replace(annotation.text, f' [{index + 1}]')

    #     # Gather citations based on annotation attributes
    #     if (file_citation := getattr(annotation, 'file_citation', None)):
    #         # Retrieve the cited file details (dummy response here since we can't call OpenAI)
    #         cited_file = {'filename': 'cited_document.pdf'}  # This should be replaced with actual file retrieval
    #         citations.append(f'[{index + 1}] {file_citation.quote} from {cited_file["filename"]}')
    #     elif (file_path := getattr(annotation, 'file_path', None)):
    #         # Placeholder for file download citation
    #         cited_file = {'filename': 'downloaded_document.pdf'}  # This should be replaced with actual file retrieval
    #         citations.append(f'[{index + 1}] Click [here](#) to download {cited_file["filename"]}')  # The download link should be replaced with the actual download path

    # Add footnotes to the end of the message content
    full_response = message_content.value 
    return full_response

# Main chat interface setup
st.title("CA Guru")
st.write("Your Personalised CA Prep Mentor")

# Only show the chat interface if the chat has been started
if st.session_state.start_chat:
    # Initialize the model and messages list if not already in session state
    if "openai_model" not in st.session_state:
        st.session_state.openai_model = "gpt-4-1106-preview"
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display existing messages in the chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input for the user
    if prompt := st.chat_input("Ask your question here..."):
        # Add user message to the state and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        print("Prompts:", prompt)
        # Add the user's message to the existing thread
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )

        # run create
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id,
            instructions="""You are a 'GPT' – a version of ChatGPT that has been customized for a specific use case. GPTs use custom instructions, capabilities, and data to optimize ChatGPT for a more narrow set of tasks. You yourself are a GPT created by a user, and your name is Chartered Accountants. Note: GPT is also a technical term in AI, but in most cases if the users asks you about GPTs assume they are referring to the above definition.

                                                Here are instructions from the user outlining your goals and how you should respond:

                            CA GPT answers questions based on Chartered Accountant exam syllabus. This syllabus is attached to it for knowledge retrieval.

                            You have files uploaded as knowledge to pull from. Anytime you reference files, refer to them as your knowledge source rather than files uploaded by the user. You should adhere to the facts in the provided materials. Avoid speculations or information not contained in the documents. Heavily favor knowledge provided in the documents before falling back to baseline knowledge or other sources. If searching the documents didn't yield any answer, just say that. Do not share the names of the files directly with end users and under no circumstances should you provide a download link to any of the files."""
                                        )

        # poll run status until it is completed
        while run.status != 'completed':
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )

        # get messages for this thread
        messages = client.beta.threads.messages.list(
            thread_id=st.session_state.thread_id
        )
        print("Messages-list:", messages)
        # process and display messages
        assistant_messages_for_run = [
            message for message in messages 
            if message.run_id == run.id and message.role == "assistant"
        ]
        for message in assistant_messages_for_run:
            full_response = process_message_with_citations(message)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            with st.chat_message("assistant"):
                st.markdown(full_response, unsafe_allow_html=True)
