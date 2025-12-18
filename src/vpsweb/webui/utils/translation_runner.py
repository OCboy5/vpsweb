#!/usr/bin/env python3
"""
Repository WebUI Translation Runner

专门为 repo_webui 功能分支创建的独立翻译工作流脚本。
与微信文章生成功能完全分离，便于快速隔离和调试翻译相关的问题。

Usage:
    from vpsweb.webui.utils.translation_runner import TranslationRunner
    runner = TranslationRunner()
    result = await runner.run_translation(...)
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加根路径以确保可以导入其他模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.services.config import get_config_facade, initialize_config_facade
from vpsweb.utils.datetime_utils import format_iso_datetime, now_utc
from vpsweb.utils.logger import get_logger
from vpsweb.utils.storage import StorageHandler

logger = get_logger(__name__)


class TranslationRunner:
    """
    Repository WebUI 专用的翻译工作流运行器

    提供独立、隔离的翻译功能，与微信文章生成完全分离。
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化翻译运行器

        Args:
            config_path: 配置文件路径，默认使用 config/default.yaml
        """
        # Initialize ConfigFacade for configuration access
        initialize_config_facade()
        self.config_facade = get_config_facade()
        self.workflow = TranslationWorkflow()
        self.storage_handler = StorageHandler(
            self.config_facade.main.system.storage.output_dir
        )
        logger.info("Repository WebUI Translation runner initialized")

    async def run_translation(
        self,
        original_poem: str,
        source_lang: str,
        target_lang: str,
        workflow_mode: str = "hybrid",
        output_dir: Optional[str] = None,
        dry_run: bool = False,
        save_output: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行翻译工作流

        Args:
            original_poem: 原始诗歌内容
            source_lang: 源语言
            target_lang: 目标语言
            workflow_mode: 工作流模式 (reasoning/non_reasoning/hybrid)
            output_dir: 输出目录，默认使用配置中的默认目录
            dry_run: 是否为试运行模式
            save_output: 是否保存输出文件
            metadata: 额外的元数据信息

        Returns:
            翻译结果字典
        """
        try:
            logger.info(f"开始翻译工作流")
            logger.info(
                f"源语言: {source_lang}, 目标语言: {target_lang}, 模式: {workflow_mode}"
            )

            if not original_poem or not original_poem.strip():
                raise ValueError("诗歌内容为空")

            logger.info(f"诗歌内容长度: {len(original_poem)} 字符")

            # 执行翻译工作流
            if dry_run:
                logger.info("🔍 DRY RUN MODE - 不会实际调用LLM服务")
                result = await self._dry_run_workflow(
                    original_poem, source_lang, target_lang, workflow_mode
                )
            else:
                result = await self.workflow.execute_translation(
                    original_poem=original_poem,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    mode=workflow_mode,
                )

            # 添加额外的元数据
            if metadata:
                result["repo_webui_metadata"] = metadata

            # 保存输出文件
            if save_output and not dry_run:
                output_path = await self._save_result(result, output_dir)
                result["output_path"] = str(output_path)
                logger.info(f"翻译结果已保存至: {output_path}")

            logger.info("翻译工作流完成")
            return result

        except Exception as e:
            logger.error(f"翻译工作流执行失败: {e}")
            raise

    async def run_translation_from_file(
        self,
        input_file: str,
        source_lang: str,
        target_lang: str,
        workflow_mode: str = "hybrid",
        output_dir: Optional[str] = None,
        dry_run: bool = False,
        save_output: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        从文件执行翻译工作流

        Args:
            input_file: 输入诗歌文件路径
            source_lang: 源语言
            target_lang: 目标语言
            workflow_mode: 工作流模式
            output_dir: 输出目录
            dry_run: 是否为试运行模式
            save_output: 是否保存输出文件
            metadata: 额外的元数据信息

        Returns:
            翻译结果字典
        """
        try:
            # 读取输入文件
            input_path = Path(input_file)
            if not input_path.exists():
                raise FileNotFoundError(f"输入文件不存在: {input_file}")

            with open(input_path, "r", encoding="utf-8") as f:
                original_poem = f.read().strip()

            # 添加文件信息到元数据
            if metadata is None:
                metadata = {}
            metadata["input_file"] = input_file
            metadata["file_size"] = len(original_poem)

            return await self.run_translation(
                original_poem=original_poem,
                source_lang=source_lang,
                target_lang=target_lang,
                workflow_mode=workflow_mode,
                output_dir=output_dir,
                dry_run=dry_run,
                save_output=save_output,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"从文件执行翻译失败: {e}")
            raise

    async def _dry_run_workflow(
        self,
        original_poem: str,
        source_lang: str,
        target_lang: str,
        workflow_mode: str,
    ) -> Dict[str, Any]:
        """
        试运行工作流，返回模拟结果

        Args:
            original_poem: 原始诗歌
            source_lang: 源语言
            target_lang: 目标语言
            workflow_mode: 工作流模式

        Returns:
            模拟的翻译结果
        """
        logger.info("执行试运行工作流")

        # 解析诗歌头部信息
        lines = original_poem.strip().split("\n")
        poem_title = "无题"
        poet_name = "佚名"

        for line in lines:
            line = line.strip()
            if line and "作者：" not in line and not poem_title:
                poem_title = line
            elif "作者：" in line:
                poet_name = line.split("作者：")[1].strip()
                break

        # 模拟翻译结果
        mock_translation = f"""{poem_title}

By {poet_name}

[Repository WebUI Dry Run Mode Mock Translation]
The actual translation would be generated by the LLM service
in {workflow_mode} mode, translating from {source_lang} to {target_lang}.
This is a simulated result for testing purposes."""

        # 模拟工作流结果
        mock_result = {
            "workflow_id": f"repo-webui-dry-run-{int(asyncio.get_event_loop().time())}",
            "input": {
                "original_poem": original_poem,
                "source_lang": source_lang,
                "target_lang": target_lang,
            },
            "mode": workflow_mode,
            "congregated_output": {
                "original_poem": original_poem,
                "initial_translation": mock_translation,
                "editor_suggestions": "[Repo WebUI Mock editor suggestions for dry-run]",
                "revised_translation": mock_translation,
                "initial_translation_notes": "[Repo WebUI Mock translation notes]",
                "revised_translation_notes": "[Repo WebUI Mock revised translation notes]",
            },
            "steps_summary": [
                {
                    "step": "initial_translation",
                    "status": "completed",
                    "llm_calls": 1,
                    "tokens_used": 1500,
                    "duration": 3.0,
                    "cost": 0.05,
                },
                {
                    "step": "editor_review",
                    "status": "completed",
                    "llm_calls": 1,
                    "tokens_used": 800,
                    "duration": 2.0,
                    "cost": 0.03,
                },
                {
                    "step": "translator_revision",
                    "status": "completed",
                    "llm_calls": 1,
                    "tokens_used": 1200,
                    "duration": 2.5,
                    "cost": 0.04,
                },
            ],
            "total_metrics": {
                "total_llm_calls": 3,
                "total_tokens_used": 3500,
                "total_duration": 7.5,
                "total_cost": 0.12,
            },
            "dry_run": True,
            "created_at": format_iso_datetime(now_utc()),
        }

        return mock_result

    async def _save_result(
        self, result: Dict[str, Any], output_dir: Optional[str] = None
    ) -> Path:
        """
        保存翻译结果到文件

        Args:
            result: 翻译结果
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        # 确定输出目录
        if output_dir is None:
            output_dir = self.config_facade.main.system.storage.output_dir

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 使用现有的保存功能
        saved_path = self.storage_handler.save_translation(
            result, str(output_path)
        )
        return Path(saved_path)

    def get_translation_summary(
        self, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取翻译结果摘要

        Args:
            result: 翻译结果

        Returns:
            摘要信息字典
        """
        summary = {
            "workflow_id": result.get("workflow_id"),
            "mode": result.get("mode"),
            "dry_run": result.get("dry_run", False),
            "created_at": result.get("created_at"),
        }

        # 输入信息
        input_data = result.get("input", {})
        summary.update(
            {
                "source_lang": input_data.get("source_lang"),
                "target_lang": input_data.get("target_lang"),
                "poem_length": len(input_data.get("original_poem", "")),
            }
        )

        # 性能指标
        metrics = result.get("total_metrics", {})
        if metrics and not result.get("dry_run"):
            summary.update(
                {
                    "total_llm_calls": metrics.get("total_llm_calls", 0),
                    "total_tokens_used": metrics.get("total_tokens_used", 0),
                    "total_duration": metrics.get("total_duration", 0),
                    "total_cost": metrics.get("total_cost", 0),
                }
            )

        # 输出文件
        if "output_path" in result:
            summary["output_path"] = result["output_path"]

        # 翻译结果预览
        congregated = result.get("congregated_output", {})
        final_translation = congregated.get("revised_translation", "")
        if final_translation:
            preview = final_translation[:200] + (
                "..." if len(final_translation) > 200 else ""
            )
            summary["translation_preview"] = preview

        return summary

    async def batch_translate(
        self,
        translation_tasks: List[Dict[str, Any]],
        output_dir: Optional[str] = None,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        批量翻译任务

        Args:
            translation_tasks: 翻译任务列表，每个任务包含必要的参数
            output_dir: 输出目录
            dry_run: 是否为试运行模式

        Returns:
            翻译结果列表
        """
        logger.info(f"开始批量翻译，共 {len(translation_tasks)} 个任务")

        results = []
        for i, task in enumerate(translation_tasks):
            try:
                logger.info(
                    f"执行第 {i+1}/{len(translation_tasks)} 个翻译任务"
                )

                result = await self.run_translation(
                    original_poem=task["original_poem"],
                    source_lang=task["source_lang"],
                    target_lang=task["target_lang"],
                    workflow_mode=task.get("workflow_mode", "hybrid"),
                    output_dir=output_dir,
                    dry_run=dry_run,
                    save_output=True,
                    metadata=task.get("metadata"),
                )

                results.append(
                    {
                        "task_index": i,
                        "status": "success",
                        "result": result,
                    }
                )

            except Exception as e:
                logger.error(f"第 {i+1} 个翻译任务失败: {e}")
                results.append(
                    {
                        "task_index": i,
                        "status": "error",
                        "error": str(e),
                    }
                )

        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(
            f"批量翻译完成: {success_count}/{len(translation_tasks)} 成功"
        )

        return results


# 便捷函数，供直接使用
async def quick_translate(
    original_poem: str,
    source_lang: str,
    target_lang: str,
    workflow_mode: str = "hybrid",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    快速翻译的便捷函数

    Args:
        original_poem: 原始诗歌内容
        source_lang: 源语言
        target_lang: 目标语言
        workflow_mode: 工作流模式
        dry_run: 是否为试运行模式

    Returns:
        翻译结果字典
    """
    runner = TranslationRunner()
    return await runner.run_translation(
        original_poem=original_poem,
        source_lang=source_lang,
        target_lang=target_lang,
        workflow_mode=workflow_mode,
        dry_run=dry_run,
    )


async def quick_translate_file(
    input_file: str,
    source_lang: str,
    target_lang: str,
    workflow_mode: str = "hybrid",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    快速文件翻译的便捷函数

    Args:
        input_file: 输入文件路径
        source_lang: 源语言
        target_lang: 目标语言
        workflow_mode: 工作流模式
        dry_run: 是否为试运行模式

    Returns:
        翻译结果字典
    """
    runner = TranslationRunner()
    return await runner.run_translation_from_file(
        input_file=input_file,
        source_lang=source_lang,
        target_lang=target_lang,
        workflow_mode=workflow_mode,
        dry_run=dry_run,
    )
