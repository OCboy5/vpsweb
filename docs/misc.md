
Refactor recommendations (where to merge execution paths)

Centralize the translation workflow into a single Pipeline / Stage model
Problem: three different LLM roles (translator / editor / reviser) are likely implemented as separate code paths but share most behavior (prompt assembly, LLM call, parse outputs).
Fix: implement a single TranslationPipeline class that accepts an ordered list of Stage objects (each Stage defines role name, prompt template, post-processing rules). This reduces duplicated orchestration code and makes it easy to add/remove stages or reuse a stage implementation.
Benefits: fewer duplicated methods, single place to handle retries/errors/logging/metrics and consistent translator notes format.
Example (suggested new file)


src/vpsweb/services/translation_pipeline.py

from typing import Callable, Dict, List, Optional

class Stage:
    def __init__(self, name: str, prompt_builder: Callable[[Dict], str], post_processor: Optional[Callable[[str], Dict]] = None):
        self.name = name
        self.build_prompt = prompt_builder
        self.post_process = post_processor or (lambda x: {"text": x})

class TranslationPipeline:
    def __init__(self, llm_call: Callable[[str], str]):
        """
        llm_call: function that takes a prompt string and returns a raw LLM response string.
        """
        self.llm_call = llm_call

    def run(self, stages: List[Stage], context: Dict) -> Dict[str, Dict]:
        """
        Runs the pipeline through each stage in order. Returns a mapping
        of stage_name -> post-processed result.
        """
        results: Dict[str, Dict] = {}
        ctx = dict(context)  # work on a copy
        for stage in stages:
            prompt = stage.build_prompt(ctx)
            raw = self.llm_call(prompt)
            processed = stage.post_process(raw)
            results[stage.name] = processed
            # allow subsequent stages to see prior outputs
            ctx.setdefault("stages", {})[stage.name] = processed
        return results



This pattern collapses duplicated orchestration into one class and makes per-stage differences small and declarative (templates + processor).
Extract shared business logic from CLI & web handlers
Problem: The CLI (vpsweb entrypoint) and FastAPI endpoints probably both implement translation, article generation, and publication flows.
Fix: Move all core operations (translate_poem, generate_wechat_article, publish_article) into src/vpsweb/services/* and make the CLI/web layers thin adapters that call those services. That prevents drifting implementations and ensures changes are made only once.
Checklist:
Add a services/wechat.py to hold WeChat generation/publish logic.
Add services/storage.py for all filesystem/JSON I/O used by CLI and web.
Ensure DB access is encapsulated in services/repository.py — do not create ad-hoc session management in multiple places.
Consolidate DB session creation and models
Problem: If multiple modules create their own SQLAlchemy engines/sessionmakers, that can hide bugs and cause duplication.
Fix: Single module (e.g., src/vpsweb/db.py) exports get_session() / engine and model imports. Replace ad-hoc session creation with dependency injection (for FastAPI) and a single factory for CLI.
Merge duplicated shell scripts into a single orchestration
Problem: multiple shell scripts (backup.sh, restore.sh, save-version.sh, push-version.sh, dev-check.sh) can hold overlapping logic and diverge.
Fix: Centralize common operations into scripts/ with a single script that supports subcommands (using bash case or a small Python script using click). Keep only small wrapper scripts for ops that must be separate.
Templates & static files
Problem: duplicate HTML fragments and unused templates increase repo size and maintenance.
Fix:
Remove templates no longer referenced by FastAPI routes.
Extract common page fragments into includes/base templates and reuse them.
Consolidate logging/error handling
Problem: multiple handlers probably use ad-hoc logging/debug prints.
Fix: central logging config (logging.getLogger("vpsweb")) that modules use; consistent exception handling at service boundaries.
Practical small checklist for a first PR

Run vulture and collect a list of unused items; create a PR that removes obviously dead functions and files (start with non-production-facing helpers).
Add a TranslationPipeline service as above; modify one area (CLI translate command and the equivalent web route) to use the pipeline; run tests.
Consolidate the changelog: remove duplicate file (decide which one to keep).
Create a services/wechat.py that both CLI and web use for article generation/publishing.
Add CI job to run ruff, mypy, pytest with coverage so future PRs don’t reintroduce dead code.
How to prioritize removal of dead code

High priority (remove quickly): functions and files that are unreferenced by code and untested; scripts that no longer match documented usage.
Medium priority: duplicated implementations of the same functionality in different layers (merge into shared service).
 Examples of likely merges (based on project structure and typical duplication)

translate command (CLI) vs /translate API endpoint -> merge orchestration into services/translate.py
generate-article vs web article generator -> move to services/wechat.py
multiple LLM wrapper functions (one per LLM role) -> a single LLM client with role/prompt templates passed in
duplicate SQLAlchemy session creation -> single db.py with get_session
A few safety notes

Don’t remove code just because static tools flag it — verify with coverage and a quick runtime test that nothing references it dynamically (e.g., reflection, importlib, runtime discovery).
When merging methods, create small adapters to avoid breaking external integrations (CLI args, stored JSON layouts, or persisted schema). Add deprecation warnings when changing public behavior.


以下是我对于过去2天“2025年杉树青年成长营”一些观察和反馈：
1. 参加骨干营的同学们的参与度、积极度和课堂氛围是过去几届中最好的。我听到几乎所有的同学都反映骨干营的课程非常好，收获很大。所以要特别对参与筹备和授课的小伙伴们表示祝贺，你们所有的付出都是值得的。
2. 骨干营的场地非常优秀，我也从场地方的吕老师那儿得到了对于上秘非常高的评价。作为一个孵化器，那儿经常举办各类活动，但是她觉得我们这次活动的组织和管理水平，参与人员的礼貌和素质，比其他所谓成年人举办的活动都要出色，所以她很欢迎我们将来再去用她的场地。祖珩的一次主动询问，不仅让我们有了一个理想的培训场地，又让杉树多了一个未来的合作伙伴 。所以“越主动，越幸运”，真的不只是一句口号。 
3. 各位导师和大杉树到现场探营，并参与课程讨论，给了同学们很大的惊喜和鼓励。谢谢各位付出时间和精力！ 
4. 课程的设置和密度在两天的时间内恰到好处。如果要有建议：
   1. 课程内容中与秘书处工作完全结合的案例比例较低。 建议在复盘前，各位授课部长根据得到的反馈再改一稿课件，这样明年的授课部长的起点会更高。
   2. 如果骨干营是两天的计划， 那么第一天晚上应该设计一个小组 project，第二天一早各组上来 present。这样对小组协作的挑战更大，营队的感觉更强。
希望同学们好好复盘，通过一届届秘书处的持续改进，把“杉树青年成长营”打造成上秘的一个品牌。事实上 ，我们已经离这个目标越来越近了。 

各位同学 ：
明年将是我们复旦8624相聚40周年的纪念。40年前一张复旦大学计算机科学系的录取通知书，把我们从四面八方召唤到了复旦校园，在最好的青春年华 ，让大家有缘在一起共同学习、生活了四年的时间。 我们6年前在筹备纪念毕业30周年大聚会的时候，就产生了给母校赠送一个艺术雕塑的想法，在大群里同学们也做过一些讨论，并通过姚志华同学的引荐，与雕塑艺术家马德老师做了初步的交流。只是后来因为疫情的来临聚会筹备工作中断了，雕塑设计的事也没有进行下去。自从我们开始筹备明年10月的大聚会，又把这个想法重新启动起来。 我们通过姚志华同学再次联络到马德老师和他的团队，和他们做了多次的沟通，并陪同到江湾校区的计算机学院新大楼实地踏勘。我们希望这件作为8624捐赠给母校（学院）的礼物，能表达我们作为校友对于母校的感情，以及对于母校未来的良好祝愿。我们对艺术家们提出的要求是作品必须有美感、有品味、非具象、永久性，除此之外给了艺术家们完全的自由去创作。马老师和他的团队化了很大的精力去理解计算机和信息社会的发展脉络，几易其稿，最终交付的设计初稿不管是造型和理念都超过了我们初始的期望。所以今天我们把这个初始设计方案提交给大家审阅，请大家提出意见和建议。如果没有太大的问题，我们会在集中整理后，把方案与学院领导进行沟通，以取得他们的认可。

各位同学：

明年将迎来我们复旦8624班相聚40周年的重要时刻。40年前，一张复旦大学计算机科学系的录取通知书，让我们从四面八方汇聚到复旦校园，在最美的青春年华里，有缘共同学习、生活了四年。

六年前筹备毕业30周年聚会时，我们便萌生了向母校赠送艺术雕塑的想法，大群中也曾就此展开讨论，并通过姚志华同学引荐，与雕塑家马得老师进行了初步交流。后因疫情导致聚会筹备中断，雕塑设计事宜也随之搁置。

自今年早些时候重启明年10月大聚会的筹备工作以来，这一想法再度被提上日程。我们通过姚志华同学再次联系到马得老师及其团队，进行了多次沟通，并陪同前往江湾校区计算机学院新大楼实地踏勘。我们希望这件由8624班捐赠给母校（学院）的礼物，既能承载校友对母校的深情，也能寄托对母校未来的美好祝愿。

我们对艺术家提出的要求是：作品需兼具美感与格调，采用非具象形式，具备永久性；此外给予艺术家充分创作自由。马老师团队投入大量精力梳理计算机与信息社会发展脉络，数易其稿，最终交付的设计初稿，其造型与理念均超出我们最初的预期。

现将该初稿提交大家审阅，恳请提出宝贵意见建议。若无太大问题，我们将汇总整理后与学院领导沟通，争取早日获得认可, 以开展下一步的设计深化与制作工作。

相聚40周年聚会筹备小组
12/10/2025

