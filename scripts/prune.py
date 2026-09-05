"""
용량 관리: 아무도 손대지 않은 오래된 논문의 초록을 비운다(껍데기만 남김).
비워진 논문은 누군가 열면 PubMed에서 초록을 자동으로 되받아 온다.

주의: PostgreSQL은 UPDATE/DELETE 직후 파일 크기가 바로 줄지 않는다(빈 공간으로 재사용됨).
따라서 진행 판단은 '남은 후보 수'로 하고, 실제 용량 회수가 필요하면 SQL Editor에서
  vacuum (full, analyze) public.papers;
를 한 번 실행한다(수 분, 그동안 쓰기 잠김).

환경변수:
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY  (필수)
  PRUNE_TARGET_MB   목표 상한 (기본 420)
  PRUNE_KEEP_DAYS   이 기간 안에 발행된 논문은 보호 (기본 365)
  PRUNE_BATCH       한 번에 처리할 편수 (기본 200, 시간 초과 시 자동으로 절반씩 축소)
"""
import json, os, re, sys
import requests

SB = re.sub(r"/(rest|auth|storage)/v1/?$", "", os.environ["SUPABASE_URL"].strip()).rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
TARGET = int(os.environ.get("PRUNE_TARGET_MB") or 420) * 1024 * 1024
KEEP_DAYS = int(os.environ.get("PRUNE_KEEP_DAYS") or 365)
BATCH0 = int(os.environ.get("PRUNE_BATCH") or 200)
BULK_LIMIT = int(os.environ.get("PRUNE_BULK_LIMIT") or 5000)  # 이보다 후보가 많으면 SQL 일괄 정리를 권함
MB = lambda b: f"{b / 1024 / 1024:.0f}MB"


def rpc(fn, args=None, timeout=180):
    r = requests.post(f"{SB}/rest/v1/rpc/{fn}", headers=H, data=json.dumps(args or {}), timeout=timeout)
    if r.status_code >= 300:
        raise RuntimeError(f"{fn}: {r.status_code} {r.text[:200]}")
    return r.json()


def is_timeout(e):
    return "57014" in str(e) or "timeout" in str(e).lower()


def run_stage(fn, label):
    """배치 크기를 조절해가며 더 처리할 것이 없을 때까지 반복."""
    batch, total, misses = BATCH0, 0, 0
    while True:
        try:
            n = int(rpc(fn, {"keep_days": KEEP_DAYS, "batch": batch}))
        except RuntimeError as e:
            if is_timeout(e) and batch > 10:
                batch //= 2
                print(f"[{label}] 시간 초과 → 배치 {batch}로 축소", flush=True)
                continue
            if is_timeout(e):
                # 더 줄일 수 없으면 이번 실행은 여기까지. 워크플로를 실패시키지 않는다.
                print(f"[{label}] 시간 초과로 중단 (누적 {total}편). "
                      "남은 양이 많으면 supabase/maintenance_bulk_prune.sql 을 SQL Editor에서 한 번 실행하세요.",
                      file=sys.stderr)
                return total
            raise
        if n == 0:
            misses += 1
            if misses >= 2:
                break
            continue
        misses = 0
        total += n
        if total % (batch * 10) < batch:
            print(f"[{label}] 누적 {total}편", flush=True)
    return total


def main():
    size = lambda: int(rpc("db_size_bytes"))
    cur = size()
    left = int(rpc("prunable_count", {"keep_days": KEEP_DAYS}))
    print(f"현재 용량 {MB(cur)} / 목표 {MB(TARGET)} · 정리 후보 {left:,}편")

    if left > BULK_LIMIT:
        print(f"후보가 {left:,}편으로 많습니다. 매일 작업에서 조금씩 처리하는 것보다,")
        print("Supabase SQL Editor에서 supabase/maintenance_bulk_prune.sql 을 한 번 실행하는 편이 빠릅니다.")
        print(f"이번 실행에서는 {BATCH0 * 20:,}편까지만 처리합니다.")
    if left:
        done = run_stage("prune_slim", "초록 비우기")
        print(f"초록 비우기 완료: {done:,}편")
    else:
        print("초록 비울 논문 없음")

    cur = size()
    if cur > TARGET:
        print(f"용량이 여전히 {MB(cur)} — 이미 비워진 오래된 논문 행을 삭제합니다")
        done = run_stage("prune_delete", "행 삭제")
        print(f"행 삭제 완료: {done:,}편")
        cur = size()

    print(f"최종 용량 {MB(cur)}")
    if cur > TARGET:
        print("파일 크기는 VACUUM 전까지 줄지 않습니다. Supabase SQL Editor에서 다음을 한 번 실행하세요:", file=sys.stderr)
        print("  vacuum (full, analyze) public.papers;", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # 정리 실패가 수집·추천까지 막지 않도록
        print(f"정리 중단: {e}", file=sys.stderr)
