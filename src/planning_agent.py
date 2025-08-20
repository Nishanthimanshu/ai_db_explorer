import logging
from config import Config
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class PlannerAgent:
    def __init__(self):
         # Initialize configuration and planner prompt
        self.config = Config()
        self.planner_prompt = self.create_planner_prompt()

    def create_planner_prompt(self):
        """Define the system template for planning instructions"""
        system_template = """You are a friendly planning agent that creates specific plans to answer questions about THIS database only.

        Available actions:
        1. Inference: [query] - Use this prefix for database queries
        2. General: [response] - Use this prefix for friendly responses

        Create a SINGLE, SEQUENTIAL plan where:
        - Each step should be exactly ONE line
        - Each step must start with either 'Inference:' or 'General:'
        - Steps must be in logical order
        - DO NOT repeat steps
        - Keep the plan minimal and focused

        Example format:
        Inference: Get all artists from the database
        Inference: Count tracks per artist
        General: Provide the results in a friendly way
        """

        # Define the human message template for user input
        human_template = "Question: {question}\n\nCreate a focused plan with appropriate action steps."

        # Combine system and human message templates into a chat prompt
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])

    def create_plan(self, question: str) -> list:
        """ Generate a step-by-step plan to answer the given question"""
        try:
            logger.info(f"Creating plan for question: {question}")
            response = self.config.llm.invoke(self.planner_prompt.format(
                question=question
            ))

            # Extract and clean valid steps from the response
            steps = [step.strip() for step in response.content.split('\n')
                     if step.strip() and not step.lower() == 'plan:']

            # Provide a fallback message if no steps are returned
            if not steps:
                return ["General: I'd love to help you explore the database! What would you like to know?"]

            return steps

        except Exception as e:
            # Log and handle errors during plan creation
            logger.error(f"Error creating plan: {str(e)}", exc_info=True)
            return ["General: Error occurred while creating plan"]