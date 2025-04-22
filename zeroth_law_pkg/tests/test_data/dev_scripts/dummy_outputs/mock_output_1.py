#!/usr/bin/env python
import sys

# Use repr() to ensure quotes and potential backslashes in the string itself are handled safely
# The string itself contains a literal \n which represents a newline
sys.stdout.write("Mocked help output for command.\\nLine 2.")
sys.stdout.flush()
