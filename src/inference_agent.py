import json
import logging
import networkx as nx
from config import Config
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class InferenceAgent:
    def __init__(self):
        self.config = Config()
        self.toolkit = SQLDatabaseToolkit(db = self.config.db_engine, llm = self.config.llm)
        self.tools = self.toolkit.get_tools()
        self.chat_prompt = self.create_chat_prompt()
        self.agent = create_openai_functions_agent(
            llm=self.config.llm,
            prompt=self.chat_prompt,
            tools=self.tools
        )
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=15
        )

        self.test_connection()

    def test_connection(self):
        try:
            self.show_tables()
            logger.info("Database connection successful")
        except Exception as e:
            print(f"Database connection failed: {e}")

    def show_tables(self) -> str:
        """Query to list all tables and views in the database"""
        query = '''
        SELECT name, type
        FROM sqlite_master
        WHERE type IN ("table", "view");
        '''

        return self.run_query(query)

    def run_query(self, query:str) -> str:
        """Execute an SQL query and handle any exception"""
        try:
            return self.config.db_engine.run(query)
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return f"Error executing query: {str(e)}"

    def create_chat_prompt(self) -> ChatPromptTemplate:
        """Create a system prompt and user prompt"""
        system_message = SystemMessagePromptTemplate.from_template(
            """You are a database inference expert for a SQLite database named {db_name}.
            Your job is to answer questions by querying the database and providing clear, accurate results.

            Rules:
            1. ONLY execute queries that retrieve data
            2. DO NOT provide analysis or recommendations
            3. Format responses as:
               Query Executed: [the SQL query used]
               Results: [the query results]
               Summary: [brief factual summary of the findings]
            4. Keep responses focused on the data only
            """
        )

        # Create a template for user-provided input
        human_message = HumanMessagePromptTemplate.from_template("{input}\n\n{agent_scratchpad}")

        # Combine system and human message templates into a chat prompt
        return ChatPromptTemplate.from_messages([system_message, human_message])

    def analyze_questions_with_graph(self, db_graph: nx.Graph, question: str) -> dict:
        """Analyse the user questions in the context of the database graph"""
        print(f"\n🔎 Starting graph analysis for: '{question}'")
        question_lower = question.lower()

        # Structure to store analysis results
        analysis = {
            'tables': [],
            'relationships': [],
            'columns': [],
            'possible_paths': []
        }

        #Scan graph nodes to identify relevant tables and columns
        for node in db_graph.nodes():
            node_data = db_graph.nodes[node]

            if "tableName" not in node_data:
                continue

            table_name = node_data['tableName'].lower()
            if not (table_name in question_lower or
                    table_name.rstrip('s') in question_lower or
                    f"{table_name}s" in question_lower):
                continue

            print(f"  📦 Found relevant table: {node_data['tableName']}")
            table_info = {'name': node_data['tableName'], 'columns': []} 

             # Find matching columns connected to the table
            for neighbor in db_graph.neighbors(node):
                col_data = db_graph.nodes[neighbor]
                if 'columnName' in col_data and col_data['columnName'].lower() in question_lower:
                    table_info['columns'].append({
                        'name': col_data['columnName'],
                        'type': col_data['columnType'],
                        'table': node_data['tableName']
                    })
                    print(f"    📎 Found relevant column: {col_data['columnName']}")

            analysis['tables'].append(table_info)

        return analysis


    def query(self, text: str, db_graph) -> str:
        """Execute a query using graph-based analysis or standard prompt"""
        try:
            if db_graph:
                print(f"\n Analysing query with graph: '{text}'")

                #Analysing the query with the db graph
                graph_analysis = self.analyze_questions_with_graph(db_graph, text)
                print(f"\n📊 Graph Analysis Results:")
                print(json.dumps(graph_analysis, indent=2))

                # Enhance the prompt with graph analysis context
                enhanced_prompt = f"""
                Database Structure Analysis:
                - Available Tables: {[t['name'] for t in graph_analysis['tables']]}
                - Table Relationships: {graph_analysis['possible_paths']}

                User Question: {text}

                Use this structural information to form an accurate query.
                """

                print(f"\n📝 Enhanced prompt created with graph context")
                return self.agent_executor.invoke({"input": enhanced_prompt, "db_name": self.config.db})['output']
            print(f"\n⚡ No graph available, executing standard query: '{text}'")
            return self.agent_executor.invoke({"input": text, "db_name": self.config.db})['output']

        except Exception as e:
            # Handle errors during query processing
            print(f"\n❌ Error in inference query: {str(e)}")
            return f"Error processing query: {str(e)}"


