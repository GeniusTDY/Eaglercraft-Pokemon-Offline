"""将 index.html 自动配置中的 enableUpdateSvc 改为 false（离线化）。
仅重编码 _eaglercraftX.g 的 gzip+base64 数据，保持其余字节不变。"""
import re, base64, gzip

P = '/workspace/web/index.html'
html = open(P, encoding='utf-8').read()

def rebake(m):
    key = m.group(1)
    if key != '_eaglercraftX.g':
        return m.group(0)
    b64 = m.group(2)
    data = gzip.decompress(base64.b64decode(b64)).decode('utf-8')
    if 'enableUpdateSvc' not in data:
        
        print('NOTE: enableUpdateSvc not present, injecting it')
        data = data.rstrip() + (',' if data and not data.endswith(',') else '') + 'enableUpdateSvc:false'
    elif 'enableUpdateSvc:true' in data:
        data = data.replace('enableUpdateSvc:true', 'enableUpdateSvc:false')
    else:
        print('NOTE: enableUpdateSvc already disabled')
    raw = gzip.compress(data.encode('utf-8'), 9)
    new_b64 = base64.b64encode(raw).decode('ascii')
    print('rebaked', key, 'len', len(b64), '->', len(new_b64))
    return m.group(0).replace(b64, new_b64)

html2, n = re.subn(r'localStorage\.setItem\("(_eaglercraftX\.g)", "([A-Za-z0-9+/=]+)"\)', rebake, html)
print('replacements:', n)
if n and html2 != html:
    open(P, 'w', encoding='utf-8').write(html2)
    print('written', P)
else:
    print('no change')
