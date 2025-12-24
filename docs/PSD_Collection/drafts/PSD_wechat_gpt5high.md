vpsweb 微信公众号文章生成与发布功能设计方案（PSD）
版本：0.2（草案）


一、目标与范围

新增两大功能：
将 vpsweb 翻译工作流的输出（outputs/*.json）转换为高质量的公众号文章（含封面可选生成）。
将生成的文章自动提交至公众号“草稿箱”，供人工复核后发布。
兼容现有工作流（hybrid/reasoning/non-reasoning），不改变核心翻译流程；允许对 JSON 模式进行前瞻性扩展。
二、微信公众平台（MP）要点与最佳实践（研究结论）

核心接口（无需用户OAuth，仅需服务号/订阅号后台AppID+Secret）：
获取 access_token: GET https://api.weixin.qq.com/cgi-bin/token
上传内容内图片（返回可外链的微信托管URL）: POST https://api.weixin.qq.com/cgi-bin/media/uploadimg
上传永久素材（封面thumb）: POST https://api.weixin.qq.com/cgi-bin/material/add_material?type=image
新建草稿: POST https://api.weixin.qq.com/cgi-bin/draft/add
更新草稿: POST https://api.weixin.qq.com/cgi-bin/draft/update
查询草稿: POST https://api.weixin.qq.com/cgi-bin/draft/get / draft/batchget
提交发布（可选）: POST https://api.weixin.qq.com/cgi-bin/freepublish/submit
内容要求与限制（常见约束，需在代码层校验）：
标题建议 ≤ 64 字节（中文64字符一般安全，但以字节计更保守）
摘要（digest）建议 ≤ 120 中文字符
正文需为微信可接受 HTML（支持 p/br/strong/em/ul/ol/li/img/section 等有限标签；外链 CSS/JS 会被剥离）
文章可开评论 need_open_comment=1；是否仅粉丝可评由 only_fans_can_comment 控制

三、CLI 命令规格

vpsweb generate-article
功能：读取一次翻译工作流 JSON，生成公众号文章（HTML + 元数据），可选自动生成封面图。
标题规范：全局统一为“【知韵译诗】{诗歌名}（{诗人名}）”
内容包含：原文、终稿译文、精炼版“译注/翻译说明”、版权声明、工作流简要溯源（可折叠）。
输入参数（示例）：
-i, --input: 必填，outputs/*.json
-o, --outdir: 文章产出目录（默认 outputs/articles/wechat/{workflow_id}/）
--lang: 文章主显示语言偏好（auto | zh | en），默认 auto 按 source_lang/target_lang 决定双语顺序
--cover auto|<path>: 封面生成策略（auto=调用图像模型；或指定本地图片路径；默认无）
--image-model: 封面模型（wanx|stable|openai等，默认 wanx 若配置有阿里DashScope）
--notes auto|initial|revised|editor: 选用哪部分作为“翻译说明”素材，默认 auto（融合+总结）
--max-notes-bullets: 默认 5（3–6 之间）
--dry-run: 仅生成本地文件，不调用任何外部API
输出产物：
article.html（用于提交给“草稿箱”的 HTML）
article.md（备份/人工校对稿）
article_meta.json（title/digest/author/cover/图片映射等）
cover.jpg（若自动生成或复制）
主要流程：
解析 JSON（参考示例结构）
标题、作者、原文（input.original_poem）
终稿译文（revised_translation.revised_translation）
译注来源（优先 revised_translation.revised_translation_notes，其次 editor_review.editor_suggestions，最后 initial_translation.initial_translation_notes）
结构化抽取：
标题、作者名（中英并存）、篇名、卷次/序号（如“其一”）
识别原文与译文分段、行（按换行渲染）
译注生成（见“译注生成时机”一节）：
将长说明压缩为 3–5 条要点（术语选择、关键意象、重要修辞/文化项、节奏/押韵策略、明显取舍）
生成 100–160 字摘要作为 digest
HTML 模板渲染（见模板草案）
输出文件写入 outdir
文章模板（HTML 片段，WeChat 友好标签；极简行内样式）
标题区
作者/来源区（小号字）
原文区（等宽诗行渲染：使用 <p> + <br>）
译文区
翻译说明（项目符号列表）
版权声明区（动态内容，见“版权声明”）
溯源区（小字，展示工作流模式、模型、时间、token与成本；可用“展开详情”折叠）
示例模板占位（Jinja2风格，实际由Python字符串.format或Jinja2渲染）
省略于此，实施时提供 article_template.html，满足微信HTML白名单
vpsweb publish-article
功能：读取 generate-article 生成的 article.html 与 meta，经过“图片上传+内容URL替换+封面上传”，调用“新建草稿”接口写入草稿箱。
输入参数：
-d, --dir: 必填，文章目录（含 article.html、article_meta.json、可选 cover.jpg）
--appid / --secret: 可从 .env 或 CLI 注入
--open-comment: 默认开启（1）
--fans-only-comment: 默认关闭（0）
--update <draft_media_id>: 若提供，调用 draft/update；否则 draft/add
输出：
成功后返回 draft_media_id，并写回 article_meta.json
步骤：
获取 access_token（缓存至本地，管理过期）
组装“新建草稿”payload：
仅一篇文章（articles: [ ... ]）
字段：title/author/digest/content/thumb_media_id/show_cover_pic/need_open_comment/only_fans_can_comment
调用 draft/add 或 draft/update

错误处理：
明确处理微信错误码（如 40001/42001 token失效重取；45009 调用频次受限）

五、“翻译说明（translation notes）”的生成时机评估

方案：在 generate-article 阶段“二次摘要”（推荐主路径）
优点：可根据平台风格与长度约束做有损压缩；可融合 initial/editor/revised 三方信息；易于迭代模板
建议：新增“article_notes_brief”字段写回 article_meta.json；如翻译 JSON 已内含“brief_notes”，则优先使用，缺失时再自动摘要

六、JSON 模式扩展建议（向后兼容）
在 outputs/*.json 的顶层与子对象中新增以下可选元数据（都为可空）：

work_meta:
title_localized、author_localized、author_english、author_chinese、dynasty/era、first_publication_year
copyright_status_original: "public_domain" | "in_copyright" | "unknown"
source_url_original
translation_meta:
translator_type: human|ai|hybrid（已有可重用）
translator_byline（人名/团队名称）
license_translation: CC-BY-4.0 | CC0 | all_rights_reserved
brief_notes（公众号可直接用的精简译注，如 3–6 条）
keywords/tags（数组）
article_meta (生成后可写回)：
article_title、article_digest
cover_prompt、cover_style、cover_path、thumb_media_id（上传后）
draft_media_id（草稿ID）、draft_url（如有）、generated_at、published_at（若未来支持直发）
workflow_meta（增强）：
model_pricing_snapshot、providers、total_cost_currency（CNY）等
legal_meta：
rights_contact_email（侵权/下架联系邮箱）、disclaimer_template_id
七、文章设计与模板要点（WeChat 兼容）

样式策略：尽量少用内联样式；使用 <section> + <p> + <br> 组合；不依赖外部CSS
诗行渲染：
原文：每行 <p>；若需严格换行，行内用 <br>，避免 <pre>
译文：同上；必要时加小号注释
结构建议（顺序可配置）：
标题（H2风格）+ 作者/朝代/语言小字
导言（1–2 句）（可选）
原文（中文，宋体/系统默认）
译文（英/中，行距略大）
翻译说明（3–5 条要点，序号列表）
版权与来源（版权声明、许可、联系邮箱）
溯源（工作流模式、模型、时间、token、成本；可折叠）
版权声明（程序动态拼装，示例）：
原作为公有领域时：
原文：作者/篇名/年代，公有领域说明（PD）
译文：译者/团队 + 许可（如 CC BY 4.0），转载须署名并保留链接
原作为受版权保护时（不建议发布全文，除非已获授权）：
显示授权语（授权方/范围/日期）；禁止再许可；引用需最小必要范围
通用尾注：
本文译文采用 vpsweb TET 工作流（模型/时间见文末），如涉及版权问题请联系 {rights_contact_email}，我们将及时处理
八、实现细节

模块与文件
app/services/wechat/article_builder.py
从 JSON 解析 -> 结构化 -> 译注摘要 -> HTML 渲染 -> 本地文件写入
app/services/wechat/publisher.py
token 管理、图片上传、封面上传、草稿新增/更新
app/templates/wechat/article_template.html
app/services/wechat/image_gen.py（可选）
基于 poem/notes 生成封面，裁剪压缩
CLI
vpsweb/cli/generate_article.py
vpsweb/cli/publish_article.py
译注摘要算法（generate-article 内）
输入：initial_notes、editor_suggestions、revised_notes
步骤：
解析关键术语（如：守拙/依依/韵/比喻意象/押韵节奏）
抽取 5–10 个候选点，去重合并（基于关键词 overlap）
语言重写为公众号读者友好的 3–5 条，每条 18–40 字
生成 100–160 字 digest（不剧透全文，突出看点）
可选：调用小温度 LLM 精炼（或纯规则/摘要）
WeChat API 调用（关键伪代码）
获取 token
GET /cgi-bin/token?grant_type=client_credential&appid=APPID&secret=SECRET
上传正文图片
POST /cgi-bin/media/uploadimg (form-data: media)
返回 {url}；替换 article.html 中对应 <img src>
上传封面
POST /cgi-bin/material/add_material?type=image (form-data: media)
返回 {media_id} -> thumb_media_id
新建草稿
POST /cgi-bin/draft/add
Payload:
{
"articles": [{
"title": "...",
"author": "知韵译诗",
"digest": "...",
"content": "<section>...</section>",
"content_source_url": "",
"thumb_media_id": "xxx",
"show_cover_pic": 1,
"need_open_comment": 1,
"only_fans_can_comment": 0
}]
}
九、质量保障与校验

生成前校验：
标题/摘要长度；HTML 大小；图片尺寸/体积
JSON 必要字段（原文、终稿译文、作者/篇名）
生成后预览：
本地开启简易预览（Jinja2 渲染 + 浏览器预览）
发布前模拟：
dry-run 模式打印将调用的 API 与要上传的文件列表
错误重试：
token 过期自动刷新；图片上传失败重传最多 3 次；接口失败记录 error_code 与建议修复
十、面向示例 JSON 的字段映射（参照你提供的样例）

标题：从 congregated_output.original_poem 首行（或 input.original_poem 解析标题）与作者（“作者：”后）提取
原文：input.original_poem（去除“作者：”、集序号等标头后按段落分行）
译文（终稿）：revised_translation.revised_translation
译注素材优先级：revised_translation.revised_translation_notes > editor_review.editor_suggestions > initial_translation.initial_translation_notes
工作流信息（溯源）：workflow_id、workflow_mode、各步 model_info、tokens_used、duration、total_cost
版权默认：
若作者为古典诗人（如陶渊明），自动判定 PD，译文默认 CC BY 4.0（可通过 CLI 覆盖）
十一、开发计划与里程碑

M1（3–5 天）
article_builder、基础模板、译注摘要（规则版）
generate-article CLI；本地预览
M2（3–5 天）
publisher：token 缓存、图片上传、草稿新增
publish-article CLI；错误码处理
M3（2–3 天）
封面图自动生成（wanx优先）+ 裁剪压缩
文章模板微调（诗行版式、暗色/留白风）
M4（2–3 天）
JSON 模式扩展（可选）、单元测试、回归测试
文档与使用示例
十二、验收标准（v1）

对样例 JSON 一键生成 article.html 与 article.md，结构正确、版式优雅
可将文章成功提交到公众号草稿箱，返回 draft_media_id 并记录到 article_meta.json
正文图片均转换为微信托管 URL；封面成功生成并设置为 thumb_media_id
译注 3–5 条简洁明了；digest 在 100–160 字内
版权声明区根据 PD/受保护两种情形自动切换
失败场景（token 失效/图片过大/HTML 超限）有明确提示与回退
十三、后续增强（可选）

文章的“多稿合并”（一次草稿包含多篇图文）
自动生成“封面题图字”（标题书法/英文字体渲染）
直发发布（freepublish/submit）+ 发布后链接回写
人类译者投稿→文章流水线（与前文“人类译者工作室”模块衔接）
附：版权声明模板（自动拼装示例）

PD 场景
原文：{作者}《{篇名}》，属公有领域（Public Domain）
译文：由“知韵译诗（vpsweb 工作流）”生成并经人工审校，除另有说明外，采用 CC BY 4.0（署名）许可。转载请注明出处与链接。
侵权/合作事宜请联系：{rights_contact_email}
受保护场景（需授权）
原文：{作者}《{篇名}》，版权受保护；已获{权利人/出版社}授权翻译与网络传播（许可号/日期）
译文许可依授权约定；非经许可请勿转载
联系：{rights_contact_email}
结论与建议

“翻译说明”建议在 generate-article 阶段做二次摘要（面向公众号读者），同时保留工作流的详细笔记；若后续频繁使用公众号摘要，可把 brief_notes 回写到 JSON，供复用与检索。
为支持后续自动化与合规，建议在翻译 JSON 中补充版权/作者时代/许可等元数据（见“JSON 扩展”），并为封面自动生成引入 cover_prompt 与 style 偏好。
以上方案最大程度复用现有 vpsweb 工作流资产，新增模块清晰、耦合度低、可渐进上线。