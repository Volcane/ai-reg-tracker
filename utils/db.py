"""
ARIS — Database Layer (updated)

Tables:
  documents         — Raw legislative/regulatory documents
  summaries         — AI-generated business intelligence summaries
  document_diffs    — Version comparison and addendum analysis results
  document_links    — Explicit relationships between documents
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    create_engine, Column, String, Text, DateTime,
    Float, Boolean, JSON, Index, text, Integer
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import DB_PATH


class Base(DeclarativeBase):
    pass


# ── Core tables ───────────────────────────────────────────────────────────────

class Document(Base):
    """Raw legislative / regulatory document fetched from a source."""
    __tablename__ = "documents"

    id             = Column(String, primary_key=True)
    source         = Column(String, nullable=False)
    jurisdiction   = Column(String, nullable=False)
    doc_type       = Column(String)
    title          = Column(Text, nullable=False)
    url            = Column(Text)
    published_date = Column(DateTime)
    agency         = Column(String)
    status         = Column(String)
    full_text      = Column(Text)
    raw_json       = Column(JSON)
    fetched_at     = Column(DateTime, default=datetime.utcnow)
    content_hash   = Column(String)

    __table_args__ = (
        Index("ix_doc_jurisdiction", "jurisdiction"),
        Index("ix_doc_source",       "source"),
        Index("ix_doc_published",    "published_date"),
    )


class Summary(Base):
    """AI-generated business-intelligence summary for a Document."""
    __tablename__ = "summaries"

    document_id     = Column(String, primary_key=True)
    plain_english   = Column(Text)
    requirements    = Column(JSON)
    recommendations = Column(JSON)
    action_items    = Column(JSON)
    deadline        = Column(String)
    impact_areas    = Column(JSON)
    urgency         = Column(String)
    relevance_score = Column(Float)
    model_used      = Column(String)
    summarized_at   = Column(DateTime, default=datetime.utcnow)


class DocumentDiff(Base):
    """
    Stores the result of a version comparison or addendum analysis
    produced by the DiffAgent.

    diff_type:
      "version_update" — same regulation, newer version published
      "addendum"       — a separate document modifies/reinterprets the base

    For version_update:
      base_document_id = older version's document ID
      new_document_id  = newer version's document ID

    For addendum:
      base_document_id = the regulation being amended or clarified
      new_document_id  = the addendum / amendment / guidance document
    """
    __tablename__ = "document_diffs"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    base_document_id      = Column(String, nullable=False)
    new_document_id       = Column(String, nullable=False)
    diff_type             = Column(String, nullable=False)
    relationship_type     = Column(String)
    change_summary        = Column(Text)
    severity              = Column(String)
    added_requirements    = Column(JSON)
    removed_requirements  = Column(JSON)
    modified_requirements = Column(JSON)
    definition_changes    = Column(JSON)
    deadline_changes      = Column(JSON)
    penalty_changes       = Column(JSON)
    scope_changes         = Column(Text)
    new_action_items      = Column(JSON)
    obsolete_action_items = Column(JSON)
    overall_assessment    = Column(Text)
    model_used            = Column(String)
    detected_at           = Column(DateTime, default=datetime.utcnow)
    reviewed              = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_diff_base",     "base_document_id"),
        Index("ix_diff_new",      "new_document_id"),
        Index("ix_diff_severity", "severity"),
        Index("ix_diff_type",     "diff_type"),
        Index("ix_diff_detected", "detected_at"),
    )


class DocumentLink(Base):
    """
    Explicit relationship between two documents.
    link_type values: "amends" | "clarifies" | "implements" | "supersedes" | "version_of"
    """
    __tablename__ = "document_links"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    base_doc_id    = Column(String, nullable=False)
    related_doc_id = Column(String, nullable=False)
    link_type      = Column(String, nullable=False)
    notes          = Column(Text)
    created_at     = Column(DateTime, default=datetime.utcnow)
    created_by     = Column(String, default="system")

    __table_args__ = (
        Index("ix_link_base",    "base_doc_id"),
        Index("ix_link_related", "related_doc_id"),
    )


# ── Engine & session factory ──────────────────────────────────────────────────

_engine  = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        Base.metadata.create_all(_engine)
    return _engine


def get_session() -> Session:
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine())
    return _Session()


# ── Documents CRUD ────────────────────────────────────────────────────────────

def upsert_document(doc_dict: Dict[str, Any]) -> bool:
    """
    Insert or update a document.
    Returns True if content changed (triggers diff pipeline in orchestrator).
    """
    content_hash = hashlib.md5(
        (doc_dict.get("full_text") or doc_dict.get("title") or "").encode()
    ).hexdigest()

    with get_session() as session:
        existing = session.get(Document, doc_dict["id"])
        if existing and existing.content_hash == content_hash:
            return False

        doc = existing or Document()
        for k, v in doc_dict.items():
            if hasattr(doc, k):
                setattr(doc, k, v)
        doc.content_hash = content_hash
        doc.fetched_at   = datetime.utcnow()
        session.merge(doc)
        session.commit()
        return True


def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    with get_session() as session:
        doc = session.get(Document, doc_id)
        return _doc_to_dict(doc) if doc else None


def get_documents_by_title_pattern(pattern: str,
                                    jurisdiction: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_session() as session:
        q = session.query(Document).filter(Document.title.ilike(f"%{pattern}%"))
        if jurisdiction:
            q = q.filter(Document.jurisdiction == jurisdiction)
        return [_doc_to_dict(d) for d in q.all()]


def get_all_documents(jurisdiction: Optional[str] = None,
                      limit: int = 500) -> List[Dict[str, Any]]:
    with get_session() as session:
        q = session.query(Document)
        if jurisdiction:
            q = q.filter(Document.jurisdiction == jurisdiction)
        return [_doc_to_dict(d) for d in
                q.order_by(Document.published_date.desc()).limit(limit).all()]


def _doc_to_dict(doc: Document) -> Dict[str, Any]:
    return {
        "id":            doc.id,
        "source":        doc.source,
        "jurisdiction":  doc.jurisdiction,
        "doc_type":      doc.doc_type,
        "title":         doc.title,
        "url":           doc.url,
        "published_date": doc.published_date.isoformat() if doc.published_date else None,
        "agency":        doc.agency,
        "status":        doc.status,
        "full_text":     doc.full_text,
    }


# ── Summaries CRUD ────────────────────────────────────────────────────────────

def upsert_summary(summary_dict: Dict[str, Any]) -> None:
    with get_session() as session:
        session.merge(Summary(**summary_dict))
        session.commit()


def get_summary(doc_id: str) -> Optional[Dict[str, Any]]:
    with get_session() as session:
        s = session.get(Summary, doc_id)
        if not s:
            return None
        return {
            "document_id":     s.document_id,
            "plain_english":   s.plain_english,
            "requirements":    s.requirements,
            "recommendations": s.recommendations,
            "action_items":    s.action_items,
            "deadline":        s.deadline,
            "impact_areas":    s.impact_areas,
            "urgency":         s.urgency,
            "relevance_score": s.relevance_score,
        }


def get_unsummarized_documents(limit: int = 50) -> List[Document]:
    with get_session() as session:
        summarized_ids = session.execute(
            text("SELECT document_id FROM summaries")
        ).scalars().all()
        return (
            session.query(Document)
            .filter(Document.id.notin_(summarized_ids))
            .order_by(Document.published_date.desc())
            .limit(limit)
            .all()
        )


def get_recent_summaries(days: int = 30,
                          jurisdiction: Optional[str] = None) -> List[Dict]:
    with get_session() as session:
        since = datetime.utcnow() - timedelta(days=days)
        q = (
            session.query(Document, Summary)
            .join(Summary, Document.id == Summary.document_id)
            .filter(Document.published_date >= since)
        )
        if jurisdiction:
            q = q.filter(Document.jurisdiction == jurisdiction)
        results = []
        for doc, summ in q.order_by(Document.published_date.desc()).all():
            results.append({
                "id":             doc.id,
                "title":          doc.title,
                "source":         doc.source,
                "jurisdiction":   doc.jurisdiction,
                "doc_type":       doc.doc_type,
                "agency":         doc.agency,
                "status":         doc.status,
                "url":            doc.url,
                "published_date": doc.published_date.isoformat() if doc.published_date else None,
                **{k: getattr(summ, k) for k in [
                    "plain_english", "requirements", "recommendations",
                    "action_items", "deadline", "impact_areas",
                    "urgency", "relevance_score"
                ]},
            })
        return results


# ── DocumentDiff CRUD ─────────────────────────────────────────────────────────

def save_diff(diff_dict: Dict[str, Any]) -> int:
    """Save a diff record. Each comparison is a new record — history is preserved."""
    with get_session() as session:
        d = DocumentDiff(**{
            k: v for k, v in diff_dict.items()
            if k != "id" and hasattr(DocumentDiff, k)
        })
        session.add(d)
        session.commit()
        session.refresh(d)
        return d.id


def diff_exists(base_id: str, new_id: str) -> bool:
    with get_session() as session:
        result = session.execute(
            text("SELECT COUNT(*) FROM document_diffs "
                 "WHERE base_document_id = :b AND new_document_id = :n"),
            {"b": base_id, "n": new_id},
        ).scalar()
        return (result or 0) > 0


def get_diffs_for_document(doc_id: str) -> List[Dict[str, Any]]:
    """All diffs where this document appears as either base or new version."""
    with get_session() as session:
        rows = session.query(DocumentDiff).filter(
            (DocumentDiff.base_document_id == doc_id) |
            (DocumentDiff.new_document_id  == doc_id)
        ).order_by(DocumentDiff.detected_at.desc()).all()
        return [_diff_to_dict(r) for r in rows]


def get_recent_diffs(days: int = 30,
                      severity: Optional[str] = None,
                      diff_type: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_session() as session:
        since = datetime.utcnow() - timedelta(days=days)
        q     = session.query(DocumentDiff).filter(DocumentDiff.detected_at >= since)
        if severity:
            q = q.filter(DocumentDiff.severity == severity)
        if diff_type:
            q = q.filter(DocumentDiff.diff_type == diff_type)
        return [_diff_to_dict(r) for r in q.order_by(DocumentDiff.detected_at.desc()).all()]


def get_unreviewed_diffs(limit: int = 50) -> List[Dict[str, Any]]:
    with get_session() as session:
        rows = (
            session.query(DocumentDiff)
            .filter(DocumentDiff.reviewed == False)          # noqa: E712
            .order_by(DocumentDiff.detected_at.desc())
            .limit(limit)
            .all()
        )
        return [_diff_to_dict(r) for r in rows]


def mark_diff_reviewed(diff_id: int) -> None:
    with get_session() as session:
        d = session.get(DocumentDiff, diff_id)
        if d:
            d.reviewed = True
            session.commit()


def _diff_to_dict(d: DocumentDiff) -> Dict[str, Any]:
    return {
        "id":                    d.id,
        "base_document_id":      d.base_document_id,
        "new_document_id":       d.new_document_id,
        "diff_type":             d.diff_type,
        "relationship_type":     d.relationship_type,
        "change_summary":        d.change_summary,
        "severity":              d.severity,
        "added_requirements":    d.added_requirements    or [],
        "removed_requirements":  d.removed_requirements  or [],
        "modified_requirements": d.modified_requirements or [],
        "definition_changes":    d.definition_changes    or [],
        "deadline_changes":      d.deadline_changes      or [],
        "penalty_changes":       d.penalty_changes       or [],
        "scope_changes":         d.scope_changes,
        "new_action_items":      d.new_action_items      or [],
        "obsolete_action_items": d.obsolete_action_items or [],
        "overall_assessment":    d.overall_assessment,
        "detected_at":           d.detected_at.isoformat() if d.detected_at else None,
        "reviewed":              d.reviewed,
    }


# ── DocumentLink CRUD ─────────────────────────────────────────────────────────

def save_link(base_doc_id: str, related_doc_id: str,
              link_type: str, notes: Optional[str] = None,
              created_by: str = "system") -> None:
    with get_session() as session:
        exists = session.execute(
            text("SELECT COUNT(*) FROM document_links "
                 "WHERE base_doc_id = :b AND related_doc_id = :r AND link_type = :t"),
            {"b": base_doc_id, "r": related_doc_id, "t": link_type},
        ).scalar()
        if exists:
            return
        session.add(DocumentLink(
            base_doc_id=base_doc_id, related_doc_id=related_doc_id,
            link_type=link_type, notes=notes, created_by=created_by,
        ))
        session.commit()


def get_links_for_document(doc_id: str) -> List[Dict[str, Any]]:
    with get_session() as session:
        rows = session.query(DocumentLink).filter(
            (DocumentLink.base_doc_id    == doc_id) |
            (DocumentLink.related_doc_id == doc_id)
        ).all()
        return [
            {
                "base_doc_id":    r.base_doc_id,
                "related_doc_id": r.related_doc_id,
                "link_type":      r.link_type,
                "notes":          r.notes,
                "created_at":     r.created_at.isoformat() if r.created_at else None,
                "created_by":     r.created_by,
            }
            for r in rows
        ]


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats() -> Dict[str, Any]:
    with get_session() as session:
        total_docs      = session.query(Document).count()
        total_summaries = session.query(Summary).count()
        federal_docs    = session.query(Document).filter_by(jurisdiction="Federal").count()
        total_diffs     = session.query(DocumentDiff).count()
        unreviewed      = session.query(DocumentDiff).filter_by(reviewed=False).count()
        critical_diffs  = session.query(DocumentDiff).filter_by(severity="Critical").count()
        high_diffs      = session.query(DocumentDiff).filter_by(severity="High").count()
        return {
            "total_documents":     total_docs,
            "total_summaries":     total_summaries,
            "federal_documents":   federal_docs,
            "state_documents":     total_docs - federal_docs,
            "pending_summaries":   total_docs - total_summaries,
            "total_diffs":         total_diffs,
            "unreviewed_diffs":    unreviewed,
            "critical_diffs":      critical_diffs,
            "high_severity_diffs": high_diffs,
        }
