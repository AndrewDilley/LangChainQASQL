from flask import Flask, render_template, request, jsonify
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from langchain import hub
import os
from dotenv import load_dotenv

load_dotenv(".env.prod")

app = Flask(__name__)

# Database connection setup
azServer = os.getenv("AZSERVER")
azDatabase = os.getenv("AZDATABASE")
sqlUser = os.getenv("AZSQLUSER")
sqlPass = os.getenv("AZSQLPASS")
connectionString = f"mssql+pyodbc://{sqlUser}:{sqlPass}@{azServer}/{azDatabase}?driver=ODBC+Driver+17+for+SQL+Server"

# LangChain and Database initialization
llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
db = SQLDatabase.from_uri(connectionString, include_tables=["vw_Maximo_Asset", "vw_Maximo_WorkOrders", "vw_Maximo_Locations"], view_support=True, schema="src")

# Setup LangChain agent
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
system_message = prompt_template.format(dialect="mssql", top_k=5)
system_message += "\n\nNote: All table and view names must be fully qualified with the schema prefix 'src.' in the SQL query."
system_message += "\n\nNote: When joining 'vw_Maximo_Locations' and 'vw_Maximo_WorkOrders', use 'vw_Maximo_Locations.location_description' to join with 'vw_Maximo_WorkOrders.location_description'."
system_message += "\n\nNote: When joining 'vw_Maximo_Asset' and 'vw_Maximo_WorkOrders', use 'vw_Maximo_Asset.assetnum' to join with 'vw_Maximo_WorkOrders.asset_id'."

agent_executor = create_react_agent(llm, tools, prompt=system_message)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    question = request.json.get('question', '')
    response_steps = []
    final_answer = ""

    for step in agent_executor.stream(
        {"messages": [{"role": "user", "content": question}]},
        stream_mode="values",
    ):
        message = step["messages"][-1]
        response_steps.append({
            'type': 'AI Message' if 'AiMessage' in str(type(message)) else 'Tool Message',
            'content': message.content
        })

    final_answer = response_steps[-1]['content'] if response_steps else "No answer generated."
    return jsonify({"steps": response_steps, "final_answer": final_answer})

if __name__ == '__main__':
    app.run(debug=True)
