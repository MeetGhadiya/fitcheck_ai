"""FitCheck AI — Full DB Migration (with credits)"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None

def upgrade():
    op.create_table('users',
        sa.Column('id',              sa.String, primary_key=True),
        sa.Column('email',           sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=True),
        sa.Column('full_name',       sa.String(255), nullable=True),
        sa.Column('avatar_url',      sa.Text, nullable=True),
        sa.Column('plan',            sa.String(20),  nullable=False, server_default='free'),
        sa.Column('status',          sa.String(20),  nullable=False, server_default='active'),
        sa.Column('is_active',       sa.Boolean, server_default='true'),
        sa.Column('is_admin',        sa.Boolean, server_default='false'),
        # Credits
        sa.Column('credits',                 sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_credits_purchased', sa.Integer, server_default='0'),
        sa.Column('total_tryons',            sa.Integer, server_default='0'),
        # Measurements
        sa.Column('height_cm',  sa.Integer, nullable=True),
        sa.Column('weight_kg',  sa.Integer, nullable=True),
        sa.Column('age',        sa.Integer, nullable=True),
        sa.Column('body_type',  sa.String(50), nullable=True),
        # Auth
        sa.Column('google_id',      sa.String(255), nullable=True, unique=True),
        sa.Column('auth_provider',  sa.String(50), server_default='email'),
        # Timestamps
        sa.Column('created_at',    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at',    sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table('credit_transactions',
        sa.Column('id',                  sa.String, primary_key=True),
        sa.Column('user_id',             sa.String, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type',                sa.String(20), nullable=False),
        sa.Column('credits',             sa.Integer, nullable=False),
        sa.Column('balance_after',       sa.Integer, nullable=False),
        sa.Column('description',         sa.String(255), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(255), nullable=True),
        sa.Column('amount_inr',          sa.Float, nullable=True),
        sa.Column('created_at',          sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_credit_txns_user_id', 'credit_transactions', ['user_id'])

    op.create_table('tryons',
        sa.Column('id',                sa.String, primary_key=True),
        sa.Column('user_id',           sa.String, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('person_image_url',  sa.Text, nullable=False),
        sa.Column('product_image_url', sa.Text, nullable=False),
        sa.Column('product_type',      sa.String(50), server_default='clothing'),
        sa.Column('product_name',      sa.String(255), nullable=True),
        sa.Column('product_url',       sa.Text, nullable=True),
        sa.Column('height_cm',         sa.Integer, nullable=True),
        sa.Column('weight_kg',         sa.Integer, nullable=True),
        sa.Column('age',               sa.Integer, nullable=True),
        sa.Column('body_type',         sa.String(50), nullable=True),
        sa.Column('status',            sa.String(20), server_default='pending'),
        sa.Column('ai_engine',         sa.String(30), nullable=True),
        sa.Column('credits_used',      sa.Integer, server_default='0'),
        sa.Column('render_time_ms',    sa.Integer, nullable=True),
        sa.Column('fit_score',         sa.Float, nullable=True),
        sa.Column('recommended_size',  sa.String(20), nullable=True),
        sa.Column('ai_notes',          sa.Text, nullable=True),
        sa.Column('result_front_url',  sa.Text, nullable=True),
        sa.Column('result_side_url',   sa.Text, nullable=True),
        sa.Column('result_back_url',   sa.Text, nullable=True),
        sa.Column('result_3q_url',     sa.Text, nullable=True),
        sa.Column('is_saved',          sa.Boolean, server_default='false'),
        sa.Column('is_flagged',        sa.Boolean, server_default='false'),
        sa.Column('error_message',     sa.Text, nullable=True),
        sa.Column('created_at',        sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at',      sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_tryons_user_id', 'tryons', ['user_id'])

    op.create_table('products',
        sa.Column('id',           sa.String, primary_key=True),
        sa.Column('source_url',   sa.Text, unique=True, nullable=False),
        sa.Column('name',         sa.String(500), nullable=True),
        sa.Column('brand',        sa.String(255), nullable=True),
        sa.Column('image_url',    sa.Text, nullable=True),
        sa.Column('image_s3_url', sa.Text, nullable=True),
        sa.Column('price',        sa.Float, nullable=True),
        sa.Column('currency',     sa.String(10), server_default='INR'),
        sa.Column('category',     sa.String(100), nullable=True),
        sa.Column('created_at',   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('products')
    op.drop_table('tryons')
    op.drop_table('credit_transactions')
    op.drop_table('users')
