import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import String, Boolean, Integer, Float, ForeignKey, JSON, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import ModelBase, GUID
from shared.enums.common import HttpMethod, EndpointRiskLevel


class DiscoveredEndpoint(ModelBase):
    __tablename__ = "discovered_endpoints"

    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False)
    path: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    method: Mapped[HttpMethod] = mapped_column(SQLEnum(HttpMethod), default=HttpMethod.GET, nullable=False)
    auth_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parameters: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    response_codes: Mapped[List[int]] = mapped_column(JSON, default=list, nullable=False)
    risk_level: Mapped[EndpointRiskLevel] = mapped_column(SQLEnum(EndpointRiskLevel), default=EndpointRiskLevel.UNASSESSED, nullable=False)
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    application: Mapped["Application"] = relationship("Application", back_populates="endpoints")
    security_tests: Mapped[List["SecurityTest"]] = relationship("SecurityTest", back_populates="endpoint", cascade="all, delete-orphan")
    outgoing_relationships: Mapped[List["EndpointRelationship"]] = relationship(
        "EndpointRelationship",
        foreign_keys="EndpointRelationship.source_endpoint_id",
        back_populates="source_endpoint",
        cascade="all, delete-orphan"
    )
    incoming_relationships: Mapped[List["EndpointRelationship"]] = relationship(
        "EndpointRelationship",
        foreign_keys="EndpointRelationship.target_endpoint_id",
        back_populates="target_endpoint",
        cascade="all, delete-orphan"
    )


class DiscoveryJob(ModelBase):
    __tablename__ = "discovery_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # OPENAPI, POSTMAN, HAR, PASSIVE
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True, nullable=False)  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    endpoints_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    endpoints_in_scope: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    endpoints_out_of_scope: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="discovery_jobs")


class EndpointRelationship(ModelBase):
    __tablename__ = "endpoint_relationships"

    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False)
    source_endpoint_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("discovered_endpoints.id", ondelete="CASCADE"), index=True, nullable=False)
    target_endpoint_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("discovered_endpoints.id", ondelete="CASCADE"), index=True, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    evidence_source: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    explanation: Mapped[str] = mapped_column(String(500), nullable=False)
    provenance: Mapped[str] = mapped_column(String(50), default="inferred", nullable=False)  # observed, documented, inferred
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    application: Mapped["Application"] = relationship("Application", back_populates="endpoint_relationships")
    source_endpoint: Mapped["DiscoveredEndpoint"] = relationship(
        "DiscoveredEndpoint",
        foreign_keys=[source_endpoint_id],
        back_populates="outgoing_relationships"
    )
    target_endpoint: Mapped["DiscoveredEndpoint"] = relationship(
        "DiscoveredEndpoint",
        foreign_keys=[target_endpoint_id],
        back_populates="incoming_relationships"
    )
