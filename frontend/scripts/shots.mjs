import puppeteer from "puppeteer-core";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = process.argv[2] || "/tmp";
const URL = "http://localhost:3000";

const b = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--no-sandbox", "--hide-scrollbars"],
  defaultViewport: { width: 1440, height: 1000, deviceScaleFactor: 2 },
});
const p = await b.newPage();
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function shot(path, name, full = true) {
  await p.goto(`${URL}${path}`, { waitUntil: "networkidle0" });
  await wait(2200);
  await p.screenshot({ path: `${OUT}/${name}.png`, fullPage: full });
  console.log(name, "ok");
}

await shot("/", "L1-landing");
await shot("/", "L1b-landing-top", false);
await shot("/method", "L2-method");
await shot("/data", "L3-data");

// lab: run a model
await p.goto(`${URL}/lab`, { waitUntil: "networkidle0" });
await wait(1500);
await p.screenshot({ path: `${OUT}/L4-lab.png`, fullPage: true });
await p.evaluate(() => {
  const btn = [...document.querySelectorAll("button")].find((x) => /Evaluate equation|Run model/.test(x.textContent));
  btn?.click();
});
await wait(3000);
await p.screenshot({ path: `${OUT}/L5-lab-results.png`, fullPage: true });

// fitted model
await p.evaluate(() => {
  [...document.querySelectorAll("button")].find((x) => x.textContent.trim() === "Negative Binomial")?.click();
});
await wait(300);
await p.evaluate(() => document.querySelectorAll('input[type=checkbox]').forEach((c) => { if (!c.checked) c.click(); }));
await wait(200);
await p.evaluate(() => [...document.querySelectorAll("button")].find((x) => /Run model/.test(x.textContent))?.click());
await wait(3500);
await p.screenshot({ path: `${OUT}/L6-lab-fitted.png`, fullPage: true });

await b.close();
console.log("done ->", OUT);
