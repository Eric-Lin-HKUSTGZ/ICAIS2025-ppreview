import base64
import os

def pdf_to_base64(pdf_path: str) -> str:
    """
    将 PDF 文件编码为 Base64 字符串。

    Args:
        pdf_path: PDF 文件的路径。

    Returns:
        Base64 编码的字符串。
    """
    try:
        with open(pdf_path, 'rb') as pdf_file: # 以二进制模式读取
            pdf_content = pdf_file.read()      # 读取二进制内容
        # 使用 base64.b64encode 将二进制数据编码为 Base64 字节串
        base64_bytes = base64.b64encode(pdf_content)
        # 将 Base64 字节串解码为字符串（通常是 UTF-8，Base64 输出保证是 ASCII）
        base64_string = base64_bytes.decode('ascii')
        return base64_string
    except FileNotFoundError:
        print(f"错误：找不到文件 {pdf_path}")
        return ""
    except Exception as e:
        print(f"错误：处理文件时出现问题 - {e}")
        return ""

def save_base64_to_file(base64_string: str, pdf_path: str) -> bool:
    """
    将 Base64 编码的字符串保存到与 PDF 文件同名、同路径的 txt 文件中。

    Args:
        base64_string: Base64 编码的字符串。
        pdf_path: 原始 PDF 文件的路径。

    Returns:
        成功返回 True，失败返回 False。
    """
    try:
        # 获取 PDF 文件的目录和文件名（不含扩展名）
        pdf_dir = os.path.dirname(pdf_path)
        pdf_name_without_ext = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # 构建 txt 文件路径
        txt_file_path = os.path.join(pdf_dir, f"{pdf_name_without_ext}.txt")
        
        # 将 Base64 字符串写入文件
        with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(base64_string)
        
        print(f"Base64 编码已保存到: {txt_file_path}")
        return True
    except Exception as e:
        print(f"错误：保存文件时出现问题 - {e}")
        return False

# --- 使用示例 ---
pdf_file_path = "/Users/eric/Desktop/icais2025/ICAIS2025-ppreview/test_pdf/2409.12259v2.pdf" # 替换为你的 PDF 文件路径
# pdf_file_path = "/Users/eric/Desktop/icais2025/ICAIS2025-ppreview/test_pdf/AlphaEvolve.pdf"
base64_encoded = pdf_to_base64(pdf_file_path)

if base64_encoded:
    print("PDF 已成功编码为 Base64:")
    # 打印前 100 个字符作为预览
    print(base64_encoded[:100] + "..." if len(base64_encoded) > 100 else base64_encoded)
    
    # 保存到 txt 文件
    save_base64_to_file(base64_encoded, pdf_file_path)