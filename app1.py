from dotenv import load_dotenv, find_dotenv
from langchain.sql_database import SQLDatabase
from langchain.llms import OpenAI


from langchain.chains.sql_database.sql_database_chain import SQLDatabaseChain


import os

# Load production environment variables
envFile = find_dotenv(".env.prod")
load_dotenv(envFile)

azServer = os.getenv("AZSERVER")
azDatabase = os.getenv("AZDATABASE")
sqlUser = os.getenv("AZSQLUSER")
sqlPass = os.getenv("AZSQLPASS")

connectionString = (
    f"mssql+pyodbc://{sqlUser}:{sqlPass}@{azServer}/{azDatabase}?driver=ODBC+Driver+17+for+SQL+Server"
)

# Initialize the SQLDatabase from the official LangChain package
db = SQLDatabase.from_uri(connectionString)
print("Sample query output:")
print(db.run("SELECT TOP 10 * FROM [src].[vw_Maximo_Hazards];"))

# Setup the LLM (make sure your OPENAI_API_KEY is set in the environment)
llm = OpenAI(temperature=0)

# Create the SQLDatabaseChain with verbose logging for debugging
db_chain = SQLDatabaseChain(llm=llm, database=db, verbose=True)

# Use natural language to query your SQL view
query = "Show me all active hazards from the view [src].[vw_Maximo_Hazards] where the status is 'active'."
result = db_chain.run(query)

print("Natural language query result:")
print(result)
