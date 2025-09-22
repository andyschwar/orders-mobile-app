from __future__ import annotations

from typing import List
from datetime import date

from sqlalchemy.orm import Session

# Import models with explicit names for clarity
from models.database import OrderItem, Delivery, DeliveryTerm


def _reset_terms_state(terms: List[DeliveryTerm]) -> None:

    for term in terms:
        term.delivered_quantity = 0
        term.is_complete = False


def _sort_terms(terms: List[DeliveryTerm]) -> List[DeliveryTerm]:

    return sorted(terms, key=lambda t: (t.planned_date, t.id))


def _sort_deliveries(deliveries: List[Delivery]) -> List[Delivery]:

    return sorted(deliveries, key=lambda d: (d.delivery_date, d.id))


def pair_deliveries_to_terms_for_item(session: Session, order_item: OrderItem) -> None:
    """
    Reassign deliveries for a single OrderItem to its DeliveryTerms in chronological order.

    Strategy:
    - Reset all terms' delivered quantities and completion flags
    - Unassign delivery_term_id on all deliveries for the item
    - Iterate deliveries by delivery_date and assign quantities to earliest terms
      with remaining capacity (planned_quantity - delivered_quantity)
    - Update each term's delivered_quantity and is_complete accordingly
    - Persist changes to the session (caller should commit)
    """

    if not hasattr(order_item, "delivery_terms") or not order_item.delivery_terms:
        # Nothing to pair if there are no terms
        return

    terms = _sort_terms(list(order_item.delivery_terms))
    deliveries = _sort_deliveries(list(order_item.deliveries))

    # Reset terms state
    _reset_terms_state(terms)

    # Unassign all deliveries from terms before re-pairing
    for d in deliveries:
        d.delivery_term_id = None

    # Greedy pairing of deliveries into terms by date order
    for delivery in deliveries:
        remaining_qty = delivery.quantity
        for term in terms:
            term_remaining_capacity = max(term.planned_quantity - term.delivered_quantity, 0)
            if term_remaining_capacity <= 0:
                continue

            assign_qty = min(remaining_qty, term_remaining_capacity)
            if assign_qty <= 0:
                continue

            # Assign this delivery to the term if not already assigned
            delivery.delivery_term_id = term.id

            # Update term delivered quantity
            term.delivered_quantity += assign_qty
            term.is_complete = term.delivered_quantity >= term.planned_quantity

            remaining_qty -= assign_qty
            if remaining_qty <= 0:
                break

        # If delivery still has remainder and all terms are full, leave delivery_term_id as last eligible term
        # (or None if none eligible). This indicates overflow beyond planned terms.

    # No explicit return; objects are mutated in-place within the session.


def pair_deliveries_to_terms_for_order_items(session: Session, order_items: List[OrderItem]) -> None:

    for oi in order_items:
        pair_deliveries_to_terms_for_item(session, oi)



