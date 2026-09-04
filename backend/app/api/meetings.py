"""Meetings API — CRUD, availability, and RSVP."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.tasks import Meeting, MeetingAttendee
from app.security import get_current_user

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    start_time: str = Field(..., description="ISO datetime")
    end_time: str = Field(..., description="ISO datetime")
    location: str = ""
    meeting_url: str = ""
    attendee_ids: list[str] = []


class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    meeting_url: Optional[str] = None


class MeetingResponse(BaseModel):
    id: str
    title: str
    description: str
    created_by: str
    start_time: str
    end_time: str
    location: str
    meeting_url: str
    attendee_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


class MeetingAttendeeResponse(BaseModel):
    id: str
    meeting_id: str
    user_id: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[MeetingResponse])
def list_meetings(
    start_after: Optional[str] = Query(None, description="ISO datetime filter"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List meetings for the organization."""
    q = db.query(Meeting).filter(Meeting.org_id == user.org_id)
    if start_after:
        q = q.filter(Meeting.start_time >= start_after)
    meetings = q.order_by(Meeting.start_time).offset(offset).limit(limit).all()
    result = []
    for m in meetings:
        count = db.query(MeetingAttendee).filter(MeetingAttendee.meeting_id == m.id).count()
        resp = MeetingResponse.model_validate(m).model_dump(mode="json")
        resp["attendee_count"] = count
        result.append(resp)
    return result


@router.post("", response_model=MeetingResponse, status_code=201)
def create_meeting(data: MeetingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new meeting."""
    meeting = Meeting(
        org_id=user.org_id,
        title=data.title,
        description=data.description,
        created_by=user.id,
        start_time=data.start_time,
        end_time=data.end_time,
        location=data.location,
        meeting_url=data.meeting_url,
    )
    db.add(meeting)
    db.flush()

    # Add creator as accepted attendee
    db.add(MeetingAttendee(meeting_id=meeting.id, user_id=user.id, status="accepted"))

    # Add other attendees
    for uid in data.attendee_ids:
        if uid != user.id:
            db.add(MeetingAttendee(meeting_id=meeting.id, user_id=uid, status="pending"))

    db.commit()
    db.refresh(meeting)
    resp = MeetingResponse.model_validate(meeting).model_dump(mode="json")
    resp["attendee_count"] = len(data.attendee_ids) + 1
    return resp


@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a single meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.org_id == user.org_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    count = db.query(MeetingAttendee).filter(MeetingAttendee.meeting_id == meeting.id).count()
    resp = MeetingResponse.model_validate(meeting).model_dump(mode="json")
    resp["attendee_count"] = count
    return resp


@router.put("/{meeting_id}", response_model=MeetingResponse)
def update_meeting(meeting_id: str, data: MeetingUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.org_id == user.org_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(meeting, field, value)
    db.commit()
    db.refresh(meeting)
    return MeetingResponse.model_validate(meeting).model_dump(mode="json")


@router.delete("/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.org_id == user.org_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    db.delete(meeting)
    db.commit()


@router.post("/{meeting_id}/rsvp")
def rsvp_meeting(meeting_id: str, status: str = Query(..., pattern="^(accepted|declined|tentative)$"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """RSVP to a meeting."""
    attendee = db.query(MeetingAttendee).filter(
        MeetingAttendee.meeting_id == meeting_id,
        MeetingAttendee.user_id == user.id,
    ).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="You are not an attendee of this meeting")
    attendee.status = status
    db.commit()
    return {"status": status}


@router.get("/{meeting_id}/attendees", response_model=list[MeetingAttendeeResponse])
def list_attendees(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List attendees for a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.org_id == user.org_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    attendees = db.query(MeetingAttendee).filter(MeetingAttendee.meeting_id == meeting_id).all()
    return [MeetingAttendeeResponse.model_validate(a).model_dump(mode="json") for a in attendees]
