// 校验 viewer.html 中的 parseMesh 纯逻辑：加载真实模型，核对中心/跨度与 Python 软渲染一致
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync('/workspace/web/viewer.html', 'utf8');
const m = src.match(/<script>([\s\S]*?)<\/script>/);
const code = m[1];
const start = code.indexOf('"use strict"');
const end = code.indexOf('/* ================= WebGL 渲染器 =================');
let pure = code.slice(start, end);
const sandbox = { Math, JSON, console };
vm.createContext(sandbox);
vm.runInContext(pure, sandbox);
const species = process.argv[2] || 'pikachu';
const g = JSON.parse(fs.readFileSync(`/workspace/web/models/${species}.geo.json`, 'utf8'));
const mesh = sandbox.parseMesh(g);
console.log(`${species}: tris=${mesh.count} center=[${mesh.center.map(v=>v.toFixed(2)).join(',')}] span=${mesh.span.toFixed(2)}`);