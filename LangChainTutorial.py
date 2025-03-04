import getpass
import os

import openai

from dotenv import load_dotenv, find_dotenv

from langchain.sql_database import SQLDatabase


env_path = find_dotenv(".env.prod")
if not env_path:
    print("Could not locate .env.prod file.")
else:
    print(f".env.prod file found at: {env_path}")

load_dotenv(env_path)

print(os.environ.get("OPENAI_API_KEY"))
print(os.environ.get("LANGSMITH_API_KEY"))
print(os.environ.get("LANGSMITH_TRACING"))
print(os.environ.get("LANGSMITH_ENDPOINT"))
print(os.environ.get("LANGSMITH_PROJECT"))


azServer = os.getenv("AZSERVER")
azDatabase = os.getenv("AZDATABASE")
sqlUser = os.getenv("AZSQLUSER")
sqlPass = os.getenv("AZSQLPASS")

connectionString = (
    f"mssql+pyodbc://{sqlUser}:{sqlPass}@{azServer}/{azDatabase}?driver=ODBC+Driver+17+for+SQL+Server"
)



from langchain_community.utilities import SQLDatabase

#db = SQLDatabase.from_uri("sqlite:///Chinook.db")

db = SQLDatabase.from_uri(connectionString,None)

print(db.dialect)
print(db.get_usable_table_names())

print(db.run("SELECT TOP 10 * FROM [src].[vw_Maximo_Hazards];"))

#db.run("SELECT * FROM Artist LIMIT 10;")

from sqlalchemy import inspect

# Get the view names from the "src" schema
inspector = inspect(db._engine)
raw_views = inspector.get_view_names(schema="src")

# Prepend the schema to each view name for full qualification
views = [f"src.{view}" for view in raw_views]
print("Fully qualified views in 'src' schema:", views)



from typing_extensions import TypedDict


class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str

from langchain.chat_models import init_chat_model
llm = init_chat_model("gpt-4o-mini", model_provider="openai")


from langchain import hub

query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")

assert len(query_prompt_template.messages) == 1
query_prompt_template.messages[0].pretty_print()


from typing_extensions import Annotated


class QueryOutput(TypedDict):
    """Generated SQL query."""

    query: Annotated[str, ..., "Syntactically valid SQL query."]


def write_query(state: State):
    """Generate SQL query to fetch information."""
    prompt = query_prompt_template.invoke(
        {
            "dialect": db.dialect,
            "top_k": 10,
            "table_info": views,
            "input": state["question"],
        }
    )
    structured_llm = llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt)
    return {"query": result["query"]}



print("Maximo Locations query:", write_query({"question": "How many Maximo Locations are there?"})
)


from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool


def execute_query(state: State):
    """Execute SQL query."""
    execute_query_tool = QuerySQLDatabaseTool(db=db)
    return {"result": execute_query_tool.invoke(state["query"])}




print("Maximo Locations count:", execute_query({"query": "SELECT COUNT(location_id) AS LocationCount FROM src.vw_Maximo_Locations;"}))


def generate_answer(state: State):
    """Answer question using retrieved information as context."""
    prompt = (
        "Given the following user question, corresponding SQL query, "
        "and SQL result, answer the user question.\n\n"
        f'Question: {state["question"]}\n'
        f'SQL Query: {state["query"]}\n'
        f'SQL Result: {state["result"]}'
    )
    response = llm.invoke(prompt)
    return {"answer": response.content}


from langgraph.graph import START, StateGraph

graph_builder = StateGraph(State).add_sequence(
    [write_query, execute_query, generate_answer]
)
graph_builder.add_edge(START, "write_query")
graph = graph_builder.compile()

for step in graph.stream(
    {"question": "How many Maximo Locations are there?"}, stream_mode="updates"
):
    print(step)

for step in graph.stream(
    {"question": "How many Maximo WorkOrders are there?"}, stream_mode="updates"
):
    print(step)