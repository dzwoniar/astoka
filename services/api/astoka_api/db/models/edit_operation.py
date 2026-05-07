"""EditOperation — append-only log of non-destructive edits on a clip.

Schema designed for Sprint 2 (filler removal, pause shrink, manual cuts) and
Sprint 8 (prompt-driven plan execution). Sprint 1 ships the table empty.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from astoka_api.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from astoka_api.db.models.clip import Clip


class EditOperation(Base, TimestampMixin):
    __tablename__ = "edit_operations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Monotonically increasing per clip — drives undo/redo (Sprint 2 EDIT-05).
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    # 'cut_segment' | 'remove_filler' | 'shrink_pause' | 'edit_word' | 'prompt_plan' (Sprint 8)
    op_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # Type-specific payload (e.g. {start: 12.4, end: 18.0} for cut_segment).
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Whether this operation is "active" — set to false on undo, true again on redo.
    is_undone: Mapped[bool] = mapped_column(default=False, nullable=False)

    clip: Mapped[Clip] = relationship("Clip", back_populates="edit_operations")

    def __repr__(self) -> str:
        return f"<EditOperation {self.op_type} seq={self.sequence}>"
