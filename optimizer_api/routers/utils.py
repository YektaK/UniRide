from typing import List, Dict
from fastapi import APIRouter, Query

from models.schemas import (
    TimeWindow, TripDirection, WeeklyScheduleEntry, StudentNode
)
from utils.time_window_extractor import TimeWindowExtractor

router = APIRouter(prefix="/api/v1", tags=["Utils"])

@router.post("/extract-time-windows", response_model=Dict[str, TimeWindow])
def extract_time_windows(
    entries: List[WeeklyScheduleEntry],
    direction: TripDirection = Query(..., description="pickup or dropoff"),
    target_day: str = Query(..., description="Day of week (monday, tuesday, etc.)"),
    window_minutes: int = Query(30, description="Time window size in minutes")
) -> Dict[str, TimeWindow]:
    extractor = TimeWindowExtractor(window_minutes=window_minutes)
    filtered_entries = [e for e in entries if e.dayOfWeek.lower() == target_day.lower()]
    
    if not filtered_entries:
        return {}
    
    time_windows = {}
    for entry in filtered_entries:
        tw = extractor.extract(entry, direction)
        time_windows[entry.id] = tw
    
    return time_windows

@router.post("/schedule-to-students", response_model=List[StudentNode])
def convert_schedule_to_students(
    entries: List[WeeklyScheduleEntry],
    target_day: str = Query(..., description="Day of week"),
    user_mapping: Dict[str, Dict] = None
) -> List[StudentNode]:
    students = []
    for entry in entries:
        if entry.dayOfWeek.lower() != target_day.lower():
            continue
        
        user_info = user_mapping.get(entry.id, {}) if user_mapping else {}
        
        student = StudentNode(
            id=entry.id,
            name=user_info.get("name", ""),
            location_code=user_info.get("location_code", "So1"),
            disability_type=user_info.get("disability_type", "So"),
            pickup_time=entry.startTime,
            dropoff_time=entry.endTime
        )
        students.append(student)
    
    return students
