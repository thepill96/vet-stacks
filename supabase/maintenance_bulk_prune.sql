-- ============================================================
-- 대량 정리 (한 번에 실행). Supabase SQL Editor에 통째로 붙여넣고 Run.
-- 수만 편을 한꺼번에 처리할 때 사용합니다. 평소 소량 정리는 매일 작업이 알아서 합니다.
--
-- 하는 일: 오래됐고 아무도 손대지 않았으며 요약도 없는 논문의 '초록만' 비웁니다.
--          제목·저자·저널·발행일·분야·PMID는 그대로 남고, 누군가 그 논문을 열면
--          PubMed에서 초록을 자동으로 되받아 옵니다.
--
-- 소요: 8만 편 기준 3~10분. 실행 중에는 사이트가 느려질 수 있습니다.
-- ============================================================

-- 0) 이 세션의 제한 시간을 넉넉히
set statement_timeout = '30min';
set lock_timeout = '2min';

-- 1) 전문검색 인덱스를 잠시 내린다 (이게 있으면 대량 수정이 수십 배 느려짐)
drop index if exists public.papers_fts_idx;

-- 2) 초록 비우기 — 아래 90은 '발행 후 N일이 지난 논문'. 더 공격적으로 하려면 30으로.
update public.papers p
   set abstract = null, abstract_pruned = true
 where p.summarized_at is null
   and p.abstract is not null and p.abstract <> ''
   and coalesce(p.pub_date, current_date) < current_date - 90
   and not exists (select 1 from public.user_papers up where up.paper_id = p.id
                   and (up.is_bookmarked or up.is_read or (up.note is not null and up.note <> '')))
   and not exists (select 1 from public.view_history v where v.paper_id = p.id)
   and not exists (select 1 from public.comments c where c.paper_id = p.id)
   and not exists (select 1 from public.recommendations r where r.paper_id = p.id);

-- 3) 인덱스 복구
create index if not exists papers_fts_idx on public.papers using gin (fts);

-- 4) 실제 디스크 회수 (이걸 해야 용량이 줄어듭니다. 수 분, 그동안 쓰기 잠김)
vacuum (full, analyze) public.papers;

-- 5) 결과 확인
select pg_size_pretty(pg_database_size(current_database())) as db_size,
       count(*) as papers,
       count(*) filter (where abstract_pruned) as slimmed,
       count(*) filter (where abstract is not null and abstract <> '') as with_abstract
  from public.papers;
