// In-page audit for the dark theme: light surfaces and low-contrast text.
async function auditDark(page, label) {
  return page.evaluate((label) => {
    const parse = (c) => {
      const m = c && c.match(/rgba?\(([^)]+)\)/);
      if (!m) return null;
      const [r, g, b, a = 1] = m[1].split(',').map((x) => parseFloat(x));
      return { r, g, b, a };
    };
    const lum = ({ r, g, b }) => {
      const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const effectiveBg = (el) => {
      for (let e = el; e; e = e.parentElement) {
        const c = parse(getComputedStyle(e).backgroundColor);
        if (c && c.a > 0.5) return c;
      }
      return { r: 0, g: 0, b: 0, a: 1 };
    };
    const visible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && parseFloat(s.opacity) > 0.1;
    };
    const desc = (el) => `${el.tagName.toLowerCase()}.${(el.className && el.className.baseVal === undefined ? el.className : '').toString().split(' ').slice(0, 4).join('.')}`;
    const problems = [];
    const htmlDark = document.documentElement.classList.contains('dark');
    if (!htmlDark) problems.push('html is missing class "dark"');
    for (const el of document.querySelectorAll('body *')) {
      if (!visible(el) || el.closest('svg')) continue;
      const s = getComputedStyle(el);
      const bg = parse(s.backgroundColor);
      const rect = el.getBoundingClientRect();
      if (bg && bg.a > 0.5 && rect.width * rect.height > 1500 && lum(bg) > 0.45) {
        problems.push(`LIGHT SURFACE ${desc(el)} bg=${s.backgroundColor} ${Math.round(rect.width)}x${Math.round(rect.height)} "${(el.innerText || '').trim().slice(0, 40)}"`);
      }
      const ownText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
      if (ownText) {
        const fg = parse(s.color);
        const back = effectiveBg(el);
        if (fg) {
          const [hi, lo] = [lum(fg), lum(back)].sort((a, b) => b - a);
          const contrast = (hi + 0.05) / (lo + 0.05);
          if (contrast < 3) problems.push(`LOW CONTRAST ${desc(el)} color=${s.color} on ${JSON.stringify(back)} ratio=${contrast.toFixed(2)} "${el.innerText.trim().slice(0, 40)}"`);
        }
      }
    }
    return { label, problems: [...new Set(problems)] };
  }, label);
}
module.exports = { auditDark };
