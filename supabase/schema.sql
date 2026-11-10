-- supabase/schema.sql
-- Sets up the database for event submissions.
--
-- HOW TO USE: in Supabase, open "SQL Editor", paste this whole file,
-- change the email address in step 5 to YOUR email, and press "Run".
-- (It's safe to run once. See README.md for the full setup.)
--
-- What it makes:
--   events         every submitted event (pending, approved or rejected)
--   reviewers      the email address(es) allowed to review
--   public_events  a read-only list of APPROVED events, without any
--                  private details, for the website to show


-- 1. The events table ------------------------------------------------------
-- The limits here match the submit form, so bad data can't sneak in even
-- if someone skips the form.
create table if not exists public.events (
  id                uuid primary key default gen_random_uuid(),
  status            text not null default 'pending'
                    check (status in ('pending', 'approved', 'rejected')),
  title             text not null check (char_length(title) between 1 and 60),
  venue_name        text not null check (char_length(venue_name) between 1 and 60),
  address           text not null check (char_length(address) between 5 and 200),
  date              date not null,
  start_time        time not null,
  end_time          time,
  category          text not null check (category in
                    ('Music', 'Art', 'Markets', 'Food and Drink', 'Film', 'Comedy', 'Community', 'Workshops')),
  short_description text not null check (char_length(short_description) between 1 and 200),
  long_description  text check (long_description is null or char_length(long_description) <= 1000),
  link              text not null check (link ~* '^https?://' and char_length(link) <= 500),
  instagram_handle  text check (instagram_handle is null or char_length(instagram_handle) <= 31),
  submitter_email   text check (submitter_email is null or char_length(submitter_email) <= 254),  -- PRIVATE
  latitude          numeric,   -- filled in when the event is approved
  longitude         numeric,
  slug              text unique,
  created_at        timestamptz not null default now(),
  reviewed_at       timestamptz
);

create index if not exists events_status_date on public.events (status, date);


-- 2. Who can review --------------------------------------------------------
create table if not exists public.reviewers (
  email text primary key
);

-- "Is the person who's logged in a reviewer?" Used by the rules below.
-- (security definer lets it read the reviewers list, which nobody else can.)
create or replace function public.is_reviewer()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.reviewers
    where lower(email) = lower(auth.jwt() ->> 'email')
  );
$$;


-- 3. The rules (Row Level Security) ------------------------------------------
-- With RLS on and no rule for the public, visitors can't read or change
-- the events table at all. New submissions come in only through the
-- "submit-event" function, which checks the spam test first.
alter table public.events enable row level security;
alter table public.reviewers enable row level security;

drop policy if exists "Reviewers can do everything" on public.events;
create policy "Reviewers can do everything" on public.events
  for all to authenticated
  using (public.is_reviewer())
  with check (public.is_reviewer());

-- Belt and braces: take away the default table permissions from the
-- public ("anon") role, and from logged-in users for the reviewers list.
revoke all on public.events from anon;
revoke all on public.reviewers from anon, authenticated;


-- 4. The public list of approved events --------------------------------------
-- The website reads this. It only has approved events from yesterday
-- onwards, and leaves out the submitter's email and other private bits.
create or replace view public.public_events as
  select id, title, venue_name, address, date, start_time, end_time, category,
         short_description, long_description, link, instagram_handle,
         latitude, longitude, slug
  from public.events
  where status = 'approved'
    and date >= (now() at time zone 'America/New_York')::date - 1;

grant select on public.public_events to anon, authenticated;


-- 5. Add yourself as the reviewer ------------------------------------------
-- CHANGE THIS to the email you'll log in with (the same one you use when
-- you create your login under Authentication -> Users).
insert into public.reviewers (email)
values ('your-email@example.com')
on conflict do nothing;
