import stategraph
import logging
import gradio as gr

def process_message(user_message, history):
    state = graph.invoke({
    "question": user_message
    })
    history += [(user_message, state['response'])]
    return "", history

with gr.Blocks(theme=gr.themes.Monochrome()) as app:
    gr.Markdown("<h2 align='center'>AI Database Explorer</h2><p align='center'>Talk to a database in your language</p>")
    with gr.Row():
        chatbot = gr.Chatbot(height=500)
    with gr.Row():
        entry = gr.Textbox(label="Chat with our AI DB Assistant:")
    with gr.Row():
        clear = gr.Button("Clear")

    entry.submit(process_message, inputs=[entry, chatbot], outputs=[entry, chatbot])
    clear.click(lambda: None, inputs=None, outputs=chatbot, queue=False)

if __name__ == "__main__":
    # Configure the main logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)

    # Adjust logging levels for specific libraries to reduce noise
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    graph = stategraph.create_graph()

    app.launch()




