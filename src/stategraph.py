import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from supervisor_agent import SupervisorAgent
from state import ConversationState
from langgraph.graph import StateGraph, START, END
from discovery_agent import DiscoveryAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def classify_user_input(state: ConversationState):
    """Classifies user input to determine if it requires database access."""

    # Define a system prompt for classifying input into predefined categories
    system_prompt = """You are an input classifier. Classify the user's input into one of these categories:
    - DATABASE_QUERY: Questions about data, requiring database access
    - GREETING: General greetings, how are you, etc.
    - CHITCHAT: General conversation not requiring database
    - FAREWELL: Goodbye messages

    Respond with ONLY the category name."""

    # Prepare messages for the LLM, including the system prompt and user's input
    messages = [
        ("system", system_prompt),  # Instructions for the LLM
        ("user", state['question'])  # User's question for classification
    ]

    # Invoke the LLM with a zero-temperature setting for deterministic output
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash",
    temperature=0, max_tokens=None, timeout=None,
    max_retries=2,
    )
    response = llm.invoke(messages)
    classification = response.content.strip()  # Extract the category from the response

    # Log the classification result
    logger.info(f"Input classified as: {classification}")

    # Update the conversation state with the input classification
    return {
        **state,
        "input_type": classification
    }

def discover_database(state: ConversationState) -> ConversationState:
    # Check if the database graph is already present in the state
    if state.get('db_graph') is None:
        logger.info("Performing one-time database schema discovery...")

        # Use the DiscoveryAgent to generate the database graph
        discovery_agent = DiscoveryAgent()
        graph = discovery_agent.discover()

        logger.info("Database schema discovery complete - this will be reused for future queries")

        # Update the state with the discovered database graph
        return {**state, "db_graph": graph}

    # Return the existing state if the database graph already exists
    return state

def create_graph():
    """Initialize the supervisor agent and state graph builder"""
    supervisor = SupervisorAgent()
    builder = StateGraph(ConversationState)

    # Add nodes representing processing steps in the flow
    builder.add_node("classify_input", classify_user_input)  # Classify the user input
    builder.add_node("discover_database", discover_database)  # Perform database discovery
    builder.add_node("create_plan", supervisor.create_plan)  # Create a plan based on input
    builder.add_node("execute_plan", supervisor.execute_plan)  # Execute the generated plan
    builder.add_node("generate_response", supervisor.generate_response)  # Generate the final response

    # Define the flow of states
    builder.add_edge(START, "classify_input")  # Start with input classification

    # Conditionally proceed to database discovery or directly to response generation
    builder.add_conditional_edges(
        "classify_input",
        lambda state: "discover_database" if state.get("input_type") == "DATABASE_QUERY" else "generate_response"
    )

    # Connect discovery to plan creation
    builder.add_edge("discover_database", "create_plan")

    # Conditionally execute the plan or generate a response if no plan exists
    builder.add_conditional_edges(
        "create_plan",
        lambda x: "execute_plan" if x.get("plan") is not None else "generate_response"
    )

    # Connect execution to response generation
    builder.add_edge("execute_plan", "generate_response")

    # End the process after generating the response
    builder.add_edge("generate_response", END)

    # Compile and return the state graph
    return builder.compile()