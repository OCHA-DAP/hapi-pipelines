from typing import Dict, List

from hdx.data.dataset import Dataset
from hdx.data.hdxobject import HDXError
from hdx.utilities.dictandlist import dict_of_sets_add


def add_message(
    messages: Dict,
    identifier: str,
    text: str,
    resource_name: str = None,
    message_type: str = "error",
    flag_in_hdx: bool = False,
) -> None:
    """
    Add a new message (typically a warning or error) to a dictionary of messages in a
    fixed format:

        identifier - {text}

    identifier is usually a dataset name.

    Args:
        messages (Dict): Dictionary of messages to which to add a new message
        identifier (str): Identifier eg. dataset name
        text (str): Text to use e.g. "sector CSS not found in table"
        resource_name (str): The resource name that the message applies to. Only needed if flagging on HDX
        message_type (str): The type of message (error or warning). Default is "error"
        flag_in_hdx (bool): Flag indicating if the message should be added to HDX metadata. Default is False

    Returns:
        None
    """
    if resource_name:
        identifier = f"{identifier} | {resource_name}"
    dict_of_sets_add(messages[message_type], identifier, text)
    if flag_in_hdx:
        dict_of_sets_add(messages["hdx_errors"], identifier, text)


def add_missing_value_message(
    messages: Dict,
    identifier: str,
    value_type: str,
    value: str,
    resource_name: str = None,
    message_type: str = "error",
    flag_in_hdx: bool = False,
) -> None:
    """
    Add a new message (typically a warning or error) concerning a missing value
    to a dictionary of messages in a fixed format:

        identifier - {text}

    identifier is usually a dataset name.

    Args:
        messages (Dict): Dictionary of messages to which to add a new message
        identifier (str): Identifier eg. dataset name
        value_type (str): Type of value e.g. "sector"
        value (str): Missing value
        resource_name (str): The resource name that the message applies to. Only needed if flagging on HDX
        message_type (str): The type of message (error or warning). Default is "error"
        flag_in_hdx (bool): Flag indicating if the message should be added to HDX metadata. Default is False

    Returns:
        None
    """
    text = f"{value_type} {value} not found"
    add_message(
        messages, identifier, text, resource_name, message_type, flag_in_hdx
    )


def add_multi_valued_message(
    messages: Dict,
    identifier: str,
    text: str,
    values: List,
    resource_name: str = None,
    message_type: str = "error",
    flag_in_hdx: bool = False,
) -> bool:
    """
    Add a new message (typically a warning or error) concerning a list of
    values to a set of messages in a fixed format:

        identifier - n {text}. First 10 values: n1,n2,n3...

    If less than 10 values, ". First 10 values" is omitted. identifier is usually
    a dataset name.

    Args:
        messages (Dict): Dictionary of messages to which to add a new message
        identifier (str): Identifier e.g. dataset name
        text (str): Text to use e.g. "negative values removed"
        values (List[str]): List of values of concern
        resource_name (str): The resource name that the message applies to. Only needed if flagging on HDX
        message_type (str): The type of message (error or warning). Default is "error"
        flag_in_hdx (bool): Flag indicating if the message should be added to HDX metadata. Default is False

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
    add_message(
        messages, identifier, text, resource_name, message_type, flag_in_hdx
    )
    return True


def write_error_to_resource(identifier: str, errors: set[str]) -> bool:
    """
    Writes error messages to a resource on HDX. If the resource already has an
    error message, it is only overwritten if the two messages are different.

    Args:
        identifier (str): The dataset and resource name that the message applies to
        errors (set[str]): Set of errors to use e.g. "negative values removed"

    Returns:
        bool: True if a message was added, False if not
    """
    dataset_name, resource_name = identifier.split(" | ")
    error_text = ", ".join(sorted(errors))
    try:
        dataset = Dataset.read_from_hdx(dataset_name)
        resource = [
            r for r in dataset.get_resources() if r["name"] == resource_name
        ][0]
    except (HDXError, IndexError):
        return False
    resource_error = resource.get("qa_hapi_report")
    if resource_error and resource_error == error_text:
        return False
    resource["qa_hapi_report"] = error_text
    resource.update_in_hdx(operation="patch")
    return True
