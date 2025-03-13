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

print("OPENAI_API_KEY:", os.environ.get("OPENAI_API_KEY"))
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

db = SQLDatabase.from_uri(connectionString, include_tables=["vw_Maximo_Asset", "vw_Maximo_WorkOrders", "vw_Maximo_Locations"], view_support=True, schema="src")

print("Dialect:",db.dialect)
print("get_usable_table_names:",db.get_usable_table_names())

#print(db.run("SELECT TOP 10 * FROM [src].[vw_Maximo_Hazards];"))


from sqlalchemy import inspect

# Get the view names from the "src" schema
# inspector = inspect(db._engine)
# raw_views = inspector.get_view_names(schema="src")

# # Prepend the schema to each view name for full qualification
# views = [f"src.{view}" for view in raw_views]
# print("Fully qualified views in 'src' schema:", views)

context = db.get_context()
# print("context:", list(context))
# print("table_info:", context["table_info"])



from typing_extensions import TypedDict

class State(TypedDict):
     question: str
     query: str
     result: str
     answer: str

from langchain.chat_models import init_chat_model
llm = init_chat_model("gpt-4o-mini", model_provider="openai")


# agents

from langchain_community.agent_toolkits import SQLDatabaseToolkit
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()
tools

#print("tools:", tools)


#system prompt

from langchain import hub

prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")

assert len(prompt_template.messages) == 1
prompt_template.messages[0].pretty_print()

system_message = prompt_template.format(dialect="mssql", top_k=5)

# Append a reminder to fully qualify table names
system_message += "\n\nNote: All table and view names must be fully qualified with the schema prefix 'src.' in the SQL query."

# Append a note for the correct join condition
#system_message += "\n\nNote: When joining 'vw_Maximo_Locations' and 'vw_Maximo_WorkOrders', use 'vw_Maximo_Locations.location_code' to join with 'vw_Maximo_WorkOrders.location_id'."

system_message += "\n\nNote: When joining 'vw_Maximo_Locations' and 'vw_Maximo_WorkOrders', use 'vw_Maximo_Locations.location_description' to join with 'vw_Maximo_WorkOrders.location_description'."

system_message += "\n\nNote: When joining 'vw_Maximo_Asset' and 'vw_Maximo_WorkOrders', use 'vw_Maximo_Asset.assetnum' to join with 'vw_Maximo_WorkOrders.asset_id'."


#initialising the agent

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

agent_executor = create_react_agent(llm, tools, prompt=system_message)

# this works

#question = "How many Maximo WorkOrders were created in January 2025?"

#     query: SELECT COUNT(*) as WorkOrderCount FROM src.vw_Maximo_WorkOrders WHERE statusdate >= '2025-01-01' AND statusdate < '2025-02-01'
# ================================= Tool Message =================================
# Name: sql_db_query

# [(3319,)]
# ================================== Ai Message ==================================

# A total of **3,319 Maximo WorkOrders** were created in January 2025.

# this doesn't work
#question = "Which location has the most work orders?"

# Error: (pyodbc.ProgrammingError) ('42000', '[42000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Error converting data type varchar to bigint. (8114) (SQLExecDirectW)')
# [SQL: SELECT l.location_id, l.location_description, COUNT(w.wonum) AS work_order_count
# FROM src.vw_Maximo_Locations l
# JOIN src.vw_Maximo_WorkOrders w
# ON l.location_id = w.location_id
# GROUP BY l.location_id, l.location_description
# ORDER BY COUNT(w.wonum) DESC
# OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY;]

#this works
#question = "give 3 assets that have pipe in their description   ?"

#this works
#question = "what are the different status descriptions?"
# The different status descriptions in the database are:

# 1. Active
# 2. Approved
# 3. Assigned
# 4. Cancelled
# 5. Cancelled (Closed)
# 6. Closed
# 7. Completed
# 8. Decommissioned
# 9. Disposed
# 10. Field Complete
# 11. In progress
# 12. Inactive
# 13. Not Ready
# 14. On Hold
# 15. On Route
# 16. Operating
# 17. Scheduled
# 18. Waiting on approval
# 19. Waiting on material

# this works
# question = "what are the different work type descriptions?"

# The different work type descriptions are:

# 1. Capital Project
# 2. Corrective Maintenance
# 3. Customer Faults
# 4. Proactive Maintenance
# 5. Scheduled Preventive Maintenance


# this works
# question = "in 2024, how many work orders were Corrective Maintenance and how many were Proactive Maintenance and what was the ratio?"

#     query: SELECT workype_description, COUNT(*) AS work_order_count FROM src.vw_Maximo_WorkOrders WHERE YEAR(statusdate) = 2024 AND workype_description IN ('Corrective Maintenance', 'Proactive Maintenance') GROUP BY workype_description;
# ================================= Tool Message =================================
# Name: sql_db_query

# [('Corrective Maintenance', 7407), ('Proactive Maintenance', 4773)]
# ================================== Ai Message ==================================

# In 2024, there were:

# - 7,407 work orders for **Corrective Maintenance**.
# - 4,773 work orders for **Proactive Maintenance**.

# The ratio of Corrective Maintenance to Proactive Maintenance is approximately **1.55:1** (7,407 : 4,773).

#this works
#question = "for each of the past 3 years, what is the ratio of Corrective Maintenance workorders to  Proactive Maintenance work orders?"

#     query: SELECT YEAR(statusdate) AS Year,
#        SUM(CASE WHEN workype_description = 'Proactive Maintenance' THEN 1 ELSE 0 END) AS Proactive_Count,
#        SUM(CASE WHEN workype_description = 'Corrective Maintenance' THEN 1 ELSE 0 END) AS Corrective_Count,
#        SUM(CASE WHEN workype_description = 'Corrective Maintenance' THEN 1 ELSE 0 END) * 1.0 / NULLIF(SUM(CASE WHEN workype_description = 'Proactive Maintenance' THEN 1 ELSE 0 END), 0) AS Ratio
# FROM src.vw_Maximo_WorkOrders
# WHERE statusdate >= DATEADD(YEAR, -3, GETDATE())
# GROUP BY YEAR(statusdate)
# ORDER BY Year DESC;
# ================================= Tool Message =================================
# Name: sql_db_query

# [(2025, 2050, 1936, Decimal('0.944390243902')), (2024, 4773, 7407, Decimal('1.551854179761')), (2023, 434, 3950, Decimal('9.101382488479')), (2022, 424, 3215, Decimal('7.582547169811'))]
# ================================== Ai Message ==================================

# Here are the ratios of Corrective Maintenance work orders to Proactive Maintenance work orders for each of the past three years:

# - **2025**: Corrective: 1936, Proactive: 2050, Ratio: **0.94**
# - **2024**: Corrective: 7407, Proactive: 4773, Ratio: **1.55**
# - **2023**: Corrective: 3950, Proactive: 434, Ratio: **9.10**
# - **2022**: Corrective: 3215, Proactive: 424, Ratio: **7.58**

# this works
# question = "what are 10 examples of the values in workorders.location_id?"
#     query: SELECT DISTINCT location_id FROM src.vw_Maximo_WorkOrders ORDER BY location_id OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY;
# ================================= Tool Message =================================
# Name: sql_db_query

# [(None,), ('004.001',), ('004.002',), ('004.004',), ('004.007',)]
# ================================== Ai Message ==================================

# Here are 5 examples of values in the `location_id` from the `workorders` table:

# 1. `004.001`
# 2. `004.002`
# 3. `004.004`
# 4. `004.007`
# 5. `None`

# this works
# question = "what are 5 examples of the values in maximo_locations.location_id?"

#     query: SELECT TOP 5 location_id FROM src.vw_Maximo_Locations ORDER BY location_id
# ================================= Tool Message =================================
# Name: sql_db_query

# [(1,), (2,), (3,), (4,), (5,)]
# ================================== Ai Message ==================================

# Here are 5 examples of values in `maximo_locations.location_id`:

# 1. 1
# 2. 2
# 3. 3
# 4. 4
# 5. 5

# this works
#question = "what are 5 examples of the values in maximo_locations.location_code?"

#     query: SELECT TOP 5 location_code FROM src.vw_Maximo_Locations ORDER BY location_code
# ================================= Tool Message =================================
# Name: sql_db_query

# [('004.001',), ('004.002',), ('004.004',), ('004.007',), ('004.009',)]
# ================================== Ai Message ==================================

# Here are 5 examples of values in the `maximo_locations.location_code`:

# 1. 004.001
# 2. 004.002
# 3. 004.004
# 4. 004.007
# 5. 004.009

# this works
# question = "Which location has the most work orders?"

#     query: SELECT TOP 5 loc.location_code, COUNT(wo.wonum) AS work_order_count
# FROM src.vw_Maximo_Locations loc
# JOIN src.vw_Maximo_WorkOrders wo ON loc.location_code = wo.location_id
# GROUP BY loc.location_code
# ORDER BY work_order_count DESC;
# ================================= Tool Message =================================
# Name: sql_db_query

# [('04.07.30.02.01', 3910), ('04.18.09.03.01', 3217), ('04.07.31.02.02', 1658), ('007.018.006.007.002', 1643), ('04.17.12.02.01', 1213)]
# ================================== Ai Message ==================================

# The locations with the most work orders are as follows:

# 1. **Location Code:** 04.07.30.02.01 - **Work Orders:** 3910
# 2. **Location Code:** 04.18.09.03.01 - **Work Orders:** 3217
# 3. **Location Code:** 04.07.31.02.02 - **Work Orders:** 1658
# 4. **Location Code:** 007.018.006.007.002 - **Work Orders:** 1643
# 5. **Location Code:** 04.17.12.02.01 - **Work Orders:** 1213

# this works
# question = "Which location description has the most work orders?"
#   Args:
#     query: SELECT l.location_description, COUNT(w.wonum) AS work_order_count
# FROM src.vw_Maximo_WorkOrders w
# JOIN src.vw_Maximo_Locations l ON l.location_code = w.location_id
# GROUP BY l.location_description
# ORDER BY work_order_count DESC;

# The location description with the most work orders is **Hamilton Township**, which has a total of **3,910 work orders**.

# this works
# question = "what are 5 examples of the values in maximo_workorders.asset_id?"
#   Args:
#     query: SELECT TOP 5 asset_id FROM src.vw_Maximo_WorkOrders ORDER BY asset_id
# ================================= Tool Message =================================
# Name: sql_db_query

# [(None,), (None,), (None,), (None,), (None,)]
# ================================== Ai Message ==================================

# It appears that there are no values present for `asset_id` in the `vw_Maximo_WorkOrders` table as all entries returned are `None`. If you need assistance with something else or a different query, please let me know!

# this works
# question = "for each of the past 3 years, what has been the ratio of Corrective Maintenance work orders to Proactive Maintenance work orders at location code 04.07.30.02.01?"

#     query: WITH WorkOrderCounts AS (
#     SELECT
#         YEAR(statusdate) AS Year,
#         worktype_id,
#         COUNT(*) AS WorkOrderCount
#     FROM src.vw_Maximo_WorkOrders
#     WHERE location_id = '04.07.30.02.01' AND status_description IN ('Closed', 'Completed')
#     GROUP BY YEAR(statusdate), worktype_id
# )
# SELECT
#     Year,
#     SUM(CASE WHEN worktype_id = 'CM' THEN WorkOrderCount ELSE 0 END) AS CorrectiveMaintenance,
#     SUM(CASE WHEN worktype_id = 'PM' THEN WorkOrderCount ELSE 0 END) AS ProactiveMaintenance,
#     CASE WHEN SUM(CASE WHEN worktype_id = 'PM' THEN WorkOrderCount ELSE 0 END) = 0 THEN NULL
#          ELSE CAST(SUM(CASE WHEN worktype_id = 'CM' THEN WorkOrderCount ELSE 0 END) AS FLOAT) / SUM(CASE WHEN worktype_id = 'PM' THEN WorkOrderCount ELSE 0 END) END AS MaintenanceRatio
# FROM WorkOrderCounts
# GROUP BY Year
# ORDER BY Year;
# ================================= Tool Message =================================
# Name: sql_db_query

# [(2021, 58, 8, 7.25), (2022, 29, 7, 4.142857142857143), (2023, 52, 14, 3.7142857142857144), (2024, 229, 30, 7.633333333333334), (2025, 35, 3, 11.666666666666666)]
# ================================== Ai Message ==================================

# Here is the ratio of Corrective Maintenance work orders to Proactive Maintenance work orders at location code `04.07.30.02.01` for the past few years:

# | Year | Corrective Maintenance | Proactive Maintenance | Maintenance Ratio |
# |------|-----------------------|-----------------------|--------------------|
# | 2021 | 58                    | 8                     | 7.25               |
# | 2022 | 29                    | 7                     | 4.14               |
# | 2023 | 52                    | 14                    | 3.71               |
# | 2024 | 229                   | 30                    | 7.63               |
# | 2025 | 35                    | 3                     | 11.67              |

#question = "what are 5 examples of the values in maximo_assets.assetnum with the associated asset_description, location_code, location_id and location_desc?"

#this works
#question = "Which location has the most work orders?"

#     query: SELECT TOP 5 l.location_description, COUNT(w.wonum) AS work_order_count
# FROM src.vw_Maximo_Locations l
# JOIN src.vw_Maximo_WorkOrders w ON l.location_description = w.location_description
# GROUP BY l.location_description
# ORDER BY work_order_count DESC;
# ================================= Tool Message =================================
# Name: sql_db_query

# [('Hamilton Township', 3916), ('Portland Township', 3220), ('Hamilton - Digby Rd SPS Catchment', 1658), ('Warrnambool WRP', 1643), ('Port Fairy Township', 1215)]
# ================================== Ai Message ==================================

# The locations with the most work orders are:

# 1. **Hamilton Township** - 3916 work orders
# 2. **Portland Township** - 3220 work orders
# 3. **Hamilton - Digby Rd SPS Catchment** - 1658 work orders
# 4. **Warrnambool WRP** - 1643 work orders
# 5. **Port Fairy Township** - 1215 work orders

# this works
#question = "Which asset has the most work orders?"

#     query: SELECT TOP 5 a.assetnum, a.asset_description, COUNT(w.wonum) AS work_order_count
# FROM src.vw_Maximo_Asset a
# JOIN src.vw_Maximo_WorkOrders w ON a.assetnum = w.asset_id
# GROUP BY a.assetnum, a.asset_description
# ORDER BY work_order_count DESC;
# ================================= Tool Message =================================
# Name: sql_db_query

# [('23230', 'Corporate - Warrnambool Depot', 451), ('23257', 'Warrnambool - Pertobe Rd SPS', 424), ('23254', 'Warrnambool - Morriss Rd SPS', 368), ('23242', 'Warrnambool - Dickson St SPS', 350), ('107024', 'Corporate - Portland Depot - Wyatt St (at Storage)', 315)]
# ================================== Ai Message ==================================

# The asset with the most work orders is **Corporate - Warrnambool Depot** with a total of **451** work orders. Here are the top five assets with the most work orders:

# 1. **Asset Number:** 23230 - **Asset Description:** Corporate - Warrnambool Depot - **Work Orders:** 451
# 2. **Asset Number:** 23257 - **Asset Description:** Warrnambool - Pertobe Rd SPS - **Work Orders:** 424
# 3. **Asset Number:** 23254 - **Asset Description:** Warrnambool - Morriss Rd SPS - **Work Orders:** 368
# 4. **Asset Number:** 23242 - **Asset Description:** Warrnambool - Dickson St SPS - **Work Orders:** 350
# 5. **Asset Number:** 107024 - **Asset Description:** Corporate - Portland Depot - Wyatt St (at Storage) - **Work Orders:** 315
# P

# this works
# question = "for Asset Number: 23257, please provide a breakdown of the number of workorders for 2022, 2023 and 2024?"

#   Args:
#     query: SELECT YEAR(statusdate) AS WorkOrderYear, COUNT(wonum) AS WorkOrderCount
# FROM src.vw_Maximo_WorkOrders
# WHERE asset_id = '23257' AND YEAR(statusdate) IN (2022, 2023, 2024)
# GROUP BY YEAR(statusdate)
# ================================= Tool Message =================================
# Name: sql_db_query

# [(2022, 79), (2023, 88), (2024, 154)]
# ================================== Ai Message ==================================

# The breakdown of work orders for Asset Number 23257 is as follows:

# - **2022**: 79 work orders
# - **2023**: 88 work orders
# - **2024**: 154 work orders


# this works
# question = "Please provide the top 5 highest ranking assets outside of Warrnambool and not a depot in terms of number of workorders generated for 2024, returning the asset number and asset description?"

#     query: SELECT a.assetnum, a.asset_description, COUNT(w.wonum) AS workorder_count
# FROM src.vw_Maximo_Asset a
# JOIN src.vw_Maximo_WorkOrders w ON a.assetnum = w.asset_id
# JOIN src.vw_Maximo_Locations l ON w.location_description = l.location_description
# WHERE l.location_description NOT LIKE '%Warrnambool%'
# AND l.locationclassification_desc NOT LIKE '%Depot%'
# AND YEAR(w.reportdate) = 2024
# GROUP BY a.assetnum, a.asset_description
# ORDER BY workorder_count DESC
# OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY;
# ================================= Tool Message =================================
# Name: sql_db_query

# [('92142', 'Konongwootong Reservoir - Raw Water Storage (Emergency)', 66), ('22948', 'South Otway - Plantation Rd Reservoir - Raw Water Storage', 58), ('92592', 'Grampians - Cruckoor Reservoir - Raw Water Storage', 53), ('22767', 'Camperdown - Park Lane Service Basin - Potable Water Storage', 52), ('344570', 'Casterton - Arundel Rd Basin Square - Storage - Floating Cover', 52)]
# ================================== Ai Message ==================================

# The top 5 highest-ranking assets outside of Warrnambool and not classified as a depot, based on the number of work orders generated for 2024, are:

# 1. **Asset Number**: 92142
#    **Asset Description**: Konongwootong Reservoir - Raw Water Storage (Emergency)
#    **Work Orders**: 66

# 2. **Asset Number**: 22948
#    **Asset Description**: South Otway - Plantation Rd Reservoir - Raw Water Storage
#    **Work Orders**: 58

# 3. **Asset Number**: 92592
#    **Asset Description**: Grampians - Cruckoor Reservoir - Raw Water Storage
#    **Work Orders**: 53

# 4. **Asset Number**: 22767
#    **Asset Description**: Camperdown - Park Lane Service Basin - Potable Water Storage
#    **Work Orders**: 52

# 5. **Asset Number**: 344570
#    **Asset Description**: Casterton - Arundel Rd Basin Square - Storage - Floating Cover
#    **Work Orders**: 52

# this works
# question = "if you add the number of work orders for January 2022, January 2023 and January 2024, and call this the January Total, and repeat this for the other 11 months, which month is highest and which month is lowest?"

#     query: SELECT MONTH(statusdate) AS Month, COUNT(*) AS WorkOrderCount
# FROM src.vw_Maximo_WorkOrders
# WHERE YEAR(statusdate) IN (2022, 2023, 2024)
# GROUP BY MONTH(statusdate)
# ================================= Tool Message =================================
# Name: sql_db_query

# [(1, 4596), (2, 3498), (3, 3642), (4, 1596), (5, 8311), (6, 4101), (7, 5015), (8, 5319), (9, 4057), (10, 4055), (11, 5779), (12, 4869)]
# ================================== Ai Message ==================================

# The work order counts for each month from January to December for the years 2022, 2023, and 2024 are as follows:

# - January: 4596
# - February: 3498
# - March: 3642
# - April: 1596
# - May: 8311
# - June: 4101
# - July: 5015
# - August: 5319
# - September: 4057
# - October: 4055
# - November: 5779
# - December: 4869

# From this data, **May** has the highest total with **8311** work orders, while **April** has the lowest total with **1596** work orders.


for step in agent_executor.stream(
    {"messages": [{"role": "user", "content": question}]},
    stream_mode="values",
):
    step["messages"][-1].pretty_print()



# from langchain import hub

# query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")

# assert len(query_prompt_template.messages) == 1
# query_prompt_template.messages[0].pretty_print()

# from typing_extensions import Annotated

# class QueryOutput(TypedDict):
#     """Generated SQL query."""

#     query: Annotated[str, ..., "Syntactically valid SQL query."]


# def write_query(state: State):
#     """Generate SQL query to fetch information."""
#     prompt = query_prompt_template.invoke(
#         {
#             "dialect": db.dialect,
#             "top_k": 10,
#             "table_info": views,
#             "input": state["question"],
#         }
#     )
#     structured_llm = llm.with_structured_output(QueryOutput)
#     result = structured_llm.invoke(prompt)
#     return {"query": result["query"]}



# print("Maximo Locations query:", write_query({"question": "How many Maximo Locations are there?"}))


# from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool


# def execute_query(state: State):
#     """Execute SQL query."""
#     execute_query_tool = QuerySQLDatabaseTool(db=db)
#     return {"result": execute_query_tool.invoke(state["query"])}



# print("Maximo Locations count:", execute_query({"query": "SELECT COUNT(location_id) AS LocationCount FROM src.vw_Maximo_Locations;"}))


# def generate_answer(state: State):
#     """Answer question using retrieved information as context."""
#     prompt = (
#         "Given the following user question, corresponding SQL query, "
#         "and SQL result, answer the user question.\n\n"
#         f'Question: {state["question"]}\n'
#         f'SQL Query: {state["query"]}\n'
#         f'SQL Result: {state["result"]}'
#     )
#     response = llm.invoke(prompt)
#     return {"answer": response.content}


# from langgraph.graph import START, StateGraph

# graph_builder = StateGraph(State).add_sequence(
#     [write_query, execute_query, generate_answer]
# )
# graph_builder.add_edge(START, "write_query")
# graph = graph_builder.compile()

# for step in graph.stream(
#     {"question": "How many Maximo Locations are there?"}, stream_mode="updates"
# ):
#     print(step)

# # this one works
# # for step in graph.stream(
# #     {"question": "How many Maximo WorkOrders are there?"}, stream_mode="updates"
# # ):
# #     print(step)

    
# # this one fails due to incorrest column name
# # for step in graph.stream(
# #     {"question": "How many Maximo WorkOrders are there for January 2025?"}, stream_mode="updates"
# # ):
# #     print(step)
    

# # dialect specific prompting

# from langchain.chains.sql_database.prompt import SQL_PROMPTS

# list(SQL_PROMPTS)

# print("SQL_PROMPTS:", list(SQL_PROMPTS))


# from langchain.chains import create_sql_query_chain

# chain = create_sql_query_chain(llm, db)
# chain.get_prompts()[0].pretty_print()

# # table definitions and example rows

# context = db.get_context()
# print("context:", list(context))
# print("table_info:", context["table_info"])


# #print("view_info:", context["view_info"])


# # need to get the views

# from sqlalchemy import inspect

# # Create an inspector from the engine
# inspector = inspect(db._engine)

# # Get view names from a specific schema, for example "src"
# raw_views = inspector.get_view_names(schema="src")

# # Optionally, prepend the schema for fully qualified names
# views = [f"src.{view}" for view in raw_views]
# print("Fully qualified views in 'src' schema:", views)


# # man in the middle processing

# #from langgraph.checkpoint.memory import MemorySaver

# # this works

# # def main():
# #     # Initialize memory persistence
# #     memory = MemorySaver()
    
# #     # Compile the graph with a checkpointer that uses memory persistence,
# #     # and set the interrupt point before "execute_query"
# #     graph = graph_builder.compile(checkpointer=memory, interrupt_before=["execute_query"])
    
# #     # Specify a thread ID in the configuration to allow resuming later
# #     config = {"configurable": {"thread_id": "1"}}
    
# #     # Stream the initial query asking for the number of employees
# #     for step in graph.stream(
# #         {"question": "How many employees are there?"},
# #         config,
# #         stream_mode="updates",
# #     ):
# #         print(step)
    
# #     # Ask for user approval to continue
# #     try:
# #         user_approval = input("Do you want to go to execute query? (yes/no): ")
# #     except Exception:
# #         user_approval = "no"
    
# #     if user_approval.lower() == "yes":
# #         # If approved, continue graph execution
# #         for step in graph.stream(None, config, stream_mode="updates"):
# #             print(step)
# #     else:
# #         print("Operation cancelled by user.")

# # if __name__ == '__main__':
# #     main()

