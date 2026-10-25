# 公共文档与服务契约

## 生成 PRD

初始化后使用 templates/prd-shell.html，填入正文和 prdPages JSON。页面目录每项包含 value、label、url、w、h，例如：
~~~json
{"value":"detail","label":"P01 · 详情","url":"../原型/需求-prototype.html#detail","w":390,"h":844}
~~~
正文放在 #prdContent，需要滚动联动的功能行加 data-preview="detail"。
原型表格内使用 .prototype-frame，原始宽高写入 data-pw/data-ph。

生成命令：
~~~sh
python3 scripts/build_prd.py --content body.html --pages pages.json --output 需求名/需求文档/需求名-PRD.html
~~~
构建器内嵌公共组件。重新构建已有文件需要 --overwrite，并自动备份。正文输入是生成材料，所有页面 URL 必须对应实际文件。
每个 HTML 可离线阅读，完整原型预览依赖同需求的原型文件，交付保留相对目录。
公共逻辑只有一处源码，修复后重新构建需要更新的产物，不将业务文案写进公共组件。

## 编辑与保存

事件委托与运行时控件重建保证保存后重新打开可用。序列化排除 data-pm-ui 节点，保留正文修改、合并单元格和尺寸。
.no-edit 内不加编辑功能；pre/code、图片和原型 iframe 不作为普通可编辑段落。
保存携带页面加载时取得的文件版本。文件变化返回冲突，先核对合并，不能自动读取新版本号后强行覆盖。
备份在 .handoff/html-backups/。下载副本不覆盖原文件，两者都不能声称已自动同步原型和流程图。

## 复制全文

只复制正文，移除工具栏、手柄、侧栏、交互按钮和编辑高亮。
每次复制建立本次请求的去重缓存，下一次重新向服务校验依赖。
原型 iframe 通过 snapshotPrototypeViaServer 转图；本地图通过 inlineAssetViaServer 内联。
“重新生成图片并复制”传 force:true。普通复制允许服务使用有效缓存。
大图按需缩至 2000px、JPEG 0.9；已有尺寸足够的图片保留原图。
失败保留明确缺图占位并报数。Clipboard API 不可用时以选区复制兜底。
目标文档首次粘贴必须确认图文保留；不能保证所有外部平台都保存 base64 图片。

## 服务与配置

先加载 ../../scripts/pm-runtime-config.js，再加载 ../../scripts/prototype-export-client.js。
配置包含本机凭据，不发布、不打进公开分享包；服务器只向本机同源页面提供这份配置。
客户端核验项目身份，请求携带项目编号和令牌。缺配置、端口被其他项目占用时明确报错。
缓存追踪 HTML、相关本地资源与共享脚本、页面状态、视口、scale 和渲染版本；远程资源无法核验时重新生成。
导出先在独立暂存文件中生成；整轮成功才发布，失败保留旧图。清单只记录已成功发布项，个人截图不清理。
只读分享允许浏览产物和下载副本，禁止保存、启动和截图生成；带图复制回本地模式使用。

## 升级兼容

旧 HTML 接入公共组件前先备份，移除重复的旧编辑、复制和导出实现。新旧组件不能同时运行。
首次升级没有安装版本清单的项目，现有文件作为定制保留，新版本位于 .pm-workflow/updates/。
只有完成候选文件合并并自测后，才能宣布项目升级完成。
项目偏好写在 .agents/workflows/local-overrides.md，模板升级不覆盖此文件。
