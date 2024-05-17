from typing import List, Set


def add_message(messages: Set[str], identifier: str, text: str) -> None:
    """
    Add a new message (typically a warning or error) to a set of messages in a
    fixed format:

        identifier - {text}

    identifier is usually a dataset name.

    Args:
        messages (Set[str]): Set of messages to which to add a new message
        identifier (str): Identifier eg. dataset name
        text (str): Text to use eg. "sector CSS not found in table"

    Returns:
        None
    """
    messages.add(f"{identifier} - {text}")


def add_missing_value_message(
    messages: Set[str], identifier: str, value_type: str, value: str
) -> None:
    """
    Add a new message (typically a warning or error) concerning a missing value
    to a set of messages in a fixed format:

        identifier - {value_type} {value} not found

    identifier is usually a dataset name.

    Args:
        messages (Set[str]): Set of messages to which to add a new message
        identifier (str): Identifier eg. dataset name
        value_type (str): Type of value eg. "sector"
        value (str): Missing value

    Returns:
        None
    """
    add_message(messages, identifier, f"{value_type} {value} not found")


def add_multi_valued_message(
    messages: Set[str], identifier: str, text: str, values: List
) -> bool:
    """
    Add a new message (typically a warning or error) concerning a list of
    values to a set of messages in a fixed format:

        identifier - n {text}. First 10 values: n1,n2,n3...

    If less than 10 values, ". First 10 values" is omitted. identifier is
    usually a dataset name.

    Args:
        messages (Set[str]): Set of messages to which to add a new message
        identifier (str): Identifier eg. dataset name
        text (str): Text to use eg. "negative values removed"
        values (List[str]): List of values of concern

    Returns:
        bool: True if a message was added, False if not
    """
    if not values:
        return False
    no_values = len(values)
    if no_values > 10:
        values = values[:10]
        msg = ". First 10 values"
    else:
        msg = ""
    text = f"{no_values} {text}{msg}: {', '.join(values)}"
    add_message(messages, identifier, text)
    return True
