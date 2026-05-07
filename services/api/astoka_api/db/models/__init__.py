"""ORM model registry — import here so Alembic autogenerate sees everything."""

from astoka_api.db.models.clip import Clip
from astoka_api.db.models.edit_operation import EditOperation
from astoka_api.db.models.highlight import Highlight, HighlightStatus
from astoka_api.db.models.job import Job, JobStatus, JobType
from astoka_api.db.models.project import Project
from astoka_api.db.models.source_material import SourceMaterial, SourceType
from astoka_api.db.models.transcript import Transcript
from astoka_api.db.models.user import User

__all__ = [
    "Clip",
    "EditOperation",
    "Highlight",
    "HighlightStatus",
    "Job",
    "JobStatus",
    "JobType",
    "Project",
    "SourceMaterial",
    "SourceType",
    "Transcript",
    "User",
]
