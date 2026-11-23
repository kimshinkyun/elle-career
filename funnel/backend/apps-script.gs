/**
 * 원장님 리드 수집 백엔드 (Google Apps Script → Google Sheets)
 *
 * 설치:
 *  1) 새 Google 스프레드시트 생성 → 확장 프로그램 > Apps Script 에 이 파일 붙여넣기
 *  2) setup() 1회 실행 (시트 3개 + 헤더 생성, 권한 승인)
 *  3) 배포 > 새 배포 > 웹 앱 | 실행: 나 | 액세스: 모든 사용자 → URL 복사
 *  4) funnel/index.html 의 CONFIG.ENDPOINT_URL 에 URL 입력
 *  5) installTriggers() 1회 실행 (2년 재확인 알림 매일 점검)
 *
 * 시트 구성
 *  - leads        : 상담용 리드 (사람이 보는 CRM, 전화번호 기준 중복 병합)
 *  - consent_log  : 동의 증빙 로그 (append-only — 절대 수정/삭제 금지)
 *  - optout_log   : 철회/수신거부 이력
 */

const SHEET_LEADS = "leads";
const SHEET_CONSENT = "consent_log";
const SHEET_OPTOUT = "optout_log";
const ALERT_EMAIL = "";   // 재확인 알림 받을 이메일 (비워두면 스크립트 소유자)

const LEAD_HEADERS = [
  "lead_id","created_at","updated_at","hospital","name","role","phone","email","specialty","stage",
  "marginal_rate","est_saving_man","lead_grade",
  "consult_request","marketing_consent","ch_sms","ch_email","ch_kakao",
  "consent_at","reconfirm_due","consent_version",
  "status","next_action","owner","memo",
  "utm_source","utm_medium","utm_campaign","utm_content","optout_token","optout_at"
];
const CONSENT_HEADERS = [
  "log_id","logged_at","lead_id","phone","event","privacy","consult_request","marketing",
  "ch_sms","ch_email","ch_kakao","version","sender","privacy_text","marketing_text","user_agent"
];
const OPTOUT_HEADERS = ["logged_at","lead_id","phone","channel","source","processed_notice_due"];

function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  [[SHEET_LEADS, LEAD_HEADERS],[SHEET_CONSENT, CONSENT_HEADERS],[SHEET_OPTOUT, OPTOUT_HEADERS]].forEach(([n,h]) => {
    const sh = ss.getSheetByName(n) || ss.insertSheet(n);
    if (sh.getLastRow() === 0) { sh.appendRow(h); sh.setFrozenRows(1); sh.getRange(1,1,1,h.length).setFontWeight("bold").setBackground("#0F1B33").setFontColor("#fff"); }
  });
  const leads = ss.getSheetByName(SHEET_LEADS);
  const col = LEAD_HEADERS.indexOf("status") + 1;
  leads.getRange(2, col, 1000).setDataValidation(SpreadsheetApp.newDataValidation()
    .requireValueInList(["신규","1차연락","상담예약","상담완료","진행중","보류","거절","수신거부"], true).build());
  // 보호: 동의 로그는 소유자만 편집
  const prot = ss.getSheetByName(SHEET_CONSENT).protect().setDescription("동의 증빙 로그 - 수정 금지");
  prot.removeEditors(prot.getEditors().filter(u => u.getEmail() !== Session.getEffectiveUser().getEmail()));
}

function doPost(e) {
  const lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    const p = JSON.parse(e.postData.contents);
    validate_(p);
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const leads = ss.getSheetByName(SHEET_LEADS), clog = ss.getSheetByName(SHEET_CONSENT);

    const now = new Date();
    const phone = String(p.phone).replace(/\D/g, "");
    const c = p.consent, ch = c.channels || {};
    const marketing = !!c.marketing && (ch.sms || ch.email || ch.kakao);

    // 1) 전화번호로 기존 리드 찾기 (중복 병합)
    const data = leads.getDataRange().getValues();
    const iPhone = LEAD_HEADERS.indexOf("phone");
    let row = -1;
    for (let r = 1; r < data.length; r++) if (String(data[r][iPhone]).replace(/\D/g,"") === phone) { row = r + 1; break; }

    const leadId = row > 0 ? data[row-1][0] : "L" + Utilities.formatDate(now, "Asia/Seoul", "yyMMddHHmmss") + Math.floor(Math.random()*90+10);
    const reconfirm = marketing ? new Date(new Date(now).setFullYear(now.getFullYear() + 2)) : "";
    const token = row > 0 ? data[row-1][LEAD_HEADERS.indexOf("optout_token")] : Utilities.getUuid().replace(/-/g,"").slice(0,16);

    const obj = {
      lead_id: leadId, created_at: row > 0 ? data[row-1][1] : now, updated_at: now,
      hospital: p.hospital, name: p.name, role: p.role, phone: p.phone, email: p.email || "",
      specialty: p.specialty, stage: p.stage,
      marginal_rate: p.marginal_rate, est_saving_man: p.est_saving_man, lead_grade: p.lead_grade,
      consult_request: !!c.consult_request, marketing_consent: marketing,
      ch_sms: marketing && !!ch.sms, ch_email: marketing && !!ch.email, ch_kakao: marketing && !!ch.kakao,
      consent_at: marketing ? now : "", reconfirm_due: reconfirm, consent_version: c.version,
      status: row > 0 ? data[row-1][LEAD_HEADERS.indexOf("status")] : "신규",
      next_action: c.consult_request ? "24시간 내 상담 연락" : (marketing ? "자료 발송 후 육성" : "연락 금지(상담·광고 동의 없음)"),
      owner: row > 0 ? data[row-1][LEAD_HEADERS.indexOf("owner")] : "",
      memo: row > 0 ? data[row-1][LEAD_HEADERS.indexOf("memo")] : "",
      utm_source: (p.attribution||{}).utm_source||"", utm_medium: (p.attribution||{}).utm_medium||"",
      utm_campaign: (p.attribution||{}).utm_campaign||"", utm_content: (p.attribution||{}).utm_content||"",
      optout_token: token, optout_at: ""
    };
    const values = LEAD_HEADERS.map(h => obj[h]);
    if (row > 0) leads.getRange(row, 1, 1, values.length).setValues([values]); else leads.appendRow(values);

    // 2) 동의 증빙 로그 (항상 append, 당시 문구 스냅샷 포함)
    clog.appendRow([
      Utilities.getUuid(), now, leadId, p.phone, row > 0 ? "re-submit" : "submit",
      !!c.privacy, !!c.consult_request, marketing, !!ch.sms, !!ch.email, !!ch.kakao,
      c.version, c.sender, c.privacy_text, c.marketing_text, c.user_agent
    ]);

    // 3) 상담 신청이 있으면 담당자에게 즉시 알림
    if (c.consult_request) notifyOwner_(obj);

    return json_({ok:true});
  } catch (err) {
    return json_({ok:false, error:String(err)});
  } finally { lock.releaseLock(); }
}

/** 수신거부/철회: https://<배포URL>?action=optout&token=XXXX  (문자·메일 하단 링크에 사용) */
function doGet(e) {
  const a = e.parameter || {};
  if (a.action === "optout" && a.token) {
    const ok = optout_(a.token, a.channel || "all", "link");
    return HtmlService.createHtmlOutput(ok ? "<h3>수신거부가 처리되었습니다.</h3>" : "<h3>유효하지 않은 링크입니다.</h3>");
  }
  return HtmlService.createHtmlOutput("OK");
}

function optout_(token, channel, source) {
  const ss = SpreadsheetApp.getActiveSpreadsheet(), leads = ss.getSheetByName(SHEET_LEADS);
  const data = leads.getDataRange().getValues(), iT = LEAD_HEADERS.indexOf("optout_token");
  for (let r = 1; r < data.length; r++) if (data[r][iT] === token) {
    const now = new Date(), set = (h, v) => leads.getRange(r+1, LEAD_HEADERS.indexOf(h)+1).setValue(v);
    set("marketing_consent", false); set("ch_sms", false); set("ch_email", false); set("ch_kakao", false);
    set("reconfirm_due", ""); set("optout_at", now); set("status", "수신거부"); set("next_action", "연락 금지");
    ss.getSheetByName(SHEET_OPTOUT).appendRow([now, data[r][0], data[r][LEAD_HEADERS.indexOf("phone")], channel, source,
      new Date(now.getTime() + 14*864e5)]);   // 처리결과 통지 기한(14일)
    ss.getSheetByName(SHEET_CONSENT).appendRow([Utilities.getUuid(), now, data[r][0], data[r][LEAD_HEADERS.indexOf("phone")], "optout",
      "", "", false, false, false, false, "", "", "", "", source]);
    return true;
  }
  return false;
}

/** 매일 실행: 재확인 만료 30일 전 리드 알림 + 만료된 광고 수신동의 자동 해제 */
function dailyConsentCheck() {
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_LEADS);
  const data = sh.getDataRange().getValues(), iDue = LEAD_HEADERS.indexOf("reconfirm_due"), now = new Date();
  const soon = [], expired = [];
  for (let r = 1; r < data.length; r++) {
    const due = data[r][iDue]; if (!(due instanceof Date)) continue;
    const days = (due - now) / 864e5;
    if (days < 0) { expired.push(r+1); } else if (days <= 30) soon.push(data[r][3] + " " + data[r][4] + " (~" + Utilities.formatDate(due,"Asia/Seoul","yyyy-MM-dd") + ")");
  }
  expired.forEach(row => {                       // 재확인 못 받으면 광고 발송 중지
    ["marketing_consent","ch_sms","ch_email","ch_kakao"].forEach(h => sh.getRange(row, LEAD_HEADERS.indexOf(h)+1).setValue(false));
    sh.getRange(row, LEAD_HEADERS.indexOf("next_action")+1).setValue("재확인 기한 만료 → 광고 발송 중지");
  });
  if (soon.length) MailApp.sendEmail(ALERT_EMAIL || Session.getEffectiveUser().getEmail(),
    "[동의 재확인] 30일 내 만료 " + soon.length + "건", soon.join("\n"));
}
function installTriggers() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger("dailyConsentCheck").timeBased().everyDays(1).atHour(9).create();
}

function notifyOwner_(o) {
  MailApp.sendEmail(ALERT_EMAIL || Session.getEffectiveUser().getEmail(),
    "[상담신청] " + o.hospital + " " + o.name + " (등급 " + o.lead_grade + ")",
    ["병원: " + o.hospital, "성함/직책: " + o.name + " / " + o.role, "연락처: " + o.phone, "진료과: " + o.specialty,
     "한계세율: " + o.marginal_rate + "% · 추정 절세 " + o.est_saving_man + "만원", "유입: " + o.utm_source + "/" + o.utm_campaign + "/" + o.utm_content].join("\n"));
}

function validate_(p) {
  if (!p || !p.consent || p.consent.privacy !== true) throw new Error("privacy consent required");
  if (!/^01[016789]-?\d{3,4}-?\d{4}$/.test(String(p.phone))) throw new Error("bad phone");
  if (!p.hospital || !p.name) throw new Error("missing fields");
}
function json_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
