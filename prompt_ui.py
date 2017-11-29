import pyperclip, hotkeys
from configparser import ConfigParser
from collections import OrderedDict
from glossarymanager import GlossaryManager
from prompt_toolkit.shortcuts import create_prompt_application, create_eventloop, print_tokens
from prompt_toolkit.interface import CommandLineInterface, AbortAction
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.token import Token
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.document import Document

class PromptUI:

    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.config = self.config['DEFAULT']
        
        self.msg('\n{}\n'.format(self.config['greeting']))
        self.glossary_manager = self.new_glossary_manager(self.config['path'])
        self.list()
        self.set(self.config['active_glossary'])
        print('Press F1 for help.')

        self.clipboard = PyperclipClipboard()
        self.history = InMemoryHistory()
        self.key_manager = hotkeys.new_manager(self)

        self.cmds = {
            'QUIT' : self.quit
            , 'SHOW' : self.show
            , 'LIST' : self.list
            , 'DEL' : self.delete
            , 'ADD' : self.add
            , 'SET' : self.set
            , 'EDIT' : self.edit
            , 'SAVE' : self.save
            , 'RELOAD' : self.reload
            , 'NEW' : self.new_glossary
            , 'HELP' : self.help
            , 'FUZZY' : self.fuzzy
            , 'CONVERT' : self.convert
            , 'MOVE': self.move
            , 'SEARCH' : self.search
            }

    def new_glossary_manager(self, path):
        """ Instantiate and return a glossary manager instance. """
        try:
            glossary_manager = GlossaryManager(path)
            return glossary_manager
        except Exception as e:
            print('... Failed!')
            self.msg(e, 2)
            raise SystemExit

    def run(self):      
        """ The main UI loop. Wait for a command with optional argument after a space.
        Search for whatever was typed if no valid command is entered. """
        while True:
            application = create_prompt_application(
                '>> '
                , mouse_support=True
                , style=style_from_dict({Token: self.config['colour0']})
                , key_bindings_registry=self.key_manager.registry
                , history=self.history
                , on_abort=AbortAction.RETRY
                , clipboard=self.clipboard
                , get_title=lambda: self.config['title']
                )
            self.cli = CommandLineInterface(application, create_eventloop())
            self.cli.stdout_proxy()
            line = self.cli.run().text
            split = line.split()
            if len(split) >= 1 : cmd = split[0].upper()
            if cmd in self.cmds:
                try: arg = ' '.join(split[1:])
                except: arg=''
                self.cmds[cmd](arg)
            else: self.search(line)

    def search(self, arg='', fuzzy=False):
        """ Search for a keyword.
         ARGS: the search keyword. """
        #RETURNS: search results in the format OrderedDict([{source, translation, context, short_name, index}])
        if arg == '': return
        self.last_search = arg
        self.search_results = self.glossary_manager.search(arg, fuzzy)
        self.show(self.config['max_results'])

    def fuzzy(self, arg=''):
        """ Fuzzy search for a keyword.
         ARGS: the search keyword.
         RETURNS: search results, ordered by relevance.
         SHORTCUT: Ctrl + F (repeats the last search fuzzily)"""
        if arg == '': arg = self.last_search
        self.search(arg, fuzzy=True)

    def list(self, arg=''):
        """ List all the currently loaded glossaries. """
        try: print('Currently loaded glossaries:\n' + self.glossary_manager.list_short_names())
        except Exception as e: self.msg(repr(e), 2)

    def quit(self, arg=''):
        """ Print a whimsical message then quit. Deregister the global hotkey.
         SHORTCUT: Ctrl + Q"""
        self.msg(self.config['farewell'])
        self.hotkey_listener.deregister()
        raise SystemExit

    def set(self, arg=''):
        """ Set the active glossary.
         ARGS: arg = the short name of the glossary to set as active. """
        try:
            self.glossary_manager.set_active_glossary(arg)
            self.msg('{} is now the active glossary.'.format(self.glossary_manager.active_glossary))
        except Exception as e: self.msg(repr(e), 2)

    def show(self, arg=''):
        """ Show the results of the last search.
         ARGS: the maximum number of search results to display.
         SHORTCUT: PageDown (displays all)"""
        try:
            if arg.upper() == 'ALL' or arg == '' or int(arg) > len(self.search_results):
                return_max = len(self.search_results)
            else: return_max = int(arg)
            if self.search_results == []: self.msg('Search term \"{}\" not found.'.format(self.last_search))
            else: self.msg('Search results for {} ({} of {}):'.format(
                self.last_search, return_max, len(self.search_results)))
            for result in self.search_results[:return_max]:
                result_number = str(self.search_results.index(result))
                if result == 'DELETED': print('{n}: {r}'.format(n=result_number, r=result))
                else: print('{n}: {r[source]}: {r[translation]} ({r[short_name]}) 〈{r[context]}〉'.format(
                    n=result_number, r=result))
        except ValueError: self.msg('SHOW command takes a number or \'all\'.', 2)
        except AttributeError: self.msg('Search for something first.', 2)
        except Exception as e: self.msg(repr(e), 2)

    def delete(self, arg=''):
        """ Delete an entry.
         ARGS: the number of the search result to delete. """
        try:
            arg = int(arg)
            result = self.search_results[arg]
            self.glossary_manager.delete(result['short_name'], result['index'])
            for r in self.search_results: 
                if not (r == 'DELETED') and ( #This shifts the indices of all the search results
                r['short_name'] == result['short_name']) and ( #after the deleted result, 
                r['index'] > result['index']): r['index'] -= 1 # so that the numbers still point to the same data.
            self.search_results[arg] = 'DELETED'
            self.msg('Removed {r[source]} from {r[short_name]}.'.format(r=result))
        except ValueError: self.msg('DEL command takes a number.', 2)
        except AttributeError: self.msg('No search results to modify.', 2)
        except IndexError: self.msg('No result with that number.', 2)
        except Exception as e: self.msg(repr(e), 2)

    def add(self, arg=''):
        """ Add an entry to the active glossary.
         ARGS: the source value of the new entry to be added.
         SHORTCUT: PageUp (adds the last search keyword) """
        if arg == '':
            try: arg = self.last_search
            except AttributeError: self.msg('Add what?', 2); return
        try:
            new_entry = OrderedDict([('source', arg), ('translation', ''), ('context', '')])
            for key in ['translation', 'context']:
                application = create_prompt_application(
                    'Add a {} for \"{}\":\n>>'.format(key, arg)
                    , mouse_support=True
                    , style=style_from_dict({Token: self.config['colour1']})
                    , key_bindings_registry=self.key_manager.registry
                    , on_abort=AbortAction.RETURN_NONE
                    , clipboard=PyperclipClipboard()
                    , get_title=lambda: self.config['title']
                    )
                c = CommandLineInterface(application, create_eventloop())
                c.stdout_proxy()
                try: new_entry[key] = c.run().text
                except AttributeError: return
            self.glossary_manager.add_entry(new_entry)
            self.msg('Added {} to {}.'.format(new_entry['source'], self.glossary_manager.active_glossary), 1)
        except Exception as e: self.msg(repr(e), 2)
        
    def edit(self, arg=''):
        """ Edit an entry by creating a sub-prompt.
         ARGS: the number of the search result to edit. """
        try:
            arg = int(arg)
            original_entry = self.search_results[arg]
            new_entry = OrderedDict([('source', original_entry['source']), ('translation', original_entry['translation'])
                                      , ('context', original_entry['context'])])
            for key in new_entry:
                application = create_prompt_application(
                    'Edit {}:\n>> '.format(key)
                    , mouse_support=True
                    , style=style_from_dict({Token: self.config['colour1']})
                    , key_bindings_registry=self.key_manager.registry
                    , on_abort=AbortAction.RETURN_NONE
                    , clipboard=PyperclipClipboard()
                    , default=new_entry[key]
                    , get_title=lambda: self.config['title']
                    )
                c = CommandLineInterface(application, create_eventloop())
                c.stdout_proxy()
                try: new_entry[key] = c.run().text
                except AttributeError: return
            self.glossary_manager.replace_entry(new_entry, original_entry['short_name'], original_entry['index'])
            self.msg('Modified {} in {}.'.format(new_entry['source'], original_entry['short_name']), 1)
            for key in new_entry: self.search_results[arg][key] = new_entry[key]
        except ValueError: self.msg('EDIT command takes a number.', 2)
        except AttributeError: self.msg('No search results to modify.', 2)
        except IndexError: self.msg('No result with that number.', 2)
        except TypeError: self.msg('That result has already been deleted.', 2)
        except Exception as e: self.msg(repr(e), 2)

    def move(self, arg=''):
        """ Move a term from one glossary to another.
         SYNTAX: "MOVE 0 to MAIN"
         ARGS: Search result number; short name of target. """
        args = arg.split()
        try:
            result_number = args[0]
            target_glossary = args[2]
            current_glossary = self.glossary_manager.active_glossary
            self.glossary_manager.set_active_glossary(target_glossary)
        except IndexError: self.msg('Syntax example: MOVE 0 to MAIN.', 2); return
        except Exception as e: self.msg(repr(e), 2); return
        try:
            original_entry = self.search_results[int(result_number)]
            new_entry = OrderedDict([('source', original_entry['source']), ('translation', original_entry['translation'])
                                     , ('context', original_entry['context'])])
            self.glossary_manager.add_entry(new_entry)
            self.msg('Moved {} to {}.'.format(new_entry['source'], self.glossary_manager.active_glossary))
            self.delete(result_number)
            self.glossary_manager.set_active_glossary(current_glossary)
        except AttributeError: self.msg('No search results to modify.', 2)
        except IndexError: self.msg('No result with that number.', 2)
        except Exception as e: self.msg(repr(e), 2)

    def save(self, arg='all'):
        """ Save a modified glossary. Print a list of the glossaries saved.
         ARGS: the short name of the glossary to save.
         SHORTCUT: Ctrl+S (save all) """
        try:
            saved_glossaries = self.glossary_manager.save(arg)
            if saved_glossaries == '' or None: return
            print('Saved {}.'.format(saved_glossaries))
        except Exception as e: self.msg(repr(e), 2)

    def convert(self, arg=''):
        """ Convert an excel-formatted glossary file to the much faster CSV.
         ARGS: the short name of the glossary to convert. """
        try:
            self.glossary_manager.convert(arg)
            print(arg.upper() + ' converted to CSV.')
        except Exception as e: self.msg(repr(e), 2)

    def reload(self, arg=''):
        """ Reload a glossary from file.
         ARGS: the short name of the glossary to reload. """
        if arg == '': self.msg('Reload what?', 2); return
        try:
            self.glossary_manager.reload(arg)
            self.msg('Reloaded {}'.format(arg.upper()))
        except Exception as e: self.msg(repr(e), 2)

    def new_glossary(self, arg=''):
        """ Add a new empty glossary. """
        if arg == '': self.msg('Type NEW followed by the name of the new glossary.'); return
        try: self.glossary_manager.new_glossary(arg)
        except Exception as e: self.msg(repr(e), 2)
        self.list()

    def help(self, arg=''):
        """ Print this help message.
         SHORTCUT: F1 """   
        print('\n ****GENERAL HELP ****\n')
        print('Type a keyword to search for it. You can cancel any operation with Ctrl + Z.')
        print('Default values can be changed by editing the file "config.ini".\n')
        print(' ***** OTHER COMMANDS ****\n')
        if arg == '':
            for key in self.cmds: print('{:8}{}'.format(key + ':', self.cmds[key].__doc__))

    def hotkey_listen(self):
        """ Instantiate the global hotkey listener, which returns highlighted text from other
       programs via the clipboard, then search for that text. """
        self.hotkey_listener = hotkeys.GlobalHotkeyListener()
        #search_paste = lambda: self.search(paste) # old method
        while True:
            paste = self.hotkey_listener.listen()
            paste = paste.strip()
            #self.cli.run_in_terminal(search_paste) # old method
            self.cli.set_return_value(Document(paste)) # new method
            self.history.append(paste)

    def msg(self, string='', style=0):
        """ Print a coloured message to the standard output.
       ARGS: string = the string to be printed
               style = the colour to print it in: 0 = primary, 1 = secondary, 2 = error. """
        colours = {0: self.config['colour0'], 1: self.config['colour1'], 2: self.config['colour2']}
        if style in colours: colour = colours[style]
        else: colour = colours[0]
        print_tokens([(Token.Text, str(string) + '\n')], style=style_from_dict({Token.Text: colour}))
