"""
Prompt模板 - 用于论文评阅系统的各个阶段
"""
import re


def detect_language(text: str) -> str:
    """检测文本语言，返回'zh'（中文）或'en'（英文）"""
    if not text:
        return 'en'
    
    # 统计中文字符数量
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 统计总字符数量（排除空格和标点）
    total_chars = len(re.findall(r'[a-zA-Z\u4e00-\u9fff]', text))
    
    if total_chars == 0:
        return 'en'
    
    # 如果中文字符占比超过30%，认为是中文
    if chinese_chars / total_chars > 0.3:
        return 'zh'
    else:
        return 'en'


def get_pdf_parse_prompt(pdf_text: str, language: str = 'en') -> str:
    """PDF结构化解析Prompt"""
    if language == 'zh':
        prompt = f"""你是一位学术论文分析专家。你的任务是从以下PDF文本中提取结构化信息。

请提取并组织以下信息为结构化格式：

1. **Title（标题）**: 论文标题
2. **Authors（作者）**: 作者列表
3. **Abstract（摘要）**: 摘要文本
4. **Keywords（关键词）**: 关键词（如果有）
5. **Introduction（引言）**: 引言部分的主要观点
6. **Methodology（方法论）**: 使用的方法/方法描述
7. **Experiments（实验）**: 实验设置和程序
8. **Results（结果）**: 主要结果和发现
9. **Conclusion（结论）**: 主要结论
10. **References（参考文献）**: 参考文献列表（如果有）
11. **Paper Type（论文类型）**: 分类为以下之一：理论性、实验性、综述/评论或其他
12. **Core Contributions（核心贡献）**: 列出本文的3-5个主要贡献
13. **Technical Approach（技术方法）**: 技术方法/方法论的简要描述

PDF文本：
{pdf_text[:20000]}

请以清晰、有组织的形式提供结构化信息。如果任何部分缺失，请注明"未找到"。

请使用中文回答。所有输出内容都必须是中文。"""
    else:
        prompt = f"""You are an expert at analyzing academic papers. Your task is to extract structured information from the following PDF text.

Please extract and organize the following information in a structured format:

1. **Title**: The paper title
2. **Authors**: List of authors
3. **Abstract**: The abstract text
4. **Keywords**: Key terms (if available)
5. **Introduction**: Main points from the introduction section
6. **Methodology**: Description of the methods/approach used
7. **Experiments**: Experimental setup and procedures
8. **Results**: Key results and findings
9. **Conclusion**: Main conclusions
10. **References**: List of references (if available)
11. **Paper Type**: Classify as one of: Theoretical, Experimental, Survey/Review, or Other
12. **Core Contributions**: List 3-5 main contributions of this paper
13. **Technical Approach**: Brief description of the technical approach/methodology

PDF Text:
{pdf_text[:20000]}

Please provide the structured information in a clear, organized format. If any section is missing, indicate "Not found"."""
    
    return prompt


def get_keyword_extraction_prompt(structured_info: str, language: str = 'en') -> str:
    """关键词提取Prompt"""
    if language == 'zh':
        prompt = f"""请仔细阅读以下论文的结构化信息（包括Title、Abstract、Keywords等），从论文的实际研究内容中提取3-4个最能代表该论文研究主题的核心关键词。

关键要求：
1. **必须从论文内容中提取**：仔细阅读Title和Abstract，提取论文实际研究的技术、方法或概念
2. **关键词必须是英文（小写）**：即使论文标题或摘要包含中文，关键词也必须是英文
3. **具体而非通用**：避免提取"research"、"method"、"study"等通用词，要提取论文特有的技术术语
4. **适合学术搜索**：关键词应该能在Semantic Scholar等学术数据库中检索到相关论文

论文结构化信息：
{structured_info[:5000]}

请基于上述论文的实际研究内容，输出恰好3-4个英文关键词，用逗号分隔，不要任何额外的文本、格式或中文说明。

示例（假设论文研究3D手部重建）：
hand detection, 3d hand reconstruction, vision transformer, multi-scale pose refinement

现在请提取关键词："""
    else:
        prompt = f"""Please carefully read the following structured paper information (including Title, Abstract, Keywords, etc.) and extract 3-4 core keywords that best represent the paper's actual research topic from the paper content.

Key Requirements:
1. **Extract from paper content**: Carefully read the Title and Abstract to extract the actual technologies, methods, or concepts studied in the paper
2. **Keywords must be in lowercase English**: Even if the paper title or abstract contains other languages, keywords must be in English
3. **Specific, not generic**: Avoid generic terms like "research", "method", "study". Extract paper-specific technical terms
4. **Suitable for academic search**: Keywords should be searchable in academic databases like Semantic Scholar

Structured Paper Information:
{structured_info[:5000]}

Based on the actual research content of the above paper, output exactly 3-4 English keywords, separated by commas, without any additional text or formatting.

Example (assuming the paper studies 3D hand reconstruction):
hand detection, 3d hand reconstruction, vision transformer, multi-scale pose refinement

Now extract the keywords:"""
    
    return prompt


def get_innovation_analysis_prompt(structured_info: str, related_papers: str, language: str = 'en') -> str:
    """创新点分析Prompt"""
    if language == 'zh':
        if not related_papers or related_papers.strip() == "" or related_papers.strip() == "No related papers found.":
            prompt = f"""你是一位研究创新分析专家。基于论文信息，识别创新点和贡献。

论文信息：
{structured_info[:5000]}

注意：未检索到相关论文，请基于论文本身的内容进行分析。

请分析：
1. **创新点（Innovation Points）**: 本文有哪些新颖的贡献？
2. **技术优势（Advantages）**: 本文方法的优势是什么？
3. **原创性评估（Originality Assessment）**: 评估原创性（高/中/低）并简要说明。

请使用中文回答。所有输出内容都必须是中文。"""
        else:
            prompt = f"""你是一位研究创新分析专家。基于论文信息和相关论文，识别创新点和差异。

论文信息：
{structured_info[:5000]}

相关论文：
{related_papers[:10000]}

请分析：
1. **创新点（Innovation Points）**: 本文有哪些新颖的贡献？
2. **与相关工作的差异（Differences from Related Work）**: 本文与现有工作有何不同？
3. **优势（Advantages）**: 本文方法的优势是什么？
4. **原创性评估（Originality Assessment）**: 评估原创性（高/中/低）并简要说明。

请使用中文回答。所有输出内容都必须是中文。"""
    else:
        if not related_papers or related_papers.strip() == "" or related_papers.strip() == "No related papers found.":
            prompt = f"""You are an expert at analyzing research innovation. Based on the paper information, identify the innovation points and contributions.

Paper Information:
{structured_info[:5000]}

Note: No related papers were found. Please analyze based on the paper content itself.

Please analyze:
1. **Innovation Points**: What are the novel contributions of this paper?
2. **Advantages**: What are the advantages of this paper's approach?
3. **Originality Assessment**: Rate the originality (High/Medium/Low) with brief explanation."""
        else:
            prompt = f"""You are an expert at analyzing research innovation. Based on the paper information and related papers, identify the innovation points and differences.

Paper Information:
{structured_info[:5000]}

Related Papers:
{related_papers[:10000]}

Please analyze:
1. **Innovation Points**: What are the novel contributions of this paper?
2. **Differences from Related Work**: How does this paper differ from existing work?
3. **Advantages**: What are the advantages of this paper's approach?
4. **Originality Assessment**: Rate the originality (High/Medium/Low) with brief explanation."""
    
    return prompt


def get_evaluation_prompt(structured_info: str, innovation_analysis: str, related_papers: str, language: str = 'en') -> str:
    """多维度评估Prompt"""
    if language == 'zh':
        prompt = f"""你是一位学术评阅专家。请从多个维度评估以下论文。

论文信息：
{structured_info[:5000]}

创新分析：
{innovation_analysis[:2000]}

相关论文背景：
{related_papers[:5000]}

请提供详细的评估，涵盖：

1. **技术质量（Technical Quality）**：
   - 方法的合理性和可靠性
   - 实验设计质量
   - 结果的可信度和有效性
   - 技术严谨性

2. **新颖性（Novelty）**：
   - 创新水平
   - 贡献意义
   - 与现有工作相比的独特性

3. **清晰度（Clarity）**：
   - 写作质量
   - 逻辑流程和组织
   - 呈现清晰度
   - 可读性

4. **完整性（Completeness）**：
   - 内容完整性
   - 实验充分性
   - 讨论深度
   - 缺失要素

请为每个维度提供详细分析。

请使用中文回答。所有输出内容都必须是中文。"""
    else:
        prompt = f"""You are an expert academic reviewer. Please evaluate the following paper from multiple dimensions.

Paper Information:
{structured_info[:5000]}

Innovation Analysis:
{innovation_analysis[:2000]}

Related Papers Context:
{related_papers[:5000]}

Please provide a detailed evaluation covering:

1. **Technical Quality**:
   - Method rationality and soundness
   - Experimental design quality
   - Result credibility and validity
   - Technical rigor

2. **Novelty**:
   - Innovation level
   - Contribution significance
   - Uniqueness compared to existing work

3. **Clarity**:
   - Writing quality
   - Logical flow and organization
   - Presentation clarity
   - Readability

4. **Completeness**:
   - Content completeness
   - Experimental sufficiency
   - Discussion depth
   - Missing elements

Provide detailed analysis for each dimension."""
    
    return prompt


def get_review_generation_prompt(structured_info: str, evaluation: str, innovation_analysis: str, language: str = 'en') -> str:
    """评阅报告生成Prompt"""
    if language == 'zh':
        prompt = f"""你是一位学术评阅专家。基于论文信息、评估和创新分析，生成一份全面的评阅报告。

论文信息：
{structured_info[:5000]}

评估：
{evaluation[:3000]}

创新分析：
{innovation_analysis[:2000]}

请以Markdown格式生成评阅报告，包含以下部分：

# 摘要（Summary）
[提供论文及其核心贡献的简要摘要]

# 优点（Strengths）
[列出论文的主要优点和亮点]

# 缺点/关注点（Weaknesses / Concerns）
[识别缺点、关注点和需要改进的领域]

# 给作者的问题（Questions for Authors）
[向作者提出建设性问题]

# 评分（Score）
- 总体（Overall）: [X]/10
- 新颖性（Novelty）: [X]/10
- 技术质量（Technical Quality）: [X]/10
- 清晰度（Clarity）: [X]/10
- 置信度（Confidence）: [X]/5

请确保：
1. 评阅具有建设性和专业性
2. 评分由评估结果证明
3. 问题具体且有用
4. 格式完全符合上述结构

请使用中文回答。所有输出内容都必须是中文。"""
    else:
        prompt = f"""You are an expert academic reviewer. Based on the paper information, evaluation, and innovation analysis, generate a comprehensive review report.

Paper Information:
{structured_info[:5000]}

Evaluation:
{evaluation[:3000]}

Innovation Analysis:
{innovation_analysis[:2000]}

Please generate a review report in Markdown format with the following sections:

# Summary
[Provide a brief summary of the paper and its core contributions]

# Strengths
[List the main strengths and highlights of the paper]

# Weaknesses / Concerns
[Identify weaknesses, concerns, and areas for improvement]

# Questions for Authors
[Pose constructive questions for the authors]

# Score
- Overall: [X]/10
- Novelty: [X]/10
- Technical Quality: [X]/10
- Clarity: [X]/10
- Confidence: [X]/5

Please ensure:
1. The review is constructive and professional
2. Scores are justified by the evaluation
3. Questions are specific and helpful
4. The format matches exactly the structure above"""
    
    return prompt

