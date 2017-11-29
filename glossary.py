import csv, xlrd, xlwt, xlsxwriter
from collections import OrderedDict
from difflib import SequenceMatcher

class Glossary:

    def __init__(self, filepath, short_name, new=False):
        self.filepath = filepath
        self.short_name = short_name
        self.content = []
        self.filetype = filepath[filepath.rfind('.')+1:]
        if new == False: self.read_from_file()
        self.modified = False

    def read_from_file(self):
        self.content = []
        if self.filetype == 'csv':
            with open(self.filepath, 'r', newline='', encoding='utf-8') as file:
                fieldnames = ['source','translation','context']
                reader = csv.DictReader(file, fieldnames=fieldnames)
                for row in reader:
                    self.content.append(row)
        elif self.filetype == 'xls' or 'xlsx':
            wb = xlrd.open_workbook(self.filepath)
            sheet = wb.sheet_by_index(0)
            self.sheetname = sheet.name
            for row in range(sheet.nrows):
                try: context = str(sheet.cell(row,2).value)
                except IndexError: context = ''
                self.content.append(OrderedDict(
                    [('source', str(sheet.cell(row,0).value))
                     , ('translation', str(sheet.cell(row,1).value))
                     , ('context', context)]))

    def search_for(self, keyword, results, fuzzy):
        """ Receive keyword as a string and a list of results, and append any hits for that keyword to the results list.
        Args: keyword = string
                results = list"""
        if fuzzy == False:
            for row in self.content:
                if keyword in row['source']:
                    results.append({'source' : row['source']
                                    , 'translation' : row['translation']
                                    , 'context': row['context']
                                    , 'short_name' : self.short_name
                                    , 'index' : self.content.index(row)
                                    , 'ratio' : None})
        if fuzzy == True:
            for row in self.content:
                ratio = SequenceMatcher(None, keyword, row['source']).ratio()
                if  ratio > 0.5:
                    results.append({'source' : row['source']
                                    , 'translation' : row['translation']
                                    , 'context': row['context']
                                    , 'short_name' : self.short_name
                                    , 'index' : self.content.index(row)
                                    , 'ratio' : ratio})

    def add(self, entry):
        """ Receive an entry as an ordered dict and append it to self.content. """
        self.content.append(entry)
        if self.modified == False:
            self.modified = True

    def remove(self, index):
        """ Receive the index of an entry and pop it out of self.content. """
        self.content.pop(index)
        if self.modified == False:
            self.modified = True

    def modify(self, index, entry):
        """ Receive the index and an amended entry and replace it in self.content. """
        if entry == self.content[index]:
            return
        self.content[index] = entry
        if self.modified == False:
            self.modified = True

    def save(self):
        """ Write any changes to file. """
        if self.filetype == 'csv': self.save_csv()
        elif self.filetype == 'xls' or 'xlsx': self.save_excel()

    def save_csv(self):
        with open(self.filepath, 'w', newline='', encoding='utf-8') as file:
            fieldnames = ['source','translation','context']
            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction='ignore')
            writer.writerows(self.content)
        self.modified = False

    def save_excel(self):
        if self.filetype == 'xls':
            wb = xlwt.Workbook(encoding='utf-8')
            sheet = wb.add_sheet(self.sheetname)
        else:
            wb = xlsxwriter.Workbook(self.filepath)
            sheet = wb.add_worksheet(self.sheetname)
        for row in self.content:
            row_num = self.content.index(row)
            sheet.write(row_num, 0, row['source'])
            sheet.write(row_num, 1, row['translation'])
            sheet.write(row_num, 2, row['context'])
        if self.filetype == 'xls': wb.save(self.filepath)
        else: wb.close()
