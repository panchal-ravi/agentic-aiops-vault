from strands.models.openai import OpenAIModel
from strands import Agent
from strands_tools import calculator
import os
from dotenv import load_dotenv

load_dotenv()

model = OpenAIModel(model_id="gpt-4o")


def main(): ...


if __name__ == "__main__":
    main()
