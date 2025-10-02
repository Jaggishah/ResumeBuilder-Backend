from langchain_community.llms import Ollama
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

def create_chat():
    # Initialize Ollama with the default model (you can change this to any model you have in Ollama)
    llm = Ollama(model="gemma3:1b")
    
    # Create a conversation chain with memory
    conversation = ConversationChain(
        llm=llm,
        memory=ConversationBufferMemory(),
        verbose=False
    )
    return conversation

def main():
    # Create the conversation chain
    conversation = create_chat()
    
    print("Chat initialized! Type 'quit' to exit.")
    
    while True:
        # Get user input
        user_input = input("You: ")
        
        # Check if user wants to quit
        if user_input.lower() == 'quit':
            break
        
        # Get the response from the model
        response = conversation.predict(input=user_input)
        print(f"Assistant: {response}")

if __name__ == "__main__":
    main()
