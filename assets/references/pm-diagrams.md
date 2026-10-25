# 流程图与交互流程图

## 业务流程图

输出 [需求名]/流程图/[需求名]-flow.html，每张图包裹在 .chart-container 中。
使用适用 Mermaid 图形，分支来自确认后的业务规则。优先本地 Mermaid 资源，联网依赖注明离线限制。
语法错误先修复标签和结构，不能删除业务分支隐藏错误。
PRD 通过 ../流程图/[需求名]-flow.html 嵌入，宽高按实际图尺寸设置。

## 交互流程图

输出 [需求名]/流程图/[需求名]-screenflow.html。存在多页跳转或关键状态转换时按需生成。
画布为 .chart-container.screenflow-canvas，每个状态有独立 .flow-node，其中 iframe 指向 ../原型/[需求名]-prototype.html#page-id。
iframe 用真实宽高后等比缩放，节点标题与 PRD 页面目录一致；流程图节点 iframe 禁用 pointer events。
用 EDGES 数组声明起点、终点、触发条件和锚点方向；布局后读取节点位置生成箭头。
- 仅用水平和垂直线段。
- 同侧回环用外侧轨道，多条边错开，不能压过其他节点。
- 标签留底色和边界空白。
- resize、iframe 加载与节点变化后重算位置。
- 提供缩放、适配、拖动和导出；嵌入时默认适配，独立打开及导出时用真实尺寸。
- 状态机图例与 PRD 状态及原型标签保持一致。

## 时序图

复杂跨端交互、流式返回或状态编排时按需生成。
位于数据埋点后、上线计划前，采用可复制 Mermaid 源码文本块，不渲染为图片。
参与方、请求顺序、等待条件、异常和结束动作按实际系统设置，不推测接口名当作研发已确认设计。
图数量按需求选择，可含 sequenceDiagram 和 stateDiagram-v2。交付前验证语法。

## 导出与验证

使用当前项目的 pm-runtime-config.js 和 prototype-export-client.js，路径均为 ../../scripts/。
导出按钮采用 .export-btn，不绑定其他截图函数，不加载 html2canvas 或 html-to-image。
检查箭头对应操作、分支条件、状态覆盖、缩放清晰度和完整截图。失败明确报告并保留旧图。
