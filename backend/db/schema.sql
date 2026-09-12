create extension if not exists vector;

-- Drops the ivfflat index from an earlier version of this schema, built
-- when the table had only a handful of rows — its cluster centroids are
-- badly calibrated for the real dataset and hurt recall. See the note
-- below for when/how to add a proper one back once the table is large.
drop index if exists conversations_embedding_idx;

-- Resolved historical conversations, used as retrieval evidence.
create table if not exists conversations (
    id                bigserial primary key,
    conversation_id   text not null unique,
    brand             text not null,
    customer_message  text not null,
    brand_reply       text not null,
    intent            text,
    embedding         vector(384) not null,  -- dim of the Pinecone llama-text-embed-v2 model
    metadata          jsonb not null default '{}'::jsonb,
    created_at        timestamptz not null default now()
);

create index if not exists conversations_brand_idx
    on conversations (brand);

-- No vector index (ivfflat/hnsw) at this dataset scale (a few thousand
-- rows): pgvector's exact sequential scan is already fast and always
-- exact here, and an ivfflat index built on a near-empty/small table has
-- badly calibrated clusters (hurts recall) until it's rebuilt. If this
-- table grows past ~50k-100k rows, add one and rebuild after bulk loads:
--
--   drop index if exists conversations_embedding_idx;
--   create index conversations_embedding_idx
--       on conversations using ivfflat (embedding vector_cosine_ops)
--       with (lists = <rows / 1000, minimum ~10>);
--   reindex index conversations_embedding_idx;  -- re-run after any large bulk insert

-- Cosine-similarity search over `conversations`, optionally scoped to one brand.
create or replace function match_conversations(
    query_embedding vector(384),
    match_count int,
    filter_brand text default null
)
returns table (
    conversation_id  text,
    brand            text,
    customer_message text,
    brand_reply      text,
    intent           text,
    metadata         jsonb,
    similarity       float
)
language sql stable as $$
    select conversation_id, brand, customer_message, brand_reply, intent, metadata,
           1 - (embedding <=> query_embedding) as similarity
    from conversations
    where filter_brand is null or brand = filter_brand
    order by embedding <=> query_embedding
    limit match_count;
$$;

-- One row per /analyze call, for auditing and offline evaluation.
create table if not exists predictions (
    id                bigserial primary key,
    customer_message  text not null,
    brand             text not null,
    intent            text,
    confidence        float,
    reply             text,
    decision          text,
    reason            text,
    evidence          jsonb not null default '[]'::jsonb,
    safety_checks     jsonb not null default '{}'::jsonb,
    created_at        timestamptz not null default now()
);

create index if not exists predictions_brand_idx
    on predictions (brand);

create index if not exists predictions_created_at_idx
    on predictions (created_at desc);

-- Per-brand intent label definitions (used to steer/validate classification).
create table if not exists intents (
    id          bigserial primary key,
    brand       text not null,
    intent      text not null,
    description text,
    unique (brand, intent)
);

create index if not exists intents_brand_idx
    on intents (brand);
