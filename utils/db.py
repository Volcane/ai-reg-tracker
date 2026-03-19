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
    origin         = Column(String, default="api")   # api | pdf_auto | pdf_manual

    __table_args__ = (
        Index("ix_doc_jurisdiction", "jurisdiction"),
        Index("ix_doc_source",       "source"),
        Index("ix_doc_published",    "published_date"),
    )


class PdfMetadata(Base):
    """
    Stores metadata about PDFs that have been downloaded or manually ingested.
    One record per document that has associated PDF extraction data.
    """
    __tablename__ = "pdf_metadata"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    document_id        = Column(String, nullable=False, unique=True)
    pdf_path           = Column(Text)           # local file path
    pdf_url            = Column(Text)           # source URL (if downloaded)
    page_count         = Column(Integer)
    word_count         = Column(Integer)
    extraction_method  = Column(String)         # pdfplumber | pypdf
    extracted_at       = Column(DateTime, default=datetime.utcnow)
    origin             = Column(String)         # pdf_auto | pdf_manual

    __table_args__ = (
        Index("ix_pdf_document_id", "document_id"),
        Index("ix_pdf_origin",      "origin"),
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
    """
    Return documents joined with their summaries (if available).

    Uses a LEFT OUTER JOIN so documents without a summary still appear —
    they show with null summary fields until summarization runs.

    The date filter applies to whichever is more recent: published_date or
    fetched_at. This ensures documents with old or null published_date are
    still visible as long as they were fetched recently.
    """
    with get_session() as session:
        since = datetime.utcnow() - timedelta(days=days)

        # LEFT OUTER JOIN — documents without summaries still returned
        q = (
            session.query(Document, Summary)
            .outerjoin(Summary, Document.id == Summary.document_id)
            .filter(
                # Include if published recently OR fetched recently
                # Handles: null published_date, historically-dated pinned docs,
                # and documents fetched today that have old publication dates
                (Document.fetched_at >= since) |
                (Document.published_date >= since)
            )
        )
        if jurisdiction:
            q = q.filter(Document.jurisdiction == jurisdiction)

        results = []
        for doc, summ in q.order_by(Document.fetched_at.desc()).all():
            summary_fields = {
                "plain_english":   None,
                "requirements":    [],
                "recommendations": [],
                "action_items":    [],
                "deadline":        None,
                "impact_areas":    [],
                "urgency":         None,
                "relevance_score": None,
            }
            if summ:
                for k in summary_fields:
                    summary_fields[k] = getattr(summ, k)

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
                "fetched_at":     doc.fetched_at.isoformat() if doc.fetched_at else None,
                "summarized":     summ is not None,
                **summary_fields,
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


# ── Learning tables ──────────────────────────────────────────────────────────

class FeedbackEvent(Base):
    """
    Human feedback on a document's relevance.
    Drives source quality scoring and keyword weight adjustment.
    """
    __tablename__ = "feedback_events"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    document_id      = Column(String, nullable=False)
    feedback         = Column(String, nullable=False)  # relevant|not_relevant|partially_relevant
    reason           = Column(Text)
    source           = Column(String)
    agency           = Column(String)
    jurisdiction     = Column(String)
    doc_type         = Column(String)
    matched_keywords = Column(JSON)    # list[str] — keywords that triggered the fetch
    claude_score     = Column(Float)   # Claude's original relevance score
    user             = Column(String, default="user")
    recorded_at      = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_fb_document",    "document_id"),
        Index("ix_fb_source",      "source"),
        Index("ix_fb_feedback",    "feedback"),
        Index("ix_fb_recorded_at", "recorded_at"),
    )


class SourceProfile(Base):
    """
    Rolling quality profile for each data source and agency.
    Tracks positive/negative feedback counts and computed quality score.
    """
    __tablename__ = "source_profiles"

    source_key     = Column(String, primary_key=True)  # source name or "agency::<name>"
    profile_json   = Column(JSON, nullable=False)
    last_updated   = Column(DateTime, default=datetime.utcnow)


class KeywordWeights(Base):
    """
    Learned per-keyword weights for the pre-filter relevance score.
    Weights start at 1.0 and drift based on feedback.
    """
    __tablename__ = "keyword_weights"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    weights_json = Column(JSON, nullable=False)   # {keyword: float}
    updated_at   = Column(DateTime, default=datetime.utcnow)


class PromptAdaptation(Base):
    """
    Domain-specific additions to the Claude interpretation prompt,
    generated when false-positive patterns are detected.
    """
    __tablename__ = "prompt_adaptations"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    match_keys   = Column(JSON)     # {source, agency, jurisdiction} to match
    instruction  = Column(Text)     # the NOTE: instruction to prepend
    basis        = Column(Text)     # how many examples drove this
    active       = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)


class ObligationRegisterCache(Base):
    """
    Cached results from the ConsolidationAgent.
    Keyed by a hash of (jurisdictions, mode).
    """
    __tablename__ = "obligation_register_cache"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    cache_key    = Column(String, nullable=False, unique=True)
    jurisdictions= Column(JSON)      # list[str]
    mode         = Column(String)    # fast | full
    register_json= Column(JSON)      # list of consolidated obligation dicts
    item_count   = Column(Integer, default=0)
    computed_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_orc_cache_key", "cache_key"),)


class CompanyProfile(Base):
    """
    Stores a company's profile for gap analysis.
    Multiple profiles are supported (e.g. per business unit or product line).
    """
    __tablename__ = "company_profiles"

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    name                    = Column(String, nullable=False)   # e.g. "ACME Corp — Healthcare Division"
    industry_sector         = Column(String)
    company_size            = Column(String)
    operating_jurisdictions = Column(JSON)    # list[str]
    ai_systems              = Column(JSON)    # list[AISytem dicts]
    current_practices       = Column(JSON)    # governance practices dict
    existing_certifications = Column(JSON)    # list[str]
    primary_concerns        = Column(Text)
    recent_changes          = Column(Text)
    created_at              = Column(DateTime, default=datetime.utcnow)
    updated_at              = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_profile_name", "name"),
    )


class GapAnalysis(Base):
    """
    Stores the result of a gap analysis run against a company profile.
    History is preserved — each run produces a new record.
    """
    __tablename__ = "gap_analyses"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    profile_id       = Column(Integer, nullable=False)
    profile_name     = Column(String)
    jurisdictions    = Column(JSON)           # list[str] — scope of this run
    docs_examined    = Column(Integer, default=0)
    applicable_count = Column(Integer, default=0)
    gap_count        = Column(Integer, default=0)
    critical_count   = Column(Integer, default=0)
    posture_score    = Column(Integer, default=0)   # 0-100
    scope_json       = Column(JSON)           # Pass 1 output
    gaps_json        = Column(JSON)           # Pass 2 output
    model_used       = Column(String)
    generated_at     = Column(DateTime, default=datetime.utcnow)
    starred          = Column(Boolean, default=False)
    notes            = Column(Text)

    __table_args__ = (
        Index("ix_gap_profile_id",   "profile_id"),
        Index("ix_gap_generated_at", "generated_at"),
    )


class ThematicSynthesis(Base):
    """
    Stores the result of a cross-document thematic synthesis run.
    One record per (topic_key, generated_at) pair — history is preserved.
    """
    __tablename__ = "thematic_syntheses"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    topic_key        = Column(String, nullable=False)   # stable hash of topic + jurisdictions
    topic            = Column(Text, nullable=False)
    jurisdictions    = Column(JSON)                     # list[str]
    docs_used        = Column(Integer, default=0)
    doc_ids          = Column(JSON)                     # list[str]
    synthesis_json   = Column(JSON)                     # full synthesis output from Claude
    conflicts_json   = Column(JSON)                     # conflict detection output from Claude
    model_used       = Column(String)
    generated_at     = Column(DateTime, default=datetime.utcnow)
    starred          = Column(Boolean, default=False)   # user can star important syntheses
    notes            = Column(Text)                     # user annotations

    __table_args__ = (
        Index("ix_synth_topic_key",    "topic_key"),
        Index("ix_synth_generated_at", "generated_at"),
    )


class FetchHistory(Base):
    """
    Log of every fetch operation, used for adaptive scheduling.
    """
    __tablename__ = "fetch_history"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    source      = Column(String, nullable=False)
    new_count   = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    fetched_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_fh_source",     "source"),
        Index("ix_fh_fetched_at", "fetched_at"),
    )


# ── Learning CRUD ─────────────────────────────────────────────────────────────

def save_feedback(fb_dict: Dict[str, Any]) -> int:
    with get_session() as session:
        ev = FeedbackEvent(**{k: v for k, v in fb_dict.items() if hasattr(FeedbackEvent, k)})
        session.add(ev)
        session.commit()
        session.refresh(ev)
        return ev.id


def get_recent_feedback(days: int = 30, document_id: Optional[str] = None) -> List[Dict]:
    with get_session() as session:
        since = datetime.utcnow() - timedelta(days=days)
        q     = session.query(FeedbackEvent).filter(FeedbackEvent.recorded_at >= since)
        if document_id:
            q = q.filter(FeedbackEvent.document_id == document_id)
        rows  = q.order_by(FeedbackEvent.recorded_at.desc()).all()
        return [
            {
                "id":               r.id,
                "document_id":      r.document_id,
                "feedback":         r.feedback,
                "reason":           r.reason,
                "source":           r.source,
                "agency":           r.agency,
                "jurisdiction":     r.jurisdiction,
                "doc_type":         r.doc_type,
                "matched_keywords": r.matched_keywords or [],
                "claude_score":     r.claude_score,
                "recorded_at":      r.recorded_at.isoformat() if r.recorded_at else None,
            }
            for r in rows
        ]


def count_feedback_by_type() -> Dict[str, int]:
    with get_session() as session:
        from sqlalchemy import func
        rows = session.query(
            FeedbackEvent.feedback, func.count(FeedbackEvent.id)
        ).group_by(FeedbackEvent.feedback).all()
        return {fb: count for fb, count in rows}


def get_recent_false_positives(source: str, limit: int = 20) -> List[Dict]:
    with get_session() as session:
        since = datetime.utcnow() - timedelta(days=60)
        rows  = (
            session.query(FeedbackEvent)
            .filter(
                FeedbackEvent.feedback == "not_relevant",
                FeedbackEvent.source   == source,
                FeedbackEvent.recorded_at >= since,
            )
            .order_by(FeedbackEvent.recorded_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "document_id": r.document_id,
                "reason":      r.reason,
                "agency":      r.agency,
                "title":       None,   # caller can join if needed
            }
            for r in rows
        ]


def count_recent_false_positives(source: str, days: int = 30) -> int:
    with get_session() as session:
        since = datetime.utcnow() - timedelta(days=days)
        return (
            session.query(FeedbackEvent)
            .filter(
                FeedbackEvent.feedback == "not_relevant",
                FeedbackEvent.source   == source,
                FeedbackEvent.recorded_at >= since,
            )
            .count()
        )


def get_false_positive_patterns() -> List[Dict]:
    """Return source+agency combinations with high false-positive rates."""
    with get_session() as session:
        from sqlalchemy import func
        rows = (
            session.query(
                FeedbackEvent.source,
                FeedbackEvent.agency,
                func.count(FeedbackEvent.id).label("fp_count"),
            )
            .filter(FeedbackEvent.feedback == "not_relevant")
            .group_by(FeedbackEvent.source, FeedbackEvent.agency)
            .having(func.count(FeedbackEvent.id) >= 3)
            .order_by(func.count(FeedbackEvent.id).desc())
            .all()
        )
        return [{"source": r.source, "agency": r.agency, "fp_count": r.fp_count} for r in rows]


def is_known_false_positive_pattern(doc: Dict) -> bool:
    """Quick check: is this source+agency combination a known bad pattern?"""
    with get_session() as session:
        count = (
            session.query(FeedbackEvent)
            .filter(
                FeedbackEvent.feedback == "not_relevant",
                FeedbackEvent.source   == doc.get("source", ""),
                FeedbackEvent.agency   == (doc.get("agency") or ""),
            )
            .count()
        )
        return count >= 8   # 8 confirmed false positives = auto-block pattern


# ── Source profiles ───────────────────────────────────────────────────────────

def get_source_profile(source_key: str) -> Optional[Dict]:
    with get_session() as session:
        row = session.get(SourceProfile, source_key)
        return row.profile_json if row else None


def upsert_source_profile(source_key: str, profile: Dict) -> None:
    with get_session() as session:
        row = session.get(SourceProfile, source_key)
        if row:
            row.profile_json = profile
            row.last_updated = datetime.utcnow()
        else:
            session.add(SourceProfile(
                source_key   = source_key,
                profile_json = profile,
                last_updated = datetime.utcnow(),
            ))
        session.commit()


def get_all_source_profiles() -> Dict[str, Dict]:
    with get_session() as session:
        rows = session.query(SourceProfile).all()
        return {r.source_key: r.profile_json for r in rows}


# ── Keyword weights ───────────────────────────────────────────────────────────

def get_keyword_weights() -> Dict[str, float]:
    with get_session() as session:
        row = session.query(KeywordWeights).order_by(
            KeywordWeights.updated_at.desc()
        ).first()
        return row.weights_json if row else {}


def save_keyword_weights(weights: Dict[str, float]) -> None:
    with get_session() as session:
        # Single row — always replace
        session.query(KeywordWeights).delete()
        session.add(KeywordWeights(weights_json=weights, updated_at=datetime.utcnow()))
        session.commit()


# ── Prompt adaptations ────────────────────────────────────────────────────────

def get_prompt_adaptations(active_only: bool = True) -> List[Dict]:
    with get_session() as session:
        q = session.query(PromptAdaptation)
        if active_only:
            q = q.filter(PromptAdaptation.active == True)   # noqa: E712
        rows = q.order_by(PromptAdaptation.created_at.desc()).all()
        return [
            {
                "id":          r.id,
                "match_keys":  r.match_keys,
                "instruction": r.instruction,
                "basis":       r.basis,
                "active":      r.active,
                "created_at":  r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


def save_prompt_adaptation(adapt_dict: Dict) -> int:
    with get_session() as session:
        pa = PromptAdaptation(**{k: v for k, v in adapt_dict.items() if hasattr(PromptAdaptation, k)})
        session.add(pa)
        session.commit()
        session.refresh(pa)
        return pa.id


def toggle_prompt_adaptation(adapt_id: int, active: bool) -> None:
    with get_session() as session:
        row = session.get(PromptAdaptation, adapt_id)
        if row:
            row.active = active
            session.commit()


# ── Fetch history ─────────────────────────────────────────────────────────────

def log_fetch_event(source: str, new_count: int, total_count: int) -> None:
    with get_session() as session:
        session.add(FetchHistory(
            source=source, new_count=new_count,
            total_count=total_count, fetched_at=datetime.utcnow(),
        ))
        session.commit()


def get_fetch_history(days: int = 60) -> List[Dict]:
    with get_session() as session:
        since = datetime.utcnow() - timedelta(days=days)
        rows  = (
            session.query(FetchHistory)
            .filter(FetchHistory.fetched_at >= since)
            .order_by(FetchHistory.fetched_at.desc())
            .all()
        )
        return [
            {
                "source":      r.source,
                "new_count":   r.new_count,
                "total_count": r.total_count,
                "fetched_at":  r.fetched_at.isoformat() if r.fetched_at else None,
            }
            for r in rows
        ]


# ── Obligation register cache CRUD ───────────────────────────────────────────

def save_register_cache(cache_key: str, register: List[Dict[str, Any]]) -> None:
    with get_session() as session:
        row = session.query(ObligationRegisterCache).filter_by(
            cache_key=cache_key
        ).first()
        if row:
            row.register_json = register
            row.item_count    = len(register)
            row.computed_at   = datetime.utcnow()
        else:
            session.add(ObligationRegisterCache(
                cache_key     = cache_key,
                register_json = register,
                item_count    = len(register),
                computed_at   = datetime.utcnow(),
            ))
        session.commit()


def get_register_cache(cache_key: str,
                        max_age_hours: int = 24) -> Optional[List[Dict]]:
    with get_session() as session:
        since = datetime.utcnow() - timedelta(hours=max_age_hours)
        row   = session.query(ObligationRegisterCache).filter(
            ObligationRegisterCache.cache_key   == cache_key,
            ObligationRegisterCache.computed_at >= since,
        ).first()
        return row.register_json if row else None


def delete_register_cache(jurisdictions: Optional[List[str]] = None) -> int:
    """Delete cached register entries. Pass None to clear all."""
    with get_session() as session:
        q = session.query(ObligationRegisterCache)
        deleted = q.delete()
        session.commit()
        return deleted


# ── Company profile CRUD ─────────────────────────────────────────────────────

def save_profile(profile_dict: Dict[str, Any]) -> int:
    """Create or update a company profile. Returns the profile ID."""
    with get_session() as session:
        profile_id = profile_dict.get("id")
        if profile_id:
            row = session.get(CompanyProfile, profile_id)
            if row:
                for k, v in profile_dict.items():
                    if hasattr(row, k) and k != "id":
                        setattr(row, k, v)
                row.updated_at = datetime.utcnow()
                session.commit()
                return row.id
        # New profile
        row = CompanyProfile(**{
            k: v for k, v in profile_dict.items()
            if hasattr(CompanyProfile, k) and k != "id"
        })
        row.created_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def get_profile(profile_id: int) -> Optional[Dict[str, Any]]:
    with get_session() as session:
        row = session.get(CompanyProfile, profile_id)
        return _profile_to_dict(row) if row else None


def list_profiles() -> List[Dict[str, Any]]:
    with get_session() as session:
        rows = session.query(CompanyProfile).order_by(
            CompanyProfile.updated_at.desc()
        ).all()
        return [_profile_to_dict(r) for r in rows]


def delete_profile(profile_id: int) -> None:
    with get_session() as session:
        row = session.get(CompanyProfile, profile_id)
        if row:
            session.delete(row)
            session.commit()


def _profile_to_dict(row: CompanyProfile) -> Dict[str, Any]:
    return {
        "id":                      row.id,
        "name":                    row.name,
        "industry_sector":         row.industry_sector,
        "company_size":            row.company_size,
        "operating_jurisdictions": row.operating_jurisdictions or [],
        "ai_systems":              row.ai_systems or [],
        "current_practices":       row.current_practices or {},
        "existing_certifications": row.existing_certifications or [],
        "primary_concerns":        row.primary_concerns,
        "recent_changes":          row.recent_changes,
        "created_at":              row.created_at.isoformat() if row.created_at else None,
        "updated_at":              row.updated_at.isoformat() if row.updated_at else None,
    }


# ── Gap analysis CRUD ─────────────────────────────────────────────────────────

def save_gap_analysis(result: Dict[str, Any]) -> int:
    """Persist a gap analysis result. Returns the new row ID."""
    with get_session() as session:
        row = GapAnalysis(
            profile_id       = result.get("profile_id"),
            profile_name     = result.get("profile_name"),
            jurisdictions    = result.get("jurisdictions", []),
            docs_examined    = result.get("docs_examined", 0),
            applicable_count = result.get("applicable_count", 0),
            gap_count        = result.get("gap_count", 0),
            critical_count   = result.get("critical_count", 0),
            posture_score    = result.get("posture_score", 0),
            scope_json       = result.get("scope"),
            gaps_json        = result.get("gaps_result"),
            model_used       = result.get("model_used", ""),
            generated_at     = datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def get_gap_analysis(analysis_id: int) -> Optional[Dict[str, Any]]:
    with get_session() as session:
        row = session.get(GapAnalysis, analysis_id)
        return _gap_to_dict(row) if row else None


def list_gap_analyses(profile_id: Optional[int] = None,
                      limit: int = 20) -> List[Dict[str, Any]]:
    with get_session() as session:
        q = session.query(GapAnalysis)
        if profile_id:
            q = q.filter(GapAnalysis.profile_id == profile_id)
        rows = q.order_by(GapAnalysis.generated_at.desc()).limit(limit).all()
        return [_gap_to_dict(r, summary_only=True) for r in rows]


def star_gap_analysis(analysis_id: int, starred: bool = True) -> None:
    with get_session() as session:
        row = session.get(GapAnalysis, analysis_id)
        if row:
            row.starred = starred
            session.commit()


def annotate_gap_analysis(analysis_id: int, notes: str) -> None:
    with get_session() as session:
        row = session.get(GapAnalysis, analysis_id)
        if row:
            row.notes = notes
            session.commit()


def _gap_to_dict(row: GapAnalysis,
                  summary_only: bool = False) -> Dict[str, Any]:
    base = {
        "id":               row.id,
        "profile_id":       row.profile_id,
        "profile_name":     row.profile_name,
        "jurisdictions":    row.jurisdictions or [],
        "docs_examined":    row.docs_examined,
        "applicable_count": row.applicable_count,
        "gap_count":        row.gap_count,
        "critical_count":   row.critical_count,
        "posture_score":    row.posture_score,
        "model_used":       row.model_used,
        "generated_at":     row.generated_at.isoformat() if row.generated_at else None,
        "starred":          row.starred,
        "notes":            row.notes,
    }
    if not summary_only:
        base["scope"]       = row.scope_json
        base["gaps_result"] = row.gaps_json
    return base


# ── PDF metadata CRUD ────────────────────────────────────────────────────────

def save_pdf_metadata(meta: Dict[str, Any]) -> int:
    """Insert or replace a PDF metadata record."""
    with get_session() as session:
        # Upsert by document_id
        existing = (
            session.query(PdfMetadata)
            .filter_by(document_id=meta["document_id"])
            .first()
        )
        if existing:
            for k, v in meta.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
            session.commit()
            return existing.id
        row = PdfMetadata(**{k: v for k, v in meta.items() if hasattr(PdfMetadata, k)})
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def get_pdf_metadata(document_id: str) -> Optional[Dict[str, Any]]:
    with get_session() as session:
        row = (
            session.query(PdfMetadata)
            .filter_by(document_id=document_id)
            .first()
        )
        return _pdf_meta_to_dict(row) if row else None


def get_all_pdf_metadata() -> List[Dict[str, Any]]:
    with get_session() as session:
        rows = session.query(PdfMetadata).order_by(PdfMetadata.extracted_at.desc()).all()
        return [_pdf_meta_to_dict(r) for r in rows]


def _pdf_meta_to_dict(row: PdfMetadata) -> Dict[str, Any]:
    return {
        "id":                row.id,
        "document_id":       row.document_id,
        "pdf_path":          row.pdf_path,
        "pdf_url":           row.pdf_url,
        "page_count":        row.page_count,
        "word_count":        row.word_count,
        "extraction_method": row.extraction_method,
        "extracted_at":      row.extracted_at.isoformat() if row.extracted_at else None,
        "origin":            row.origin,
    }


# ── Synthesis CRUD ────────────────────────────────────────────────────────────

def save_synthesis(result: Dict[str, Any]) -> int:
    """Persist a thematic synthesis result. Returns the new row ID."""
    with get_session() as session:
        row = ThematicSynthesis(
            topic_key      = result.get("topic_key", ""),
            topic          = result.get("topic", ""),
            jurisdictions  = result.get("jurisdictions", []),
            docs_used      = result.get("docs_used", 0),
            doc_ids        = result.get("doc_ids", []),
            synthesis_json = result.get("synthesis"),
            conflicts_json = result.get("conflicts"),
            model_used     = result.get("model_used", ""),
            generated_at   = datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def get_existing_synthesis(topic_key: str, max_age_days: int = 7) -> Optional[Dict[str, Any]]:
    """Return the most recent synthesis for a topic_key if it is fresh enough."""
    with get_session() as session:
        since = datetime.utcnow() - timedelta(days=max_age_days)
        row   = (
            session.query(ThematicSynthesis)
            .filter(
                ThematicSynthesis.topic_key    == topic_key,
                ThematicSynthesis.generated_at >= since,
            )
            .order_by(ThematicSynthesis.generated_at.desc())
            .first()
        )
        return _synthesis_to_dict(row) if row else None


def get_synthesis_by_id(synthesis_id: int) -> Optional[Dict[str, Any]]:
    with get_session() as session:
        row = session.get(ThematicSynthesis, synthesis_id)
        return _synthesis_to_dict(row) if row else None


def get_recent_syntheses(limit: int = 20) -> List[Dict[str, Any]]:
    """Return recent synthesis records (summary only — no full JSON)."""
    with get_session() as session:
        rows = (
            session.query(ThematicSynthesis)
            .order_by(ThematicSynthesis.generated_at.desc())
            .limit(limit)
            .all()
        )
        return [_synthesis_to_dict(r, summary_only=True) for r in rows]


def star_synthesis(synthesis_id: int, starred: bool = True) -> None:
    with get_session() as session:
        row = session.get(ThematicSynthesis, synthesis_id)
        if row:
            row.starred = starred
            session.commit()


def annotate_synthesis(synthesis_id: int, notes: str) -> None:
    with get_session() as session:
        row = session.get(ThematicSynthesis, synthesis_id)
        if row:
            row.notes = notes
            session.commit()


def delete_synthesis(synthesis_id: int) -> None:
    with get_session() as session:
        row = session.get(ThematicSynthesis, synthesis_id)
        if row:
            session.delete(row)
            session.commit()


def _synthesis_to_dict(row: ThematicSynthesis,
                        summary_only: bool = False) -> Dict[str, Any]:
    base = {
        "id":           row.id,
        "topic_key":    row.topic_key,
        "topic":        row.topic,
        "jurisdictions": row.jurisdictions or [],
        "docs_used":    row.docs_used,
        "model_used":   row.model_used,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        "starred":      row.starred,
        "notes":        row.notes,
        "has_conflicts": bool(row.conflicts_json),
        "conflict_count": (
            len(row.conflicts_json.get("conflicts", []))
            if row.conflicts_json else 0
        ),
    }
    if not summary_only:
        base["synthesis"]  = row.synthesis_json
        base["conflicts"]  = row.conflicts_json
        base["doc_ids"]    = row.doc_ids or []
    return base


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
        total_feedback  = session.query(FeedbackEvent).count()
        not_relevant    = session.query(FeedbackEvent).filter_by(feedback="not_relevant").count()
        adaptations     = session.query(PromptAdaptation).filter_by(active=True).count()
        total_syntheses = session.query(ThematicSynthesis).count()
        total_pdfs      = session.query(PdfMetadata).count()
        pdf_manual      = session.query(PdfMetadata).filter_by(origin="pdf_manual").count()
        pdf_auto        = session.query(PdfMetadata).filter_by(origin="pdf_auto").count()
        total_profiles  = session.query(CompanyProfile).count()
        total_analyses  = session.query(GapAnalysis).count()
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
            "total_feedback":      total_feedback,
            "false_positives":     not_relevant,
            "prompt_adaptations":  adaptations,
            "total_syntheses":     total_syntheses,
            "total_pdfs":          total_pdfs,
            "pdf_manual":          pdf_manual,
            "pdf_auto":            pdf_auto,
            "company_profiles":    total_profiles,
            "gap_analyses":        total_analyses,
        }
