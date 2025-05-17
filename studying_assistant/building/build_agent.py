import re
import os
import warnings
from dotenv import load_dotenv

warnings.simplefilter("ignore")

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS 
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.tools import DuckDuckGoSearchRun
from langchain.agents import Tool
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain import PromptTemplate
from langchain.utilities import SerpAPIWrapper
from langchain.agents import AgentExecutor, OpenAIFunctionsAgent, create_react_agent
from typing import Callable
from hydra.utils import instantiate
import hydra
from omegaconf import DictConfig, OmegaConf
from studying_assistant.building.obsidian_db import create_vector_db


def build_agent(cfg: DictConfig):
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    serp_api_key = os.getenv("SERPAPI_API_KEY")


    embeddings = GoogleGenerativeAIEmbeddings(
        model=cfg.llm.embedding_model,
        google_api_key=google_api_key
    )

    db_path = "obsidian_db"

    if os.path.exists(db_path) and os.path.isdir(db_path):
        db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
        print("FAISS database loaded.")
    else:
        create_vector_db(cfg)
        db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)

    llm = ChatGoogleGenerativeAI(model=cfg.llm.model, google_api_key=google_api_key)

    notes_prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
                You are a helpful assistant that uses the user's personal notes and online search to answer questions about data science, ML, and current topics.
                Use the following context to answer the question at the end.
                If you don't know the answer, just say that you don't know.

                Context:
                {context}

                Question:
                {question}

                Answer:""")

    retriever = db.as_retriever()
    obsidian = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": notes_prompt}
    )

    note_tool = Tool(
        name="PersonalNotesQA",
        func=obsidian.run,
        description="Use this to answer questions based on user's personal study notes"
    )

    search_tool = SerpAPIWrapper(serpapi_api_key=serp_api_key)
    web_tool = Tool(
        name="WebSearch",
        func=search_tool.run,
        description="Use this to search for up-to-date information including current prices, news, or any real-time data. Always use this when asked about current information that might not be in the notes."
    )

    react_template = """Answer the following questions as best you can. You have access to the following tools:

    {tools}

    You can use the write_note tool to save information as a markdown file. 
    Input format: 'filename: <name>, content: <your note>'. 
    The note will be saved to the ../ISLP directory.
    The notes should follow the same style as my notes that you can access from PersonalNotesQA tool.
    You can also use WebSearch tool to validate you notes.
    Add this token at the end of the notes <endofnotes>

    Previous conversation:
    {chat_history}

    Use the following format:

    Question: the input question you must answer
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Action Input/Observation can repeat N times)
    Thought: I now know the final answer
    Final Answer: the final answer to the original input question

    Begin!

    Question: {input}
    Thought:{agent_scratchpad}"""

    agent_prompt = PromptTemplate(
        template=react_template,
        input_variables=["tools", "tool_names", "input", "agent_scratchpad", "chat_history"]
    )

    def write_to_markdown(note_input: str, base_dir: str = fr"C:\Users\Youssef Atef\Desktop\{cfg.vault.name}") -> str:
        """
        note_input format: "filename: <filename>, content: <note content>"
        """
        try:
            match = re.search(r'filename:\s*(.*?),\s*content:\s*(.*)', note_input, re.DOTALL)
            filename = match.group(1).strip().replace('_', ' ')
            content = match.group(2).strip()
            content = content.replace("<endofnotes>", "")
            
            if not content:
                return "No content provided."

            content = content.encode("utf-8").decode("unicode_escape")
            os.makedirs(base_dir, exist_ok=True)

            if not filename.endswith(".md"):
                filename += ".md"

            filepath = os.path.join(base_dir, f"{filename}")
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(content + "\n\n")

            return f"Note saved as {filepath}"

        except Exception as e:
            return f"Failed to write note: {e}"

    write_note_tool = Tool(
        name="write_note",
        func=write_to_markdown,
        description="Use this tool to write notes or save information to a markdown file. Input should be the content of the note."
    )

    tools = [web_tool, note_tool, write_note_tool]
    agent = create_react_agent(llm, tools, agent_prompt)
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, handle_parsing_errors=True, memory=memory
    )

    return agent_executor

if __name__ == "__main__":
    @hydra.main(config_path="conf", config_name="config")
    def main(cfg: DictConfig):
        print(OmegaConf.to_yaml(cfg))
        build_agent(cfg)
    
    main()