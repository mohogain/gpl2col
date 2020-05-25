#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    File name: gpl2col.py
    Author: Micheál Ó hÓgáin
    GitHub: mohogain
    Date created: 25/05/2020
"""

import sys
import getopt
import re
import tempfile

class process_entry:
    """
        Handles the transformation of the GIMP colour palette data.
        Upon instantiation, checks if line begins with RGB value.

        NB: There is a lot of variation in the way leading zeros are
        presented in .gpl files (e.g. as 0, as whitespace, omitted).
        This is handled by identifying the colour code section with
        regex, removing leading and trailing whitespace from this
        section, splitting this section by the remaining whitespace,
        then converting the list items to integers
    """
    def __init__(self, line):
        self.line = line
        self.colour_code_pattern = \
        r'^[\s|\d]{1,3}\s[\s|\d]{1,3}\s[\s|\d]{1,3}'
        if re.match(self.colour_code_pattern, self.line):
            self.code_raw = \
            ((re.match(self.colour_code_pattern, self.line)).group(0))
            self.is_valid = True
        else:
            self.is_valid = False

    def __bool__(self):
        """
            Returns determination made as to whether the line supplied
            is a colour palette item
        """
        return self.is_valid
    
    def process_entry_hex(self):
        """
            ArtRage .col file stores colour codes in BGR format.
            Each entry ends with value 0xFF.
        """
        self.code = self.code_raw.strip()
        entry = re.split(r'\s{1,3}', self.code)
        return bytearray \
        ([int(entry[2]),int(entry[1]),int(entry[0]),int(255)])
    
    def process_entry_name(self):
        """
            Colour names are delimited by 0x00 0x00 0x00.
            Characters in names are interspersed with 0x00.
        """
        self.code_len = len(self.code_raw)
        name_content = bytearray(2)
        for c in (self.line[self.code_len:].strip()):
            name_content.extend(b'\x00')
            name_content.extend(c.encode('utf-8'))
        return name_content

class process_template:
    """
        Handles the creation of the .col file template.

        NB: .col file stores the number of entries as a single byte,
        as such the max number of entries that can be included in the
        colour palette is 255. This is not checked here.

        .col files created in ArtRage 6 assign a value other than null
        to the 28th block; the process by which this is generated could
        not be determined but the file functions as normal if this block
        is set to null.
    """
    def __init__(self, entry_count):
        # Create file header
        self.file_header_content = bytearray.fromhex \
        ('41 52 32 20 43 4F 4C 4F 52 20 50 52 45 53 45 54 0D 0A 8F')
        i = 1
        while i < len(self.file_header_content):
            self.file_header_content.insert(i, 0)
            i += 2
        self.file_header_content.extend(b'\x30\x00\xFF')
        self.file_header_content.extend(bytes(8))
        self.file_header_content.extend(bytes([entry_count]))
        self.file_header_content.extend(bytes(3))
        # Create name section preamble
        self.name_header_content = bytearray.fromhex \
        ('41 52 53 77 61 74 63 68 46 69 6C 65 56 65 72 73 69 6F 6E 2D 33')
        i = 1
        while i < len(self.name_header_content):
            self.name_header_content.insert(i, 0)
            i += 2

    def get_file_header(self):
        return self.file_header_content
    
    def get_name_header(self):
        return self.name_header_content

def check_if_valid_input(line):
    """
        GIMP palette files begin with "GIMP Palette" as the first line.
    """
    gpl_header = 'GIMP Palette\n'
    if line == gpl_header:
        return True
    else:
        return False

def main(argv):
    inputfile = ''
    outputfile = ''
    helpstring = ('Name: gpl2col\nFunction: converts GIMP colour palette ' + \
    'file (.gpl) to ArtRage colour palette file (.col)\nUsage: ' + \
    'gpl2col.py -i <.gpl file> -o <.col file>')
    try:
        opts, _args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        print (helpstring)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print (helpstring)
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-o", "--ofile"):
            outputfile = arg
    with open(inputfile) as ipf, \
    tempfile.TemporaryFile() as tmp_name, \
    tempfile.TemporaryFile() as tmp_hex:
        if check_if_valid_input(ipf.readline()) == False:
            print('Warning! The input file may not be a valid GIMP ' + \
            'colour palette file.\n\nProceeding...')
        # ArtRage .col file associates names with colour codes by order
        # Here the colour code and name of a GIMP palette item are
        # formatted and stored in the correct order
        entry_count = 0
        for line in ipf:
            if entry_count > 254:
                print('\nThe provided GIMP colour palette has more ' + \
                'entries than the entry limit for ArtRage .col files ' + \
                '(255).\n\nAborting process...')
                return
            else:
                entry = process_entry(line)
                if bool(entry) == True:
                    tmp_name.write(entry.process_entry_name())
                    tmp_hex.write(entry.process_entry_hex())
                    entry_count += 1
                else:
                    pass
        # Adds trailing 0x00 0x00 0x00 to name section
        tmp_name.write(bytes(3))
        with tempfile.TemporaryFile() as tmp_main:
            template_material = process_template(entry_count)
            tmp_main.write(template_material.get_file_header())
            tmp_hex.seek(0)
            while True:
                hexval = tmp_hex.read(1)
                tmp_main.write(hexval)
                if not hexval:
                    break
            tmp_main.write(template_material.get_name_header())
            tmp_name.seek(0)
            while True:
                nmchar = tmp_name.read(1)
                tmp_main.write(nmchar)
                if not nmchar:
                    break
            tmp_main.seek(0)
            opf = open(outputfile, 'wb')
            opf.write(tmp_main.read())
            opf.close()
            print('\nDone!')
            return

if __name__ == "__main__":
   main(sys.argv[1:])

