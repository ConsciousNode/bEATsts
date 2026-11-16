import os, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
OUT = os.path.join(ROOT, 'beatsts.html')
CANVAS_OUT = os.path.join(os.path.dirname(ROOT), 'artifacts', 'file_generation', 'ttl=63d', 'output', 'beatsts.html')

parts = []
for fn in sorted(os.listdir(SRC)):
    if fn.endswith('.js'):
        with open(os.path.join(SRC, fn), 'r', encoding='utf-8') as f:
            parts.append(f'// === {fn} ===\n' + f.read())

js_bundle = '\n\n'.join(parts)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; media-src 'none'; connect-src 'none'; font-src 'none'; object-src 'none'; frame-src 'none';" />
  <title>bEATsts - ConsciousNode SoftWorks (MIT)</title>
  <!-- INLINE STYLE: GBA Shell, Crisp Pixel Canvas & Phone Touch Controls -->
  <style>
    * {{ box-sizing: border-box; user-select: none; -webkit-user-select: none; }}
    body {{
      margin: 0; padding: 8px;
      background: #14161f; color: #f8f8f0;
      font-family: monospace;
      display: flex; flex-direction: column; align-items: center; justify-content: flex-start;
      min-height: 100vh;
    }}
    .shell {{
      width: 100%; max-width: 560px;
      background: #232738; border: 3px solid #3c425e; border-radius: 14px;
      padding: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }}
    .header {{
      display: flex; justify-content: space-between; align-items: center;
      font-size: 12px; color: #f8e888; margin-bottom: 6px; flex-wrap: wrap; gap: 6px;
    }}
    .screen-wrap {{
      background: #0b0d14; padding: 6px; border-radius: 8px; border: 2px solid #10131d;
      display: flex; justify-content: center;
    }}
    #gba-screen {{
      width: 100%; max-width: 480px; aspect-ratio: 3 / 2;
      image-rendering: pixelated; image-rendering: crisp-edges;
      background: #101420; display: block;
    }}
    .controls-bar {{
      margin-top: 10px;
      display: flex; justify-content: space-between; align-items: center; gap: 8px;
    }}
    .dpad {{
      display: grid; grid-template-columns: repeat(3, 44px); grid-template-rows: repeat(3, 44px);
      gap: 3px;
    }}
    .dpad button, .ab-pad button, .sys-pad button {{
      background: #3a4058; color: #f8f8f0; border: 2px solid #565f82;
      border-radius: 8px; font-family: monospace; font-weight: bold; font-size: 14px;
      cursor: pointer; touch-action: manipulation;
    }}
    .dpad button:active, .ab-pad button:active, .sys-pad button:active {{
      background: #f0c040; color: #14161f;
    }}
    .dpad .empty {{ visibility: hidden; }}
    .ab-pad {{ display: flex; gap: 12px; align-items: center; }}
    .ab-pad button {{
      width: 54px; height: 54px; border-radius: 50%;
      background: #8c2f39; border-color: #c85862; font-size: 16px;
    }}
    .ab-pad button[data-gba-btn="A"] {{ background: #2d6a4f; border-color: #52b788; }}
    .sys-pad {{
      display: flex; flex-direction: column; gap: 6px; align-items: center;
    }}
    .sys-pad button {{ padding: 6px 10px; font-size: 11px; border-radius: 12px; }}
    .meta-row {{
      margin-top: 10px; padding-top: 8px; border-top: 1px solid #3c425e;
      display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: space-between;
      font-size: 11px;
    }}
    .meta-row input[type="text"] {{
      background: #14161f; color: #f8f8f0; border: 1px solid #565f82;
      padding: 4px 6px; border-radius: 4px; width: 96px; font-family: monospace;
    }}
    .meta-row button, .meta-row label.btn {{
      background: #2f354b; color: #a8dadc; border: 1px solid #565f82;
      padding: 4px 8px; border-radius: 4px; cursor: pointer; font-family: monospace; font-size: 11px;
    }}
    #import-file {{ display: none; }}
    @media (max-width: 420px) {{
      .dpad {{ grid-template-columns: repeat(3, 38px); grid-template-rows: repeat(3, 38px); }}
      .ab-pad button {{ width: 46px; height: 46px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="header">
      <span>bEATsts &bull; ConsciousNode SoftWorks (MIT)</span>
      <span>240&times;160 GBA Engine</span>
    </div>
    <div class="screen-wrap">
      <canvas id="gba-screen" width="240" height="160"></canvas>
    </div>
    <div class="controls-bar">
      <div class="dpad" aria-label="D-Pad">
        <div class="empty"></div>
        <button type="button" data-gba-btn="UP" aria-label="Up">&#9650;</button>
        <div class="empty"></div>
        <button type="button" data-gba-btn="LEFT" aria-label="Left">&#9664;</button>
        <div class="empty"></div>
        <button type="button" data-gba-btn="RIGHT" aria-label="Right">&#9654;</button>
        <div class="empty"></div>
        <button type="button" data-gba-btn="DOWN" aria-label="Down">&#9660;</button>
        <div class="empty"></div>
      </div>
      <div class="sys-pad">
        <button type="button" data-gba-btn="START">START (M)</button>
        <button type="button" data-gba-btn="SELECT">SELECT (N)</button>
      </div>
      <div class="ab-pad">
        <button type="button" data-gba-btn="B" aria-label="B Button">B</button>
        <button type="button" data-gba-btn="A" aria-label="A Button">A</button>
      </div>
    </div>
    <div class="meta-row">
      <div>Name: <input id="player-name-input" type="text" maxlength="10" value="Brie" aria-label="Player Name" /></div>
      <div style="display:flex;gap:6px;">
        <button type="button" id="btn-export-save">Export Save</button>
        <label class="btn" for="import-file">Import Save</label>
        <input type="file" id="import-file" accept=".json,application/json" />
      </div>
    </div>
  </div>

  <!-- INLINE SCRIPT: bEATsts Complete Data, GBA Graphics, Chiptune Audio & Game Engine -->
  <script>
{js_bundle}

// Wire Export / Import Save file buttons (CSP-safe data: URI download)
document.getElementById('btn-export-save').addEventListener('click', () => {{
  const json = Game.exportSaveJson(Game.activeSlot);
  if (!json) return;
  const a = document.createElement('a');
  a.href = 'data:application/json;charset=utf-8,' + encodeURIComponent(json);
  a.download = `beatsts_slot_${{Game.activeSlot + 1}}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}});

document.getElementById('import-file').addEventListener('change', (ev) => {{
  const file = ev.target.files && ev.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {{
    if (Game.importSaveJson(String(reader.result), Game.activeSlot)) {{
      Game.screen = 'OVERWORLD';
      Game.playMapMusic();
    }}
  }};
  reader.readAsText(file);
}});

window.addEventListener('load', () => Game.init());
  </script>
</body>
</html>
"""

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)

os.makedirs(os.path.dirname(CANVAS_OUT), exist_ok=True)
shutil.copyfile(OUT, CANVAS_OUT)
print(f"Built {OUT} ({len(html)} bytes) and copied to {CANVAS_OUT}")
