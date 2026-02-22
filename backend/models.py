from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class Holding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, unique=True)
    thesis: Optional[str] = None
    conviction: Optional[str] = None
    timeframe: Optional[str] = None
    kill_switch: Optional[str] = None
    comment: Optional[str] = None
    
    # Manual override fields (from portfolio.csv)
    purchase_price: Optional[float] = None
    quantity: Optional[float] = None
    commission: Optional[float] = None
    trade_date: Optional[datetime] = None
    
    # Relations
    transactions: List["Transaction"] = Relationship(back_populates="holding")

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    holding_id: Optional[int] = Field(default=None, foreign_key="holding.id")
    
    symbol: str = Field(index=True)
    date: datetime
    type: str # Buy, Sell, Dividend, Transf In, etc.
    quantity: Optional[float] = 0.0
    price: Optional[float] = 0.0
    commission: float = 0.0
    amount: float = 0.0 # Total amount in transaction currency
    currency: str = "CAD"
    description: Optional[str] = None
    source: str = "Manual" # CIBC, RBC, TD, Manual
    
    holding: Optional[Holding] = Relationship(back_populates="transactions")

class RealizedPnL(SQLModel, table=True):
    """Stores realized (closed) P&L computed from broker CSV transaction history."""
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    currency: str = "CAD"        # The currency of the pnl_amount (CAD or USD)
    pnl_amount: float = 0.0      # Realized gain/loss in the above currency
    source: str = "broker_csv"   # e.g. "broker_csv" or "manual"

class UserSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True)
    value: str
