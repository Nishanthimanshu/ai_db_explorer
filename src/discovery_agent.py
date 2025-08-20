import json
import logging
import networkx as nx
from config import Config
from langchain.tools import Tool
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DiscoveryAgent:
    def __init__(self):
        self.config = Config()
        self.toolkit = SQLDatabaseToolkit(db=self.config.db_engine, llm=self.config.llm)
        self.tools = self.toolkit.get_tools()

        self.tools.extend(
            [
                Tool(
                    name = "VISUALISE_SCHEMA",
                func = self.discover,
                description = "Create a visual graph representation of the database schema showing tables, columns, and their relationships."
                )
            ]
        )

        self.chat_prompt = self.create_chat_prompt()
        self.agent = create_openai_functions_agent(
            llm = self.config.llm,
            prompt = self.chat_prompt,
            tools = self.tools,
        )

        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent = self.agent,
            tools = self.tools,
            verbose = True,
            handle_parsing_errors = True,
            max_iterations = 3,
        )

    def run_query(self, query):
        return self.config.db_engine.run(query)

    def create_chat_prompt(self):
         # Create the system message template for generating SQL responses
        system_message = SystemMessagePromptTemplate.from_template(
            """
            You are an AI assistant for querying a SQLLite database named {db_name}.
            Your responses should be formatted as json only.
            Always strive for clarity, terseness and conciseness in your responses.
            Return a json array with all the tables, using the example below:

            Example output:
            ```json
            [
                {{
                    tableName: [NAME OF TABLE RETURNED],
                    columns: [
                        {{
                            "columnName": [COLUMN 1 NAME],
                            "columnType": [COLUMN 1 TYPE],
                            "isOptional": [true OR false],
                            "foreignKeyReference": {{
                                "table": [REFERENCE TABLE NAME],
                                "column": [REFERENCE COLUMN NAME]
                            }}
                        }},
                        {{
                            "columnName": [COLUMN 2 NAME],
                            "columnType": [COLUMN 2 TYPE],
                            "isOptional": [true OR false],
                            "foreignKeyReference": {{
                                "table": [REFERENCE TABLE NAME],
                                "column": [REFERENCE COLUMN NAME]
                            }}
                        }}
                    ]
                }}
            ]
            ```

            ## mandatory
            only output json
            do not put any extra commentary
            """
        )

        # Define the human message template
        human_message = HumanMessagePromptTemplate.from_template("{input}\n\n{agent_scratchpad}")

        # Combine the system and human templates into a chat prompt
        return ChatPromptTemplate.from_messages([system_message, human_message])
    
    def discover(self) -> nx.Graph:
        """Perform schema discovery and return a graph representation."""
        logger.info("Performing discovery...")
        prompt = "For all tables in this database, show the table name, column name, column type, if its optional. Also show Foreign key references to other columns. Do not show examples. Output only as json."

        # Invoke the agent executor with the discovery prompt
        response = self.agent_executor.invoke({"input": prompt, "db_name": self.config.db})

        # Convert the JSON response into a graph representation
        graph = self.jsonToGraph(response)
        return graph

    def jsonToGraph(self, response):
        """Parse the JSON response, construct and return a graph representation."""
        output = response['output']
        return self.parseJson(output)

    def parseJson(self, output):
        """Parse the JSON response and return a graph representation."""
        response = output[output.find('\n')+1:output.rfind('\n')]
        data = json.loads(response)

        graph = nx.Graph() # Initialize an empty graph
        nodeIds = 0 # Track table nodes
        columnIds = len(data)+1 # Track column nodes
        labeldict = {} # Dictionary to store node labels for visualization
        canonicalColumns = {} # Map table-column pairs to column node Ids

        #Add tables and columns as nodes in the graph
        for table in data:
            nodeIds +=1 
            graph.add_node(nodeIds )
            graph.nodes[nodeIds]['tableName'] = table['tableName']
            labeldict[nodeIds] = table['tableName']

            # Add tables and columns as nodes in the graph
            for column in table['columns']:
                columnIds +=1 
                graph.add_node(columnIds)
                graph.nodes[columnIds]['columnName'] = column['columnName']
                graph.nodes[columnIds]['columnType'] = column['columnType']
                graph.nodes[columnIds]['isOptional'] = column['isOptional']
                #graph.nodes[columnIds]['foreignKeyReference'] = column['foreignKeyReference']
                labeldict[columnIds] = column['columnName']
                canonicalColumns[table['tableName']+'-'+column['columnName']] = columnIds
                
                graph.add_edge(nodeIds, columnIds)

            # Add edges for foreign key references
            for table in data:
                for column in table['columns']:
                    try:
                        if column["foreignKeyReference"] is not None:
                            this_column = table["tableName"] + column["columnName"]
                            reference_column_ = column["foreignKeyReference"]["table"] + column["foreignKeyReference"]["column"]
                            graph.add_edge(canonicalColumns[this_column], canonicalColumns[reference_column_])
                    except Exception:
                        pass

        return graph



            
