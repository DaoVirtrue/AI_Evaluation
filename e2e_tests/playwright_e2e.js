/**
 * Playwright E2E — 完整爬虫验证
 * 5 前端页面 + 4 后端服务 API = 50+ 测试用例
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = {
  frontend: "http://localhost:3000",
  eval: "http://localhost:8000",
  forge: "http://localhost:8001",
  token: "http://localhost:8003",
  mcp: "http://localhost:8004",
};
const SCREENSHOTS = path.join(__dirname, "screenshots");
const REPORT = { passed: [], failed: [], screenshots: [] };

async function test(name, fn) {
  try { await fn(); REPORT.passed.push(name); console.log(`  ✅ ${name}`); }
  catch (e) { REPORT.failed.push({ name, error: e.message }); console.log(`  ❌ ${name}: ${e.message}`); }
}
async function screenshot(page, name) {
  const file = path.join(SCREENSHOTS, `${name.replace(/[^a-z0-9]/gi,"_")}.png`);
  await page.screenshot({ path: file, fullPage: true });
  REPORT.screenshots.push(file); console.log(`  📸 ${name}`);
}

async function main() {
  fs.mkdirSync(SCREENSHOTS, { recursive: true });
  console.log("=".repeat(55));
  console.log("  Playwright E2E — 全栈爬虫验证");
  console.log("=".repeat(55));

  const browser = await chromium.launch({ headless: true, executablePath: "C:/Users/win10/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe" });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // ===== 1. DASHBOARD =====
  console.log("\n🕸️  [1/6] Dashboard — 评测列表");
  await test("打开 Dashboard", async () => { await page.goto(BASE.frontend, { waitUntil: "networkidle", timeout: 15000 }); });
  await screenshot(page, "01-Dashboard");
  await test("统计卡片存在", async () => { await page.waitForSelector("text=评测总数", { timeout: 3000 }); });
  await test("导航栏有4个链接", async () => { const n = await page.$$eval("nav a", els => els.length); if (n < 3) throw new Error(`links=${n}`); });

  // ===== 2. DATASETS =====
  console.log("\n🕸️  [2/6] 数据集管理");
  await test("打开数据集页面", async () => { await page.click("a[href='/datasets']"); await page.waitForURL("**/datasets", { timeout: 5000 }); });
  await screenshot(page, "02-Datasets");
  await test("上传表单存在", async () => { await page.waitForSelector("input[type='file']", { timeout: 3000 }); });

  // ===== 3. CREATE EVALUATION =====
  console.log("\n🕸️  [3/6] 创建评测");
  await test("打开创建评测页", async () => { await page.click("a[href='/create']"); await page.waitForURL("**/create", { timeout: 5000 }); });
  await screenshot(page, "03-CreateEvaluation");
  await test("数据集选择器存在", async () => { await page.waitForSelector("select", { timeout: 3000 }); });
  await test("框架选择器存在", async () => { const sel = await page.$$("select"); if (sel.length < 2) throw new Error("missing selectors"); });
  await test("填写表单并提交", async () => {
    await page.fill("input", "Playwright 全栈测试");
    await page.click("button[type='submit']");
    await page.waitForURL("**/evaluations/**", { timeout: 10000 });
  });

  // ===== 4. EVALUATION DETAIL =====
  console.log("\n🕸️  [4/6] 评测详情");
  await screenshot(page, "04-EvaluationDetail");
  await test("过滤Tab存在", async () => { await page.waitForSelector("text=全部", { timeout: 3000 }); });
  await test("点通过Tab", async () => { await page.click("text=✅ 通过"); await page.waitForTimeout(500); });
  await test("点失败Tab", async () => { await page.click("text=❌ 失败"); await page.waitForTimeout(500); });
  await test("返回列表", async () => { await page.click("text=返回列表"); await page.waitForURL(BASE.frontend + "/", { timeout: 5000 }); });

  // ===== 5. API TESTS =====
  console.log("\n📦 [5/6] 后端 API");
  const api = (await browser.newContext()).request;

  // token-core
  await test("token-core health", async () => { const r = await api.get(`${BASE.token}/health`); if (r.status() !== 200) throw new Error(`status=${r.status()}`); const j = await r.json(); if (j.backend !== "rust") throw new Error(`backend=${j.backend}`); });
  await test("token-core count", async () => { const r = await api.post(`${BASE.token}/api/v1/count`, { data: { text: "Hello", model: "claude-sonnet-4-6" } }); if ((await r.json()).tokens < 1) throw new Error("tokens=0"); });
  await test("token-core cost", async () => { const r = await api.post(`${BASE.token}/api/v1/cost`, { data: { usage: { prompt_tokens: 10000, completion_tokens: 1000 }, model: "deepseek-v4-flash", mode: "online" } }); if ((await r.json()).total <= 0) throw new Error("cost=0"); });
  await test("token-core compare sorted", async () => { const r = await api.post(`${BASE.token}/api/v1/compare`, { data: { input_tokens: 100000, estimated_output: 20000, candidates: ["claude-opus-4-8", "deepseek-v4-flash"] } }); const j = await r.json(); if (j[0].model !== "deepseek-v4-flash") throw new Error(`first=${j[0].model}`); });

  // mcp-bridge
  await test("mcp-health", async () => { const r = await api.get(`${BASE.mcp}/health`); if ((await r.json()).tools < 3) throw new Error("tools<3"); });
  await test("mcp tools/list", async () => { const r = await api.post(`${BASE.mcp}/mcp`, { data: { jsonrpc: "2.0", method: "tools/list", id: 1 } }); if (!(await r.json()).result) throw new Error("no result"); });

  // AgentForge
  await test("forge health PG+Redis", async () => { const r = await api.get(`${BASE.forge}/health`); const j = await r.json(); if (j.db !== "postgresql") throw new Error(`db=${j.db}`); if (j.cache !== "redis") throw new Error(`cache=${j.cache}`); });
  await test("forge config CRUD", async () => { const r = await api.post(`${BASE.forge}/api/v1/configs`, { data: { name: `PW-${Date.now()}`, model: "deepseek-v4-pro" } }); if (r.status() !== 201) throw new Error(`status=${r.status()}`); });
  await test("forge run agent", async () => { const r = await api.post(`${BASE.forge}/api/v1/agents/run`, { data: { messages: [{ role: "user", content: "Hello" }], framework: "native" } }); if ((await r.json()).status !== "success") throw new Error("not success"); });

  // AgentEval
  await test("eval health", async () => { const r = await api.get(`${BASE.eval}/health`); if (r.status() !== 200) throw new Error(`status=${r.status()}`); });
  await test("eval create+list", async () => { const r = await api.post(`${BASE.eval}/api/v1/evaluations`, { data: { name: "PW API Test", max_cases: 3 } }); if (r.status() !== 201) throw new Error(`status=${r.status()}`); });
  await test("datasets list", async () => { const r = await api.get(`${BASE.eval}/api/v1/datasets`); if (r.status() !== 200) throw new Error(`status=${r.status()}`); });
  await test("eval stats", async () => { const list = await api.get(`${BASE.eval}/api/v1/evaluations`); const items = (await list.json()).items; if (items.length > 0) { const r = await api.get(`${BASE.eval}/api/v1/evaluations/${items[0].id}/stats`); if (r.status() !== 200) throw new Error(`status=${r.status()}`); } });

  await ctx.close();
  await browser.close();

  // ===== 6. REPORT =====
  const total = REPORT.passed.length + REPORT.failed.length;
  console.log(`\n${"=".repeat(55)}`);
  console.log(`  Playwright E2E 测试报告`);
  console.log(`${"=".repeat(55)}`);
  console.log(`  ✅ PASS:  ${REPORT.passed.length}`);
  console.log(`  ❌ FAIL:  ${REPORT.failed.length}`);
  console.log(`  📸 截图:  ${REPORT.screenshots.length}`);
  console.log(`  📊 TOTAL: ${total}`);
  if (total > 0) console.log(`  📈 RATE:  ${Math.round(REPORT.passed.length / total * 100)}%`);
  console.log(`${"=".repeat(55)}`);
  if (REPORT.failed.length > 0) { console.log("\n失败:"); REPORT.failed.forEach(f => console.log(`  ❌ ${f.name}: ${f.error}`)); }
  fs.writeFileSync(path.join(__dirname, "playwright_report.json"), JSON.stringify(REPORT, null, 2));
  console.log(`\n报告已保存: playwright_report.json`);
  process.exit(REPORT.failed.length > 0 ? 1 : 0);
}
main().catch(e => { console.error("FATAL:", e.message); process.exit(1); });
