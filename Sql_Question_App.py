from flask import Flask, render_template, request, jsonify
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from langchain import hub
import os
import ast
import calendar
import re
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
db = SQLDatabase.from_uri(
    connectionString,
    include_tables=["vw_Maximo_Asset", "vw_Maximo_WorkOrders", "vw_Maximo_Locations"],
    view_support=True,
    schema="src"
)

# Setup LangChain agent
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
system_message = prompt_template.format(dialect="mssql", top_k=5)
system_message += "\n\nNote: All table and view names must be fully qualified with the schema prefix 'src.' in the SQL query."
system_message += "\n\nNote: When joining 'vw_Maximo_Locations' and 'vw_Maximo_WorkOrders', use 'vw_Maximo_Locations.location_description' to join with 'vw_Maximo_WorkOrders.location_description'."
system_message += "\n\nNote: When joining 'vw_Maximo_Asset' and 'vw_Maximo_WorkOrders', use 'vw_Maximo_Asset.assetnum' to join with 'vw_Maximo_WorkOrders.asset_id'."

agent_executor = create_react_agent(llm, tools, prompt=system_message)

def generate_dynamic_visualization_data(steps, visualize):
    """
    Dynamically parse the agent's output to create chart data.
    1. If 'visualize' is False, return None.
    2. Otherwise, iterate over each step:
       - If the content is a Python literal list of tuples, parse it.
       - Otherwise, if it contains bullet-point text with '###' headings and month bullets,
         parse that text.
    3. Return the first successfully parsed data or None if nothing could be parsed.
    """
    if not visualize:
        return None

    for step in steps:
        content = step.get('content', '').strip()

        # 1) Try parsing as Python literal data, e.g. [(1344, 6, 2023), (951, 7, 2023), ...]
        if content.startswith('[') and content.endswith(']'):
            chart_data = _parse_python_list_literal(content)
            if chart_data is not None:
                return chart_data

        # 2) Otherwise, try parsing the bullet-point text format
        if '###' in content:
            chart_data = _parse_bullet_point_text(content)
            if chart_data is not None and len(chart_data['labels']) > 0:
                return chart_data

    return None

def _parse_python_list_literal(content):
    """
    Parse a Python list literal of tuples, where each tuple is (value, month, year).
    Returns a dict { 'labels': [...], 'values': [...] } or None on failure.
    """
    try:
        data = ast.literal_eval(content)
        if isinstance(data, list) and all(isinstance(item, tuple) and len(item) == 3 for item in data):
            labels = []
            values = []
            for (val, month, year) in data:
                month_name = calendar.month_name[month]
                labels.append(f"{month_name} {year}")
                values.append(val)
            return {"labels": labels, "values": values}
    except Exception:
        return None
    return None

def _parse_bullet_point_text(content):
    """
    Parse bullet-point text with a year heading and month-value bullets.
    For example:
      ### 2024
      - **January**: 1160
      - **February**: 1382
      - **March**: 1509
      - **April**: 1228
    Returns a dict { 'labels': [...], 'values': [...] }.
    """
    lines = content.split('\n')
    current_year = None
    labels = []
    values = []

    # Regex to match a year heading, e.g. "### 2024"
    year_pattern = re.compile(r'^###\s+(\d{4})$')
    # Regex to match a bullet line, e.g. "- **January**: 1160"
    month_pattern = re.compile(r'^-\s\*\*(\w+)\*\*:\s(\d+)')

    for line in lines:
        line = line.strip()
        match_year = year_pattern.match(line)
        if match_year:
            current_year = match_year.group(1)
            continue

        match_month = month_pattern.match(line)
        if match_month and current_year:
            month_name = match_month.group(1)
            value = int(match_month.group(2))
            labels.append(f"{month_name} {current_year}")
            values.append(value)
    
    return {"labels": labels, "values": values}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    question = request.json.get('question', '')
    visualize_flag = request.json.get('visualize', False)
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

    # Generate dynamic visualization data from the response steps
    visualization_data = generate_dynamic_visualization_data(response_steps, visualize_flag)

    return jsonify({
        "steps": response_steps,
        "final_answer": final_answer,
        "visualizationData": visualization_data
    })

if __name__ == '__main__':
    app.run(debug=True)
