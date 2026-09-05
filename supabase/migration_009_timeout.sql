-- 과거 논문 대량 수집 시 저장이 시간 초과되지 않도록 서버 역할의 제한 시간을 늘린다.
-- (기본 8초 → 120초. 사용자용 anon/authenticated 역할은 그대로 두어 사이트 응답성은 유지)
alter role service_role set statement_timeout = '120s';
notify pgrst, 'reload config';
