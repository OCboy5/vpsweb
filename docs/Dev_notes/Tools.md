Tools

1. aicodeprep-gui

2.


1. the vpsweb project can produce pretty good poetry translations from Chinese to English or vice versa. I've attached two examples in the uploaded .json files. I've also uploaded the T-E-T workflow prompts(hybrid mode: non_reasoning, reasoning, non_reasonging) for your reference. My challenge is: how can I improve the workflow prompts to further enhance the quality of the translations to the highest level as possible, even equal to or exceed the best human poetry translators. What are the directions of enhancement I should consider?  Should I use some few-shot examples? Should I give the LLMs more instructions? What are your considerations and suggestions? I want this project to test the upper limit capability of LLMs in poetry translation, which is one of the toughest challenge to human intelligence. So please think extremely hard, research best practices, and come up with your proposal. And please check with me if there's anything unclear to you.


1. Now let's complete the last step for this phase of the project. let's integrate the CLI wechat article generation workflow to the WebUI. In the Poem details page, for each ai translation that has valid "translation notes", will display a "Publish" button. Click on the button, will start the wechat article generation workflow, and use the same output directory structure as the CLI wechat article workflow to generate the wechat article. These outputs are ready for the CLI publish-article workflow to upload to wechat.  
2. Please investigate the current codebase thoroughly when planning. Reuse what's available as much as possible. 
3. Make sure to check the WebUI output .json file structure and the CLI wechat article workflow expected input .json structure to see if there's any discrepancy that will disrupt the parser.
Please check with me if there's anything unclear to you.


# 角色：代码审查专家 (Code Review Master)

## 核心指令
- 你是一位经验极其丰富软件架构师。
- 你的唯一目标是找出代码中潜在的问题，无论多小。
- 直接说出问题所在，并给出修改建议，不要说任何客套话。

## 审查维度
- **性能**: 检查是否存在不必要的循环、重复计算或低效的算法。
- **质量**：检查是否存在Dead Code及无用或冗余的functions和参数。
- **可读性**: 代码是否清晰易懂？命名是否规范？
- **安全**:是否存在SQL注入、跨站脚本等潜在安全漏洞？
- **最佳实践**: 是否遵循了该语言和框架的最新最佳实践？

你的任务是：审查src/vpsweb/下的所有Python代码文件，但禁止任何修改，对每个文件的审查结果与修改建议都写入 docs/claudecode/code_review_report_1102.md。审查和修改建议的详细程度请参考docs/geminicli/code_review_report.md。ultrathink.

综合代码审查报告文件docs/claudecode/code_review_report_1102.md和分支并行重构设计策
略文件docs/claudecode/branch_refactoring_strategy.md，制定详细的重构实施计划docs/claudecode/refactor_implementation_plan.md, 
要求： 
1. 保证所有重构工作在refactor branch进行，不对main branch做任何修改，并且对现有文件的改动存入v2标识的文件（保留原文件），若有新的文件生成也以v2标识
2. 实施的进程安排以高优先级、中优先级、低优先级问题的次序进行，要保证每一个问题的解决都以通过单元测试和集成测试为完成的标志
3. 如有任何不清楚、不确定的问题，随时和我沟通求得意见，不要凭假设自作决定。
4. 此次重构项目以解决代码审查报告文件中揭示的问题为主，不追求增加任何新的功能。同时计划和实施时必须牢记vpsweb是一个个人兴趣项目，不追求达到企业级的软件质量和可靠性、扩展性要求。
5. 生成的详细实施计划必须经过我的审阅和修改之后，才可以开始实施。
6. Ultrathink.

是否需要我帮助完善测试基础设施？A: 是的，需要重建一个新的测试基础设施。现有的通不过CI/CD流程
重构过程中是否可以引入新的依赖（如tenacity用于重试）？A：可以
是否希望保持最小依赖原则？A：是
数据库结构的修改是否需要保持向后兼容？A：是的，如果为此造成困难，请向我提出
是否有现有的生产数据需要考虑？A：是的
个人项目的性能要求是什么？A：性能不是主要考虑因素
是否需要设定具体的性能基准？A：性能不是主要考虑因素，现在系统的性能就可以接受






微信公众号
Appid: wxf92f7edea2893dfc
Appsecret: 8db8f2224fe70e75eb9e12bb83569819
公众号密码：Uv_36fihG38BagT
access_token: 


Commands:

# Phase 1: Repository Core
claude "Read the PSD and implement the database schema (schema.sql) with all tables, indexes, triggers, and views as specified"

claude "Implement the PoemRepository class in src/vpsweb/repository/core.py according to the PSD specifications"

claude "Create the data models in src/vpsweb/repository/models.py with all Pydantic classes from the PSD"

# Phase 2: API
claude "Create the FastAPI application in src/vpsweb/web/app.py with all routers and middleware as specified in the PSD"

claude "Implement all API endpoints in src/vpsweb/web/api/ according to the PSD"

# Phase 3: Web UI
claude "Build the base template and home page according to the PSD UI specifications"

claude "Create the translation workflow page with real-time progress display as specified"




✅ **公有领域作品**（安全）
- 作者逝世超过50年的作品
- 明确声明放弃版权的作品
- 政府公文、时事新闻等

⚠️ **需要授权的作品**（风险）
- 现代诗歌（1925年后发表）
- 当代诗人作品
- 有明确版权声明的作品


【著作权声明】
本译文与译注完全由知韵(VoxPoetica)AI工具生成制作,仅供学习交流使用。原作品版权归原作者所有，如有侵权请联系删除。翻译内容未经授权，不得转载,不得用于商业用途。若需引用，请注明出处。

本翻译由AI工具vpsweb生成，仅供学习交流使用。
原作品版权归原作者所有，如有侵权请联系删除。
翻译内容未经授权，不得用于商业用途。

总结：合规操作清单

事项	建议
原诗版权	✅ 已进入公有领域，可自由使用
AI译文版权	❌ 极可能不受保护，不可主张权利
公众号发布	✅ 可发布，但须标注“AI生成”
署名方式	❌ 不可署名为“本人翻译”
侵权风险	⚠️ 需排除与现有受保护译本的实质性相似
证据留存	✅ 保留生成日志、模型信息等

合规模板（可直接放到文章尾部）

示例 A（原作 PD + 你主张译文权利，采用 CC BY 4.0）
原文信息

作者：Edna St. Vincent Millay
篇名：First Fig（1918 首刊，本作品已进入公有领域）
版本来源：xxx（如选用某权威版本请注明）
译文信息

译者：张三（使用 vpsweb 工作流生成初稿并经人工修订）
许可：CC BY 4.0（署名）
发布渠道：个人网站 / 微信公众号
日期：2025-10-07
备注：保留对原作者署名与作品完整的尊重；工作流与模型信息见附录/链接
示例 B（原作仍受保护，已获许可）
原文信息

作者：某某
篇名：xxx（版权仍在有效期）
授权：经某出版社/权利人书面同意进行翻译与网络传播（许可编号/日期）
译文信息
译者：李四（AI 辅助 + 人工定稿）
许可：依权利人授权约定（如仅限本公众号发布，不得再许可）
备注：如需转载，请联系 rights@yourdomain.com


地区	            一般规则	                                                         特殊说明
中国大陆	     作者去世后 50 年（到次年12月31日截止）	                                多人合著，以最后去世者为准
美国	一般为 作者去世后70年；但出版时间早于1929年的作品（截至2025年）已进入公共领域	      特定规则见下文
欧盟各国	         作者去世后 70年	                                                  与美国类似
日本、韩国	         去世后70年	                                                  日本自2018年起由50年延至70年
加拿大、澳大利亚	  去世后70年	                                                   过去为50年，已延长至70年
