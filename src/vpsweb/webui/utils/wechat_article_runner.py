#!/usr/bin/env python3
"""
Repository WebUI WeChat Article Runner

专门为 repo_webui 功能分支创建的独立微信文章生成脚本。
与翻译工作流完全分离，便于快速隔离和调试微信文章生成相关的问题。

Usage:
    from vpsweb.webui.utils.wechat_article_runner import WeChatArticleRunner
    runner = WeChatArticleRunner()
    result = runner.generate_from_translation(...)
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

# 添加根路径以确保可以导入其他模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from vpsweb.utils.article_generator import ArticleGenerator, ArticleGeneratorError
from vpsweb.utils.config_loader import load_config
from vpsweb.models.wechat import (
    ArticleGenerationResult,
    ArticleGenerationConfig,
    WeChatArticleStatus,
)
from vpsweb.utils.logger import get_logger

logger = get_logger(__name__)


class WeChatArticleRunner:
    """
    Repository WebUI 专用的微信文章生成运行器

    提供独立、隔离的微信文章生成功能，与翻译工作流完全分离。
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化微信文章生成运行器

        Args:
            config_path: 配置文件路径，默认使用 config/default.yaml
        """
        self.config = load_config(config_path)

        # 初始化文章生成器
        self.article_config = ArticleGenerationConfig(
            **self.config.wechat.article_generation.model_dump()
        )

        self.article_generator = ArticleGenerator(
            config=self.article_config,
            providers_config=(
                self.config.providers.model_dump()
                if hasattr(self.config, "providers")
                else None
            ),
            wechat_llm_config=(
                self.config.models.wechat_translation_notes.model_dump()
                if hasattr(self.config, "models")
                and hasattr(self.config.models, "wechat_translation_notes")
                else None
            ),
            system_config=self.config.model_dump(),
        )

        logger.info("Repository WebUI WeChat Article runner initialized")

    def generate_from_translation(
        self,
        translation_json_path: str,
        output_dir: Optional[str] = None,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        dry_run: bool = False,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> ArticleGenerationResult:
        """
        从翻译JSON文件生成微信文章

        Args:
            translation_json_path: 翻译JSON文件路径
            output_dir: 输出目录
            author: 文章作者
            digest: 自定义摘要
            dry_run: 是否为试运行模式
            custom_metadata: 自定义元数据

        Returns:
            文章生成结果
        """
        try:
            logger.info(f"开始从翻译文件生成微信文章: {translation_json_path}")

            # 使用现有的文章生成器
            result = self.article_generator.generate_from_translation(
                translation_json_path=translation_json_path,
                output_dir=output_dir,
                author=author,
                digest=digest,
                dry_run=dry_run,
            )

            # 添加自定义元数据
            if custom_metadata:
                if not hasattr(result, "custom_metadata"):
                    result.custom_metadata = {}
                result.custom_metadata.update(custom_metadata)

            logger.info(f"微信文章生成完成: {result.slug}")
            return result

        except ArticleGeneratorError as e:
            logger.error(f"微信文章生成失败: {e}")
            raise
        except Exception as e:
            logger.error(f"微信文章生成过程中发生意外错误: {e}")
            raise ArticleGeneratorError(f"Unexpected error: {e}")

    def generate_from_translation_data(
        self,
        translation_data: Dict[str, Any],
        output_dir: Optional[str] = None,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        dry_run: bool = False,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> ArticleGenerationResult:
        """
        从翻译数据字典生成微信文章

        Args:
            translation_data: 翻译数据字典
            output_dir: 输出目录
            author: 文章作者
            digest: 自定义摘要
            dry_run: 是否为试运行模式
            custom_metadata: 自定义元数据

        Returns:
            文章生成结果
        """
        try:
            # 创建临时JSON文件
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(translation_data, f, ensure_ascii=False, indent=2)
                temp_json_path = f.name

            try:
                # 生成文章
                result = self.generate_from_translation(
                    translation_json_path=temp_json_path,
                    output_dir=output_dir,
                    author=author,
                    digest=digest,
                    dry_run=dry_run,
                    custom_metadata=custom_metadata,
                )

                return result

            finally:
                # 清理临时文件
                Path(temp_json_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"从翻译数据生成微信文章失败: {e}")
            raise ArticleGeneratorError(f"Failed to generate article from data: {e}")

    def batch_generate_articles(
        self,
        translation_files: List[str],
        output_base_dir: Optional[str] = None,
        author: Optional[str] = None,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        批量生成微信文章

        Args:
            translation_files: 翻译JSON文件路径列表
            output_base_dir: 输出基础目录
            author: 文章作者
            dry_run: 是否为试运行模式

        Returns:
            生成结果列表
        """
        logger.info(f"开始批量生成微信文章，共 {len(translation_files)} 个文件")

        results = []
        for i, translation_file in enumerate(translation_files):
            try:
                logger.info(
                    f"处理第 {i+1}/{len(translation_files)} 个文件: {translation_file}"
                )

                result = self.generate_from_translation(
                    translation_json_path=translation_file,
                    output_dir=output_base_dir,
                    author=author,
                    dry_run=dry_run,
                    custom_metadata={
                        "batch_index": i,
                        "batch_total": len(translation_files),
                    },
                )

                results.append(
                    {
                        "file_index": i,
                        "file_path": translation_file,
                        "status": "success",
                        "result": result,
                    }
                )

            except Exception as e:
                logger.error(f"第 {i+1} 个文件处理失败: {e}")
                results.append(
                    {
                        "file_index": i,
                        "file_path": translation_file,
                        "status": "error",
                        "error": str(e),
                    }
                )

        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(f"批量生成完成: {success_count}/{len(translation_files)} 成功")

        return results

    def get_article_summary(self, result: ArticleGenerationResult) -> Dict[str, Any]:
        """
        获取文章生成结果摘要

        Args:
            result: 文章生成结果

        Returns:
            摘要信息字典
        """
        summary = {
            "slug": result.slug,
            "title": result.article.title,
            "author": result.article.author,
            "digest": result.article.digest,
            "status": result.status.value,
            "output_directory": result.output_directory,
            "html_path": result.html_path,
            "metadata_path": result.metadata_path,
        }

        # 诗歌信息
        summary.update(
            {
                "poem_title": result.article.poem_title,
                "poet_name": result.article.poet_name,
                "source_lang": result.article.source_lang,
                "target_lang": result.article.target_lang,
            }
        )

        # LLM 指标
        if result.llm_metrics:
            summary["llm_metrics"] = result.llm_metrics

        # 封面图片信息
        if (
            hasattr(result.article, "cover_image_path")
            and result.article.cover_image_path
        ):
            summary["cover_image_path"] = result.article.cover_image_path
            summary["show_cover_pic"] = getattr(result.article, "show_cover_pic", False)

        # 自定义元数据
        if hasattr(result, "custom_metadata") and result.custom_metadata:
            summary["custom_metadata"] = result.custom_metadata

        return summary

    def validate_translation_file(self, translation_json_path: str) -> Dict[str, Any]:
        """
        验证翻译JSON文件是否适合生成微信文章

        Args:
            translation_json_path: 翻译JSON文件路径

        Returns:
            验证结果字典
        """
        validation_result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "metadata": {},
        }

        try:
            # 检查文件是否存在
            file_path = Path(translation_json_path)
            if not file_path.exists():
                validation_result["errors"].append(
                    f"文件不存在: {translation_json_path}"
                )
                return validation_result

            # 尝试加载JSON
            with open(translation_json_path, "r", encoding="utf-8") as f:
                translation_data = json.load(f)

            # 验证必需字段
            required_fields = ["workflow_id", "input", "congregated_output"]
            for field in required_fields:
                if field not in translation_data:
                    validation_result["errors"].append(f"缺少必需字段: {field}")

            # 验证输入数据
            input_data = translation_data.get("input", {})
            required_input_fields = ["original_poem", "source_lang", "target_lang"]
            for field in required_input_fields:
                if field not in input_data:
                    validation_result["errors"].append(f"输入数据缺少必需字段: {field}")

            # 验证聚合输出
            congregated = translation_data.get("congregated_output", {})
            required_congregated_fields = ["original_poem", "revised_translation"]
            for field in required_congregated_fields:
                if field not in congregated:
                    validation_result["warnings"].append(f"聚合输出缺少字段: {field}")

            # 提取元数据
            if not validation_result["errors"]:
                original_poem = input_data.get("original_poem", "")
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

                validation_result["metadata"] = {
                    "poem_title": poem_title,
                    "poet_name": poet_name,
                    "source_lang": input_data.get("source_lang"),
                    "target_lang": input_data.get("target_lang"),
                    "workflow_id": translation_data.get("workflow_id"),
                }

                validation_result["valid"] = True

        except json.JSONDecodeError as e:
            validation_result["errors"].append(f"JSON格式错误: {e}")
        except Exception as e:
            validation_result["errors"].append(f"验证过程中发生错误: {e}")

        return validation_result

    def create_mock_article_result(
        self,
        translation_json_path: str,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> ArticleGenerationResult:
        """
        创建模拟的文章生成结果（用于测试）

        Args:
            translation_json_path: 翻译JSON文件路径
            custom_metadata: 自定义元数据

        Returns:
            模拟的文章生成结果
        """
        # 验证文件并提取元数据
        validation = self.validate_translation_file(translation_json_path)

        if not validation["valid"]:
            raise ArticleGeneratorError(
                f"Invalid translation file: {', '.join(validation['errors'])}"
            )

        metadata = validation["metadata"]

        # 创建模拟文章
        from vpsweb.models.wechat import WeChatArticle

        mock_article = WeChatArticle(
            title=f"【知韵译诗】{metadata['poem_title']}（{metadata['poet_name']}）",
            content="<p>这是模拟生成的文章内容</p>",
            digest="这是模拟生成的文章摘要",
            author="Repository WebUI",
            poem_title=metadata["poem_title"],
            poet_name=metadata["poet_name"],
            source_lang=metadata["source_lang"],
            target_lang=metadata["target_lang"],
            translation_workflow_id=metadata["workflow_id"],
            translation_json_path=translation_json_path,
        )

        # 创建模拟结果
        mock_result = ArticleGenerationResult(
            article=mock_article,
            html_path="",  # 模拟路径
            metadata_path="",  # 模拟路径
            slug=f"mock-{metadata['poet_name']}-{metadata['poem_title']}",
            output_directory="",
            status=WeChatArticleStatus.GENERATED,
            llm_metrics={
                "mock": True,
                "tokens_used": 0,
                "cost": 0,
            },
        )

        # 添加自定义元数据
        if custom_metadata:
            mock_result.custom_metadata = custom_metadata

        return mock_result


# 便捷函数，供直接使用
def quick_generate_article(
    translation_json_path: str,
    author: Optional[str] = None,
    dry_run: bool = False,
) -> ArticleGenerationResult:
    """
    快速生成微信文章的便捷函数

    Args:
        translation_json_path: 翻译JSON文件路径
        author: 文章作者
        dry_run: 是否为试运行模式

    Returns:
        文章生成结果
    """
    runner = WeChatArticleRunner()
    return runner.generate_from_translation(
        translation_json_path=translation_json_path,
        author=author,
        dry_run=dry_run,
    )


def validate_translation_file(translation_json_path: str) -> Dict[str, Any]:
    """
    验证翻译文件的便捷函数

    Args:
        translation_json_path: 翻译JSON文件路径

    Returns:
        验证结果字典
    """
    runner = WeChatArticleRunner()
    return runner.validate_translation_file(translation_json_path)
