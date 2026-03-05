-- Migration 040: Hook Library
-- Slice 102 (Fix F) — user-visible, editable hook library.
-- Agents pull from this table before writing. Users can add, edit, delete hooks.
-- Auto-populated: every approved post's opening line is saved as a hook.

create table if not exists hook_library (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references auth.users(id) on delete cascade,
    brand_id        uuid references personal_brands(id) on delete cascade,
    hook_text       text not null,
    hook_type       text not null default 'custom',
    -- hook_type values: anxiety | benefit | story | competitor | belief | curiosity | custom
    source          text default 'manual',
    -- source values: manual | pipeline_approved | brand_chat | agent
    times_used      integer not null default 0,
    engagement_score float,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- Indexes
create index if not exists hook_library_user_idx      on hook_library(user_id);
create index if not exists hook_library_brand_idx     on hook_library(brand_id);
create index if not exists hook_library_type_idx      on hook_library(hook_type);
create index if not exists hook_library_times_used_idx on hook_library(times_used desc);

-- RLS
alter table hook_library enable row level security;

create policy "Users manage own hooks"
    on hook_library for all
    using (user_id = auth.uid())
    with check (user_id = auth.uid());

-- Increment times_used when an agent uses a hook
create or replace function increment_hook_usage(hook_ids uuid[])
returns void language plpgsql security definer as $$
begin
    update hook_library
    set times_used = times_used + 1,
        updated_at = now()
    where id = any(hook_ids);
end;
$$;

-- Updated_at trigger
create or replace function update_hook_library_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger hook_library_updated_at
    before update on hook_library
    for each row execute function update_hook_library_updated_at();
