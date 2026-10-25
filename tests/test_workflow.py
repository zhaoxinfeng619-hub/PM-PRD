import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "assets/scripts"))
from pm_runtime import atomic_write, create_config


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="pm-workflow-test-")
        cls.root = Path(cls.temp.name)
        subprocess.run([sys.executable, str(REPO / "scripts/initialize.py"), "--project", str(cls.root)],
                       check=True, stdout=subprocess.DEVNULL)
        cls.cfg = json.loads((cls.root / ".pm-workflow/runtime.json").read_text())
        cls.module = load_module(cls.root / "scripts/prototype_server.py", "test_pm_server")
        cls.module.Handler.log_message = lambda *args: None
        cls.http = cls.module.ThreadedHTTPServer(("127.0.0.1", cls.cfg["port"]), cls.module.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True); cls.thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.cfg["port"])
        cls.headers = {"Content-Type":"application/json", "X-PM-Token":cls.cfg["token"],
                       "X-PM-Project":cls.cfg["project_id"], "Origin":cls.url}
        cls.builder = load_module(cls.root / "scripts/build_prd.py", "test_pm_builder")

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close(); cls.thread.join(5)
        cls.temp.cleanup()

    def setUp(self):
        self.req = self.root / self._testMethodName
        for kind in ["原型", "需求文档", "流程图", "原型截图"]:
            (self.req / kind).mkdir(parents=True, exist_ok=True)
        self.proto = self.req / "原型/demo-prototype.html"
        self.proto.write_text('''<!doctype html><html><head><style>
        .gallery{display:flex;gap:20px}.device{width:200px;height:150px;background:#90bade}
        .single .device-wrapper{display:none}.single .device-wrapper.active{display:block}
        </style></head><body class="tiled"><div class="gallery">
        <div class="device-wrapper"><div class="device" id="one" data-export-name="页面一">FIRST</div></div>
        <div class="device-wrapper"><div class="device" id="two" data-export-name="页面二">SECOND</div></div>
        </div></body></html>''', encoding="utf-8")
        self.prd = self.req / "需求文档/demo-PRD.html"
        self.prd.write_text("<!doctype html><html><body>original</body></html>", encoding="utf-8")
        self.flow = self.req / "流程图/demo-screenflow.html"
        self.flow.write_text('''<!doctype html><html><body><div class="chart-container" style="width:220px;height:200px">
        <iframe src="../原型/demo-prototype.html#one" width="200" height="180"></iframe></div></body></html>''', encoding="utf-8")

    def call(self, route, data=None, headers=None):
        request = Request(self.url + route, data=None if data is None else json.dumps(data).encode(),
                          headers=self.headers if headers is None else headers)
        try:
            with urlopen(request, timeout=60) as r: return r.status, json.load(r)
        except HTTPError as e:
            with e: return e.code, json.load(e)

    def snapshot(self, src=None, **opts):
        code, data = self.call("/api/snapshot", dict(src=src or "../原型/demo-prototype.html#one",
                                                   base=str(self.prd), **opts))
        self.assertEqual(code, 200, data)
        return data

    def test_strict_save_revision_backup(self):
        original = self.prd.read_bytes()
        proto_before = self.proto.read_bytes()
        code, result = self.call("/api/save-html", {"path":str(self.req / "需求文档/missing.html"), "content":"<html>wrong</html>"})
        self.assertEqual(code, 400)
        self.assertEqual(self.proto.read_bytes(), proto_before)
        rev = self.call("/api/revision", {"path":str(self.prd)})[1]["revision"]
        self.assertEqual(self.call("/api/save-html", {"path":str(self.prd),"content":"<html>new</html>","revision":"wrong"})[0],409)
        code, result = self.call("/api/save-html", {"path":str(self.prd),"content":"<html>new</html>","revision":rev})
        self.assertEqual(code,200,result)
        self.assertEqual((self.root / result["backup"]).read_bytes(),original)
        self.assertEqual(self.call("/api/save-html", {"path":str(self.prd),"content":"<html>stale</html>","revision":rev})[0],409)

    def test_origin_token_project_and_readonly(self):
        self.assertEqual(self.call("/api/revision", {"path":str(self.prd)}, {"Content-Type":"application/json"})[0],403)
        for bad in [{"Origin":"https://example.invalid"}, {"X-PM-Project":"wrong"}, {"X-PM-Token":"wrong"}]:
            self.assertEqual(self.call("/api/revision", {"path":str(self.prd)},dict(self.headers,**bad))[0],403)
        for file in ["/.pm-workflow/runtime.json", "/scripts/prototype_server.py", "/.git/config"]:
            try: urlopen(self.url+file)
            except HTTPError as e:
                self.assertEqual(e.code,404); e.close()
            else: self.fail("私有文件不应可访问")
        headers = {"Sec-Fetch-Site":"cross-site"}
        try: urlopen(Request(self.url+"/scripts/pm-runtime-config.js",headers=headers))
        except HTTPError as e:
            self.assertEqual(e.code,403); e.close()
        else: self.fail("配置不应跨站读取")
        self.module.READ_ONLY = True
        try:
            self.assertEqual(self.call("/api/revision", {"path":str(self.prd)})[0],403)
            raw=urlopen(self.url+"/scripts/pm-runtime-config.js").read().decode()
            self.assertNotIn(self.cfg["token"],raw)
            self.assertIn("readOnly",raw)
        finally: self.module.READ_ONLY=False

    def test_cache_dependencies_scale_force_and_query(self):
        first=self.snapshot()
        second=self.snapshot()
        self.assertFalse(first["cached"]); self.assertTrue(second["cached"])
        large=self.snapshot(scale=3)
        self.assertFalse(large["cached"]); self.assertNotEqual(first["dataUrl"],large["dataUrl"])
        self.assertFalse(self.snapshot(scale=3, force=True)["cached"])
        one=self.snapshot(src="../流程图/demo-screenflow.html#chart-1")
        self.assertTrue(self.snapshot(src="../流程图/demo-screenflow.html#chart-1")["cached"])
        self.proto.write_text(self.proto.read_text().replace("#90bade","#e63d50"))
        changed=self.snapshot(src="../流程图/demo-screenflow.html#chart-1")
        self.assertFalse(changed["cached"]); self.assertNotEqual(one["dataUrl"],changed["dataUrl"])
        q1=self.snapshot(src="../原型/demo-prototype.html?view=a#one")
        q2=self.snapshot(src="../原型/demo-prototype.html?view=b#one")
        self.assertNotEqual(q1["file"],q2["file"])
        self.assertTrue(self.snapshot(src="../原型/demo-prototype.html?view=a#one")["cached"])

    def test_export_failure_retains_previous_and_personal_images(self):
        m=self.module
        personal=self.req / "原型截图/personal.png"; personal.write_bytes(b"personal")
        with m._snapshot_lock: asyncio.run(m._run_screenshots(self.proto, {}))
        self.assertIsNone(m._get_state()["error"])
        manifest=m._read_manifest(self.proto)
        old={it["file"]:(self.req / "原型截图" / it["file"]).read_bytes() for it in manifest["items"]}
        self.proto.write_text(self.proto.read_text().replace('id="two"', 'style="display:none" id="two"'))
        with m._snapshot_lock: asyncio.run(m._run_screenshots(self.proto, {}))
        self.assertIsNotNone(m._get_state()["error"])
        self.assertEqual(m._get_state()["success_count"],0)
        self.assertTrue(m._get_state()["failed_pages"])
        for name, raw in old.items(): self.assertEqual((self.req/"原型截图"/name).read_bytes(),raw)
        self.assertEqual(m._read_manifest(self.proto),manifest)
        self.assertEqual(personal.read_bytes(),b"personal")

    def test_atomic_publication_rollback(self):
        m=self.module
        dest=self.req/"原型截图/a.png";dest.write_bytes(b"old")
        with tempfile.TemporaryDirectory() as folder:
            stage=Path(folder);(stage/"a.png").write_bytes(b"new")
            items=[{"file":"a.png"}, {"file":"../invalid.png"}]
            with self.assertRaises(ValueError): m._publish_batch(self.proto,stage,items)
            self.assertEqual(dest.read_bytes(),b"old")

    def test_initialize_customization_and_project_isolation(self):
        customized=self.root / ".agents/workflows/edu-pm-demand.md"
        previous=customized.read_text();customized.write_text(previous+"\nCUSTOM RULE\n")
        subprocess.run([sys.executable,str(REPO/"scripts/initialize.py"),"--project",str(self.root)],check=True,stdout=subprocess.DEVNULL)
        self.assertIn("CUSTOM RULE",customized.read_text())
        self.assertTrue((self.root/".pm-workflow/updates/.agents/workflows/edu-pm-demand.md").exists())
        self.assertEqual(json.loads((self.root/".pm-workflow/runtime.json").read_text())["project_id"],self.cfg["project_id"])
        with tempfile.TemporaryDirectory() as folder:
            other=create_config(folder)
            self.assertNotEqual(other["project_id"],self.cfg["project_id"])
            self.assertNotEqual(other["token"],self.cfg["token"])
            self.assertNotEqual(other["port"],other["launcher_port"])
        ignore=(self.root/".gitignore").read_text()
        self.assertIn("/scripts/pm-runtime-config.js",ignore)

    def assemble_prd(self):
        pages=[{"value":"one","label":"页面一","url":"../原型/demo-prototype.html#one","w":200,"h":150},
               {"value":"two","label":"页面二","url":"../原型/demo-prototype.html#two","w":200,"h":150}]
        body='''<h1>编辑测试</h1><table class="scheme-table"><thead><tr><th>模块</th><th>功能</th><th>原型</th><th>说明</th></tr></thead><tbody>
        <tr data-preview="one"><td rowspan="2">模块一</td><td>功能一</td><td><div class="prototype-frame" data-pw="200" data-ph="150"><iframe class="prototype-iframe" src="../原型/demo-prototype.html#one"></iframe></div></td><td>说明一</td></tr>
        <tr data-preview="two"><td>功能二</td><td>无原型</td><td>说明二</td></tr></tbody></table>'''
        self.builder.build(body,pages,self.prd,overwrite=True)

    def test_document_reload_rowspan_preview_and_clipboard(self):
        from playwright.sync_api import sync_playwright
        self.assemble_prd()
        with sync_playwright() as p:
            b=p.chromium.launch(headless=True)
            ctx=b.new_context(viewport={"width":1440,"height":900},permissions=["clipboard-read","clipboard-write"])
            page=ctx.new_page(); errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(self.url+"/"+quote(str(self.prd.relative_to(self.root))),wait_until="networkidle")
            page.wait_for_function("!!window.PMDocument")
            self.assertEqual(page.locator(".pm-preview").count(),1)
            page.wait_for_function("()=>{const e=document.querySelector('.prototype-frame');return Math.abs(e.clientHeight-e.clientWidth*.75)<2;}")
            page.locator("tbody tr").first.locator('[data-pm-action="add-row"]').click(force=True)
            self.assertEqual(page.locator("tbody tr").count(),3)
            self.assertEqual(page.locator("tbody td").first.get_attribute("rowspan"),"3")
            page.locator('[data-pm-action="save"]').click()
            page.wait_for_function("document.querySelector('.pm-status').textContent.startsWith('已保存')")
            page.reload(wait_until="networkidle")
            self.assertEqual(page.locator(".pm-preview").count(),1)
            page.locator("tbody tr").last.locator('[data-pm-action="add-row"]').click(force=True)
            self.assertEqual(page.locator("tbody tr").count(),4)
            self.assertEqual(page.locator("tbody tr").last.locator("td").count(),4)
            page.locator('.pm-preview select').select_option("two")
            self.assertTrue(page.locator(".pm-preview iframe").get_attribute("src").endswith("#two"))
            previous=page.locator(".pm-zoom").text_content()
            page.locator('[data-pm-action="plus"]').click()
            self.assertNotEqual(page.locator(".pm-zoom").text_content(),previous)
            result=page.evaluate("window.PMDocument.copyAll(false)")
            self.assertEqual(result,{"ok":1,"failed":0})
            copied=page.evaluate("async()=>{const items=await navigator.clipboard.read();return await (await items[0].getType('text/html')).text();}")
            self.assertIn("data:image/png;base64,",copied)
            self.assertNotIn("<iframe",copied)
            self.assertNotIn("data-pm-ui",copied)
            self.assertNotIn("pm-preview",copied)
            page.locator("tbody tr").first.locator('[data-pm-action="delete-row"]').click(force=True)
            self.assertEqual(page.locator("tbody td").first.get_attribute("rowspan"),"2")
            self.assertEqual(errors,[])
            ctx.close();b.close()

    def test_builder_escape_and_overwrite_protection(self):
        pages=[{"value":"one","label":"</script><script>bad()</script>","url":"../原型/demo-prototype.html#one","w":200,"h":150}]
        with self.assertRaises(FileExistsError): self.builder.build("<h1>Hello</h1>",pages,self.prd)
        self.builder.build("<h1>Hello</h1>",pages,self.prd,overwrite=True)
        self.assertNotIn("</script><script>bad()",self.prd.read_text())

    def test_missing_environment_message_and_launcher_identity(self):
        result=subprocess.run([sys.executable,str(self.root/"scripts/start_service.py"),"--check"],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("--install",result.stderr)
        launcher=load_module(self.root/"scripts/prototype_launcher.py","test_pm_launcher")
        self.assertEqual(launcher.launch(),"already-running")
        old=launcher.CONFIG["project_id"]
        launcher.CONFIG["project_id"]="another-project"
        try:
            with self.assertRaisesRegex(RuntimeError,"其他项目"): launcher.launch()
        finally: launcher.CONFIG["project_id"]=old

    def test_file_open_save_and_copy_failure_fallback(self):
        from playwright.sync_api import sync_playwright
        self.assemble_prd()
        with sync_playwright() as p:
            b=p.chromium.launch(headless=True);page=b.new_page()
            page.goto(self.prd.as_uri(),wait_until="networkidle")
            page.locator('#prdContent h1').fill('文件模式保存')
            page.locator('[data-pm-action="save"]').click()
            page.wait_for_function("document.querySelector('.pm-status').textContent.startsWith('已保存')")
            self.assertIn('文件模式保存',self.prd.read_text())
            page.evaluate("""() => {
              window.snapshotPrototypeViaServer=async()=>{throw Error('测试服务失败');};
              Object.defineProperty(navigator,'clipboard',{value:undefined,configurable:true});
              document.execCommand=()=>{window.copiedFallback=getSelection().toString();return true;};
            }""")
            self.assertEqual(page.evaluate('window.PMDocument.copyAll(true)'),{'ok':0,'failed':1})
            self.assertIn('图片未复制',page.evaluate('window.copiedFallback'))
            self.assertIn('1 张缺失',page.locator('.pm-status').text_content())
            b.close()

    def test_acceptance_states_rates_roundtrip_and_changed_expectation(self):
        from playwright.sync_api import sync_playwright
        directory=self.req/'验收清单';directory.mkdir()
        target=directory/'cases.html'
        cases=[{'id':'C'+str(i),'title':'测试','module':'发布','preconditions':'已登录','data':'草稿','steps':['提交'],'expected':'成功'} for i in range(1,5)]
        spec={'version':'1.0','title':'验收测试','cases':cases}
        script=(REPO/'assets/scripts/pm-acceptance.js').read_text()
        def write_spec():
            target.write_text('<!doctype html><main id="acceptanceContent"></main><script id="acceptanceData" type="application/json">'+json.dumps(spec)+'</script><script>'+script+'</script>')
        write_spec()
        with sync_playwright() as p:
            b=p.chromium.launch(headless=True);page=b.new_page()
            page.goto(self.url+'/'+quote(str(target.relative_to(self.root))))
            initial=page.evaluate('PMAcceptance.stats()')
            self.assertIsNone(initial['passRate']);self.assertEqual(initial['completion'],0)
            self.assertIn('原因',page.evaluate("()=>{try{PMAcceptance.set('C4',{status:'跳过'})}catch(e){return e.message}}"))
            page.evaluate("PMAcceptance.set('C1',{status:'通过',actual:'成功',evidence:'手工走查通过',tester:'PM'})")
            page.evaluate("PMAcceptance.set('C2',{status:'未通过',actual:'失败',evidence:'缺陷记录',tester:'PM'})")
            page.evaluate("PMAcceptance.set('C4',{status:'跳过',reason:'当前版本不适用'})")
            stats=page.evaluate('PMAcceptance.stats()')
            self.assertEqual(stats['counts'],{'待验收':1,'通过':1,'未通过':1,'跳过':1})
            self.assertAlmostEqual(stats['completion'],2/3);self.assertEqual(stats['passRate'],.5)
            page.get_by_label('状态筛选').select_option('跳过')
            self.assertEqual(page.locator('article').count(),1)
            exported=page.evaluate('PMAcceptance.exported()')
            page.reload();self.assertEqual(page.evaluate('PMAcceptance.stats()'),stats)
            page.evaluate('(data)=>PMAcceptance.imported(data)',exported)
            exported['version']='other'
            self.assertIn('版本',page.evaluate('(data)=>{try{PMAcceptance.imported(data)}catch(e){return e.message}}',exported))
            spec['cases'][0]['expected']='新的预期';write_spec();page.reload()
            self.assertEqual(page.evaluate("PMAcceptance.exported().records.C1.status"),'待验收')
            self.assertEqual(page.evaluate("PMAcceptance.exported().records.C1.history.length"),1)
            b.close()


if __name__ == "__main__": unittest.main()
