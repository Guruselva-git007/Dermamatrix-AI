/* Original, decorative vector art. No photo, biometric or model data enters it.
   CSS owns motion; removing its children cancels every animation immediately. */
(() => {
  'use strict';
  const face = () => {
    const widths = [22, 48, 64, 70, 68, 56, 37, 13];
    const rows = widths.map((width, row) => Array.from({ length: 7 }, (_, col) => [280 + (col - 3) * width / 3, 36 + row * 24 + Math.abs(col - 3) * (row < 4 ? 2 : -2)]));
    const lines = [];
    rows.forEach((row, r) => row.forEach((p, c) => {
      if (c < row.length - 1) lines.push(`M${p}L${row[c + 1]}`);
      if (r < rows.length - 1) {
        lines.push(`M${p}L${rows[r + 1][c]}`);
        if (c < row.length - 1) lines.push(`M${p}L${rows[r + 1][c + 1]}`);
      }
    }));
    return `<g class="scanner-mesh"><path d="${lines.join(' ')}"/></g><g class="scanner-contour"><path d="M280 22C231 22 208 55 211 107L219 163Q238 211 280 230Q322 211 341 163L349 107C352 55 329 22 280 22Z"/><path d="M229 101Q246 84 263 102Q246 117 229 101ZM297 102Q314 84 331 101Q314 117 297 102ZM280 102L268 145Q280 152 292 145M252 177Q280 163 308 177Q280 192 252 177Z"/><circle cx="247" cy="102" r="6"/><circle cx="313" cy="102" r="6"/></g>`;
  };
  const iris = `<g transform="translate(112 130)" class="scanner-satellite"><circle r="52"/><circle r="43" stroke-dasharray="2 5"/><circle r="29"/><circle r="13"/><path d="M-66 0Q0-65 66 0Q0 65-66 0Z"/><path d="M0-52V-30M0 30V52M-52 0H-30M30 0H52"/></g>`;
  const ridges = (x, y, scale = 1) => `<g transform="translate(${x} ${y}) scale(${scale})" class="scanner-ridges">${[15, 24, 33, 42, 51].map(r => `<path d="M${-r} 40V0A${r} ${r} 0 0 1 ${r} 0V34Q${r} ${70 + r / 3} ${r - 18} ${80 + r / 3}"/>`).join('')}<path d="M0-7V30Q0 57-12 69M-8 4V30Q-8 48-17 58"/></g>`;
  const hair = `<g class="scanner-contour"><path d="M219 211Q207 155 216 102C226 20 339 18 347 103Q351 162 335 211M231 212Q224 168 229 111C235 47 327 43 333 111Q337 170 322 216"/>${[-40,-26,-12,2,16,30,44].map((x,i)=>`<path d="M${280+x} 211C${250+x} 170 ${320+x/2} 104 ${276+x} ${45+Math.abs(3-i)*8}"/>`).join('')}</g><g class="scanner-mesh"><path d="M211 130Q280 89 349 130M211 153Q280 116 347 153M217 177Q280 145 342 177"/></g>`;
  const nail = `<g class="scanner-contour"><path d="M228 228V86C228 12 332 12 332 86V228M242 112V83Q242 43 280 43Q318 43 318 83V112Q280 137 242 112Z"/><path d="M246 146Q280 156 314 146M243 169Q280 180 317 169M242 194Q280 205 318 194"/></g><g class="scanner-mesh"><path d="M253 59L306 112M241 84L296 125M272 44L318 89M242 112L302 53M259 124L317 70"/></g>`;
  const sweat = `<g class="scanner-contour"><path d="M280 31C264 61 232 91 232 124A48 48 0 0 0 328 124C328 91 296 61 280 31Z"/><path d="M251 124Q251 148 271 151M280 55V72"/></g><g class="scanner-mesh"><ellipse cx="280" cy="200" rx="86" ry="20"/><ellipse cx="280" cy="200" rx="61" ry="13"/><ellipse cx="280" cy="200" rx="35" ry="7"/></g>`;
  const artwork = {
    Skin: () => face() + iris + ridges(449, 110, .78),
    Hair: () => hair + `<g class="scanner-satellite"><path d="M65 176Q113 54 160 106M72 193Q129 62 160 124M81 204Q140 90 162 146"/><circle cx="442" cy="131" r="47"/><path d="M414 153Q425 88 456 103M426 163Q446 95 466 120M439 166Q455 115 474 137"/></g>`,
    Nails: () => nail + iris + ridges(449, 110, .78),
    Sweat: () => sweat + `<g class="scanner-satellite"><circle cx="112" cy="130" r="48"/><path d="M83 130L103 150L140 111M419 100H478M419 130H466M419 160H478"/><circle cx="405" cy="100" r="2"/><circle cx="405" cy="130" r="2"/><circle cx="405" cy="160" r="2"/></g>`,
  };
  function stop() {
    const stage = document.getElementById('assessmentScanner');
    if (!stage) return;
    stage.classList.remove('is-scanning');
    stage.innerHTML = '';
    delete stage.dataset.variant;
  }
  function start(area) {
    stop();
    const stage = document.getElementById('assessmentScanner');
    if (!stage || !Object.hasOwn(artwork, area)) return;
    stage.dataset.variant = area.toLowerCase();
    stage.innerHTML = `<svg viewBox="0 0 560 260" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg"><g class="scanner-grid"><path d="M30 65H530M30 130H530M30 195H530M112 22V238M196 22V238M280 22V238M364 22V238M448 22V238"/></g><g class="scanner-orbit"><ellipse cx="280" cy="130" rx="112" ry="116" stroke-dasharray="2 7"/></g>${artwork[area]()}<g class="scanner-brackets"><path d="M202 49V21H229M331 21H358V49M202 211V239H229M331 239H358V211"/></g></svg><span class="scanner-beam"></span><span class="scanner-pulse"></span>`;
    stage.classList.add('is-scanning');
    visibility();
  }
  function visibility() {
    document.getElementById('assessmentScanner')?.classList.toggle('is-paused', document.hidden);
  }
  document.addEventListener('visibilitychange', visibility);
  window.AssessmentScanner = Object.freeze({ start, stop });
})();
