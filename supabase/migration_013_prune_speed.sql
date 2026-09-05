-- 정리 쿼리 가속: 보호 여부 확인(NOT EXISTS)과 후보 선정에 쓰이는 인덱스

create index if not exists user_papers_paper_idx     on public.user_papers (paper_id);
create index if not exists view_history_paper_idx    on public.view_history (paper_id);
create index if not exists comments_paper_only_idx   on public.comments (paper_id);
create index if not exists recommendations_paper_idx on public.recommendations (paper_id);

-- 후보(요약 없음 + 초록 있음)를 발행일 순으로 빨리 찾기 위한 부분 인덱스
create index if not exists papers_prune_candidate_idx
  on public.papers (pub_date asc nulls first)
  where summarized_at is null and abstract is not null;

-- 남은 후보 수 (진행 상황 확인용 — DB 용량은 VACUUM 전까지 즉시 줄지 않으므로 이 값으로 판단)
create or replace function public.prunable_count(keep_days int default 365)
returns bigint language sql stable security definer as $$
  select count(*) from public.papers p
  where p.summarized_at is null
    and p.abstract is not null and p.abstract <> ''
    and coalesce(p.pub_date, current_date) < current_date - keep_days
    and not exists (select 1 from public.user_papers up where up.paper_id = p.id
                    and (up.is_bookmarked or up.is_read or (up.note is not null and up.note <> '')))
    and not exists (select 1 from public.view_history v where v.paper_id = p.id)
    and not exists (select 1 from public.comments c where c.paper_id = p.id)
    and not exists (select 1 from public.recommendations r where r.paper_id = p.id);
$$;

analyze public.papers;
