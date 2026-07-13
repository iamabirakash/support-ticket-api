from sqlalchemy.orm import Session

from app.config import settings
from app.models import Queue, Ticket
from app.schemas import TicketBulkEntry, TicketCreate, TicketCreateStandalone


def _ensure_queue_capacity(queue: Queue, quantity: int) -> None:
    new_total = queue.current_ticket_count + quantity
    if new_total > queue.capacity:
        raise ValueError("capacity_exceeded")
    if settings.MAX_TICKETS_PER_QUEUE is not None and new_total > settings.MAX_TICKETS_PER_QUEUE:
        raise ValueError("capacity_exceeded")


def create_ticket(db: Session, data: TicketCreateStandalone) -> Ticket:
    if data.queue_id:
        queue = db.query(Queue).filter(Queue.id == data.queue_id).first()
        if not queue:
            raise ValueError("queue_not_found")
        _ensure_queue_capacity(queue, data.quantity)
        ticket = Ticket(
            title=data.title,
            complexity=data.complexity,
            queue_id=data.queue_id,
            quantity=data.quantity,
        )
        db.add(ticket)
        queue.current_ticket_count += data.quantity
    else:
        ticket = Ticket(
            title=data.title,
            complexity=data.complexity,
            queue_id=None,
            quantity=data.quantity,
        )
        db.add(ticket)

    db.commit()
    db.refresh(ticket)
    return ticket


def add_ticket_to_queue(db: Session, queue_id: str, data: TicketCreate) -> Ticket:
    queue = db.query(Queue).filter(Queue.id == queue_id).first()
    if not queue:
        raise ValueError("queue_not_found")
    _ensure_queue_capacity(queue, data.quantity)
    ticket = Ticket(
        title=data.title,
        complexity=data.complexity,
        queue_id=queue_id,
        quantity=data.quantity,
    )
    db.add(ticket)
    queue.current_ticket_count += data.quantity
    db.commit()
    db.refresh(ticket)
    return ticket


def bulk_add_tickets(db: Session, queue_id: str, entries: list[TicketBulkEntry]) -> int:
    queue = db.query(Queue).filter(Queue.id == queue_id).first()
    if not queue:
        raise ValueError("queue_not_found")
    total_quantity = sum(entry.quantity for entry in entries)
    _ensure_queue_capacity(queue, total_quantity)

    for entry in entries:
        ticket = Ticket(
            title=entry.title,
            complexity=entry.complexity,
            queue_id=queue_id,
            quantity=entry.quantity,
        )
        db.add(ticket)
        queue.current_ticket_count += entry.quantity
    db.commit()
    return len(entries)


def list_tickets_by_queue(db: Session, queue_id: str) -> list[Ticket]:
    queue = db.query(Queue).filter(Queue.id == queue_id).first()
    if not queue:
        raise ValueError("queue_not_found")
    return list(queue.tickets)


def get_ticket_by_id(db: Session, ticket_id: str) -> Ticket | None:
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()


def update_ticket_complexity(db: Session, ticket_id: str, complexity: int) -> None:
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise ValueError("ticket_not_found")
    ticket.complexity = complexity
    db.commit()


def remove_ticket_quantity(
    db: Session, queue_id: str, ticket_id: str, quantity: int | None
) -> None:
    queue = db.query(Queue).filter(Queue.id == queue_id).first()
    if not queue:
        raise ValueError("queue_not_found")
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.queue_id == queue_id).first()
    if not ticket:
        raise ValueError("ticket_not_found")
    if quantity is not None:
        to_remove = min(quantity, ticket.quantity)
        ticket.quantity -= to_remove
        queue.current_ticket_count -= to_remove
        if ticket.quantity <= 0:
            db.delete(ticket)
    else:
        queue.current_ticket_count -= ticket.quantity
        db.delete(ticket)
    db.commit()


def bulk_remove_tickets(
    db: Session, queue_id: str, ticket_ids: list[str] | None
) -> None:
    queue = db.query(Queue).filter(Queue.id == queue_id).first()
    if not queue:
        raise ValueError("queue_not_found")
    if ticket_ids is not None:
        tickets = db.query(Ticket).filter(
            Ticket.queue_id == queue_id,
            Ticket.id.in_(ticket_ids),
        ).all()
        for ticket in tickets:
            queue.current_ticket_count -= ticket.quantity
            db.delete(ticket)
    else:
        for ticket in list(queue.tickets):
            queue.current_ticket_count -= ticket.quantity
            db.delete(ticket)
    db.commit()
