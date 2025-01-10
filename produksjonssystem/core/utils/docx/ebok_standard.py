import logging
import os

import requests

from datetime import datetime

from core.config import Config
from core.directory import Directory
from core.utils.report import Report


class Ebok_standard:

    def isRomanNumeral(romanStr):
        # https://stackoverflow.com/questions/20973546/check-if-an-input-is-a-valid-roman-numeral
        N = 1
        for i in range(N):
            units = ["I", "II", "III" , 'IV' , 'V', 'VI', 'VII', 'VIII', "IX"]
            tens = ['X', "XX", "XXX", 'XL', 'L', 'LX', 'LXX', 'LXXX', 'XC']
            hundreds = ['C', 'CC', 'CCC', 'CD', 'D', 'DC', 'DCC', 'DCCC', 'CM']
            thousands = ['M', 'MM', 'MMM']
            allTypes = [units, tens, hundreds, thousands][::-1]
            isError = False
            lenRom = len(romanStr)
            copy = romanStr
            while len(copy) > 0 and len(allTypes) > 0:
                currentUnit = allTypes[0]
                # check units
                firstNum = copy[0]
                lastTwo = copy[:2]
                last3 = copy[:3]
                last4 = copy[:4]
                isLastTwo = lastTwo in currentUnit and len(lastTwo) == 2
                isLast3 = last3 in currentUnit and len(last3) == 3
                isLast4 = last4 in currentUnit and len(last4) == 4

                if (firstNum in currentUnit and not (isLastTwo or isLast3 or isLast4) ):
                    copy = copy[1::]
                    isError = False
                elif (isLastTwo and not (isLast3 or isLast4) ):
                    copy = copy[2::]
                    isError = False
                elif (isLast3 and not (isLast4) ):
                    copy = copy[3::]
                    isError = False
                elif (isLast4):
                    copy = copy[4::]
                    isError = False
                else:

                    isError = True
                allTypes.pop(0)

            if (isError or len(copy) != 0 ):
                return 0
            else:
                return 1

        return 0
        """import roman
            def is_valid_roman(input_string):
                try:
                    # Try converting the input to an integer using the roman library
                    roman.fromRoman(input_string)
                    return True
                except roman.InvalidRomanNumeralError:
                    # If an InvalidRomanNumeralError is raised, it's not a valid Roman numeral
                    return False
        """
    @staticmethod
    def remark(self):
        # Ebok standard 4.4
        print( "remark")
    @staticmethod
    def table_of_contents(self):
        # Ebok standard 4.5
        print( "table_of_contents")
    @staticmethod
    def copyright(self):
        # Ebok standard 4.9
        print( "© Statped")

    @staticmethod
    def lists(self):
        # Ebok standard 5
        print( "lists")
    @staticmethod
    def excercise(self):
        # Ebok standard 6
        print( "excercise")

    @staticmethod
    def typesetting_and_symbols(self):
        # Ebok standard 7
        print( "typesetting_and_symbols")
    @staticmethod
    def illustrations(self):
        # Ebok standard 8
        print( "illustrations")
    @staticmethod
    def table(self):
        # Ebok standard 9
        print( "© table")

    @staticmethod
    def convert(self, html_file):
        print("Test")
        return html_file