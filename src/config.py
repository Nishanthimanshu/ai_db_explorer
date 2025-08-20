import os
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        #Load required environment variables
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY")
        self.db = os.getenv("DATABASE")
        self.groq_api_key = os.getenv("GROQ_API_KEY")

         # Ensure all required variables are set, otherwise raise an error
        if not all([self.gemini_api_key, self.db]):
            raise ValueError("Missing required environment variables: GEMINI_API_KEY, DATABASE")

        # Configure database connection
        self.db_engine = SQLDatabase.from_uri(f"sqlite:///{self.db}")

        # Set up language models with specific configurations
        self.llm = ChatGoogleGenerativeAI(temperature=0,  model="gemini-2.5-flash",)  # Default model
        self.llm_groq = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant")  # Explicitly use llama3.1-8b-instant