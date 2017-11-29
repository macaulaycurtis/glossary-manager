from prompt_ui import PromptUI
from threading import Thread

def run():
    ui = PromptUI()

    listen_thread = Thread(target=ui.hotkey_listen, daemon=True)
    listen_thread.start()

    ui.run()

if __name__ == '__main__':
    run()
