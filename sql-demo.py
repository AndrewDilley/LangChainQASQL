from dotenv import load_dotenv,find_dotenv
from langchain.sql_database import SQLDatabase

import os

envFile = find_dotenv(".env.prod")
load_dotenv(envFile)

azServer = os.getenv("AZSERVER")
azDatabase = os.getenv("AZDATABASE")
sqlUser = os.getenv("AZSQLUSER")
sqlPass = os.getenv("AZSQLPASS")

connectionString = (
    f"mssql+pyodbc://{sqlUser}:{sqlPass}@{azServer}/{azDatabase}?driver=ODBC+Driver+17+for+SQL+Server"
)

db = SQLDatabase.from_uri(connectionString,None)

print(db.run("SELECT TOP 10 * FROM [src].[vw_Maximo_Hazards];"))