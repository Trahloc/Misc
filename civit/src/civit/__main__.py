"""
# PURPOSE: Entry point for the civit package.

## INTERFACES:
 # main(): executes the main function from cli.py

## DEPENDENCIES:
 - civit.cli
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from civit.cli import main

if __name__ == '__main__':
    main()
