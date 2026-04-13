import enum


class PaymentCurrency(str, enum.Enum):
    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
