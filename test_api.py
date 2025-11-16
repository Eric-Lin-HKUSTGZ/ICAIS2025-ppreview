#!/usr/bin/env python3
"""
API服务测试程序
用于测试论文评阅API的流式响应
"""

import os
import sys
import json
import base64
import requests
import argparse
from pathlib import Path


def pdf_to_base64(pdf_path: str) -> str:
    """
    读取PDF文件并转换为Base64编码的字符串。

    Args:
        pdf_path: PDF文件的路径。

    Returns:
        Base64 编码的字符串。
    """
    try:
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
        return pdf_base64
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {pdf_path}")
        return ""
    except Exception as e:
        print(f"❌ 错误：读取PDF文件时出现问题 - {e}")
        return ""


def parse_sse_line(line: str) -> dict:
    """
    解析SSE数据行
    
    Args:
        line: SSE格式的数据行
        
    Returns:
        解析后的数据字典，如果解析失败返回None
    """
    line = line.strip()
    if not line:
        return None
    
    # 检查结束标记（处理可能的重复前缀）
    if line == "data: [DONE]" or line == "data: data: [DONE]":
        return {"done": True}
    
    # 检查是否是SSE数据行（处理可能的重复前缀）
    if line.startswith("data: "):
        data_str = line[6:]  # 移除第一个 "data: " 前缀
        
        # 如果还有重复的 "data: " 前缀，再次移除
        if data_str.startswith("data: "):
            data_str = data_str[6:]
        
        try:
            data = json.loads(data_str)
            return data
        except json.JSONDecodeError as e:
            # JSON解析失败，返回None
            return None
    
    # 如果不是以"data: "开头，可能是其他SSE字段（如event、id等），忽略
    return None


def test_paper_review_api(
    api_url: str,
    pdf_path: str,
    query: str = "Please review this paper",
    output_file: str = None,
    debug: bool = False
):
    """
    测试论文评阅API
    
    Args:
        api_url: API端点URL
        pdf_path: PDF文件路径
        query: 查询字符串
        output_file: 输出文件路径（可选，如果提供则保存完整响应）
        debug: 是否启用调试模式
    """
    print(f"📄 测试文件: {pdf_path}")
    print(f"🔗 API端点: {api_url}")
    print(f"❓ 查询: {query}")
    print("-" * 80)
    
    # 1. 读取PDF文件并转换为base64
    print("📖 正在读取PDF文件并转换为Base64...")
    base64_content = pdf_to_base64(pdf_path)
    if not base64_content:
        print("❌ PDF文件读取失败，退出测试")
        return
    
    # 计算原始PDF文件大小
    try:
        pdf_size = os.path.getsize(pdf_path)
        pdf_size_mb = pdf_size / (1024 * 1024)
        print(f"✅ PDF文件已读取，文件大小: {pdf_size_mb:.2f} MB")
    except:
        pass
    
    print(f"✅ Base64编码完成，长度: {len(base64_content)} 字符")
    print("-" * 80)
    
    # 2. 构建请求
    request_data = {
        "query": query,
        "pdf_content": base64_content
    }
    
    # 3. 发送POST请求（流式响应）
    print("🚀 发送请求到API...")
    print("-" * 80)
    
    try:
        # 发送请求，确保stream=True以支持流式响应
        response = requests.post(
            api_url,
            json=request_data,
            stream=True,  # 关键：启用流式响应
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            },
            timeout=1200  # 20分钟超时
        )
        
        response.raise_for_status()
        
        # 检查响应类型
        content_type = response.headers.get('Content-Type', '')
        if 'text/event-stream' not in content_type:
            print(f"⚠️ 警告: 响应Content-Type不是text/event-stream，而是: {content_type}")
        
        # 检查响应头
        # print(f"[DEBUG] 响应状态码: {response.status_code}")
        # print(f"[DEBUG] 响应头 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        # print(f"[DEBUG] 响应头 Transfer-Encoding: {response.headers.get('Transfer-Encoding', 'N/A')}")
        
        # 4. 处理流式响应
        print("\n📥 开始接收流式响应:\n")
        print("=" * 80)
        
        full_content = ""
        chunk_count = 0
        line_count = 0
        raw_line_count = 0
        debug_mode = debug  # 使用参数控制调试模式
        
        try:
            # 使用iter_content手动处理SSE流，确保正确处理流式数据
            # SSE格式是 data: {...}\n\n，每个事件之间用两个换行符分隔
            buffer = ""
            done_received = False
            
            # 使用iter_content逐块读取，避免缓冲问题
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if not chunk:
                    # 空chunk可能表示流结束，但继续尝试读取
                    if debug_mode:
                        # print("[DEBUG] 收到空chunk，继续等待...")
                        pass
                    continue
                
                raw_line_count += len(chunk)
                buffer += chunk
                
                # 处理缓冲区中的完整行（按\n分割）
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    # 空行表示SSE事件结束，继续处理下一个事件
                    if not line:
                        continue
                    
                    line_count += 1
                    
                    # 调试：打印前5行处理后的数据（总是打印，帮助定位问题）
                    # if line_count <= 5:
                    #     print(f"[DEBUG] 行 {line_count}: {repr(line[:150])}")
                    
                    # 解析SSE数据
                    data = parse_sse_line(line)
                    
                    if data is None:
                        # 如果解析失败，记录前几个失败的行以便调试
                        # if line_count <= 10:
                        #     print(f"[DEBUG] 解析失败的行 {line_count}: {repr(line[:200])}")
                        continue
                    
                    # 检查是否是结束标记
                    if data.get("done"):
                        print("\n" + "=" * 80)
                        print("✅ 响应完成")
                        done_received = True
                        break
                    
                    # 提取content内容
                    if "choices" in data and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        
                        if content:
                            # 实时输出内容
                            print(content, end='', flush=True)
                            full_content += content
                            chunk_count += 1
                            
                            # 每100个chunk打印一次调试信息
                            # if chunk_count % 100 == 0:
                            #     print(f"\n[DEBUG] 已接收 {chunk_count} 个chunk，总内容长度: {len(full_content)} 字符", end='', flush=True)
                    else:
                        # 如果解析成功但没有choices，记录前几个以便调试
                        # if line_count <= 10:
                        #     print(f"[DEBUG] 解析成功但无choices，行 {line_count}，数据键: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                        pass
                
                # 如果收到结束标记，退出循环
                if done_received:
                    break
            
            # 处理剩余的缓冲区内容
            if buffer.strip() and not done_received:
                if debug_mode:
                    # print(f"[DEBUG] 剩余缓冲区内容: {repr(buffer)}")
                    pass
                # 尝试解析剩余内容
                for line in buffer.split('\n'):
                    line = line.strip()
                    if line:
                        data = parse_sse_line(line)
                        if data and data.get("done"):
                            print("\n" + "=" * 80)
                            print("✅ 响应完成（从缓冲区）")
                            break
        
        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断接收流式响应")
            # print(f"[DEBUG] 已处理行数: {line_count}, 原始字符数: {raw_line_count}, chunk数: {chunk_count}")
        except Exception as parse_error:
            print(f"\n❌ 解析SSE流时出错: {parse_error}")
            import traceback
            traceback.print_exc()
            # print(f"[DEBUG] 已处理行数: {line_count}, 原始字符数: {raw_line_count}, chunk数: {chunk_count}")
            # 尝试读取响应内容以便调试
            try:
                response.raw.read(1024)
            except:
                pass
        
        print(f"\n\n📊 统计信息:")
        print(f"  - 接收到的原始字符数: {raw_line_count}")
        print(f"  - 处理后的行数: {line_count}")
        print(f"  - 接收到的chunk数量: {chunk_count}")
        print(f"  - 总内容长度: {len(full_content)} 字符")
        
        # 5. 保存完整响应到文件（如果指定）
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                print(f"  - 完整响应已保存到: {output_file}")
            except Exception as e:
                print(f"  - ⚠️ 保存响应失败: {e}")
        
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时（超过20分钟）")
        import traceback
        traceback.print_exc()
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ 连接错误: {e}")
        print("   请确保API服务正在运行")
        import traceback
        traceback.print_exc()
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP错误: {e}")
        print(f"   状态码: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
        try:
            if hasattr(e, 'response') and e.response is not None:
                print(f"   响应内容: {e.response.text[:500]}")
        except:
            pass
        import traceback
        traceback.print_exc()
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()


def list_pdf_files(test_pdf_dir: str):
    """列出test_pdf目录中的所有PDF文件"""
    pdf_dir = Path(test_pdf_dir)
    if not pdf_dir.exists():
        print(f"❌ 目录不存在: {test_pdf_dir}")
        return []
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    return sorted(pdf_files)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="测试论文评阅API服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 测试默认PDF文件
  python test_api.py

  # 测试指定PDF文件
  python test_api.py --pdf test_pdf/attention_is_all_you_need.pdf

  # 指定API URL和查询
  python test_api.py --url http://localhost:3000/paper_review --query "Please provide a detailed review"

  # 保存响应到文件
  python test_api.py --output review_result.txt
        """
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:3000/paper_review",
        help="API端点URL (默认: http://localhost:3000/paper_review)"
    )
    
    parser.add_argument(
        "--pdf",
        type=str,
        help="PDF文件路径（相对于test_pdf目录或绝对路径）"
    )
    
    parser.add_argument(
        "--query",
        type=str,
        default="Please review this paper",
        help="查询字符串 (默认: 'Please review this paper')"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（可选，保存完整响应）"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出test_pdf目录中的所有PDF文件"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式，显示原始SSE数据"
    )
    
    args = parser.parse_args()
    
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    test_pdf_dir = script_dir / "test_pdf"
    
    # 列出PDF文件
    if args.list:
        print("📚 test_pdf目录中的PDF文件:")
        pdf_files = list_pdf_files(str(test_pdf_dir))
        if pdf_files:
            for i, pdf_file in enumerate(pdf_files, 1):
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                print(f"  {i}. {pdf_file.name} ({size_mb:.2f} MB)")
        else:
            print("  (无PDF文件)")
        return
    
    # 确定PDF文件路径
    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.is_absolute():
            # 相对路径，尝试从test_pdf目录或当前目录查找
            test_pdf_path = test_pdf_dir / pdf_path.name
            if test_pdf_path.exists():
                pdf_path = test_pdf_path
            elif pdf_path.exists():
                pass  # 使用当前目录下的路径
            else:
                print(f"❌ 找不到PDF文件: {args.pdf}")
                print(f"   尝试了: {test_pdf_path}")
                print(f"   尝试了: {pdf_path}")
                return
    else:
        # 使用默认PDF文件（第一个找到的）
        pdf_files = list_pdf_files(str(test_pdf_dir))
        if not pdf_files:
            print(f"❌ test_pdf目录中没有找到PDF文件: {test_pdf_dir}")
            return
        pdf_path = pdf_files[0]
        print(f"ℹ️  未指定PDF文件，使用默认文件: {pdf_path.name}")
    
    # 检查PDF文件是否存在
    if not pdf_path.exists():
        print(f"❌ PDF文件不存在: {pdf_path}")
        return
    
    # 运行测试
    test_paper_review_api(
        api_url=args.url,
        pdf_path=str(pdf_path),
        query=args.query,
        output_file=args.output,
        debug=args.debug
    )


if __name__ == "__main__":
    main()

