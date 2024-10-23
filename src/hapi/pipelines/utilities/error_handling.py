import logging
from typing import List, Tuple

from hdx.data.dataset import Dataset
from hdx.data.hdxobject import HDXError
from hdx.utilities.dictandlist import dict_of_sets_add

logger = logging.getLogger(__name__)


class ErrorManager:
    def __init__(
        self,
    ):
        self.shared_errors = {
            "error": {},
            "warning": {},
            "hdx_error": {},
        }

    def add_message(
        self,
        pipeline: str,
        identifier: str,
        text: str,
        resource_name: str = None,
        message_type: str = "error",
        flag_to_hdx: bool = False,
    ) -> None:
        """
        Add a new message (typically a warning or error) to a dictionary of messages in a
        fixed format:
            pipeline - identifier - {text}
        identifier is usually a dataset name.
        Args:
            pipeline (str): Name of the pipeline originating the error
            identifier (str): Identifier e.g. dataset name
            text (str): Text to use e.g. "sector CSS not found in table"
            resource_name (str): The resource name that the message applies to. Only needed if flagging on HDX
            message_type (str): The type of message (error or warning). Default is "error"
            flag_to_hdx (bool): Flag indicating if the message should be added to HDX metadata. Default is False
        Returns:
            None
        """
        error_id = (pipeline, identifier)
        error_message = f"{pipeline} - {identifier} - {text}"
        dict_of_sets_add(
            self.shared_errors[message_type], error_id, error_message
        )
        if flag_to_hdx:
            error_id = (pipeline, identifier, resource_name)
            dict_of_sets_add(self.shared_errors["hdx_error"], error_id, text)

    def add_missing_value_message(
        self,
        pipeline: str,
        identifier: str,
        value_type: str,
        value: str,
        resource_name: str = None,
        message_type: str = "error",
        flag_to_hdx: bool = False,
    ) -> None:
        """
        Add a new message (typically a warning or error) concerning a missing value
        to a dictionary of messages in a fixed format:
            pipeline - identifier - {text}
        identifier is usually a dataset name.
        Args:
            pipeline (str): Name of the scaper originating the error
            identifier (str): Identifier e.g. dataset name
            value_type (str): Type of value e.g. "sector"
            value (str): Missing value
            resource_name (str): The resource name that the message applies to. Only needed if flagging on HDX
            message_type (str): The type of message (error or warning). Default is "error"
            flag_to_hdx (bool): Flag indicating if the message should be added to HDX metadata. Default is False
        Returns:
            None
        """
        text = f"{value_type} {value} not found"
        self.add_message(
            pipeline,
            identifier,
            text,
            resource_name,
            message_type,
            flag_to_hdx,
        )

    def add_multi_valued_message(
        self,
        pipeline: str,
        identifier: str,
        text: str,
        values: List,
        resource_name: str = None,
        message_type: str = "error",
        flag_to_hdx: bool = False,
    ) -> bool:
        """
        Add a new message (typically a warning or error) concerning a list of
        values to a set of messages in a fixed format:
            pipeline - identifier - n {text}. First 10 values: n1,n2,n3...
        If less than 10 values, ". First 10 values" is omitted. identifier is usually
        a dataset name.
        Args:
            pipeline (str): Name of the scaper originating the error
            identifier (str): Identifier e.g. dataset name
            text (str): Text to use e.g. "negative values removed"
            values (List[str]): List of values of concern
            resource_name (str): The resource name that the message applies to. Only needed if flagging on HDX
            message_type (str): The type of message (error or warning). Default is "error"
            flag_to_hdx (bool): Flag indicating if the message should be added to HDX metadata. Default is False
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
        self.add_message(
            pipeline,
            identifier,
            text,
            resource_name,
            message_type,
            flag_to_hdx,
        )
        return True

    def output_errors(self, flag_to_hdx: bool) -> None:
        for _, errors in self.shared_errors["error"].items():
            errors = sorted(errors)
            for error in errors:
                logger.error(error)
        for _, warnings in self.shared_errors["warning"].items():
            warnings = sorted(warnings)
            for warning in warnings:
                logger.warning(warning)
        if flag_to_hdx:
            for identifier, errors in self.shared_errors["hdx_error"].items():
                write_error_to_resource(identifier, errors)


def write_error_to_resource(identifier: Tuple[str], errors: set[str]) -> bool:
    """
    Writes error messages to a resource on HDX. If the resource already has an
    error message, it is only overwritten if the two messages are different.
    Args:
        identifier (Tuple[str]): The scraper, dataset, and resource names that the message applies to
        errors (set[str]): Set of errors to use e.g. "negative values removed"
    Returns:
        bool: True if a message was added, False if not
    """
    # We are using the names here because errors may be specified in the YAML by us
    _, dataset_name, resource_name = identifier
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
