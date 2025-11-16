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
        prompt = f"""你是一位学术评阅专家。请从多个维度深入评估以下论文。

论文信息：
{structured_info[:5000]}

创新分析：
{innovation_analysis[:2000]}

相关论文背景：
{related_papers[:5000]}

请提供详细的评估，涵盖以下维度。**重要**：如果论文信息中包含章节号、表格号或图表号（如§3.3.1、Table 3、Figure 2等），请在评估中引用这些具体位置。

1. **技术质量（Technical Quality）**：
   - 方法的合理性和可靠性：评估方法设计的理论基础、技术路线的合理性
   - 实验设计质量：评估实验设置的严谨性、对照组的合理性、评估指标的恰当性
   - 结果的可信度和有效性：深入分析实验结果，包括：
     * 成功和失败的模式（在哪些任务或场景下表现好/差）
     * 结果的统计显著性
     * 与基线比较的公平性和有效性
     * 是否存在潜在的混淆因素（如计算资源、LLM版本差异等）
   - 技术严谨性：评估算法实现的细节、计算复杂度的分析、可扩展性考虑

2. **新颖性（Novelty）**：
   - 创新水平：深入理解论文的技术创新，包括：
     * 核心算法或方法的新颖之处
     * 与现有工作的本质区别
     * 技术创新对领域的贡献程度
   - 贡献意义：评估论文贡献的学术价值和实用价值
   - 与现有工作相比的独特性：基于相关论文背景，详细分析论文的独特贡献

3. **清晰度（Clarity）**：
   - 写作质量：评估论文的表达是否清晰、准确
   - 逻辑流程和组织：评估论文的结构是否合理、逻辑是否清晰
   - 呈现清晰度：评估图表、表格、公式的清晰度和可读性
   - 可读性：评估论文是否易于理解，包括：
     * 数学公式和符号的一致性
     * 技术术语的定义和使用
     * 关键概念的解释是否充分

4. **完整性（Completeness）**：
   - 内容完整性：评估论文是否涵盖了必要的组成部分
   - 实验充分性：评估实验是否充分验证了论文的贡献，包括：
     * 消融研究的完整性
     * 不同设置下的实验验证
     * 失败案例的分析
   - 讨论深度：评估论文对结果的分析、局限性的讨论是否深入
   - 缺失要素：识别论文中缺失的重要信息，如：
     * 实现细节
     * 超参数设置的合理性
     * 可复现性相关的信息
     * 资源消耗的讨论

**评估要求**：
1. 对每个维度提供详细、具体的分析，避免泛泛而谈
2. 引用具体的章节、表格或图表来支撑你的评估
3. 深入分析实验结果，识别成功和失败的模式
4. 深入理解技术创新，评估其新颖性和贡献
5. 保持客观、建设性的评估态度

请为每个维度提供详细分析。

请使用中文回答。所有输出内容都必须是中文。"""
    else:
        prompt = f"""You are an expert academic reviewer. Please evaluate the following paper in depth from multiple dimensions.

Paper Information:
{structured_info[:5000]}

Innovation Analysis:
{innovation_analysis[:2000]}

Related Papers Context:
{related_papers[:5000]}

Please provide a detailed evaluation covering the following dimensions. **Important**: If the paper information includes section numbers, table numbers, or figure numbers (e.g., §3.3.1, Table 3, Figure 2), please cite these specific locations in your evaluation.

1. **Technical Quality**:
   - Method rationality and soundness: Assess the theoretical foundation of the method design and the rationality of the technical approach
   - Experimental design quality: Evaluate the rigor of experimental setup, reasonableness of control groups, and appropriateness of evaluation metrics
   - Result credibility and validity: Deeply analyze experimental results, including:
     * Patterns of success and failure (which tasks or scenarios perform well/poorly)
     * Statistical significance of results
     * Fairness and validity of baseline comparisons
     * Potential confounding factors (e.g., computational resources, LLM version differences)
   - Technical rigor: Assess algorithm implementation details, computational complexity analysis, scalability considerations

2. **Novelty**:
   - Innovation level: Deeply understand the paper's technical innovations, including:
     * Novel aspects of core algorithms or methods
     * Essential differences from existing work
     * Contribution level of technical innovation to the field
   - Contribution significance: Assess the academic and practical value of the paper's contributions
   - Uniqueness compared to existing work: Based on related papers context, provide detailed analysis of the paper's unique contributions

3. **Clarity**:
   - Writing quality: Assess whether the paper's expression is clear and accurate
   - Logical flow and organization: Evaluate whether the paper's structure is reasonable and logic is clear
   - Presentation clarity: Assess the clarity and readability of figures, tables, and equations
   - Readability: Evaluate whether the paper is easy to understand, including:
     * Consistency of mathematical formulas and notation
     * Definition and use of technical terms
     * Whether explanations of key concepts are sufficient

4. **Completeness**:
   - Content completeness: Assess whether the paper covers necessary components
   - Experimental sufficiency: Evaluate whether experiments sufficiently validate the paper's contributions, including:
     * Completeness of ablation studies
     * Experimental validation under different settings
     * Analysis of failure cases
   - Discussion depth: Assess whether the paper's analysis of results and discussion of limitations are in-depth
   - Missing elements: Identify important missing information in the paper, such as:
     * Implementation details
     * Rationale for hyperparameter settings
     * Reproducibility-related information
     * Discussion of resource consumption

**Evaluation Requirements**:
1. Provide detailed, specific analysis for each dimension, avoiding generalizations
2. Cite specific sections, tables, or figures to support your evaluation
3. Deeply analyze experimental results, identifying patterns of success and failure
4. Deeply understand technical innovations, assessing their novelty and contributions
5. Maintain an objective, constructive evaluation attitude

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

请提供精炼准确的摘要（150-200字），必须包含：
1. 论文的核心贡献（1-2句话）
2. 主要方法或技术路线（1句话）
3. 关键实验结果和数据（如性能指标、准确率、提升幅度等具体数值）

摘要应该简洁明了，让读者快速了解论文的核心价值。

# 优点（Strengths）

请按2-3个维度组织优点，每个维度：
1. 使用明确的主题句作为开头（如"创新的图搜索算法"、"有效的知识集成"等）
2. 详细说明该优点的具体表现和意义
3. 如果论文信息中包含章节号、图表号（如§3.3.1、Figure 2、Table 3等），请引用这些具体位置
4. 引用具体的实验数据或结果来支撑你的观点

每个优点应该独立成段，逻辑清晰，有说服力。

# 缺点/关注点（Weaknesses / Concerns）

请从以下维度分析缺点和关注点（至少涵盖3-4个维度）：
1. **技术细节**：实现细节、计算复杂度、算法设计等方面的不足
2. **方法论**：实验设计、比较方法、评估指标等方面的局限性
3. **实验设计**：实验设置、基线比较、结果分析等方面的不足
4. **可复现性**：代码可用性、超参数设置、资源需求等方面的关注点

每个缺点应该：
- 明确指出具体的问题
- 说明为什么这是一个问题（影响或风险）
- 如果可能，引用具体的章节、表格或图表
- 保持客观和建设性的语调

# 给作者的问题（Questions for Authors）

请提出4-5个建设性问题，覆盖以下方面：
1. 技术细节：关于算法实现、机制设计的具体问题
2. 实验分析：关于实验结果、比较方法的问题
3. 泛化性：关于方法适用性、扩展性的问题
4. 设计选择：关于关键设计决策的理由和影响

每个问题应该：
- 具体明确，直接针对论文中的技术点或方法
- 有助于澄清论文中的模糊之处或深化理解
- 避免过于宽泛或与论文无关的问题

# 评分（Score）

请为以下维度评分，并为每个评分提供简要说明（1-2句话）：

- 总体（Overall）: [X]/10
  [说明：简要说明总体评分的理由，综合考虑论文的创新性、技术质量、实验验证等方面]

- 新颖性（Novelty）: [X]/10
  [说明：评估论文的创新程度，与现有工作的区别]

- 技术质量（Technical Quality）: [X]/10
  [说明：评估方法的合理性、实验设计的严谨性、结果的可信度]

- 清晰度（Clarity）: [X]/10
  [说明：评估论文的写作质量、逻辑组织、表达清晰度]

- 置信度（Confidence）: [X]/5
  [说明：评估你对评阅结论的置信程度，考虑实验验证的充分性、结果的可复现性等]

**重要要求**：
1. 评分必须与评阅内容高度一致，不能出现矛盾
2. 评分应该客观公正，反映论文的真实水平
3. 每个评分的说明应该简洁明了，直接对应评阅中的分析

请确保：
1. 评阅具有建设性和专业性
2. 所有内容基于提供的论文信息、评估和创新分析
3. 格式完全符合上述结构
4. 使用中文回答，所有输出内容都必须是中文"""
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

Provide a concise and accurate summary (150-200 words) that MUST include:
1. The paper's core contributions (1-2 sentences)
2. Main methods or technical approaches (1 sentence)
3. Key experimental results and data (specific metrics such as performance indicators, accuracy, improvement percentages, etc.)

The summary should be clear and concise, allowing readers to quickly understand the paper's core value.

# Strengths

Organize strengths into 2-3 dimensions. For each dimension:
1. Start with a clear topic sentence (e.g., "Innovative graph-based search algorithm", "Effective knowledge integration", etc.)
2. Provide detailed explanation of the specific manifestations and significance of this strength
3. If the paper information includes section numbers, figure/table references (e.g., §3.3.1, Figure 2, Table 3), cite these specific locations
4. Support your points with specific experimental data or results

Each strength should be a separate paragraph with clear logic and strong persuasiveness.

# Weaknesses / Concerns

Analyze weaknesses and concerns from the following dimensions (cover at least 3-4 dimensions):
1. **Technical Details**: Deficiencies in implementation details, computational complexity, algorithm design, etc.
2. **Methodology**: Limitations in experimental design, comparison methods, evaluation metrics, etc.
3. **Experimental Design**: Deficiencies in experimental setup, baseline comparisons, result analysis, etc.
4. **Reproducibility**: Concerns about code availability, hyperparameter settings, resource requirements, etc.

Each weakness should:
- Clearly identify the specific problem
- Explain why this is a problem (impact or risk)
- If possible, cite specific sections, tables, or figures
- Maintain an objective and constructive tone

# Questions for Authors

Pose 4-5 constructive questions covering the following aspects:
1. Technical details: Specific questions about algorithm implementation and mechanism design
2. Experimental analysis: Questions about experimental results and comparison methods
3. Generalization: Questions about method applicability and scalability
4. Design choices: Questions about the rationale and impact of key design decisions

Each question should:
- Be specific and directly address technical points or methods in the paper
- Help clarify ambiguities or deepen understanding
- Avoid being too broad or unrelated to the paper

# Score

Rate the following dimensions and provide a brief justification (1-2 sentences) for each score:

- Overall: [X]/10
  [Justification: Briefly explain the rationale for the overall score, considering innovation, technical quality, experimental validation, etc.]

- Novelty: [X]/10
  [Justification: Assess the level of innovation and differences from existing work]

- Technical Quality: [X]/10
  [Justification: Assess method rationality, experimental design rigor, result credibility]

- Clarity: [X]/10
  [Justification: Assess writing quality, logical organization, presentation clarity]

- Confidence: [X]/5
  [Justification: Assess your confidence in the review conclusions, considering experimental validation sufficiency, result reproducibility, etc.]

**Important Requirements**:
1. Scores must be highly consistent with the review content, with no contradictions
2. Scores should be objective and fair, reflecting the paper's true quality
3. Justifications should be concise and directly correspond to the analysis in the review

Please ensure:
1. The review is constructive and professional
2. All content is based on the provided paper information, evaluation, and innovation analysis
3. The format exactly matches the structure above"""
    
    return prompt

