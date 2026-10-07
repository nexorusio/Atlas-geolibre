"""Apply the Nexorus frontend identity to the pinned GeoLens release."""

import json
import shutil
import sys
from pathlib import Path

frontend = Path(sys.argv[1])
bundle = Path(__file__).parent
assets = bundle / 'assets'
if json.loads((frontend / 'package.json').read_text())['version'] != '1.22.0':
    raise SystemExit('This branding bundle requires GeoLens 1.22.0.')

def replace(path, old, new):
    content = path.read_text()
    if old not in content:
        raise SystemExit(f'Upstream branding anchor missing: {path.name}')
    path.write_text(content.replace(old, new))

shutil.copyfile(bundle / 'GeoLensLogo.tsx', frontend / 'src/components/GeoLensLogo.tsx')
for name in ('nexorus-wordmark.png', 'nexorus-icon.png', 'favicon.png',
             'apple-touch-icon.png', 'pwa-192x192.png', 'pwa-512x512.png'):
    shutil.copyfile(assets / name, frontend / 'public' / name)

replace(frontend / 'src/hooks/use-document-title.ts', 'GeoLens', 'Nexorus Atlas Catalog')
replace(frontend / 'src/hooks/__tests__/use-document-title.test.ts', 'GeoLens', 'Nexorus Atlas Catalog')
for name in ('MapViewerGate.chunkLoadFailure', 'MapViewerGate.pendingChunk',
             'MapViewerGate', 'NotFoundPage'):
    replace(frontend / f'src/pages/__tests__/{name}.test.tsx',
            'GeoLens', 'Nexorus Atlas Catalog')
replace(frontend / 'src/pages/__tests__/LoginPage.footerAndMobileBranding.test.tsx',
        "name: /GeoLens/", "name: /Nexorus Atlas Catalog/")
for language in ('en', 'es', 'fr', 'de', 'zh'):
    path = frontend / f'src/i18n/locales/{language}/common.json'
    content = json.loads(path.read_text())
    content['appName'] = 'Nexorus Atlas Catalog'
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n')
replace(frontend / 'src/i18n/resources.test.ts',
        '// Product and standards names',
        "// Product and standards names\n  'common:appName', // Nexorus Atlas Catalog")

html = frontend / 'index.html'
content = html.read_text()
content = content.replace('GeoLens', 'Nexorus Atlas Catalog')
lines = [line for line in content.splitlines() if '<link rel="icon"' not in line]
index = next(i for i, line in enumerate(lines) if '<link rel="apple-touch-icon"' in line)
lines.insert(index, '    <link rel="icon" type="image/png" href="/favicon.png" />')
content = '\n'.join(lines) + '\n'
content = content.replace('content="/og-image.png"', 'content="/nexorus-icon.png"')
content = '\n'.join(line for line in content.splitlines()
                    if 'property="og:image:width"' not in line
                    and 'property="og:image:height"' not in line) + '\n'
html.write_text(content)

path = frontend / 'public/manifest.webmanifest'
manifest = json.loads(path.read_text())
manifest.update(name='Nexorus Atlas Catalog', short_name='Atlas Catalog',
                background_color='#08172f', theme_color='#08172f')
manifest['icons'] = [dict(src=f'/pwa-{size}x{size}.png', sizes=f'{size}x{size}',
                          type='image/png', purpose='any') for size in (192, 512)]
path.write_text(json.dumps(manifest, indent=2) + '\n')

with (frontend / 'src/index.css').open('a') as css:
    css.write('''

/* Nexorus Atlas surface colors; existing contrast and accent tokens remain. */
.dark {
  --background: #08172f;
  --card: #0d203d;
  --popover: #0d203d;
  --sidebar: #08172f;
}
''')
print('Nexorus Atlas Catalog branding applied.')
