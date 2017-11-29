import os, threading
from glossary import Glossary

class GlossaryManager:

    def __init__(self, path):
        """ Declare a dict to hold Glossary objects and attempt to load all files in the directory.
        ARGS: the glossary folder path (string) """
        self.glossary_dir = path
        self.glossaries = {}
        try:
            filenames = (os.listdir(self.glossary_dir))
        except FileNotFoundError: raise FileNotFoundError('The glossary directory does not exist.')
        for file in filenames:
            filepath = self.glossary_dir + '/' + file
            if os.path.isfile(filepath):
                short_name = self.new_short_name(file)
                t = threading.Thread(target=self.add_glossary, args=(filepath, short_name))
                t.start()
                t.join()

    def new_short_name(self, file):
        """ Accept a filename and return a valid and unique short name based thereupon.
        ARGS: filename (string)
        RETURNS: short name (string) """
        invalid_chars = ''.join(c for c in map(chr, range(256)) if not c.isalnum())
        name = file[:file.rfind('.')]
        for c in invalid_chars: name = name.replace(c, '')
        if len(name) > 4: initials = name[0:4].upper()
        else: initials = name.upper()
        inc = 2
        short_name = initials
        while short_name in self.glossaries or short_name == ('ALL' or ''):
            short_name = initials + str(inc)
            inc += 1
        return short_name

    def add_glossary(self, filepath, short_name, new=False):
        """ Add a glossary to the glossaries dict.
        ARGS: filepath (string), short_name (string) """
        self.glossaries.update({short_name : Glossary(filepath, short_name, new)})

    def new_glossary(self, name):
        """ Add a new empty glossary to the glossaries dict.
        ARGS: filename (str) """
        filename = name + '.csv'
        short_name = self.new_short_name(filename)
        filepath = self.glossary_dir + '/' + filename
        self.add_glossary(filepath, short_name, new=True)

    def list_short_names(self):
        """ List all the currently loaded glossaries by short name """
        short_names = list(self.glossaries.keys())
        return str(short_names).strip('[]').replace('\'', '')
   
    def search(self, keyword, fuzzy=False):
        """ Searches all glossaries for a keyword. ARGS: keyword (string) """
        search_results = []
        for short_name in self.glossaries:
            t = threading.Thread(target=self.glossaries[short_name].search_for, args=(keyword, search_results, fuzzy))
            t.start()
            t.join()
        if fuzzy == True: search_results.sort(key = lambda s: s['ratio'], reverse=True)
        else: search_results.sort(key = lambda s: len(s['source']))
        return search_results
        
    def delete(self, short_name, index):
        """Delete an entry from a Glossary.
        ARGS: short_name (string), index (from search results; int) """
        self.glossaries[short_name].remove(index)
        
    def replace_entry(self, entry, short_name, index):
        """Replace an entry in a Glossary.
        ARGS: new entry (OrderedDict), short_name (string), index (from search results; int) """
        self.glossaries[short_name].modify(index, entry)

    def add_entry(self, entry):
        """Add an entry to the active Glossary.
        ARGS: new entry (OrderedDict) """
        try: self.glossaries[self.active_glossary].add(entry)
        except AttributeError: raise Exception('Set an active glossary')

    def set_active_glossary(self,short_name):
        """ Set the active Glossary.
        ARGS: short name (string) """
        short_name = short_name.upper()
        if short_name in self.glossaries:
            self.active_glossary = short_name
        else: raise Exception('{} is not a loaded glossary.'.format(short_name))

    def save(self, short_name):
        """ Save a Glossary (or all) and return a list of saved glossaries.
        ARGS: short name (string)
        RETURNS: saved glossaries (list) """
        short_name = short_name.upper()
        saved_glossaries = []
        if short_name == 'ALL':
            for glossary in self.glossaries:
                if self.glossaries[glossary].modified == True:
                    self.glossaries[glossary].save()
                    saved_glossaries.append(self.glossaries[glossary].short_name)
            return str(saved_glossaries).strip('[]').replace('\'', '')
        elif short_name in self.glossaries:
            if self.glossaries[short_name].modified == True:
                self.glossaries[short_name].save()
                return short_name
        else: raise Exception('{} is not a loaded glossary.'.format(short_name))

    def convert(self, short_name):
        short_name = short_name.upper()
        if short_name in self.glossaries:
            if self.glossaries[short_name].filetype == 'xls' or 'xlsx':
                self.glossaries[short_name].filetype = 'csv'
                filename = self.glossaries[short_name].filepath[:self.glossaries[short_name].filepath.rfind('.')]
                self.glossaries[short_name].filepath = filename + '.csv'
                self.glossaries[short_name].save()
        else: raise Exception('{} is not a loaded glossary.'.format(short_name))

    def reload(self, short_name):
        """ Reload a glossary from file.
        ARGS: short name (string) """
        short_name = short_name.upper()
        if short_name in self.glossaries:
            self.glossaries[short_name].read_from_file()
        else: raise Exception('{} is not a loaded glossary.'.format(short_name))
