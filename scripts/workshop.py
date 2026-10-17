"""节目素材工坊：初始化、比例适配、Wowidea 生成、建置及 GitHub Pages 部署。"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

KIT = Path(__file__).resolve().parents[1]
FOLDERS = {
    "01_分镜": "段落表、时间码、分镜和转场设计。",
    "02_参考素材": "风格图、视觉参考和设计参考；保留来源说明。",
    "03_资产与需求": "show.json、屏幕分辨率、舞台遮罩、PGM 遮罩及原始设计稿。",
    "04_输出交付": "按版本保存最终网页、预览和部署记录。",
    "05_素材工坊": "工坊源代码、构建工具、运行环境和配置。",
    "06_音乐": "原始音频、歌词、节拍表；不自动公开发布原音频。",
    "07_AE资产素材": "生成原件、比例适配后的 PNG、生成计划和任务记录。",
    "08_Blender工程": "需要时保存三维工程及依赖素材。",
    "99_归档": "旧版本与明确淘汰的素材，不覆盖原件。"
}
SPEC = "03_资产与需求/show.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run(command, cwd=None, timeout=120):
    result = subprocess.run([str(x) for x in command], cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode:
        detail = (result.stderr or result.stdout)[-3000:]
        # CLI diagnostics should not contain tokens; redact known credential patterns anyway.
        detail = re.sub(r'(?i)(Bearer\s+|(?:api[_-]?key|access[_-]?token)["\s:=]+)[^\s",}]+', r'\1[REDACTED]', detail)
        raise RuntimeError(f"命令失败（退出码 {result.returncode}）：{Path(str(command[0])).name}\n{detail}")
    return result.stdout.strip()


def decode(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some CLI versions put a short progress prefix before the envelope.
        for i, ch in enumerate(text):
            if ch == '{':
                try:
                    return json.JSONDecoder().raw_decode(text[i:])[0]
                except json.JSONDecodeError:
                    pass
        raise ValueError("CLI 未返回可识别的 JSON；请检查原任务，勿自动重复提交。")


def cli(project):
    candidates = [project / "05_素材工坊/.wowidea/runtime/dist/cli.js",
                  project / "05_素材工坊/.tools/wowidea/dist/cli.js",
                  project / "05_素材工坊/.tools/wowidea/node_modules/@easyai/cli/dist/cli.js",
                  KIT / ".tools/wowidea/node_modules/@easyai/cli/dist/cli.js"]
    node = shutil.which("node")
    for path in candidates:
        if path.is_file() and node:
            return [node, str(path)]
    executable = shutil.which("wowidea.cmd" if os.name == "nt" else "wowidea")
    if executable:
        bundled = Path(executable).parent / 'node_modules/@easyai/cli/dist/cli.js'
        if bundled.is_file() and node:
            return [node, str(bundled)]
        return [executable]
    raise RuntimeError("未找到 Wowidea CLI。先运行 scripts/install.py，或安装 @easyai/cli 并完成账号初始化。")


def model_info(project, model):
    data = decode(run(cli(project) + ["models", "show", model, "--json"], timeout=120))
    return data.get("data", data)


def choose_ratio(width, height, ratios):
    valid = []
    for ratio in ratios:
        if re.fullmatch(r"\d+(?:\.\d+)?:\d+(?:\.\d+)?", ratio):
            a, b = map(float, ratio.split(':'))
            if a > 0 and b > 0:
                valid.append((abs(math.log((a / b) / (width / height))), ratio))
    if not valid:
        raise ValueError("所选模型没有明确可用的图片比例，请检查实时模型能力。")
    return min(valid)[1]


def render_prompt(template, values):
    def replace(match):
        key = match.group(1)
        if key not in values:
            raise ValueError(f"未知提示词占位符：{key}")
        return str(values[key])
    return re.sub(r"\{\{([^{}]+)\}\}", replace, template)


def load_project(project):
    show = read(project / SPEC)
    if show.get("schemaVersion") != 1:
        raise ValueError("show.json schemaVersion 必须为 1")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", show["id"]):
        raise ValueError("节目 id 使用英文字母开头的英数、下划线或短横线。")
    for key in ['width', 'height']:
        n = show['stage'][key]
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            raise ValueError("舞台宽高必须为正整数")
    if not isinstance(show['fps'], int) or show['fps'] <= 0 or show['bpm'] <= 0:
        raise ValueError("fps 为正整数、bpm 为正数。")
    if not show['parts'] or not show['screens']:
        raise ValueError("至少需要一个段落和一个屏幕区域")
    for collection in [show['parts'], show['screens']]:
        ids = [x['id'] for x in collection]
        if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', x) for x in ids):
            raise ValueError('屏幕和段落 ID 必须唯一，使用英文字母开头的英数、下划线或短横线')
    for part in show['parts']:
        if part['duration']['unit'] not in ['seconds', 'beats'] or part['duration']['value'] <= 0:
            raise ValueError('段落需要正数 seconds 或 beats 时长')
    for screen in show['screens']:
        if min(screen['x'], screen['y']) < 0 or min(screen['w'], screen['h']) <= 0:
            raise ValueError('屏幕位置和宽高无效')
        if screen['x'] + screen['w'] > show['stage']['width'] or screen['y'] + screen['h'] > show['stage']['height']:
            raise ValueError('屏幕区域超出舞台')
    return show


def import_file(source, root, folder):
    if not source:
        return None
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError(f"输入文件不存在：{source}")
    target = root / folder / source.name
    if source != target.resolve():
        if target.exists():
            raise FileExistsError(f"目标已存在，拒绝覆盖：{target}")
        shutil.copy2(source, target)
    return target.relative_to(root).as_posix()


def init_project(args):
    from PIL import Image
    project = args.project.resolve()
    if (project / SPEC).exists():
        raise FileExistsError("项目已经初始化；请直接修改 show.json，不会覆盖现有目录。")
    project.mkdir(parents=True, exist_ok=True)
    for name, purpose in FOLDERS.items():
        folder = project / name
        folder.mkdir(exist_ok=True)
        readme = folder / "目录说明.md"
        if not readme.exists():
            readme.write_text(f"# {name}\n\n{purpose}\n", encoding='utf-8')
    # The runner is self-contained after copying into 05_素材工坊.
    runtime = project / '05_素材工坊'
    if runtime.resolve() != KIT.resolve():
        for name in ['src', 'tools', 'scripts', 'docs', 'skills']:
            if (KIT / name).is_dir():
                shutil.copytree(KIT / name, runtime / name, dirs_exist_ok=False,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copyfile(KIT / 'requirements.txt', runtime / 'requirements.txt')
    mask_file = import_file(args.mask, project, '03_资产与需求')
    if mask_file:
        with Image.open(project / mask_file) as im:
            if im.size != (args.width, args.height) or im.format != 'PNG':
                raise ValueError('遮罩必须是与正式屏幕完全同尺寸的 PNG，不能自动拉伸。已保留原件。')
        mask = {'type': 'image', 'file': mask_file, 'channel': args.mask_channel, 'invert': args.mask_invert}
    else:
        mask = {'type': 'geometry', 'shapes': [{'type': 'rect', 'x': 0, 'y': 0, 'w': args.width, 'h': args.height}]}
    audio_file = import_file(args.audio, project, '06_音乐')
    show = {
        'schemaVersion': 1, 'id': args.id, 'name': args.name,
        'stage': {'width': args.width, 'height': args.height}, 'fps': args.fps, 'bpm': args.bpm,
        'stageMask': mask, 'pgm': {'enabled': False},
        'screens': [{'id': 'main', 'name': '主屏', 'x': 0, 'y': 0, 'w': args.width, 'h': args.height}],
        'style': args.style, 'palette': ['#101827', '#261c48', '#f9afcf', '#87dbe5'],
        'audio': {'file': audio_file, 'offsetSeconds': 0, 'embedPreview': False, 'notes': ''},
        'generation': {'model': 'Nano Banana 2', 'resolution': '4K', 'maxJobs': 12, 'fit': 'cover',
                       'references': [], 'promptTemplate': '为《{{节目名称}}》的{{段落名称}}制作舞台视觉背景。屏幕为{{屏幕名称}}，正式尺寸{{屏幕宽}}×{{屏幕高}}，比例{{屏幕比例}}；生成采用模型支持的{{生成比例}}。风格：{{风格}}。该段{{时长秒}}秒，{{BPM}} BPM。视觉方向：{{段落提示}}。音频描述：{{音频摘要}}。请让主体和关键轮廓适合远距离观看，照顾宽高比例和边缘裁切。文字由网页独立排版，生成图不要添加文字、水印或界面。'},
        'parts': [{'id': 'S01', 'name': '主视觉循环', 'duration': {'unit': 'seconds', 'value': args.duration},
                   'loop': True, 'text': args.name, 'subtitle': '节目专属素材工坊',
                   'prompt': args.style, 'backgrounds': {}}]
    }
    write(project / SPEC, show)
    (project / '00_项目简报.md').write_text(f'# {args.name}｜项目简报\n\n- 节目代号：{args.id}\n- 正式画布：{args.width}×{args.height}\n- FPS：{args.fps}\n- BPM：{args.bpm}\n- 初始时长：{args.duration} 秒\n- 配置：[show.json](03_资产与需求/show.json)\n- 目录说明：[项目目录说明.md](项目目录说明.md)\n\n'+('已导入遮罩。\n' if mask_file else '**尚未提供遮罩，暂用全画布；正式舞台映射尚未验收。**\n'), encoding='utf-8')
    (project / '项目目录说明.md').write_text('# 项目目录说明\n\n' + '\n'.join(f'- `{k}/`：{v}' for k, v in FOLDERS.items()) + '\n\n配置入口：`03_资产与需求/show.json`。工坊入口：`05_素材工坊/scripts/workshop.py`。交付网页在 `04_输出交付/<版本>/web/index.html`。\n', encoding='utf-8')
    for filename, heading in [('00_子对话说明.md', '交接说明'), ('进度.md', '制作进度'), ('成片ID记录.md', '成片与任务 ID 记录'), ('制作方案.md', '制作方案')]:
        p = project / filename
        if not p.exists():
            p.write_text(f'# {heading}\n\n项目已初始化。先读取 `00_项目简报.md`、`项目目录说明.md` 和 `03_资产与需求/show.json`。\n', encoding='utf-8')
    skill = KIT / 'skills/stage-asset-workshop'
    if skill.is_dir():
        shutil.copytree(skill, project / '.agents/skills/stage-asset-workshop', dirs_exist_ok=True)
    (project / 'AGENTS.md').write_text('# 节目素材工坊\n\n先读 `00_项目简报.md` 和 `03_资产与需求/show.json`。按 `.agents/skills/stage-asset-workshop/SKILL.md` 工作。网页使用简体中文；原始素材保留；任务 ID 和进度写回根目录文档。使用 Wowidea CLI --direct，不使用 Canvas，不自行绕过平台调用供应商。\n', encoding='utf-8')
    print(f'已初始化：{project}\n配置：{project / SPEC}\n下一步：编辑段落、屏幕区域及视觉需求，运行 plan。')


def plan(project, capability=None):
    show = load_project(project)
    gen = show['generation']
    info = read(capability) if capability else model_info(project, gen['model'])
    info = info.get('data', info)
    cap = info.get('capabilities', {}).get('image_generate', {})
    ratios = cap.get('aspect_ratio_allowed', [])
    if gen['resolution'] not in cap.get('output_resolutions', []):
        raise ValueError('所选分辨率不在模型实时能力内；请修改设置，不会自动更换模型或规格。')
    jobs = []
    for part in show['parts']:
        seconds = part['duration']['value'] * (60 / show['bpm'] if part['duration']['unit'] == 'beats' else 1)
        for screen in show['screens']:
            ratio = choose_ratio(screen['w'], screen['h'], ratios)
            divisor = math.gcd(int(screen['w']), int(screen['h']))
            values = {'节目名称': show['name'], '段落名称': part['name'], '屏幕名称': screen['name'],
                      '屏幕宽': screen['w'], '屏幕高': screen['h'],
                      '屏幕比例': f"{int(screen['w'])//divisor}:{int(screen['h'])//divisor}", '生成比例': ratio,
                      '时长秒': round(seconds, 4), 'BPM': show['bpm'], '风格': show['style'],
                      '段落提示': part.get('prompt', show['style']), '文本': part.get('text', ''),
                      '音频摘要': show.get('audio', {}).get('notes', '')}
            prompt = render_prompt(gen['promptTemplate'], values)
            references = []
            reference_hashes = []
            for ref in gen.get('references', []):
                path = (project / ref).resolve()
                if not path.is_file():
                    raise ValueError(f'参考文件不存在：{ref}')
                references.append(str(path))
                reference_hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
            request = {'model': gen['model'], 'prompt': prompt, 'aspect_ratio': ratio, 'resolution': gen['resolution'], 'n': 1}
            if references:
                request['image_urls'] = references
            identity = {'part': part['id'], 'screen': screen['id'], 'request': {k:v for k,v in request.items() if k!='image_urls'},
                        'referenceHashes': reference_hashes}
            key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
            jobs.append({'id': key, 'partId': part['id'], 'screenId': screen['id'], 'target': screen,
                         'fit': gen.get('fit', 'cover'), 'request': request})
    if len(jobs) > gen.get('maxJobs', 12):
        raise ValueError(f"计划为 {len(jobs)} 个生成任务，超出 maxJobs={gen.get('maxJobs',12)}；未提交任务。请明确修改任务范围或上限。")
    result = {'schemaVersion': 1, 'projectId': show['id'], 'jobs': jobs,
              'note': '生成比例来自实时模型能力；正式像素通过保留原件的本地 cover/contain 适配。生成不等于原生舞台解析度。'}
    write(project / '07_AE资产素材/生成计划.json', result)
    write(project / '07_AE资产素材/模型能力.json', info)
    print(f'已生成计划：{len(jobs)} 项。未提交付费任务。')
    return result


def fit_image(source, target, width, height, mode):
    from PIL import Image, ImageOps
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert('RGBA')
        if mode == 'cover':
            output = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS)
        elif mode == 'contain':
            fitted = ImageOps.contain(image, (width, height), method=Image.Resampling.LANCZOS)
            output = Image.new('RGBA', (width, height))
            output.alpha_composite(fitted, ((width-fitted.width)//2, (height-fitted.height)//2))
        else:
            raise ValueError('fit 必须为 cover 或 contain；不默认非等比拉伸。')
        target.parent.mkdir(parents=True, exist_ok=True)
        output.save(target)


def generate(project):
    from PIL import Image
    show = load_project(project)
    jobs = plan(project)['jobs']
    runtime = project / '05_素材工坊'
    runtime.mkdir(parents=True, exist_ok=True)
    setup = decode(run(cli(project) + ['--json', 'project', 'setup', '--dir', runtime, '--name', show['name'], '--no-canvas'], timeout=300))
    # User-selected CLI direct mode; local setup never creates a remote Canvas.
    for job in jobs:
        record_path = project / f"07_AE资产素材/生成记录/{job['id']}.json"
        adapted = project / f"07_AE资产素材/适配素材/{job['partId']}_{job['screenId']}_{job['id']}.png"
        if record_path.exists():
            old = read(record_path)
            if old.get('status') == 'complete':
                original = Path(old.get('original', ''))
                if not original.is_absolute():
                    original = project / original
                adaptation = {'fit': job['fit'], 'width': int(job['target']['w']), 'height': int(job['target']['h'])}
                if not adapted.is_file() or old.get('adaptation') != adaptation:
                    if not original.is_file():
                        raise RuntimeError('已完成任务的原件不存在，无法重新适配。请恢复原任务下载，不会重复生成。')
                    fit_image(original, adapted, adaptation['width'], adaptation['height'], adaptation['fit'])
                    old['adaptation'] = adaptation
                    write(record_path, old)
                print(f"复用已完成素材：{job['id']}")
                part = next(p for p in show['parts'] if p['id']==job['partId'])
                part.setdefault('backgrounds', {})[job['screenId']] = adapted.relative_to(project).as_posix()
                continue
            raise RuntimeError(f"任务 {job['id']} 已有提交记录，状态 {old.get('status')}；请检查原任务，不会自动重提。记录：{record_path}")
        request_path = project / f"07_AE资产素材/请求/{job['id']}.json"
        write(request_path, job['request'])
        record = {'id': job['id'], 'status': 'submitting', 'requestedRatio': job['request']['aspect_ratio'],
                  'requestedResolution': job['request']['resolution']}
        write(record_path, record)
        try:
            envelope = decode(run(cli(project) + ['--json','image','generate','--direct','--file',request_path,
                                  '--project-dir',runtime,'--dir',project/'07_AE资产素材/生成原件'], timeout=3600))
            data = envelope.get('data', envelope)
            record['result'] = data
            paths = data.get('paths') or []
            if isinstance(paths, dict):
                paths = list(paths.values())
            if isinstance(paths, str):
                paths = [paths]
            if data.get('outputSpec', {}).get('status') == 'mismatch':
                raise ValueError('Wowidea 返回 outputSpec mismatch；保留原任务，不会自动重生成。')
            originals = [Path(p) for p in paths if isinstance(p,str) and Path(p).is_file()]
            if not originals:
                raise ValueError('任务未返回本地下载文件；请恢复同一任务下载，不会重复提交。')
            original = originals[0]
            with Image.open(original) as image:
                iw, ih = image.size
            a, b = map(float, job['request']['aspect_ratio'].split(':'))
            if abs(math.log((iw/ih)/(a/b))) > .035:
                raise ValueError(f'生成比例不符：实际 {iw}×{ih}，要求 {a:g}:{b:g}。保留结果，不重试。')
            fit_image(original, adapted, int(job['target']['w']), int(job['target']['h']), job['fit'])
            record.update(status='complete', originalSize=[iw,ih], adapted=adapted.relative_to(project).as_posix(),
                          original=os.path.relpath(original,project), taskId=data.get('taskId'), billing=data.get('pricing','接口未提供'),
                          adaptation={'fit':job['fit'],'width':int(job['target']['w']),'height':int(job['target']['h'])})
            part = next(p for p in show['parts'] if p['id']==job['partId'])
            part.setdefault('backgrounds', {})[job['screenId']] = adapted.relative_to(project).as_posix()
            write(project/SPEC,show)
            write(record_path,record)
            with (project/'成片ID记录.md').open('a',encoding='utf-8') as stream:
                stream.write(f"\n- {job['partId']}/{job['screenId']}：CLI direct 任务 `{record.get('taskId')}`，记录 `{record_path.relative_to(project).as_posix()}`\n")
            print(f"素材完成：{adapted}\nCLI 任务：{record.get('taskId')}\n计费：{record['billing']}")
        except Exception as error:
            record.update(status='needs_attention', diagnostic=str(error))
            write(record_path,record)
            raise
    write(project/SPEC,show)


def inspect_audio(project, show):
    audio = show.get('audio', {})
    if not audio.get('file'):
        return None
    path = project / audio['file']
    if not path.is_file():
        raise ValueError('音频文件不存在')
    probe = shutil.which('ffprobe')
    if probe:
        info = decode(run([probe,'-v','error','-show_entries','format=duration:stream=codec_type,sample_rate,channels','-of','json',path]))
        duration = float(info.get('format',{}).get('duration',0))
        audio['durationSeconds'] = duration
        write(project/'06_音乐/音频信息.json',info)
    elif path.suffix.lower()=='.wav':
        import wave
        with wave.open(str(path)) as stream:
            audio['durationSeconds'] = stream.getnframes()/stream.getframerate()
    else:
        print('未找到 ffprobe：保留音频，不推断精确时长和 BPM。')
    return audio


def build(project, output=None):
    show = load_project(project)
    audio = inspect_audio(project,show)
    runtime = project/'05_素材工坊'
    runtime.mkdir(parents=True,exist_ok=True)
    base = runtime.resolve()
    def relative(path):
        return Path(os.path.relpath((project/path).resolve(),base)).as_posix()
    def mask(spec):
        result = dict(spec)
        if result.get('type')=='image':
            result['file']=relative(result['file'])
        return result
    assets, parts = {}, []
    for part in show['parts']:
        item = dict(part)
        item['backgroundAssets'] = []
        for screen in show['screens']:
            path = part.get('backgrounds',{}).get(screen['id'])
            if path:
                key=f"{part['id']}_{screen['id']}"
                assets[key]={'file':relative(path),'x':screen['x'],'y':screen['y'],'w':screen['w'],'h':screen['h']}
                item['backgroundAssets'].append(key)
        item['layers']=[{'id':'background','name':'视觉背景','static':True,'cutPgm':True},
                        {'id':'art','name':'标题文字','cutPgm':True},
                        {'id':'fx','name':'节拍特效'},
                        {'id':'frame','name':'屏幕轮廓','static':True}]
        parts.append(item)
    pgm=dict(show.get('pgm',{'enabled':False}))
    if pgm.get('enabled'):
        pgm['mask']=mask(pgm['mask'])
    cfg={'schemaVersion':1,'projectId':show['id'],'title':show['name']+' · 素材工坊','stage':show['stage'],
         'fps':show['fps'],'bpm':show['bpm'],'previewMaxWidth':1440,'imageSmoothing':True,'clipExportToStage':show.get('clipExportToStage',False),
         'stageMask':mask(show['stageMask']),'pgm':pgm,'assets':assets,'parts':parts,'palette':show.get('palette',[]),
         'audio':dict(audio or {}),'screens':show['screens']}
    if audio:
        cfg['audio']['file']=relative(audio['file'])
    write(runtime/'project.config.json',cfg)
    output = Path(output).resolve() if output else project/'04_输出交付'/time.strftime('v%Y%m%d_%H%M%S')/'web'
    spec=importlib.util.spec_from_file_location('workshop_builder',KIT/'tools/build.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.build(runtime/'project.config.json',output)
    shutil.copyfile(output/'workshop.html',output/'index.html')
    (output/'.nojekyll').touch()
    write(output/'workshop-site.json',{'generator':'stage-asset-workshop','projectId':show['id'],'title':show['name'],'width':show['stage']['width'],'height':show['stage']['height'],'fps':show['fps']})
    # The full source snapshot can reveal local source paths; the public build only needs runtime metadata.
    (output/'project.snapshot.json').unlink()
    with (project/'进度.md').open('a',encoding='utf-8') as stream:
        stream.write(f'\n- 已构建网页：`{output}`；待按正式舞台和 AE 工程验收。\n')
    print(f'网页入口：{output / "index.html"}')
    return output


def deploy(project, directory, repository):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
        raise ValueError('部署仓库格式为 owner/repo')
    directory=Path(directory).resolve()
    marker=read(directory/'workshop-site.json')
    if marker.get('generator')!='stage-asset-workshop':
        raise ValueError('只部署本工具生成并带标记的静态网页目录')
    gh=shutil.which('gh')
    git=shutil.which('git')
    if not gh or not git:
        raise RuntimeError('部署需要 Git 和 GitHub CLI；先安装并完成 gh auth login。')
    run([gh,'auth','status'])
    result=subprocess.run([gh,'repo','view',repository,'--json','name'],capture_output=True)
    if result.returncode:
        # Creation is explicitly requested by invoking deploy with the target repo.
        run([gh,'repo','create',repository,'--public','--description','节目专属素材工坊，由 stage-asset-workshop 构建'])
    url=f'https://github.com/{repository}.git'
    with tempfile.TemporaryDirectory(prefix='stage-workshop-deploy-') as temp:
        checkout=Path(temp)/'site'
        branches=run([git,'ls-remote','--heads',url,'gh-pages'])
        if branches:
            run([git,'clone','--quiet','--depth','1','--branch','gh-pages','--single-branch',url,checkout])
            existing=checkout/'workshop-site.json'
            if not existing.is_file() or read(existing).get('generator')!='stage-asset-workshop':
                raise ValueError('现有 gh-pages 不是本工具管理的站点，停止覆盖。')
            old=read(checkout/'site-files.json') if (checkout/'site-files.json').is_file() else []
            for name in old:
                target=(checkout/name).resolve()
                if checkout.resolve() not in target.parents:
                    raise ValueError('站点文件记录包含目录外路径')
                if target.is_file():
                    target.unlink()
        else:
            checkout.mkdir()
            run([git,'init','--quiet','--initial-branch=gh-pages'],cwd=checkout)
            run([git,'remote','add','origin',url],cwd=checkout)
        files=[]
        for path in directory.rglob('*'):
            if path.is_file():
                rel=path.relative_to(directory)
                # The build contains only runtime code/media, never Canvas auth or raw task records.
                if any(p.startswith('.') and p!='.nojekyll' for p in rel.parts):
                    continue
                target=checkout/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
                files.append(rel.as_posix())
        (checkout/'.nojekyll').touch()
        files.append('.nojekyll')
        write(checkout/'site-files.json',sorted(set(files)))
        run([git,'config','user.name','Stage Asset Workshop'],cwd=checkout)
        run([git,'config','user.email','stage-workshop@users.noreply.github.com'],cwd=checkout)
        run([git,'add','--all'],cwd=checkout)
        if run([git,'status','--porcelain'],cwd=checkout):
            run([git,'commit','--quiet','-m',f"Deploy {marker['projectId']} workshop"],cwd=checkout)
            run([git,'push','origin','gh-pages'],cwd=checkout,timeout=300)
    request={'source':{'branch':'gh-pages','path':'/'},'build_type':'legacy'}
    api=f'repos/{repository}/pages'
    exists=subprocess.run([gh,'api',api],capture_output=True).returncode==0
    request_file=project/'04_输出交付/部署请求.json'
    write(request_file,request)
    response=decode(run([gh,'api',api,'--method','PUT' if exists else 'POST','--input',request_file])) if not exists else None
    # PUT may return 204; avoid requiring a JSON response when updating an existing site.
    if exists:
        run([gh,'api',api,'--method','PUT','--input',request_file])
    state=decode(run([gh,'api',api]))
    write(project/'04_输出交付/部署记录.json',{'repository':repository,'url':state.get('html_url'),'status':state.get('status'),'source':str(directory)})
    print(f"已推送并配置 Pages：{state.get('html_url')}\n构建状态：{state.get('status')}；首次发布需等待 GitHub 完成构建，不能把推送成功当成已上线。")
    return state


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init',help='创建清晰的节目目录和可替换配置')
    init.add_argument('--project',type=Path,required=True)
    init.add_argument('--id',default='my_show');init.add_argument('--name',required=True)
    init.add_argument('--width',type=int,required=True);init.add_argument('--height',type=int,required=True)
    init.add_argument('--duration',type=float,required=True);init.add_argument('--fps',type=int,default=25);init.add_argument('--bpm',type=float,default=120)
    init.add_argument('--mask',type=Path);init.add_argument('--mask-channel',choices=['luminance','alpha'],default='luminance');init.add_argument('--mask-invert',action='store_true')
    init.add_argument('--audio',type=Path);init.add_argument('--style',default='按节目主题设计舞台视觉，构图适合屏幕比例')
    for name in ['plan','generate','build','deploy','all','doctor']:
        p=sub.add_parser(name)
        p.add_argument('--project',type=Path,default=Path('.'))
        if name=='plan':p.add_argument('--capabilities',type=Path,help='离线复用已保存的模型能力；不执行生成')
        if name in ['build','all']:p.add_argument('--out',type=Path)
        if name=='deploy':p.add_argument('--dir',type=Path,required=True);p.add_argument('--repo',required=True)
        if name=='all':p.add_argument('--repo',help='显式提供时，构建后发布到该 GitHub Pages 仓库')
    args=parser.parse_args();project=args.project.resolve()
    if args.command=='init':
        if min(args.width,args.height,args.duration,args.fps,args.bpm)<=0:raise ValueError('初始化数值必须为正数')
        init_project(args)
    elif args.command=='plan':plan(project,args.capabilities)
    elif args.command=='generate':generate(project)
    elif args.command=='build':build(project,args.out)
    elif args.command=='deploy':deploy(project,args.dir,args.repo)
    elif args.command=='all':
        generate(project);output=build(project,args.out)
        if args.repo:deploy(project,output,args.repo)
    elif args.command=='doctor':
        print('Python:',sys.version.split()[0]);print('Node:',shutil.which('node'));print('ffprobe:',shutil.which('ffprobe'));print('GitHub CLI:',shutil.which('gh'))
        print(run(cli(project)+['doctor','--json']))


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    try:main()
    except Exception as error:
        print(f'操作停止：{error}',file=sys.stderr)
        sys.exit(1)
