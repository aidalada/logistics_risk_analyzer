"""Rebuild orders for three-model ML pipeline

Revision ID: 2b3c4d5e6f70
Revises: 96fe24aa14ee
Create Date: 2026-04-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b3c4d5e6f70"
down_revision: Union[str, Sequence[str], None] = "96fe24aa14ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # We intentionally rebuild `orders` to match the new product schema.
    # Existing data will be dropped.
    op.drop_table("order_history")
    op.drop_table("orders")

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="New"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),

        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("freight_value", sa.Float(), nullable=False),
        sa.Column("weight_g", sa.Float(), nullable=False),
        sa.Column("length_cm", sa.Float(), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("width_cm", sa.Float(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("payment_type", sa.String(), nullable=False),
        sa.Column("installments", sa.Integer(), nullable=False),
        sa.Column("customer_lat", sa.Float(), nullable=False),
        sa.Column("customer_lng", sa.Float(), nullable=False),
        sa.Column("seller_lat", sa.Float(), nullable=False),
        sa.Column("seller_lng", sa.Float(), nullable=False),
        sa.Column("purchase_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_delivery_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("customer_state", sa.String(), nullable=False),

        sa.Column("delay_probability", sa.Float(), nullable=False),
        sa.Column("damage_probability", sa.Float(), nullable=False),
        sa.Column("cancel_probability", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),

        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_id"), "orders", ["id"], unique=False)
    op.create_index(op.f("ix_orders_owner_id"), "orders", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_owner_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_id"), table_name="orders")
    op.drop_table("orders")

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cargo_description", sa.String(), nullable=False),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("distance", sa.Float(), nullable=True),
        sa.Column("cargo_type", sa.Integer(), nullable=True),
        sa.Column("delivery_date", sa.String(), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("driver_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["driver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_id"), "orders", ["id"], unique=False)

    op.create_table(
        "order_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("old_status", sa.String(), nullable=True),
        sa.Column("new_status", sa.String(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_history_id"), "order_history", ["id"], unique=False)

