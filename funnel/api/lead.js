/**
 * 리드 수집 API (Vercel/Netlify 호환 서버리스) → 노션 DB 저장
 *
 * 환경변수 (배포 서비스의 Environment Variables에만 저장, 코드/채팅에 절대 노출 금지)
 *   NOTION_TOKEN   노션 내부 통합(Internal Integration) 토큰
 *   ALLOWED_ORIGIN (선택) 랜딩 도메인. 예: https://makers-tax.vercel.app
 *
 * 노션 설정: 통합을 만든 뒤 '고객' DB와 '동의 로그' DB 페이지에서 ··· > 연결 추가로 통합을 연결하세요.
 */
const NOTION = "https://api.notion.com/v1";
const VERSION = "2022-06-28";
const CUSTOMER_DB = "49bae769-c2d0-497f-927e-31baca0a5be5";   // 고객
const CONSENT_DB = "4212114b-324c-814a-908d-df640d112ab1";    // 동의 로그

const hdr = () => ({ "Authorization": `Bearer ${process.env.NOTION_TOKEN}`, "Notion-Version": VERSION, "Content-Type": "application/json" });
const text = s => [{ type: "text", text: { content: String(s ?? "").slice(0, 1900) } }];
const chunks = s => String(s ?? "").match(/[\s\S]{1,1900}/g)?.slice(0, 20).map(c => ({ type: "text", text: { content: c } })) ?? [];
const sel = v => v ? { select: { name: String(v).slice(0, 100) } } : { select: null };
const day = d => d.toISOString().slice(0, 10);

const PHONE_RE = /^01[016789]-?\d{3,4}-?\d{4}$/;

async function notion(path, body, method = "POST") {
  const r = await fetch(NOTION + path, { method, headers: hdr(), body: body ? JSON.stringify(body) : undefined });
  const j = await r.json();
  if (!r.ok) throw new Error(`Notion ${r.status}: ${j.message || JSON.stringify(j)}`);
  return j;
}

function buildCustomerProps(p, now) {
  const c = p.consent || {}, ch = c.channels || {};
  const marketing = !!c.marketing && !!(ch.sms || ch.email || ch.kakao);
  const channels = [ch.sms && "문자", ch.email && "이메일", ch.kakao && "카카오톡"].filter(Boolean);
  const reconfirm = new Date(now); reconfirm.setFullYear(reconfirm.getFullYear() + 2);
  const next = new Date(now); next.setDate(next.getDate() + 1);
  const a = p.attribution || {};
  const props = {
    "이름": { title: text(p.name) },
    "병원명": { rich_text: text(p.hospital) },
    "직책": sel(p.role),
    "진료과": sel(p.specialty),
    "운영 단계": sel(p.stage),
    "직업": sel("병의원"),
    "연락처": { phone_number: p.phone },
    "한계세율(%)": { number: Number(p.marginal_rate) || 0 },
    "추정 절세(만원)": { number: Number(p.est_saving_man) || 0 },
    "리드 등급": sel(p.lead_grade),
    "개인정보 동의": { checkbox: c.privacy === true },
    "상담 신청": { checkbox: !!c.consult_request },
    "마케팅 수신동의": { checkbox: marketing },
    "수신 채널": { multi_select: marketing ? channels.map(name => ({ name })) : [] },
    "동의 일시": { date: { start: now.toISOString() } },
    "재확인 기한": marketing ? { date: { start: day(reconfirm) } } : { date: null },
    "동의 문구 버전": { rich_text: text(c.version) },
    "UTM 소재": { rich_text: text([a.utm_source, a.utm_medium, a.utm_campaign, a.utm_content].filter(Boolean).join(" / ")) },
    "올해 공제 희망": { checkbox: true },
    "트랙": sel(now.getMonth() >= 9 ? "연말" : "일반")
  };
  if (p.email) props["이메일"] = { email: p.email };
  if (/ig|insta/i.test(a.utm_source || "")) props["유입 경로"] = sel("인스타");
  if (c.consult_request) props["다음 행동일"] = { date: { start: day(next) } };
  return { props, marketing, channels };
}

module.exports = async function handler(req, res) {
  const origin = process.env.ALLOWED_ORIGIN || "*";
  res.setHeader("Access-Control-Allow-Origin", origin);
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ ok: false });

  try {
    if (!process.env.NOTION_TOKEN) throw new Error("NOTION_TOKEN not set");
    const p = typeof req.body === "string" ? JSON.parse(req.body) : req.body;
    if (!p?.consent || p.consent.privacy !== true) return res.status(400).json({ ok: false, error: "privacy consent required" });
    if (!PHONE_RE.test(String(p.phone))) return res.status(400).json({ ok: false, error: "bad phone" });
    if (!p.hospital || !p.name) return res.status(400).json({ ok: false, error: "missing fields" });

    const now = new Date();
    const { props, marketing, channels } = buildCustomerProps(p, now);

    // 전화번호로 기존 고객 조회 → 있으면 갱신(단계·메모 보존), 없으면 생성
    const found = await notion(`/databases/${CUSTOMER_DB}/query`, { filter: { property: "연락처", phone_number: { equals: p.phone } }, page_size: 1 });
    let page, isNew = found.results.length === 0;
    if (isNew) {
      page = await notion("/pages", { parent: { database_id: CUSTOMER_DB }, properties: props });
    } else {
      page = await notion(`/pages/${found.results[0].id}`, { properties: props }, "PATCH");
    }

    // 동의 증빙 로그 (항상 새 행 추가)
    const c = p.consent;
    await notion("/pages", {
      parent: { database_id: CONSENT_DB },
      properties: {
        "로그": { title: text(`${now.toISOString().slice(0, 16).replace("T", " ")} ${p.name} ${isNew ? "제출" : "재제출"}`) },
        "이벤트": sel(isNew ? "제출" : "재제출"),
        "연락처": { phone_number: p.phone },
        "개인정보 동의": { checkbox: true },
        "상담 신청": { checkbox: !!c.consult_request },
        "마케팅 수신동의": { checkbox: marketing },
        "수신 채널": { multi_select: marketing ? channels.map(name => ({ name })) : [] },
        "동의 문구 버전": { rich_text: text(c.version) },
        "전송자": { rich_text: text(c.sender) },
        "동의 문구 스냅샷": { rich_text: chunks(`[개인정보]\n${c.privacy_text}\n\n[광고성 정보]\n${c.marketing_text}`) },
        "고객": { relation: [{ id: page.id }] }
      }
    });
    return res.status(200).json({ ok: true });
  } catch (e) {
    console.error(e);
    return res.status(500).json({ ok: false });   // 클라이언트는 실패 시 로컬 대기열에 보관 후 재시도
  }
};
