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
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# 添加根路径以确保可以导入其他模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from vpsweb.utils.article_generator import ArticleGenerator, ArticleGeneratorError
from vpsweb.services.config import get_config_facade, ConfigFacade
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

    def __init__(self, config_path: Optional[str] = None, config_facade: Optional[ConfigFacade] = None):
        """
        初始化微信文章生成运行器

        Args:
            config_path: 配置文件路径，默认使用 config/default.yaml (legacy)
            config_facade: ConfigFacade instance (preferred)
        """
        # Support both legacy and ConfigFacade patterns
        if config_facade is not None:
            self._config_facade = config_facade
            self._using_facade = True
            self.config = None  # Not needed with ConfigFacade
            print("✅ Using ConfigFacade for WeChat article runner")
        else:
            # Try to get from global ConfigFacade
            try:
                self._config_facade = get_config_facade()
                self._using_facade = True
                self.config = None
                print("✅ Using global ConfigFacade for WeChat article runner")
            except RuntimeError:
                # Fall back: create a temporary CompleteConfig for compatibility
                from vpsweb.models.config import CompleteConfig, MainConfig, WorkflowConfig, ProvidersConfig
                from vpsweb.utils.config_loader import load_model_registry_config, load_task_templates_config

                # Create a minimal compatibility config
                main_config = MainConfig(
                    workflow_mode="hybrid",
                    workflow=WorkflowConfig(name="wechat", version="1.0.0"),
                )
                providers_config = ProvidersConfig()
                self.config = CompleteConfig(main=main_config, providers=providers_config)
                self._config_facade = None
                self._using_facade = False
                print("⚠️ Using compatibility config for WeChat article runner")

        # Initialize article generator with ConfigFacade if available
        if self._using_facade:
            # Create article config from ConfigFacade
            from vpsweb.models.wechat import ArticleGenerationConfig
            wechat_config = self._config_facade.models.get_wechat_article_generation_config() or {}
            article_config = ArticleGenerationConfig(**wechat_config)
            self.article_generator = ArticleGenerator(config=article_config, config_facade=self._config_facade)
        else:
            # Legacy pattern: check for WeChat configuration
            if hasattr(self.config, "wechat") and hasattr(
                self.config.wechat, "article_generation"
            ):
                # Use complete WeChat configuration
                wechat_config = self.config.wechat.article_generation.model_dump()
                print("✅ Using WeChat configuration from legacy config")
            else:
                # Use default configuration
                wechat_config = {
                    "include_translation_notes": True,
                    "copyright_text": "【著作权声明】\n本译文与译注完全由知韵(VoxPoetica)AI工具生成制作，仅供学习交流使用。原作品版权归原作者所有，如有侵权请联系删除。翻译内容未经授权，不得转载、不得用于商业用途。若需引用，请注明出处。",
                    "article_template": "codebuddy",
                    "default_cover_image_path": "config/html_templates/cover_image_big.jpg",
                    "default_local_cover_image_name": "cover_image_big.jpg",
                    "model_type": "non_reasoning",
                }
                print("⚠️ Using default WeChat configuration (config.wechat not found)")

            # Initialize article generator with legacy config
            self.article_config = ArticleGenerationConfig(**wechat_config)
            self.article_generator = ArticleGenerator(
                config=self.article_config,
                providers_config=(
                    self.config.providers if hasattr(self.config, "providers") else None
                ),
                wechat_llm_config=(
                    self.config.providers.wechat_translation_notes.model_dump()
                    if hasattr(self.config, "providers")
                    and hasattr(self.config.providers, "wechat_translation_notes")
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
            print(
                f"📄 Starting WeChat article generation from file: {translation_json_path}"
            )
            logger.info(f"开始从翻译文件生成微信文章: {translation_json_path}")

            print(f"🔧 Calling article generator...")
            # 使用现有的文章生成器
            result = self.article_generator.generate_from_translation(
                translation_json_path=translation_json_path,
                output_dir=output_dir,
                author=author,
                digest=digest,
                dry_run=dry_run,
            )
            print(f"✅ Article generator returned result successfully!")

            # Fix metadata paths and add source_html_path for WebUI usage
            result = self._fix_webui_metadata(
                result, translation_json_path, result.output_directory
            )

            # Custom metadata handling - skip for now since model doesn't support it
            # Note: custom_metadata parameter kept for API compatibility
            print(f"📝 WeChat article generation completed: {result.slug}")
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
            print(f"📝 Creating temporary JSON file for article generation...")
            # 创建临时JSON文件
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(translation_data, f, ensure_ascii=False, indent=2)
                temp_json_path = f.name

            print(f"✅ Temporary JSON file created: {temp_json_path}")

            try:
                print(f"🚀 Starting article generation from translation data...")
                # 生成文章
                result = self.generate_from_translation(
                    translation_json_path=temp_json_path,
                    output_dir=output_dir,
                    author=author,
                    digest=digest,
                    dry_run=dry_run,
                    custom_metadata=custom_metadata,
                )
                print(f"✅ Article generation completed successfully!")

                # Fix metadata paths for WebUI usage
                result = self._fix_webui_metadata(
                    result, temp_json_path, result.output_directory
                )

                return result

            finally:
                # 清理临时文件
                Path(temp_json_path).unlink(missing_ok=True)
                print(f"🧹 Temporary file cleaned up: {temp_json_path}")

        except Exception as e:
            print(f"❌ Failed to generate article from data: {e}")
            logger.error(f"从翻译数据生成微信文章失败: {e}")
            raise ArticleGeneratorError(f"Failed to generate article from data: {e}")

    def _fix_webui_metadata(
        self,
        result: ArticleGenerationResult,
        original_json_path: str,
        output_dir: Optional[str],
    ) -> ArticleGenerationResult:
        """
        Fix metadata paths for WebUI usage.

        This method addresses the issues where:
        1. source_json_path points to a temporary file instead of the actual source
        2. source_html_path is missing but needed for browser viewing

        Args:
            result: Original article generation result
            original_json_path: Path to the original translation JSON file (if available)
            output_dir: Output directory where articles were generated

        Returns:
            Updated ArticleGenerationResult with corrected metadata
        """
        try:
            # Load the metadata file
            if not output_dir:
                print("⚠️ No output_dir provided, cannot fix metadata paths")
                return result

            metadata_path = Path(output_dir) / "metadata.json"
            if not metadata_path.exists():
                print(f"⚠️ Metadata file not found: {metadata_path}")
                return result

            # Read current metadata
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata_dict = json.load(f)

            # Fix source_json_path - remove temporary file path and add meaningful reference
            if "source_json_path" in metadata_dict:
                temp_path = metadata_dict["source_json_path"]
                if temp_path.startswith("/var/folders/") or temp_path.startswith(
                    "/tmp/"
                ):
                    # Replace with meaningful translation reference
                    if "poet_name" in metadata_dict and "poem_title" in metadata_dict:
                        poet = metadata_dict["poet_name"]
                        title = metadata_dict["poem_title"]
                        metadata_dict["source_json_path"] = (
                            f"WebUI Translation: {title} by {poet}"
                        )
                    else:
                        metadata_dict["source_json_path"] = (
                            f"WebUI Translation (generated {datetime.now().strftime('%Y-%m-%d')})"
                        )
                    print(
                        f"🔧 Fixed source_json_path: {metadata_dict['source_json_path']}"
                    )

            # Add source_html_path for browser viewing
            html_file_path = Path(output_dir) / "article.html"
            if html_file_path.exists():
                metadata_dict["source_html_path"] = str(html_file_path.absolute())
                print(f"🔧 Added source_html_path: {metadata_dict['source_html_path']}")
            else:
                print(f"⚠️ HTML file not found: {html_file_path}")

            # Write updated metadata
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_dict, f, ensure_ascii=False, indent=2)

            print(f"✅ Updated metadata file with correct paths")

            # Update the result object if needed (Note: ArticleGenerationResult might not have metadata field)
            # This depends on the ArticleGenerationResult structure

            return result

        except Exception as e:
            print(f"⚠️ Failed to fix metadata paths: {e}")
            logger.error(f"Failed to fix metadata paths: {e}")
            # Return original result if fixing fails
            return result

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
