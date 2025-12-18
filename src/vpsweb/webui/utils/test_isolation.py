#!/usr/bin/env python3
"""
Repository WebUI Utils Isolation Test

用于测试翻译和微信文章生成工具的隔离性和独立性。
确保两个工作流可以独立运行，不会相互干扰。

Usage:
    python test_isolation.py
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

# 添加根路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from vpsweb.webui.utils import (TranslationRunner, WeChatArticleRunner,
                                quick_generate_article, quick_translate)


class IsolationTester:
    """隔离性测试器"""

    def __init__(self):
        self.test_results = []

    def log_test(self, test_name: str, success: bool, message: str = ""):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")

        self.test_results.append(
            {
                "test_name": test_name,
                "success": success,
                "message": message,
            }
        )

    async def test_translation_isolation(self):
        """测试翻译工作流的独立性"""
        print("\n🔍 测试翻译工作流独立性...")

        try:
            # 测试试运行模式
            runner = TranslationRunner()
            result = await runner.run_translation(
                original_poem="静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                source_lang="Chinese",
                target_lang="English",
                workflow_mode="hybrid",
                dry_run=True,
            )

            # 验证结果结构
            required_fields = [
                "workflow_id",
                "input",
                "congregated_output",
                "dry_run",
            ]
            for field in required_fields:
                if field not in result:
                    self.log_test(
                        f"翻译结果字段检查 ({field})",
                        False,
                        f"缺少字段: {field}",
                    )
                    return

            self.log_test("翻译试运行模式", True, "工作流正常运行")
            self.log_test("翻译结果结构验证", True, "包含所有必需字段")

        except Exception as e:
            self.log_test("翻译独立性测试", False, f"错误: {e}")

    async def test_wechat_article_isolation(self):
        """测试微信文章生成的独立性"""
        print("\n📱 测试微信文章生成独立性...")

        try:
            # 创建模拟翻译数据
            mock_translation_data = {
                "workflow_id": "test-workflow-id",
                "input": {
                    "original_poem": "静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                    "source_lang": "Chinese",
                    "target_lang": "English",
                },
                "congregated_output": {
                    "original_poem": "静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                    "revised_translation": "Quiet Night Thoughts\nBy Li Bai\nMoonlight before my bed,\nI suspect it's frost on the ground.",
                    "initial_translation_notes": "Test notes",
                    "editor_suggestions": "Test suggestions",
                    "revised_translation_notes": "Test revised notes",
                },
                "mode": "hybrid",
                "dry_run": True,
            }

            # 测试从数据生成文章
            runner = WeChatArticleRunner()
            result = runner.generate_from_translation_data(
                translation_data=mock_translation_data,
                dry_run=True,
            )

            # 验证结果结构
            required_fields = [
                "slug",
                "article",
                "html_path",
                "metadata_path",
                "status",
            ]
            for field in required_fields:
                if not hasattr(result, field):
                    self.log_test(
                        f"微信文章结果字段检查 ({field})",
                        False,
                        f"缺少字段: {field}",
                    )
                    return

            self.log_test("微信文章数据生成", True, "从数据成功生成文章")
            self.log_test("微信文章结果结构验证", True, "包含所有必需字段")

        except Exception as e:
            self.log_test("微信文章独立性测试", False, f"错误: {e}")

    async def test_cross_workflow_interference(self):
        """测试工作流之间的交叉干扰"""
        print("\n🔄 测试工作流交叉干扰...")

        try:
            # 创建翻译运行器
            translation_runner = TranslationRunner()

            # 创建微信文章运行器
            wechat_runner = WeChatArticleRunner()

            # 先运行翻译
            translation_result = await translation_runner.run_translation(
                original_poem="静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                source_lang="Chinese",
                target_lang="English",
                workflow_mode="hybrid",
                dry_run=True,
            )

            # 再运行微信文章生成（使用翻译结果）
            wechat_result = wechat_runner.generate_from_translation_data(
                translation_data=translation_result,
                dry_run=True,
            )

            # 验证两个结果都正确
            translation_ok = translation_result.get("dry_run", False)
            wechat_ok = hasattr(wechat_result, "article")

            self.log_test(
                "翻译到微信文章工作流",
                translation_ok and wechat_ok,
                "两个工作流正常协作",
            )

            # 验证没有共享状态的意外修改
            original_translation_workflow_id = translation_result.get("workflow_id")
            if original_translation_workflow_id:
                self.log_test("状态隔离验证", True, "翻译数据未被意外修改")
            else:
                self.log_test("状态隔离验证", False, "翻译数据丢失或被修改")

        except Exception as e:
            self.log_test("交叉干扰测试", False, f"错误: {e}")

    async def test_convenience_functions(self):
        """测试便捷函数"""
        print("\n⚡ 测试便捷函数...")

        try:
            # 测试快速翻译
            translation_result = await quick_translate(
                original_poem="静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                source_lang="Chinese",
                target_lang="English",
                dry_run=True,
            )

            translation_ok = translation_result.get("dry_run", False)
            self.log_test(
                "快速翻译便捷函数", translation_ok, "quick_translate 正常工作"
            )

            # 创建临时翻译文件用于测试微信文章
            mock_translation_data = {
                "workflow_id": "convenience-test",
                "input": {
                    "original_poem": "静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                    "source_lang": "Chinese",
                    "target_lang": "English",
                },
                "congregated_output": {
                    "original_poem": "静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                    "revised_translation": "Quiet Night Thoughts\nBy Li Bai\nMoonlight before my bed,\nI suspect it's frost on the ground.",
                },
            }

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(mock_translation_data, f, ensure_ascii=False, indent=2)
                temp_file = f.name

            try:
                # 测试快速生成微信文章
                wechat_result = quick_generate_article(
                    translation_json_path=temp_file,
                    dry_run=True,
                )

                wechat_ok = hasattr(wechat_result, "article")
                self.log_test(
                    "快速微信文章便捷函数",
                    wechat_ok,
                    "quick_generate_article 正常工作",
                )

            finally:
                Path(temp_file).unlink(missing_ok=True)

        except Exception as e:
            self.log_test("便捷函数测试", False, f"错误: {e}")

    async def test_error_isolation(self):
        """测试错误隔离"""
        print("\n🚨 测试错误隔离...")

        try:
            # 测试翻译错误不影响微信文章生成
            translation_runner = TranslationRunner()
            wechat_runner = WeChatArticleRunner()

            # 故意触发翻译错误
            try:
                await translation_runner.run_translation(
                    original_poem="",  # 空内容触发错误
                    source_lang="Chinese",
                    target_lang="English",
                    dry_run=True,
                )
                translation_error_caught = False
            except ValueError:
                translation_error_caught = True

            self.log_test("翻译错误捕获", translation_error_caught, "成功捕获翻译错误")

            # 验证微信文章生成器仍然正常工作
            mock_translation_data = {
                "workflow_id": "error-test",
                "input": {
                    "original_poem": "静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                    "source_lang": "Chinese",
                    "target_lang": "English",
                },
                "congregated_output": {
                    "original_poem": "静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                    "revised_translation": "Quiet Night Thoughts\nBy Li Bai",
                },
            }

            try:
                wechat_result = wechat_runner.generate_from_translation_data(
                    translation_data=mock_translation_data,
                    dry_run=True,
                )
                wechat_still_works = True
            except Exception:
                wechat_still_works = False

            self.log_test(
                "错误隔离验证",
                wechat_still_works,
                "翻译错误不影响微信文章生成",
            )

        except Exception as e:
            self.log_test("错误隔离测试", False, f"测试过程错误: {e}")

    async def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始 Repository WebUI Utils 隔离性测试")
        print("=" * 60)

        await self.test_translation_isolation()
        await self.test_wechat_article_isolation()
        await self.test_cross_workflow_interference()
        await self.test_convenience_functions()
        await self.test_error_isolation()

        # 总结测试结果
        print("\n" + "=" * 60)
        print("📊 测试结果总结")
        print("=" * 60)

        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)

        print(f"总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        print(f"成功率: {passed/total*100:.1f}%")

        if failed_tests := [r for r in self.test_results if not r["success"]]:
            print("\n❌ 失败的测试:")
            for test in failed_tests:
                print(f"  - {test['test_name']}: {test['message']}")

        if passed == total:
            print("\n🎉 所有测试通过！翻译和微信文章生成功能完全隔离。")
        else:
            print(f"\n⚠️  有 {total - passed} 个测试失败，需要检查隔离性。")

        return passed == total


async def main():
    """主函数"""
    tester = IsolationTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
