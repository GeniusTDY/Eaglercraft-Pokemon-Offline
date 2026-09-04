"""批量删除项目中的注释（保持功能不变）。

按文件类型分别处理：
  - .py      : tokenize 识别注释，保留 shebang 与编码声明
  - .java    : 状态机（字符串/字符字面量安全）
  - .sh      : 状态机（引号/heredoc 安全，保留 shebang）
  - .yml/.yaml: 状态机（引号/块标量安全）
  - .properties: 行首 # 或 !
  - .css     : 状态机（字符串安全）
  - .js/.html: 调用 node + espree 处理（见 clean_js.js）

跳过目录与二进制/数据文件。用法: python3 clean_comments.py [--apply]
不带 --apply 时仅统计（dry-run）。
"""
import io
import os
import re
import subprocess
import sys
import tokenize

ROOT = '/workspace'

SKIP_DIRS = {
    '__pycache__', '.git', '.trae-html-share-packages',
    'build', 'classes',               
    'world', 'world_nether', 'world_the_end',  
    'logs', 'crash-reports', 'cache', 'versions',
    'eagcert', 'players', 'disabled', 'locales', 'drivers',
    'lang_dump',                      
}

PROCESS_EXTS = {'.py', '.java', '.sh', '.yml', '.yaml', '.properties', '.css', '.js', '.html'}
NODE = 'node'
NODE_PATH = '/root/.nvm/versions/node/v24.1.0/lib/node_modules/eslint/node_modules'
HELPER = os.path.join(ROOT, '_clean_js.js')





def _py_comment_ranges(src):
    """返回 (start_offset, end_offset) 列表，用 tokenize 找出真实注释。"""
    try:
        toks = tokenize.generate_tokens(io.StringIO(src).readline)
        toks = list(toks)
    except Exception:
        return None
    line_offsets = []
    off = 0
    for ln in src.splitlines(True):
        line_offsets.append(off)
        off += len(ln)

    def pos2off(row, col):
        if row - 1 < len(line_offsets):
            return line_offsets[row - 1] + col
        return off

    ranges = []
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            s = pos2off(tok.start[0], tok.start[1])
            e = pos2off(tok.end[0], tok.end[1])
            ranges.append((s, e))
    return ranges


def clean_py(src):
    if not src.strip():
        return src
    
    keep = 0
    lines = src.split('\n')
    if lines and lines[0].startswith('#!'):
        keep = 1
    if keep == 1 and len(lines) > 1 and re.match(r'^\s*#.*coding[:=]\s*[-a-zA-Z0-9_.]+', lines[1]):
        keep = 2
    keep_off = 0
    if keep:
        acc = 0
        for i in range(keep):
            acc += len(lines[i]) + 1  
        keep_off = acc
    ranges = _py_comment_ranges(src)
    if ranges is None:
        return src
    
    ranges = [(s, e) for (s, e) in ranges if e > keep_off and s >= keep_off]
    if not ranges:
        return src
    parts = []
    last = keep_off
    for s, e in ranges:
        if s < last:
            continue
        parts.append(src[last:s])
        seg = src[s:e]
        parts.append('\n' * seg.count('\n'))
        last = e
    parts.append(src[last:])
    return ''.join(parts)






def clean_java(src):
    out = []
    i = 0
    n = len(src)
    state = 'code'
    while i < n:
        c = src[i]
        if state == 'code':
            if c == '/' and i + 1 < n and src[i + 1] == '/':
                state = 'line'; i += 2; continue
            if c == '/' and i + 1 < n and src[i + 1] == '*':
                state = 'block'; i += 2; continue
            if c == '"':
                state = 'string'; out.append(c); i += 1; continue
            if c == "'":
                state = 'char'; out.append(c); i += 1; continue
            out.append(c); i += 1
        elif state == 'line':
            if c == '\n':
                out.append(c); state = 'code'
            i += 1
        elif state == 'block':
            if c == '*' and i + 1 < n and src[i + 1] == '/':
                state = 'code'; i += 2; continue
            if c == '\n':
                out.append(c)
            i += 1
        elif state == 'string':
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(src[i + 1]); i += 2; continue
            if c == '"':
                state = 'code'
            i += 1
        elif state == 'char':
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(src[i + 1]); i += 2; continue
            if c == "'":
                state = 'code'
            i += 1
    return ''.join(out)






def _strip_shell_comment(line):
    out = []
    i = 0
    n = len(line)
    in_sq = False
    in_dq = False
    while i < n:
        c = line[i]
        if in_sq:
            out.append(c)
            if c == "'":
                in_sq = False
            i += 1
            continue
        if in_dq:
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(line[i + 1]); i += 2; continue
            if c == '"':
                in_dq = False
            i += 1
            continue
        if c == "'":
            in_sq = True; out.append(c); i += 1; continue
        if c == '"':
            in_dq = True; out.append(c); i += 1; continue
        if c == '#':
            prev = line[i - 1] if i > 0 else ''
            if prev == '' or prev.isspace() or prev in ';|&()<>':
                return ''.join(out).rstrip()
            out.append(c); i += 1; continue
        out.append(c); i += 1
    return ''.join(out)


def clean_shell(src):
    lines = src.split('\n')
    out = []
    heredoc = None
    for idx, line in enumerate(lines):
        if idx == 0 and line.startswith('#!'):
            out.append(line)
            continue
        if heredoc is not None:
            out.append(line)
            if line.strip() == heredoc:
                heredoc = None
            continue
        s = _strip_shell_comment(line)
        out.append(s)
        m = re.search(r'<<-?\s*["\']?([A-Za-z_][A-Za-z0-9_]*)["\']?', s)
        if m:
            heredoc = m.group(1)
    return '\n'.join(out)






def _strip_yaml_comment(line):
    out = []
    i = 0
    n = len(line)
    in_sq = False
    in_dq = False
    while i < n:
        c = line[i]
        if in_sq:
            out.append(c)
            if c == "'":
                
                if i + 1 < n and line[i + 1] == "'":
                    out.append("'"); i += 2; continue
                in_sq = False
            i += 1
            continue
        if in_dq:
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(line[i + 1]); i += 2; continue
            if c == '"':
                in_dq = False
            i += 1
            continue
        if c == "'":
            in_sq = True; out.append(c); i += 1; continue
        if c == '"':
            in_dq = True; out.append(c); i += 1; continue
        if c == '#':
            prev = line[i - 1] if i > 0 else ''
            if prev == '' or prev.isspace():
                return ''.join(out).rstrip()
            out.append(c); i += 1; continue
        out.append(c); i += 1
    return ''.join(out)


def _block_scalar_indent(line):
    """若该行是块标量声明（key: | 或 key: >），返回需要原样保留的缩进值。"""
    s = line.rstrip()
    m = re.search(r'[|>][+-]?\d*\s*$', s)
    if not m:
        return None
    
    pre = s[:m.start()].rstrip()
    if not pre or pre.endswith(':'):
        return None
    
    return len(s) - len(s.lstrip())


def clean_yaml(src):
    lines = src.split('\n')
    out = []
    block_indent = None
    for raw in lines:
        if block_indent is not None:
            ind = len(raw) - len(raw.lstrip())
            if raw.strip() == '' or ind > block_indent:
                out.append(raw)
                continue
            block_indent = None
        s = _strip_yaml_comment(raw)
        out.append(s)
        bi = _block_scalar_indent(s)
        if bi is not None:
            block_indent = bi
    return '\n'.join(out)






def clean_properties(src):
    out = []
    for line in src.split('\n'):
        s = line.lstrip()
        if s.startswith('#') or s.startswith('!'):
            out.append('')
        else:
            out.append(line)
    return '\n'.join(out)


def clean_css(src):
    out = []
    i = 0
    n = len(src)
    state = 'code'
    while i < n:
        c = src[i]
        if state == 'code':
            if c == '/' and i + 1 < n and src[i + 1] == '*':
                state = 'block'; i += 2; continue
            if c == '"':
                state = 's1'; out.append(c); i += 1; continue
            if c == "'":
                state = 's2'; out.append(c); i += 1; continue
            out.append(c); i += 1
        elif state == 'block':
            if c == '*' and i + 1 < n and src[i + 1] == '/':
                state = 'code'; i += 2; continue
            if c == '\n':
                out.append(c)
            i += 1
        elif state == 's1':
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(src[i + 1]); i += 2; continue
            if c == '"':
                state = 'code'
            i += 1
        elif state == 's2':
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(src[i + 1]); i += 2; continue
            if c == "'":
                state = 'code'
            i += 1
    return ''.join(out)






def collect_files():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in PROCESS_EXTS:
                
                low = fn.lower()
                if 'backup' in low or '_before_' in low:
                    continue
                files.append(os.path.join(dirpath, fn))
    return files


HANDLERS = {
    '.py': clean_py,
    '.java': clean_java,
    '.sh': clean_shell,
    '.yml': clean_yaml,
    '.yaml': clean_yaml,
    '.properties': clean_properties,
    '.css': clean_css,
}


def main():
    apply = '--apply' in sys.argv
    files = sorted(collect_files())
    total_removed = 0
    total_changed = 0
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        with io.open(f, 'r', encoding='utf-8', errors='replace') as fh:
            src = fh.read()
        if ext in HANDLERS:
            out = HANDLERS[ext](src)
        elif ext in ('.js', '.html'):
            env = dict(os.environ)
            env['NODE_PATH'] = NODE_PATH
            p = subprocess.run([NODE, HELPER, f], capture_output=True, text=True, env=env)
            if p.returncode != 0:
                print('  [node error rc=%s] %s : %s' % (p.returncode, f, p.stderr.strip()[:120]))
                continue
            out = p.stdout
            if not out:
                print('  [node no output] %s' % f)
                continue
        else:
            continue
        removed = max(0, len(src) - len(out))
        if removed > 0:
            total_removed += removed
            total_changed += 1
            print('  %8d  %s' % (removed, os.path.relpath(f, ROOT)))
            if apply:
                with io.open(f, 'w', encoding='utf-8') as fh:
                    fh.write(out)
    print('----')
    print('files with comments removed: %d, bytes removed: %d (apply=%s)' % (
        total_changed, total_removed, apply))
    return 0


if __name__ == '__main__':
    sys.exit(main())
