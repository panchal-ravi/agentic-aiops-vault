"""
Compound expression parser for CloudWatch log filtering.

This module provides parsing and evaluation of compound expressions with logical
operators for advanced log filtering scenarios, including JSON path evaluation.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CompoundExpressionError(Exception):
    """Base exception for compound expression parsing errors."""

    pass


class CompoundExpressionParser:
    """
    Parser and evaluator for compound expressions with logical operators.

    Supports JSON path expressions like $.request.operation and logical operators
    like &&, ||, along with comparison operators.
    """

    def __init__(self):
        """Initialize the compound expression parser."""
        self.operators = {
            "&&": self._and_operation,
            "||": self._or_operation,
            "=": self._equals_operation,
            "!=": self._not_equals_operation,
            ">": self._greater_than_operation,
            "<": self._less_than_operation,
            ">=": self._greater_equal_operation,
            "<=": self._less_equal_operation,
        }

    def parse_and_evaluate(self, expression: str, log_data: dict[str, Any]) -> bool:
        """
        Parse and evaluate a compound expression against log data with performance optimizations.

        Args:
            expression: Compound expression string
            log_data: JSON log data to evaluate against

        Returns:
            bool: True if expression matches the log data

        Raises:
            CompoundExpressionError: If expression is invalid or evaluation fails
        """
        try:
            # Clean and normalize the expression
            expression = expression.strip()
            if not expression:
                return True

            # Fast path: Check for common patterns in Vault PKI expressions
            if self._fast_vault_pki_check(expression, log_data):
                return True

            # Handle single conditions or compound expressions
            return self._evaluate_expression(expression, log_data)

        except Exception as e:
            logger.debug(f"Error evaluating compound expression: {e}")
            # Don't raise exception for performance - just return False
            return False

    def _fast_vault_pki_check(self, expression: str, log_data: dict[str, Any]) -> bool:
        """
        Fast path check for common Vault PKI expressions.

        Args:
            expression: Compound expression string
            log_data: JSON log data

        Returns:
            bool: True if fast path matched, False to fall back to full parsing
        """
        # Quick checks for Vault PKI patterns
        if "request.operation" in expression and "pki_int/issue" in expression:
            # Check operation
            operation = log_data.get("request", {}).get("operation")
            if operation != "update":
                return False

            # Check path
            path = log_data.get("request", {}).get("path", "")
            if "pki_int/issue" not in path:
                return False

            # Check entity_id exists
            entity_id = log_data.get("auth", {}).get("entity_id")
            if not entity_id:
                return False

            # Check expiration exists
            expiration = log_data.get("response", {}).get("data", {}).get("expiration")
            if expiration is None:
                return False

            # If we get here, it's likely a match - let full parsing handle the rest
            # but we've already verified the expensive parts

        return False  # Fall back to full parsing

    def _evaluate_expression(self, expression: str, log_data: dict[str, Any]) -> bool:
        """Evaluate a potentially compound expression."""
        # Remove outer parentheses if they wrap the entire expression
        expression = self._remove_outer_parentheses(expression)

        # Find the main logical operator (&&, ||) at the top level
        main_operator, left_expr, right_expr = self._find_main_operator(expression)

        if main_operator:
            # Evaluate compound expression
            left_result = self._evaluate_expression(left_expr, log_data)
            right_result = self._evaluate_expression(right_expr, log_data)
            return self.operators[main_operator](left_result, right_result)
        else:
            # Evaluate single condition
            return self._evaluate_condition(expression, log_data)

    def _find_main_operator(self, expression: str) -> tuple[str | None, str, str]:
        """
        Find the main logical operator at the top level of the expression.

        Returns:
            tuple: (operator, left_expression, right_expression) or (None, "", "")
        """
        paren_level = 0
        i = 0

        # Look for || first (lower precedence)
        while i < len(expression) - 1:
            if expression[i] == "(":
                paren_level += 1
            elif expression[i] == ")":
                paren_level -= 1
            elif paren_level == 0 and expression[i : i + 2] == "||":
                left = expression[:i].strip()
                right = expression[i + 2 :].strip()
                return ("||", left, right)
            i += 1

        # Then look for && (higher precedence)
        paren_level = 0
        i = 0
        while i < len(expression) - 1:
            if expression[i] == "(":
                paren_level += 1
            elif expression[i] == ")":
                paren_level -= 1
            elif paren_level == 0 and expression[i : i + 2] == "&&":
                left = expression[:i].strip()
                right = expression[i + 2 :].strip()
                return ("&&", left, right)
            i += 1

        return (None, "", "")

    def _remove_outer_parentheses(self, expression: str) -> str:
        """Remove outer parentheses if they wrap the entire expression."""
        expression = expression.strip()
        if not expression.startswith("(") or not expression.endswith(")"):
            return expression

        # Check if the parentheses actually wrap the entire expression
        paren_count = 0
        for i, char in enumerate(expression):
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
                if paren_count == 0 and i < len(expression) - 1:
                    # Parentheses close before the end, so they don't wrap everything
                    return expression

        # Remove the outer parentheses
        return expression[1:-1].strip()

    def _evaluate_condition(self, condition: str, log_data: dict[str, Any]) -> bool:
        """Evaluate a single condition like $.request.operation = "update"."""
        condition = condition.strip()

        # Find the comparison operator
        for op in ["!=", ">=", "<=", "=", ">", "<"]:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()

                    # Evaluate left side (JSON path)
                    left_value = self._evaluate_json_path(left, log_data)

                    # Evaluate right side (literal value)
                    right_value = self._parse_literal_value(right)

                    # Apply comparison
                    return self.operators[op](left_value, right_value)

        raise CompoundExpressionError(f"Invalid condition format: {condition}")

    def _evaluate_json_path(self, path: str, data: dict[str, Any]) -> Any:
        """
        Evaluate a JSON path expression like $.request.operation.

        Args:
            path: JSON path string (e.g., "$.request.operation")
            data: JSON data to traverse

        Returns:
            Any: Value at the specified path, or None if not found
        """
        path = path.strip()

        # Handle $ prefix
        if path.startswith("$."):
            path = path[2:]
        elif path.startswith("$"):
            path = path[1:]

        # Split the path and traverse the data
        parts = path.split(".") if path else []
        current = data

        try:
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None

            return current

        except (KeyError, TypeError, AttributeError):
            return None

    def _parse_literal_value(self, value: str) -> Any:
        """Parse a literal value from the expression."""
        value = value.strip()

        # Remove quotes if present
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]

        # Try to parse as number
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # Try to parse as boolean
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False

        # Return as string
        return value

    def _and_operation(self, left: Any, right: Any) -> bool:
        """Logical AND operation."""
        return bool(left) and bool(right)

    def _or_operation(self, left: Any, right: Any) -> bool:
        """Logical OR operation."""
        return bool(left) or bool(right)

    def _equals_operation(self, left: Any, right: Any) -> bool:
        """Equality comparison."""
        return left == right

    def _not_equals_operation(self, left: Any, right: Any) -> bool:
        """Inequality comparison."""
        return left != right

    def _greater_than_operation(self, left: Any, right: Any) -> bool:
        """Greater than comparison."""
        try:
            return left > right
        except TypeError:
            return False

    def _less_than_operation(self, left: Any, right: Any) -> bool:
        """Less than comparison."""
        try:
            return left < right
        except TypeError:
            return False

    def _greater_equal_operation(self, left: Any, right: Any) -> bool:
        """Greater than or equal comparison."""
        try:
            return left >= right
        except TypeError:
            return False

    def _less_equal_operation(self, left: Any, right: Any) -> bool:
        """Less than or equal comparison."""
        try:
            return left <= right
        except TypeError:
            return False


def create_vault_pki_expression(path_pattern: str, hashed_subject: str) -> str:
    """
    Create a compound expression for Vault PKI certificate operations.

    Args:
        path_pattern: Path pattern (e.g., "pki_int/issue/*")
        hashed_subject: HMAC-SHA256 hashed certificate subject
        expiration_check: Whether to include expiration check (legacy parameter)

    Returns:
        str: Compound expression ready for evaluation
    """
    base_expr = (
        f'(($.request.path = "{path_pattern}/revoke") && ($.request.data.serial_number = "{hashed_subject}") && '
        f'($.auth.entity_id != "") && ($.response.mount_type = "pki")) || '
        f'(($.request.path = "{path_pattern}/issue/*") && ($.response.data.serial_number = "{hashed_subject}") && '
        f'($.auth.entity_id != ""))'
    )

    # base_expr = (
    #     f'($.request.path = "{path_pattern}/") && ($.request.data.common_name = "{hashed_subject}")'
    # )

    # Note: expiration_check parameter is now ignored as the new format
    # is handled in the calling code with entity_id and placeholder checks
    return base_expr
