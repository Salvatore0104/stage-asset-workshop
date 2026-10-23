import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('workshop',ROOT/'scripts/workshop.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
CAP={'capabilities':{'image_generate':{'aspect_ratio_allowed':['1:1','16:9','9:16','21:9','4:1','8:1','1:8'],'output_resolutions':['4K']}}}


class WorkshopTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'节目 with spaces'
        args=argparse.Namespace(project=self.root,id='test_show',name='测试节目',width=640,height=360,
                                duration=8,fps=25,bpm=120,mask=None,mask_channel='luminance',mask_invert=False,
                                audio=None,style='纸片和玻璃')
        w.init_project(args)

    def tearDown(self):
        self.temp.cleanup()

    def test_directories_and_portable_skill(self):
        for name in w.FOLDERS:self.assertTrue((self.root/name/'目录说明.md').is_file())
        self.assertTrue((self.root/'.agents/skills/stage-asset-workshop/SKILL.md').is_file())
        self.assertTrue((self.root/'05_素材工坊/scripts/workshop.py').is_file())
        memory=(self.root/'项目记忆.md').read_text(encoding='utf-8')
        self.assertIn('不要加 --direct',memory)
        self.assertIn('.wowidea/project.json',memory)
        self.assertIn('默认交付本地 HTML',memory)
        self.assertNotIn('--no-canvas',memory)
        agents=(self.root/'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('项目记忆.md',agents)
        self.assertIn('不要加 --direct',agents)
        self.assertIn('项目记忆.md',(self.root/'00_子对话说明.md').read_text(encoding='utf-8'))
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        first=(ROOT/'docs/prompts/首次安装.txt').read_text(encoding='utf-8').strip()
        update=(ROOT/'docs/prompts/更新.txt').read_text(encoding='utf-8')
        deploy=(ROOT/'docs/prompts/部署.txt').read_text(encoding='utf-8')
        self.assertFalse((ROOT/'docs/使用提示词.txt').exists())
        self.assertNotIn(first, readme)
        for name in ['docs/prompts/首次安装.txt', 'docs/prompts/更新.txt', 'docs/prompts/部署.txt']:
            self.assertIn(name, readme)
        self.assertIn('scripts/install.sh', first)
        self.assertIn('scripts/install.ps1', first)
        self.assertIn('project init', first)
        self.assertIn('不要加 --direct', first)
        self.assertIn('不要操作无限画布', first)
        self.assertIn('不要覆盖', update)
        self.assertIn('不要加 --direct', update)
        self.assertIn('gh-pages', deploy)
        self.assertIn('不要', deploy)
        self.assertEqual(w.first_install_prompt().strip(), first)

    def test_ratio_selection_uses_model_capabilities(self):
        self.assertEqual(w.choose_ratio(7800,1000,['1:1','4:1','8:1']),'8:1')
        self.assertEqual(w.choose_ratio(1000,7800,['1:1','1:8','9:16']),'1:8')
        with self.assertRaises(ValueError):w.choose_ratio(10,10,['auto','adaptive'])

    def test_prompt_replacement_and_beats(self):
        show=w.load_project(self.root);show['parts'][0]['duration']={'unit':'beats','value':32}
        w.write(self.root/w.SPEC,show)
        with patch.object(w,'model_info',return_value=CAP):result=w.plan(self.root)
        self.assertIn('16.0秒',result['jobs'][0]['request']['prompt'])
        self.assertEqual(result['jobs'][0]['request']['aspect_ratio'],'16:9')
        with self.assertRaises(ValueError):w.render_prompt('{{未知}}',{})

    def test_model_resolution_and_job_limit_preflight(self):
        show=w.load_project(self.root);show['generation']['maxJobs']=0;w.write(self.root/w.SPEC,show)
        with patch.object(w,'model_info',return_value=CAP),self.assertRaises(ValueError):w.plan(self.root)
        show['generation']['maxJobs']=12;show['generation']['resolution']='12K';w.write(self.root/w.SPEC,show)
        with patch.object(w,'model_info',return_value=CAP),self.assertRaises(ValueError):w.plan(self.root)

    def test_fit_preserves_original_and_exact_output(self):
        source=self.root/'original.png';Image.new('RGBA',(100,100),'red').save(source)
        before=source.read_bytes()
        cover=self.root/'cover.png';contain=self.root/'contain.png'
        w.fit_image(source,cover,320,100,'cover');w.fit_image(source,contain,320,100,'contain')
        with Image.open(cover) as im:self.assertEqual(im.size,(320,100))
        with Image.open(contain) as im:self.assertEqual(im.getpixel((0,0))[3],0)
        self.assertEqual(source.read_bytes(),before)

    def test_build_native_and_simplified_runtime(self):
        output=w.build(self.root,self.root/'web')
        html=(output/'index.html').read_text(encoding='utf-8')
        self.assertIn('lang="zh-CN"',html)
        self.assertIn('测试节目',html)
        self.assertNotIn('__CONFIG__',html)
        self.assertNotIn('素材工坊 · 示範',html)
        self.assertFalse((output/'project.snapshot.json').exists())
        self.assertEqual(w.read(output/'workshop-site.json')['width'],640)

    def test_generation_caches_completed_job(self):
        source=self.root/'result.png';Image.new('RGBA',(640,360),'blue').save(source)
        calls=[]
        def fake_run(command,**kwargs):
            calls.append(command)
            if 'generate' in command:
                return json.dumps({'data':{'paths':[str(source)],'taskId':'mock-id'}})
            return json.dumps({'data':{}})
        with patch.object(w,'model_info',return_value=CAP),patch.object(w,'cli',return_value=['mock']),patch.object(w,'run',side_effect=fake_run):
            w.generate(self.root);w.generate(self.root)
        generated=[command for command in calls if 'generate' in command]
        self.assertEqual(len(generated),1)
        self.assertNotIn('--direct',generated[0])
        self.assertNotIn('--no-canvas',generated[0])
        self.assertIn(str(self.root),generated[0])
        self.assertTrue(any(command[1:3]==['project','init'] for command in calls))
        self.assertTrue(w.load_project(self.root)['parts'][0]['backgrounds']['main'].endswith('.png'))

    def test_existing_wowidea_project_skips_init(self):
        marker=self.root/'.wowidea'/'project.json'
        marker.parent.mkdir()
        marker.write_text('{"keep":true}',encoding='utf-8')
        source=self.root/'result.png';Image.new('RGBA',(640,360),'blue').save(source)
        calls=[]
        def fake_run(command,**kwargs):
            calls.append(command)
            if 'generate' in command:
                return json.dumps({'data':{'paths':[str(source)],'taskId':'mock-id'}})
            return json.dumps({'data':{}})
        with patch.object(w,'model_info',return_value=CAP),patch.object(w,'cli',return_value=['mock']),patch.object(w,'run',side_effect=fake_run):
            w.generate(self.root)
        self.assertFalse(any('init' in command for command in calls))
        self.assertEqual(marker.read_text(encoding='utf-8'),'{"keep":true}')

    def test_init_conflict_does_not_overwrite(self):
        marker=w.wowidea_project_file(self.root)
        def fake_run(command,**kwargs):
            marker.parent.mkdir(parents=True,exist_ok=True)
            marker.write_text('{"name":"kept"}',encoding='utf-8')
            raise RuntimeError('命令失败（退出码 4）')
        with patch.object(w,'cli',return_value=['mock']),patch.object(w,'run',side_effect=fake_run):
            w.ensure_wowidea_project(self.root,'测试节目')
        self.assertEqual(marker.read_text(encoding='utf-8'),'{"name":"kept"}')

    def test_find_wowidea_prefers_path_command(self):
        with patch.object(w.shutil,'which',side_effect=lambda name: '/usr/local/bin/wowidea' if name=='wowidea' else None):
            self.assertEqual(w.find_wowidea(),['/usr/local/bin/wowidea'])

    def test_generation_mismatch_never_auto_rerolls(self):
        source=self.root/'bad.png';Image.new('RGBA',(100,100),'blue').save(source)
        calls=[]
        def fake_run(command,**kwargs):
            if 'generate' in command:
                calls.append(command);return json.dumps({'data':{'paths':[str(source)],'taskId':'mock-id'}})
            return json.dumps({'data':{}})
        with patch.object(w,'model_info',return_value=CAP),patch.object(w,'cli',return_value=['mock']),patch.object(w,'run',side_effect=fake_run):
            with self.assertRaises(ValueError):w.generate(self.root)
            with self.assertRaises(RuntimeError):w.generate(self.root)
        self.assertEqual(len(calls),1)
        self.assertEqual(w.read(next((self.root/'07_AE资产素材/生成记录').glob('*.json')))['status'],'needs_attention')

    def test_duplicate_initialization_refuses_overwrite(self):
        args=argparse.Namespace(project=self.root)
        with self.assertRaises(FileExistsError):w.init_project(args)

    def test_wrong_size_mask_rejected_by_build(self):
        path=self.root/'03_资产与需求/wrong.png';Image.new('L',(20,20),255).save(path)
        show=w.load_project(self.root);show['stageMask']={'type':'image','file':'03_资产与需求/wrong.png','channel':'luminance'};w.write(self.root/w.SPEC,show)
        with self.assertRaises(ValueError):w.build(self.root,self.root/'web')


if __name__=='__main__':unittest.main()
