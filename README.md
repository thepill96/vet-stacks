# Vet Stacks

(저장소·폴더 이름은 `vet-paper-radar` 그대로입니다. 사이트 주소도 변하지 않습니다.)

> Interface languages: English (default), 한국어, 日本語, Deutsch, Español — switch from the top bar or Settings. Summaries are generated in English and Korean. Category/journal-group names in `config/sources.json` are English keys; the UI translates them (add translations in `web/src/lib/i18n.js`).

수의·인의 임상 논문을 매일 아침 7시(KST) PubMed에서 언어 제한 없이 모아 분류하고, Claude가 원문 언어와 무관하게 한국어·영어 두 버전의 요약·임상 포인트를 달아 주며, 초대된 동료들과 각자 읽음·북마크·메모·히스토리를 남기는 사이트.

```
PubMed ──(GitHub Actions, 매일 07:00 KST)──▶ Supabase DB ◀──── 웹앱 (GitHub Pages)
                │                                 ▲                 로그인 / 필터 / 검색
                └── Claude 요약 ───────────────────┘                 읽음·북마크·메모·히스토리
                                                                    Obsidian · Anki · Readwise 내보내기
```

| 폴더 | 역할 |
|---|---|
| `config/sources.json` | 수집할 저널·분야 키워드·수집 기간. **가장 자주 손댈 파일** |
| `scripts/fetch_pubmed.py` | PubMed 수집 → 분류 → DB 저장 → Claude 요약 |
| `scripts/recommend.py` | 사용자별 관심 프로필 → 새 논문 추천 → 알림 메일 (수집 직후 실행) |
| `.github/workflows/` | 매일 수집(`fetch.yml`), 웹 배포(`deploy.yml`) |
| `supabase/schema.sql` | DB 테이블, 초대 명단 게이트, 권한(RLS) |
| `supabase/functions/` | 버튼 눌렀을 때 요약 생성 / Readwise 전송 / Notion DB 동기화 (API 키를 서버에 숨김) |
| `web/` | React 웹앱 |

---

## 설치 (한 번만, 약 40분)

### 1. Supabase 프로젝트
1. https://supabase.com → New project (리전 Northeast Asia/Seoul 권장). DB 비밀번호는 보관.
2. 왼쪽 **SQL Editor** → `supabase/schema.sql` 내용 전체 붙여넣기 → Run.
3. 가입은 누구나 할 수 있고, **첫 가입자가 자동으로 관리자**가 됩니다. 이후 가입자는 승인 전까지 "승인 대기 중" 화면만 보이며, 관리자가 **설정 → 사용자 승인**에서 승인/차단합니다. 대기자가 있으면 매일 아침 관리자에게 메일이 갑니다.
4. **Project Settings → API** 에서 세 값을 복사해 둡니다.
   - Project URL
   - `anon` `public` 키 (웹앱용)
   - `service_role` 키 (수집 스크립트용 — **절대 웹앱이나 공개 저장소에 넣지 않기**)

### 2. 로그인 방식 (Google + 이메일)
Supabase → Authentication → Providers에서 **Email**(기본 켜짐)과 **Google**을 모두 켭니다. 이메일 가입은 인증 메일 링크를 눌러야 로그인됩니다. Providers 화면에 표시되는 **Callback URL**(`https://xxxx.supabase.co/auth/v1/callback`)을 각 서비스에 등록하면 됩니다.

**Google** (무료)
1. console.cloud.google.com → 새 프로젝트 → API 및 서비스 → OAuth 동의 화면 → 외부(External), 앱 이름·이메일 입력.
   테스트 모드로 두면 등록한 테스트 사용자 100명까지 쓸 수 있고 심사가 필요 없습니다.
2. 사용자 인증 정보 → OAuth 클라이언트 ID → 웹 애플리케이션 → 승인된 리디렉션 URI에 Supabase Callback URL 등록.
3. 만들어진 클라이언트 ID·보안 비밀번호를 Supabase의 Google Provider에 붙여 넣고 Enable → Save.

(Apple 로그인은 Apple Developer Program 연 $99가 필요해 지금은 넣지 않았습니다. 나중에 추가하려면 Supabase의 Apple Provider를 켜고 `web/src/components/Auth.jsx`에 버튼을 하나 더 두면 됩니다.)

**공통**: Authentication → URL Configuration의 Site URL과 Redirect URLs에 사이트 주소(`https://<아이디>.github.io/<저장소>/`)를 넣어야 로그인 후 제대로 돌아옵니다.

### 3. Edge Functions (요약 버튼·Readwise 전송)
터미널에서 (Supabase CLI 설치: `npm i -g supabase`):
```bash
supabase login
supabase link --project-ref <프로젝트 ref>   # 대시보드 URL의 xxxxx 부분
supabase secrets set ANTHROPIC_API_KEY=sk-ant-...
supabase functions deploy summarize
supabase functions deploy readwise-export
supabase functions deploy notion-export
```
(`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`는 Edge Function에 자동 주입됩니다.)

### 4. GitHub 저장소
1. 이 폴더를 새 저장소(예: `vet-paper-radar`)에 올립니다.
2. **Settings → Secrets and variables → Actions → New repository secret** 으로 등록:

   | 이름 | 값 |
   |---|---|
   | `SUPABASE_URL` | Project URL |
   | `SUPABASE_ANON_KEY` | anon 키 |
   | `SUPABASE_SERVICE_ROLE_KEY` | service_role 키 |
   | `ANTHROPIC_API_KEY` | Claude API 키 (없으면 요약 없이 수집만) |
   | `NCBI_API_KEY` | 선택. https://www.ncbi.nlm.nih.gov/account/settings/ 에서 발급하면 수집이 빨라짐 |
   | `GMAIL_USER` | 추천 메일을 보낼 Gmail 주소 (예: 본인 Gmail) |
   | `GMAIL_APP_PASSWORD` | 그 Gmail의 **앱 비밀번호** 16자리 (아래 "추천 알림 메일" 참고) |

3. **Settings → Pages → Source**를 **GitHub Actions**로.
4. **Actions** 탭 → "Fetch PubMed papers" → Run workflow → `lookback_days`를 `30`으로 해서 첫 수집. (이후엔 매일 자동으로 최근 3일치)
5. `web/` 아래 파일을 한 번 push하면 "Deploy web to GitHub Pages"가 돌고, `https://<아이디>.github.io/<저장소>/` 에서 열립니다.

### 5. 로컬에서 띄워 보기 (선택)
```bash
cd web
cp .env.example .env     # URL과 anon 키 입력
npm install
npm run dev              # http://localhost:5173
```

---

## 매일 쓰는 법
- 기간 필터는 **논문 발행일** 기준입니다(사이트가 수집한 날짜가 아님). 그래서 1년을 고르면 지난 1년 안에 발행된 논문만 보이고, 수집을 오늘 시작했어도 과거 논문을 넣어두면 그대로 걸러집니다.
- 수집 대상은 `config/sources.json`의 저널 75종입니다. PubMed 전체가 들어오는 것이 아니라, 이 저널에 실린 논문 중 `must_match` 조건을 통과한 것만 저장됩니다. 그 밖의 논문은 검색창 아래 PubMed 구역에서 찾아 **가져오기**를 눌렀을 때만 들어옵니다.
- **논문** 탭: 왼쪽 "보기"에서 분야별/저널별/최신순으로 묶어 보고, 대상(수의/인의)을 고르면 그 아래 분야·저널 목록이 해당 대상 것만 남습니다. 검색창은 제목·초록·요약 전체를 찾습니다.
- **읽음 표시**: 목록 왼쪽의 빨간 점 = 안 읽음, 초록 ✓ = 읽음. 점을 클릭하면 바로 토글되고, 논문을 열면 자동으로 읽음 처리됩니다(설정에서 끌 수 있음). 상세 화면 맨 위 상태 줄에서도 바꿀 수 있어요.
- 상세 화면은 **요약 → 초록 → 내 메모 → 토론** 순서. 메모는 본인만 보고 1초 뒤 자동 저장, 토론(댓글)은 승인된 멤버 모두에게 보입니다. 본인 댓글은 수정·삭제 가능, 관리자는 모든 댓글 삭제 가능.
- **구성 · 알고리즘** 페이지에 수집·분류·요약·추천 방식과 저널·키워드 전체가 표시되고, **피드백 · 의견**에서 익명 의견을 보낼 수 있습니다(관리자는 설정에서 확인).
- **자동 요약은 꺼져 있습니다**(`max_ai_summaries_per_run: 0`). 매일 아침 작업은 논문 수집만 하고, 요약은 논문 화면의 **AI 요약 생성** 버튼을 누를 때만 만들어집니다. 과거 논문을 한꺼번에 요약하고 싶을 때만 Run workflow에서 `max_summaries`에 숫자를 넣으세요(편당 약 2~3원).
- 요약은 항상 **한국어·영어 두 버전**이 함께 생성됩니다. 요약창 위 탭(한국어 / English / 병기)으로 바꿔 보고, **설정 → 요약 언어**에서 기본값을 정합니다. 일본어·독일어 등 비영어 논문은 원어 제목이 영어 제목 아래에 표시되고 "원문 ○○" 칩이 붙습니다.
- **북마크**/**히스토리** 탭 상단에서 목록 전체를 Obsidian .md 한 파일 / Anki 가져오기 파일 / Readwise 하이라이트로 내보냅니다.
- **설정**에서 Readwise 토큰(https://readwise.io/access_token)을 저장하면 Readwise 버튼이 동작합니다.

## 추천 알림 메일
매일 수집이 끝나면 `recommend.py`가 사용자마다 관심 프로필(북마크·메모 3점, 읽음 2점, 열람 1점, 검색어 2.5점, 설정에 적은 키워드 4점)을 만들고, 최근 8일 내 수집된 논문 중 분야·저널·제목 키워드가 맞는 것을 점수화해 상위 10편을 **추천** 탭에 넣습니다. 설정에서 고른 주기(매일/주 1회/끄기)에 따라 같은 목록을 이메일로 보냅니다. 메일의 논문 링크를 누르면 사이트에서 바로 그 논문이 열립니다.

**Gmail로 보내기 (도메인 없이, 권장)**
1. Google 계정 → 보안 → **2단계 인증** 켜기 (이미 켜져 있으면 생략).
2. https://myaccount.google.com/apppasswords → 앱 이름 `vet-paper-radar` → 만들기 → 16자리 비밀번호 복사.
3. GitHub Secrets에 `GMAIL_USER`(Gmail 주소), `GMAIL_APP_PASSWORD`(16자리, 공백 있어도 됨) 등록.
4. 테스트: Actions → Fetch PubMed papers → Run workflow에서 `force_digest`를 `1`로 → 주기와 상관없이 지금 메일 발송. 추천이 생기려면 먼저 논문을 몇 편 열어보고 북마크나 검색을 해두어야 합니다.

Gmail은 하루 500통 한도라 동료 몇 명 규모에는 충분합니다. 나중에 도메인이 생기면 `RESEND_API_KEY`와 `MAIL_FROM`을 대신 넣으면 Resend로 발송됩니다.

## PubMed 전체 검색 (아카이빙 대신 필요한 것만)
검색창에 무언가를 입력하면 먼저 내 서재에서 찾고, 목록 아래에 **"서재에 없나요?"** 구역이 붙습니다. 거기서 같은 검색어로 PubMed 3,900만 편 전체를 실시간으로 검색합니다(서재에 결과가 하나도 없으면 자동으로 펼쳐집니다). 검색은 NCBI에 직접 물어보므로 저장 공간을 쓰지 않고, **가져오기**를 누른 논문만 우리 DB에 들어옵니다. 가져온 논문은 분야가 자동 분류되고 북마크에 추가되며, 이후에는 요약·메모·댓글·내보내기가 모두 됩니다.

- PubMed 문법을 그대로 씁니다: `AND` / `OR` / `NOT`, `"정확한 구절"`, `author[au]`, `journal[ta]`.
- 왼쪽에서 고른 대상(수의/인의) 필터가 PubMed 검색에도 적용되고, 20편 단위로 넘겨 볼 수 있으며, 여러 편 선택 후 일괄 가져오기(한 번에 50편까지)가 됩니다.
- 이미 서재에 있는 논문은 "보관됨"으로 표시되어 중복 저장되지 않습니다.
- 함수 배포와 시크릿: `supabase functions deploy pubmed`. NCBI 키가 있으면 `supabase secrets set NCBI_API_KEY=...` 로 넣으면 검색이 빨라집니다(선택).

**왜 전체를 담지 않는가**: PubMed 전체는 초록 포함 120GB 이상이라 Supabase 무료 500MB는 물론 Pro(8GB)로도 감당하기 어렵고(월 수십만 원), NCBI 일괄 배포본을 매일 반영하는 별도 서버가 필요합니다. PubMed 자체가 무료 검색을 제공하므로 사본을 갖는 것보다 "검색은 PubMed에, 보관은 내가 고른 것만"이 실용적입니다.

## 관리자 기능
관리자로 로그인하면 상단 메뉴에 **Admin / 관리자** 탭이 생깁니다.
- **개요**: 논문 수, 이번 주 신규, 요약된 논문, 멤버 수, 승인 대기, 댓글, 새 피드백
- **가입 승인**: 대기자 승인·차단 (대기자가 있으면 탭에 빨간 숫자 + 매일 아침 메일)
- **회원 활동**: 멤버별 열람·읽음·북마크·메모·댓글·검색 수와 마지막 활동 시각, 차단·관리자 지정
- **공지**: 로그인한 멤버에게 화면 가운데 팝업으로 표시. 안내/중요 두 단계이며, 각자 '확인'을 누르면 그 사람에게는 다시 뜨지 않습니다. 비활성화·삭제 가능
- **피드백**: 상태(새로 옴·예정·완료·거절) 지정과 답장. 익명이 아닌 의견을 보낸 멤버는 자기 피드백 화면에서 답장을 봅니다
- **AI 요약 사용량**: 월별·경로별(자동/수동) 요약 편수와 토큰, 추정 비용

첫 관리자는 첫 가입자가 자동으로 됩니다. 이미 가입한 계정을 관리자로 만들려면 SQL Editor에서:
```sql
update public.profiles set is_admin = true, status = 'approved' where email = '본인이메일';
```

## Notion 연동
논문을 Notion 데이터베이스에 열(속성)별로 정리합니다. 논문 한 편이 한 행이고, 본문에는 한/영 요약·임상 포인트·내 메모·원문 초록(토글)·출처가 들어갑니다. 같은 논문을 다시 보내면 PMID로 찾아 속성(읽음·북마크·메모)만 갱신하고 중복 행을 만들지 않습니다.
1. https://www.notion.so/my-integrations 에서 **새 내부 통합**을 만들고 토큰을 복사합니다. 권한은 콘텐츠 읽기·삽입·업데이트.
2. Notion에서 논문 DB를 둘 페이지를 열고 우측 상단 **··· → 연결(Connections)** 에서 방금 만든 통합을 추가합니다. (이 단계를 빼먹으면 "object_not_found" 오류가 납니다.)
3. 사이트 **설정 → Notion 연동**에 토큰과 그 페이지 링크를 넣고 **데이터베이스 만들기**. 이미 DB가 있으면 그 ID를 직접 넣어도 되지만, 열 이름이 `notion-export/index.ts`의 `DB_PROPERTIES`와 같아야 합니다.
4. 논문 화면의 **Notion** 버튼(한 편) 또는 북마크·히스토리 탭 상단의 **Notion**(목록 전체)으로 보냅니다.

참고: 인스타그램 가이드처럼 Claude 데스크탑 루틴 + PubMed/Notion 커넥터만으로도 비슷한 흐름을 만들 수 있습니다. 차이는 이 사이트가 저널·키워드 필터, 동료별 로그인·히스토리, 한/영 병기, Obsidian·Anki·Readwise까지 한 곳에서 처리한다는 점이고, Notion은 그중 하나의 출구가 됩니다.

## 저널 표기 확인
저널명이 PubMed 표기와 다르면 수집이 조용히 0건이 됩니다. 저널을 추가한 뒤에는 Actions → **Check journal names** → Run workflow 를 돌리세요. 저널마다 전체·최근 논문 수를 찍고, 검색되지 않는 표기는 ✗로 모아서 알려줍니다.

## 저널·분야 바꾸기
`config/sources.json`만 고치고 push하면 다음 수집부터 반영됩니다.
- 저널 추가: `{ "name": "PubMed 정식 저널명", "species": "vet" 또는 "human", "group": "표시용 묶음" }`. 양이 많은 저널은 `must_match`에 키워드를 넣어 제목/초록에 그 단어가 있을 때만 수집.
- 분야 추가: `categories`에 `"분야명": ["키워드", ...]`. 키워드는 단어 시작 위치에서 매칭됩니다(`hepat` → hepatic, hepatectomy).
- 저널명이 맞는지는 PubMed에서 `"Journal Name"[Journal]`로 검색해 확인하세요.

## 비용
- Supabase, GitHub Pages/Actions: 이 규모에서는 무료 티어로 충분.
- Claude 요약: 논문 1편당 대략 1~2원 수준(초록 길이에 따라 다름). `max_ai_summaries_per_run`으로 상한 조절.

## 이미 설치했다면 (업데이트)
`supabase/migration_008_admin.sql`을 실행하세요(공지·피드백 답장·회원 활동 통계·AI 요약 사용량).
마이그레이션은 번호 순서대로 실행합니다(004 → 005 → 006 → 007). 모두 재실행해도 안전합니다. 007은 멤버 간 댓글(토론) 기능입니다.
`supabase/migration_006_i18n.sql`을 실행하세요(기존 한글 분야명을 영어 키로 변환, ui_lang 컬럼).
`supabase/migration_005_approval.sql`을 실행하고(가입 승인제·피드백·동적 필터), `summarize` 함수를 재배포하세요. 실행 후 마지막 줄의 주석을 본인 이메일로 바꿔 실행하면 관리자가 됩니다.
`supabase/migration_004_digest.sql`도 실행하세요(추천·알림 메일).
`supabase/migration_003_notion.sql`도 실행하고 `notion-export` 함수를 배포하세요.
`supabase/migration_002_bilingual.sql`을 SQL Editor에서 실행하고, Edge Function을 다시 배포(`supabase functions deploy summarize readwise-export`)한 뒤 push하세요. 기존 한글 요약만 있는 논문에 영어를 채우려면 migration 파일 끝의 주석 SQL을 실행하면 다음 수집 때 다시 요약됩니다.

## 비밀번호를 잊었을 때
**본인(멤버 모두)** — 로그인 화면의 "비밀번호를 잊으셨나요?" → 이메일 입력 → 받은 메일의 링크를 누르면 새 비밀번호 설정 화면이 뜹니다. 링크는 1시간 정도만 유효합니다. Google로 가입한 계정은 비밀번호가 없으니 Google 버튼으로 들어가면 됩니다.

**관리자 계정을 아예 못 여는 경우** — 사이트 밖에서 되돌릴 수 있는 길이 두 가지 있습니다.
1. Supabase 대시보드 → Authentication → Users → 해당 사용자 오른쪽 ··· → **Reset password**(재설정 메일 발송) 또는 **Send magic link**(비밀번호 없이 로그인).
2. 그 이메일 자체를 못 쓰는 상황이면, 다른 계정으로 가입한 뒤 SQL Editor에서 관리자로 올리면 됩니다:
   ```sql
   update public.profiles set is_admin = true, status = 'approved' where email = '새이메일';
   ```
Supabase 대시보드 로그인(GitHub 계정)만 살아 있으면 언제든 복구할 수 있으므로, 그 계정의 2단계 인증을 켜 두는 편이 안전합니다.

**메일이 안 올 때** — Supabase 무료 플랜의 기본 발송은 시간당 통수 제한이 있고 스팸함으로 가기 쉽습니다. 스팸함을 먼저 확인하고, 자주 쓸 것 같으면 Authentication → Emails에서 SMTP(예: Resend)를 연결하세요.

## 과거 논문 대량 수집
Actions → Fetch PubMed papers → Run workflow에서 `lookback_days`를 크게(365 / 1825) 주면 됩니다. `max_summaries`는 기본이 `0`이라 요약 없이 수집만 합니다. 5년치는 저널 34종 기준 4만 편 안팎이고 30~60분 걸립니다.

저장은 저널 단위로 끊어서 이뤄지므로 중간에 실패해도 앞서 저장된 저널은 그대로 남고, 다시 실행하면 PMID 기준으로 중복 없이 이어집니다. 저장 중 `statement timeout`(57014)이 나면 `supabase/migration_009_timeout.sql`을 한 번 실행하세요.

## 용량 관리 — 껍데기만 남기고, 열면 되살아납니다
수집이 끝날 때마다 `scripts/prune.py`가 자동으로 실행됩니다.

**1단계(항상 실행)**: 발행 1년 이상이면서 아무도 손대지 않았고 요약도 없는 논문의 **초록만 비웁니다.** 제목·저자·저널·발행일·분야·PMID는 남으므로 목록과 검색에 그대로 나옵니다. 초록이 논문 데이터의 8~9할이라, 껍데기는 편당 0.5KB 수준입니다.

**자동 복원**: 그 논문을 누군가 열면 PubMed에서 초록을 즉시 받아 화면을 채우고 DB에도 되돌립니다(1초 남짓, "초록을 다시 받아오는 중" 표시). 이후 그 논문은 열람 기록에 남아 보호 대상이 되어 다시 비워지지 않습니다. 요약 생성도 복원을 먼저 하고 진행합니다.

**2단계(목표 초과 시에만)**: 이미 초록이 비워진 논문만 오래된 순서로 삭제합니다. 언제든 재수집·재가져오기로 복구됩니다.

**절대 건드리지 않는 것**: 북마크·메모·읽음 표시된 논문, 열람 기록에 있는 논문, 댓글이 달린 논문, 추천에 올라간 논문, AI 요약이 있는 논문.

**조정**: Settings → Secrets and variables → Actions → **Variables** 탭에서 `PRUNE_KEEP_DAYS`(기본 365, 줄일수록 껍데기화가 공격적), `PRUNE_TARGET_MB`(기본 420), `PRUNE_BATCH`(기본 200).

**중요 — 정리 후 용량이 안 줄어 보일 때**: PostgreSQL은 초록을 비우거나 행을 지워도 파일 크기가 즉시 줄지 않고 빈 공간으로 남겨 재사용합니다. 그래서 정리 직후 Admin의 사용 용량이 그대로일 수 있습니다. 실제로 회수하려면 SQL Editor에서 한 번 실행하세요(수 분 걸리고 그동안 쓰기가 잠깁니다):
```sql
vacuum (full, analyze) public.papers;
```
평소에는 굳이 필요 없습니다. 비운 공간을 새 논문이 다시 채우므로 용량이 더 늘지 않습니다. Admin 탭 개요에 사용 용량·보호 논문·초록 비운 논문 수가 표시됩니다.

이 구조 덕분에 "자주 보는 논문만 초록을 갖고, 나머지는 목록만 유지"가 자동으로 이뤄집니다. 10만 편이라도 대부분 껍데기라면 100MB 안쪽이라, 무료 500MB로도 넓은 아카이브를 유지할 수 있습니다.

## 검색이 느릴 때
논문이 수만 편이 되면 인덱스가 없을 때 검색이 수십 초까지 걸립니다. `supabase/migration_010_search_speed.sql`을 한 번 실행하세요(전문 검색·발행일·대상·저널·분야 인덱스). 검색창은 타이핑이 멈추면 0.4초 뒤 자동으로 걸러지며, 목록 건수는 정확한 집계 대신 추정치(`~`)를 씁니다. 4만 편 규모에서 정확한 집계는 그 자체로 몇십 초가 걸리기 때문입니다.

## 문제 해결
- **수집 로그에 `canceling statement due to statement timeout` (57014)**: 한 번에 저장하는 양이 많아 DB가 끊은 것. `supabase/migration_009_timeout.sql`을 실행한 뒤 다시 돌리면 됩니다.
- **관리자 탭 내용이 비어 있음**: `supabase/migration_008_admin.sql`을 실행하지 않은 것. 실행하면 화면 위 노란 안내가 사라지고 숫자가 채워집니다.
- **로그인 화면 주소에 `error=access_denied&error_code=otp_expired`가 붙음**: 만료된(또는 이미 사용한) 인증·재설정 메일 링크를 누른 것. 주소에서 `#` 뒤를 지우고 다시 들어가 새 링크를 요청하세요.
- **가입했는데 "승인 대기 중"만 보임**: 관리자 계정으로 설정 → 사용자 승인. 본인이 첫 가입자인데도 그렇다면 SQL Editor에서 `update public.profiles set is_admin = true, status = 'approved' where email = '본인이메일';`
- **로그인 후 빈 화면/에러**: Supabase URL Configuration의 Redirect URLs에 배포 주소가 없는 경우.
- **논문이 하나도 없음**: Actions 탭에서 "Fetch PubMed papers" 실행 기록과 로그 확인. Secrets 이름 오타가 가장 흔함.
- **AI 요약 생성 실패**: Edge Function이 배포되지 않았거나 `ANTHROPIC_API_KEY` 시크릿 미설정.
