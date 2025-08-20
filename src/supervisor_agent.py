import logging
from config import Config
from inference_agent import InferenceAgent
from planning_agent import PlannerAgent
from discovery_agent import DiscoveryAgent
from langchain_core.prompts import ChatPromptTemplate
from state import ConversationState

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class SupervisorAgent:
    def __init__(self):
        # Initialize configuration and agents
        self.config = Config()
        self.inference_agent = InferenceAgent()
        self.planner_agent = PlannerAgent()
        self.discovery_agent = DiscoveryAgent()

        #Prompts for different types of responses
        self.db_response_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a response coordinator that creates final responses based on:
            Original Question: {question}
            Database Results: {db_results}

            Rules:
            1. ALWAYS include ALL results from database queries in your response
            2. Format the response clearly with each piece of information on its own line
            3. Use bullet points or numbers for multiple pieces of information
            4. Only provide the final results summary.
            """)
        ])

        self.chat_response_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a friendly AI assistant.
            Respond naturally to the user's message.
            Keep responses brief and friendly.
            Don't make up information about weather, traffic, or other external data.
            """)
        ])

    def create_plan(self, state: ConversationState) -> ConversationState:
        """Generate a plan using planner agent"""
        plan = self.planner_agent.create_plan(
            question = state["question"]
        )

        #log the plan, seperating inference and general steps
        logger.info("Generated plan:")
        inference_steps = [step for step in plan if step.startswith('Inference:')]
        general_steps = [step for step in plan if step.startswith('General:')]

        if inference_steps:
            logger.info("Inference Steps:")
            for i,step in enumerate(inference_steps, 1):
                logger.info(f"  {i}. {step}")

        if general_steps:
            logger.info("General Steps:")
            for i,step in enumerate(inference_steps, 1):
                logger.info(f"  {i}. {step}")

        return {
            **state, "plan": plan
        }

    def execute_plan(self, state: ConversationState) -> ConversationState:
        # Execute the generated plan step by step
        results = []

        try:
            for step in state['plan']:
                if ':' not in step:
                    continue

                step_type, content = step.split(':', 1)
                content = content.strip()

                if step_type.lower().strip() == 'inference':
                    # Handle inference steps using the InferenceAgent
                    try:
                        result = self.inference_agent.query(content, state.get('db_graph'))
                        results.append(f"Step: {step}\nResult: {result}")
                    except Exception as e:
                        logger.error(f"Error in inference step: {str(e)}", exc_info=True)
                        results.append(f"Step: {step}\nError: Query failed - {str(e)}")
                else:
                    # Handle general steps
                    results.append(f"Step: {step}\nResult: {content}")

            # Return state with results
            return {
                **state,
                "db_results": "\n\n".join(results) if results else "No results were generated."
            }

        except Exception as e:
            logger.error(f"Error in execute_plan: {str(e)}", exc_info=True)
            return {**state, "db_results": f"Error executing steps: {str(e)}"}

    def generate_response(self, state:ConversationState) -> ConversationState:
         # Generate the final response based on the input type
        logger.info("Generating final response")
        is_chat = state.get("input_type") in ["GREETING", "CHITCHAT", "FAREWELL"]
        prompt = self.chat_response_prompt if is_chat else self.db_response_prompt

        # Invoke the LLM to generate the response
        response = self.config.llm.invoke(prompt.format(
            question=state['question'],
            db_results=state.get('db_results', '')
        ))

        # Update state with the response and clear the plan
        return {**state, "response": response.content, "plan": []}
