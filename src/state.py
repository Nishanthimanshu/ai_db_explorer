import networkx as nx
from typing_extensions import NotRequired
from typing import Annotated, TypedDict, List, Optional

def db_graph_reducer():
    # Reducer function for handling database graph updates
    def _reducer(previous_value: Optional[nx.Graph], new_value: nx.Graph) -> nx.Graph:
        if previous_value is None:  # If no previous graph exists, use the new graph
            return new_value
        return previous_value  # Otherwise, retain the existing graph
    return _reducer

def plan_reducer():
    # Reducer function for updating plans
    def _reducer(previous_value: Optional[List[str]], new_value: List[str]) -> List[str]:
        return new_value if new_value is not None else previous_value  # Use the new plan if available
    return _reducer

def classify_input_reducer():
    # Reducer function for input classification
    def _reducer(previous_value: Optional[str], new_value: str) -> str:
        return new_value  # Always replace with the latest classification
    return _reducer


class ConversationState(TypedDict):
    """Defines the conversation state structure and associated reducers"""
    question: str  # Current user question
    input_type: Annotated[str, classify_input_reducer()]  # Classification of the input type
    plan: Annotated[List[str], plan_reducer()]  # Step-by-step plan to respond to the question
    db_results: NotRequired[str]  # Optional field for database query results
    response: NotRequired[str]  # Optional field for generated response
    db_graph: Annotated[Optional[nx.Graph], db_graph_reducer()] = None  # Optional field for database graph
