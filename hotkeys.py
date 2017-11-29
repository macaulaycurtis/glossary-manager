import win32con, win32gui, win32console, win32api
import ctypes, time, pyperclip
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.keys import Keys
from prompt_toolkit.filters import HasSelection

class GlobalHotkeyListener:

    def __init__(self):
        """Register hotkey (shift + insert)"""
        ctypes.windll.user32.RegisterHotKey(None, 1, win32con.MOD_SHIFT, win32con.VK_INSERT)
        self.hwnd = win32console.GetConsoleWindow()

    def listen(self):
        """Wait for hotkey to be triggered, then get and return highlighted text. """
        msg = ctypes.wintypes.MSG()
        while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == win32con.WM_HOTKEY:
                try: focus_hwnd = win32gui.GetForegroundWindow()
                except: focus_hwnd = None
                if focus_hwnd != self.hwnd:
                    paste = self.get_highlighted_text()
                    self.show_window()
                    return paste

    def deregister(self):
        """Unregister hotkey"""
        ctypes.windll.user32.UnregisterHotKey(None, 1)

    def show_window(self):
        """Show window (only works when running in a console)"""
        if win32gui.GetWindowPlacement(self.hwnd)[1] == 2: #if minimized
            win32gui.ShowWindow(self.hwnd, 4)
        else:
            win32gui.ShowWindow(self.hwnd, 5)
        win32gui.SetWindowPos(self.hwnd,win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE + win32con.SWP_NOSIZE)  
        win32gui.SetWindowPos(self.hwnd,win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE + win32con.SWP_NOSIZE)  
        win32gui.SetWindowPos(self.hwnd,win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_SHOWWINDOW + win32con.SWP_NOMOVE + win32con.SWP_NOSIZE)
        win32gui.SetForegroundWindow(self.hwnd)

    def get_highlighted_text(self):
        """Save clipboard, borrow it for a second to copy the highlighted text, then restore the original.
        (Only works on programs that use ctrl+c to copy.)"""
        original_clipboard = pyperclip.paste()

        #Emulate Ctrl+C
        time.sleep(0.15) #Sleep to allow the user's fingers to leave the keys.
        win32api.keybd_event(win32con.VK_LCONTROL, 0, 0, 0)
        win32api.keybd_event(0x43, 0, 0, 0)
        time.sleep(0.15) #Sleep to allow the program to detect the virtual keypress.
        win32api.keybd_event(win32con.VK_LCONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(0x43, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.15) #Sleep to allow the program to respond.
        
        search_arg = pyperclip.paste()
        pyperclip.copy(original_clipboard)
        return search_arg

def new_manager(self):
    """ Create a prompt-toolkit KeyBindingManager and register all the local keyboard shortcuts.
         Return the KeyBindingManager instance."""
    key_manager = KeyBindingManager()
        
    @key_manager.registry.add_binding(Keys.PageUp) # PgUp adds the last search term to the active glossary.
    def _(event):
        event.cli.run_in_terminal(self.add)

    @key_manager.registry.add_binding(Keys.PageDown) # PgDn shows all of the search results.
    def _(event):
        event.cli.run_in_terminal(self.show)

    @key_manager.registry.add_binding(Keys.ControlZ) # CtrlZ cancels whatever action is in progress.
    def _(event):
        event.cli.abort()

    @key_manager.registry.add_binding(Keys.ControlQ) #CtrlQ quits the program.
    def _(event):
        event.cli.run_in_terminal(self.quit) 

    @key_manager.registry.add_binding(Keys.ControlS) # CtrlS saves all modified glossaries.
    def _(event):
        event.cli.run_in_terminal(self.save)

    @key_manager.registry.add_binding(Keys.F1) # F1 displays help.
    def _(event):
        event.cli.run_in_terminal(self.help)

    @key_manager.registry.add_binding(Keys.ControlF) # CtrlF repeats a search fuzzily.
    def _(event):
        event.cli.run_in_terminal(self.fuzzy)

    @key_manager.registry.add_binding(Keys.ControlV, filter=~HasSelection()) #CtrlV pastes text from the clipboard.
    def _(event):
        event.cli.current_buffer.insert_text(self.clipboard.get_data().text)

    @key_manager.registry.add_binding(Keys.ControlV, filter=HasSelection()) #CtrlV pastes text from the clipboard.
    def _(event):
        event.cli.current_buffer.cut_selection()
        event.cli.current_buffer.insert_text(self.clipboard.get_data().text)

    @key_manager.registry.add_binding(Keys.ControlX, filter=HasSelection()) # CtrlX cuts highlighted text. (buggy)
    def _(event):
        data = event.cli.current_buffer.cut_selection()
        event.cli.current_buffer.exit_selection()
        self.clipboard.set_data(data)

    @key_manager.registry.add_binding(Keys.ControlC, filter=HasSelection()) # CtrlC copies highlighted text.
    def _(event):
        data = event.cli.current_buffer.copy_selection()
        event.cli.current_buffer.exit_selection()
        self.clipboard.set_data(data)

    @key_manager.registry.add_binding(Keys.ControlA) # CtrlA highlights all.
    def _(event):
        event.cli.current_buffer.cursor_position += event.cli.current_buffer.document.get_start_of_line_position(after_whitespace=False)
        event.cli.current_buffer.start_selection()
        event.cli.current_buffer.cursor_position += event.cli.current_buffer.document.get_end_of_line_position()

    return key_manager

if __name__ == '__main__':
    ghl = GlobalHotkeyListener()
    for i in range(2):
        paste = ghl.listen()
        print(paste)
    ghl.deregister()
    
