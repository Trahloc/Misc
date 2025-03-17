#!/usr/bin/env python3
"""
PURPOSE: Template file demonstrating proper Zeroth Law structure and documentation patterns.
         This file serves as an example for implementing the Zeroth Law AI-Driven Development framework.

INTERFACES:
  - example_function(param1: str, param2: int) -> bool: Demonstrates proper function documentation
  - ExampleClass: Demonstrates proper class documentation

DEPENDENCIES:
  - None

ZEROTH LAW STATUS: 100% Complete
  - [x] Clear file purpose
  - [x] Interface documentation complete
  - [x] Function size compliance
  - [x] Semantic naming
  - [x] Proper documentation
"""

from typing import Dict, List, Optional, Union
import logging  # Added import for logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def example_function(descriptive_parameter_name: str, numeric_value: int = 0) -> bool:
    """
    Demonstrates proper function documentation and implementation under Zeroth Law.

    Args:
        descriptive_parameter_name: A detailed description that explains what this parameter does
        numeric_value: A value that controls some aspect of the function behavior

    Returns:
        Boolean indicating success or failure

    Raises:
        ValueError: If parameters don't meet expected criteria
    """
    logging.debug(f"Entering example_function with parameters: {descriptive_parameter_name}, {numeric_value}")
    
    if not descriptive_parameter_name:
        logging.error("descriptive_parameter_name cannot be empty")
        raise ValueError("descriptive_parameter_name cannot be empty")

    # This is a simple implementation for demonstration purposes
    result = len(descriptive_parameter_name) > numeric_value
    logging.debug(f"Exiting example_function with result: {result}")
    
    return result


class ExampleClass:
    """
    Demonstrates proper class documentation and structure under Zeroth Law.

    This class shows how to organize class code to maintain readability
    and ensure AI comprehension without external context.
    """

    def __init__(self, configuration: Dict[str, Union[str, int]]):
        """
        Initialize the class with configuration settings.

        Args:
            configuration: Dictionary containing configuration parameters
        """
        self.config = configuration
        self.initialized = True
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Validates the provided configuration.

        Private helper method demonstrating proper internal function naming and documentation.
        """
        required_keys = ["name", "value"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required configuration key: {key}")

    def process_data(self, input_data: List[str]) -> List[Dict[str, any]]:
        """
        Process a list of string data into structured information.

        Args:
            input_data: List of strings to process

        Returns:
            List of dictionaries containing processed data

        Raises:
            ValueError: If input_data is empty
        """
        if not input_data:
            raise ValueError("Input data cannot be empty")

        result = []
        for item in input_data:
            processed_item = self._transform_item(item)
            if processed_item:
                result.append(processed_item)

        return result

    def _transform_item(self, item: str) -> Optional[Dict[str, any]]:
        """
        Transform a single data item into a structured format.

        Args:
            item: String data to transform

        Returns:
            Dictionary with transformed data or None if transformation failed
        """
        if not item:
            return None

        return {
            "original": item,
            "length": len(item),
            "type": self.config.get("name", "default"),
            "processed": True
        }


# Simple usage example to demonstrate the code in action
def main():
    """Main function demonstrating usage of the example components."""
    logging.info("Starting main function")

    # Example function usage
    try:
        result = example_function("test string", 5)
        print(f"Function result: {result}")
    except ValueError as e:
        logging.error(f"Error in example_function: {e}")

    # Example class usage
    config = {"name": "example", "value": 42}
    processor = ExampleClass(config)

    data = ["item1", "item2", "item3"]
    processed = processor.process_data(data)
    print(f"Processed data: {processed}")

    # Additional example usage
    try:
        empty_result = example_function("", 5)  # This should raise an error
    except ValueError as e:
        logging.error(f"Error in example_function with empty string: {e}")

    # Testing with different numeric values
    result2 = example_function("another test", 10)
    print(f"Function result with different numeric value: {result2}")

    logging.info("Exiting main function")


if __name__ == "__main__":
    main()

"""
ZEROTH LAW ASSESSMENT: 100% Complete (AI's subjective evaluation)

Improvements made:
  - Implemented comprehensive header with clear purpose
  - Added complete interface documentation with types
  - Created self-contained example with minimal external dependencies
  - Used semantic naming throughout the codebase
  - Maintained small, focused functions with clear purposes

Next improvements needed:
  - None identified - this template represents full compliance with Zeroth Law principles
"""
