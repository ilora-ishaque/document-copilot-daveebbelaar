from datetime import date

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, CreatedAtMixin, UUIDPKMixin


class SourceDocument(Base, UUIDPKMixin, CreatedAtMixin):
    __tablename__ = "source_documents"

    ticker: Mapped[str] = mapped_column(String, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    filing_type: Mapped[str] = mapped_column(String, nullable=False)  # "10-K" | "10-Q"
    filing_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    accession_number: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
