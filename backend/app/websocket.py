"""WebSocket manager for real-time grading notifications."""
import json
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import JWTError, jwt
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections per user."""

    def __init__(self):
        # user_id -> list of WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected: user {user_id} (total: {self.count()})")

    def disconnect(self, user_id: int, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected: user {user_id} (total: {self.count()})")

    async def send_to_user(self, user_id: int, message: dict):
        """Send a JSON message to all connections of a specific user."""
        if user_id in self.active_connections:
            dead = []
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(user_id, ws)

    async def broadcast(self, message: dict):
        """Send a JSON message to ALL connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)

    async def notify_grade_ready(self, user_id: int, exam_id: int, score: float, total_marks: float):
        """Send a grading notification to a specific student."""
        message = {
            "type": "grade_ready",
            "exam_id": exam_id,
            "score": score,
            "total_marks": total_marks,
            "percentage": round((score / total_marks) * 100, 2) if total_marks > 0 else 0,
            "message": f"Your exam has been graded! Score: {score}/{total_marks}",
        }
        await self.send_to_user(user_id, message)

    async def notify_batch_graded(self, user_id: int, exam_id: int, results: List[dict]):
        """Notify a student that their full exam submission has been graded."""
        total_score = sum(r.get("score", 0) for r in results)
        total_marks = sum(r.get("marks", 0) for r in results)
        message = {
            "type": "exam_graded",
            "exam_id": exam_id,
            "question_count": len(results),
            "total_score": total_score,
            "total_marks": total_marks,
            "percentage": round((total_score / total_marks) * 100, 2) if total_marks > 0 else 0,
            "results": results,
            "message": f"Exam grading complete! Total: {total_score}/{total_marks}",
        }
        await self.send_to_user(user_id, message)

    def count(self) -> int:
        """Total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    def user_count(self) -> int:
        """Number of unique connected users."""
        return len(self.active_connections)


# Global singleton
manager = ConnectionManager()


def _verify_ws_token(token: str) -> Optional[int]:
    """Verify a JWT token and return user_id, or None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return int(payload.get("sub", 0))
    except (JWTError, ValueError, TypeError):
        return None


@router.websocket("/ws/grade/{user_id}")
async def websocket_grade_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(..., description="JWT access token"),
):
    """WebSocket endpoint for real-time grading notifications.
    
    Connect with: ws://host/ws/grade/{user_id}?token=<jwt_access_token>
    """
    # Verify the token belongs to this user
    verified_id = _verify_ws_token(token)
    if verified_id is None or verified_id != user_id:
        await websocket.close(code=4001, reason="Invalid or mismatched token")
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive; handle client pings/messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id, websocket)
